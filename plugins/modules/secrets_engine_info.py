#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao secrets engine information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: secrets_engine_info
short_description: Read an OpenBao secrets engine mount.
description:
  - Return information about a secrets engine mount in OpenBao.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  path:
    description: Mount path of the secrets engine (without trailing slash).
    required: true
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
- name: Check if a secrets engine is mounted
  mrekiba.bao.secrets_engine_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: secret
  register: engine

- name: Show engine details
  ansible.builtin.debug:
    msg: "Type: {{ engine.type }}, Accessor: {{ engine.accessor }}"
  when: engine.exists
"""

RETURN = r"""
exists:
  description: Whether the secrets engine mount exists.
  type: bool
  returned: always
path:
  description: The mount path that was queried.
  type: str
  returned: always
type:
  description: The secrets engine type (e.g. kv, transit, pki).
  type: str
  returned: when exists
accessor:
  description: The mount accessor.
  type: str
  returned: when exists
description:
  description: Human-readable description of the mount.
  type: str
  returned: when exists
options:
  description: Engine-specific options.
  type: dict
  returned: when exists
data:
  description: Raw mount data from the API (empty dict when the mount does not exist).
  type: dict
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def run_module():
    arg_spec = dict(
        path=dict(type="str", required=True),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    path = module.params["path"].strip("/")
    key = path.rstrip("/") + "/"

    try:
        mounts = client.sys.list_mounted_secrets_engines()
        existing = mounts.get("data", mounts).get(key)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to list secrets engines: {exc}")
        return

    result = dict(
        changed=False,
        exists=existing is not None,
        path=path,
        data=existing or {},
    )

    if existing:
        result["type"] = existing.get("type", "")
        result["accessor"] = existing.get("accessor", "")
        result["description"] = existing.get("description", "")
        result["options"] = existing.get("options") or {}

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
