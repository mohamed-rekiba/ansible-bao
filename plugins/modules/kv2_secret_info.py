#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao KV v2 secret information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: kv2_secret_info
short_description: Read metadata (and optionally data) for an OpenBao KV v2 secret.
description:
  - Return metadata about a secret stored in an OpenBao KV version 2 engine.
  - By default only metadata is returned (version, timestamps, custom_metadata).
    Set I(include_data=true) to also retrieve the secret data.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  mount:
    description: Mount path of the KV v2 engine (without trailing slash).
    required: true
    type: str
  path:
    description: Path within the KV engine (without the mount prefix).
    required: true
    type: str
  include_data:
    description: >-
      When C(true), the secret data is included in the return value.
      Defaults to C(false) so secret values are never exposed unless
      explicitly requested.
    required: false
    type: bool
    default: false
  bao_addr:
    description: OpenBao server URL.
    required: true
    type: str
  bao_token:
    description: OpenBao authentication token.
    required: true
    type: str
  bao_namespace:
    description: OpenBao namespace to operate in. All API calls will be scoped to this namespace.
    required: false
    type: str
  bao_ca_cert:
    description: Path to a CA certificate file for TLS verification.
    required: false
    type: path
  bao_skip_verify:
    description: Skip TLS certificate verification.
    required: false
    type: bool
    default: false
author:
  - Mohamed Rekiba (@mohamed-rekiba)
"""

EXAMPLES = r"""
- name: Check if a secret exists (metadata only)
  mrekiba.bao.kv2_secret_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    mount: secret
    path: myapp/config
  register: secret

- name: Show metadata
  ansible.builtin.debug:
    msg: "Version: {{ secret.metadata.current_version }}"
  when: secret.exists

- name: Read the secret data
  mrekiba.bao.kv2_secret_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    mount: secret
    path: myapp/config
    include_data: true
  register: secret_with_data
  no_log: true
"""

RETURN = r"""
exists:
  description: Whether the secret exists.
  type: bool
  returned: always
path:
  description: The full secret path (mount/path) that was queried.
  type: str
  returned: always
metadata:
  description: >-
    Secret metadata from the API (current_version, created_time, updated_time,
    custom_metadata, etc.). Empty dict when the secret does not exist.
  type: dict
  returned: always
data:
  description: >-
    The secret key-value data. Only returned when I(include_data=true) and the
    secret exists.
  type: dict
  returned: when include_data is true and secret exists
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _read_metadata(client, mount: str, path: str) -> dict | None:
    """Read secret metadata. Returns None if the secret doesn't exist."""
    try:
        resp = client.secrets.kv.v2.read_secret_metadata(
            path=path,
            mount_point=mount,
        )
        return resp.get("data", {})
    except hvac.exceptions.InvalidPath:
        return None
    except hvac.exceptions.VaultError as exc:
        if "404" in str(exc):
            return None
        raise


def _read_secret_data(client, mount: str, path: str) -> dict | None:
    """Read current secret data. Returns None if it doesn't exist."""
    try:
        resp = client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point=mount,
            raise_on_deleted_version=True,
        )
        return resp.get("data", {}).get("data")
    except hvac.exceptions.InvalidPath:
        return None
    except hvac.exceptions.VaultError as exc:
        if "404" in str(exc):
            return None
        raise


def run_module():
    arg_spec = dict(
        mount=dict(type="str", required=True),
        path=dict(type="str", required=True),
        include_data=dict(type="bool", required=False, default=False),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    mount = module.params["mount"].strip("/")
    path = module.params["path"].strip("/")
    include_data = module.params["include_data"]

    try:
        metadata = _read_metadata(client, mount, path)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read secret metadata at '{mount}/{path}': {exc}")
        return

    exists = metadata is not None

    result = dict(
        changed=False,
        exists=exists,
        path=f"{mount}/{path}",
        metadata=metadata or {},
    )

    if include_data and exists:
        try:
            secret_data = _read_secret_data(client, mount, path)
            result["data"] = secret_data or {}
        except hvac.exceptions.VaultError as exc:
            module.fail_json(msg=f"Failed to read secret data at '{mount}/{path}': {exc}")
            return

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
