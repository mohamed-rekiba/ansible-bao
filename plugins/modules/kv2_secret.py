#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao KV v2 secrets."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: kv2_secret
short_description: Write, read, or delete an OpenBao KV v2 secret.
description:
  - Manage secrets in an OpenBao KV version 2 secrets engine.
  - Idempotent -- compares secret data before creating a new version.
  - Secret data is never logged or included in module output.
version_added: "1.0.0"
options:
  mount:
    description: Mount path of the KV v2 engine (without trailing slash).
    required: true
    type: str
  path:
    description: Path within the KV engine (without the mount prefix).
    required: true
    type: str
  data:
    description: >-
      Secret data as a dict. Required when I(state=present).
      This parameter is marked no_log to prevent secret leakage.
    required: false
    type: dict
  state:
    description: Whether the secret should be present or absent.
    choices: [present, absent]
    default: present
    type: str
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
- name: Write a KV v2 secret
  mrekiba.bao.kv2_secret:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    mount: secret
    path: myapp/config
    data:
      db_host: postgres.default.svc
      db_port: "5432"
      db_password: "{{ lookup('env', 'DB_PASSWORD') }}"
    state: present

- name: Delete all versions of a secret
  mrekiba.bao.kv2_secret:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    mount: secret
    path: myapp/config
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the secret was modified.
  type: bool
  returned: always
path:
  description: The secret path that was managed.
  type: str
  returned: always
version:
  description: The secret version after the operation (when creating/updating).
  type: int
  returned: when state is present and changed
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _read_secret(client, mount: str, path: str) -> dict | None:
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
        data=dict(type="dict", required=False, default=None, no_log=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=arg_spec,
        required_if=[("state", "present", ["data"])],
        supports_check_mode=True,
    )
    client = bao_client(module)

    mount = module.params["mount"].strip("/")
    path = module.params["path"].strip("/")
    data = module.params["data"]
    state = module.params["state"]

    result = dict(changed=False, path=f"{mount}/{path}")

    try:
        current_data = _read_secret(client, mount, path)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read secret at '{mount}/{path}': {exc}")
        return

    if state == "present":
        if current_data is None or current_data != data:
            result["changed"] = True
            result["diff"] = dict(
                before="(secret exists)" if current_data else "(no secret)",
                after="(secret written)",
            )
            if not module.check_mode:
                try:
                    resp = client.secrets.kv.v2.create_or_update_secret(
                        path=path,
                        secret=data,
                        mount_point=mount,
                    )
                    version = resp.get("data", {}).get("version")
                    if version:
                        result["version"] = version
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to write secret: {exc}")
    else:
        if current_data is not None:
            result["changed"] = True
            result["diff"] = dict(
                before="(secret exists)",
                after="(deleted)",
            )
            if not module.check_mode:
                try:
                    client.secrets.kv.v2.delete_metadata_and_all_versions(
                        path=path,
                        mount_point=mount,
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to delete secret: {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
