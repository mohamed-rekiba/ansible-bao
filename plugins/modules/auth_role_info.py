#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao auth method role information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: auth_role_info
short_description: Read a role on an OpenBao auth method.
description:
  - Return information about a role on an authentication method in OpenBao.
  - Works with any auth method that supports the C(/auth/:path/role/:name) API
    (e.g., approle, jwt, ldap, kubernetes).
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  auth_path:
    description: Mount path of the auth method (without trailing slash).
    required: true
    type: str
  name:
    description: Name of the role.
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
- name: Check if an AppRole role exists
  mrekiba.bao.auth_role_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    auth_path: approle
    name: my-app
  register: role

- name: Show role config
  ansible.builtin.debug:
    msg: "{{ role.data }}"
  when: role.exists
"""

RETURN = r"""
exists:
  description: Whether the role exists.
  type: bool
  returned: always
role:
  description: The role name that was queried.
  type: str
  returned: always
auth_path:
  description: The auth mount path.
  type: str
  returned: always
data:
  description: Role configuration from the API (empty dict when the role does not exist).
  type: dict
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _read_role(client, auth_path: str, name: str) -> dict | None:
    """Read a role from an auth method. Returns None if it doesn't exist."""
    try:
        resp = client.adapter.get(f"/v1/auth/{auth_path}/role/{name}")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except hvac.exceptions.InvalidPath:
        return None
    except Exception as exc:
        if "404" in str(exc) or "no entry found" in str(exc).lower():
            return None
        raise


def run_module():
    arg_spec = dict(
        auth_path=dict(type="str", required=True),
        name=dict(type="str", required=True),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    auth_path = module.params["auth_path"].strip("/")
    name = module.params["name"]

    try:
        current = _read_role(client, auth_path, name)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read role '{name}' on '{auth_path}': {exc}")
        return

    result = dict(
        changed=False,
        exists=current is not None,
        role=name,
        auth_path=auth_path,
        data=current or {},
    )
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
