#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao auth method roles."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: auth_role
short_description: Create, update, or delete a role on an OpenBao auth method.
description:
  - Manage roles on authentication methods in OpenBao.
  - Works with any auth method that supports the C(/auth/:path/role/:name) API
    (e.g., approle, jwt, ldap, kubernetes).
  - Idempotent -- compares role configuration before applying changes.
version_added: "1.0.0"
options:
  auth_path:
    description: Mount path of the auth method (without trailing slash).
    required: true
    type: str
  name:
    description: Name of the role.
    required: true
    type: str
  config:
    description: >-
      Role configuration dict. Keys depend on the auth method type.
      For AppRole: C(token_policies), C(token_ttl), etc.
      For JWT: C(bound_audiences), C(user_claim), C(role_type), etc.
    required: false
    type: dict
    default: {}
  state:
    description: Whether the role should be present or absent.
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
- name: Create an AppRole auth role
  mrekiba.bao.auth_role:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    auth_path: approle
    name: my-app
    config:
      token_policies: app-read
      token_ttl: 1h
    state: present

- name: Delete a role
  mrekiba.bao.auth_role:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    auth_path: approle
    name: old-role
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the role was modified.
  type: bool
  returned: always
role:
  description: The role name that was managed.
  type: str
  returned: always
auth_path:
  description: The auth mount path.
  type: str
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


def _config_differs(current: dict, desired: dict) -> bool:
    """Check if any desired key differs from current role config."""
    if not desired:
        return False
    for key, value in desired.items():
        current_val = current.get(key)
        if current_val is None:
            return True
        if isinstance(value, list) and isinstance(current_val, list):
            if sorted(str(v) for v in value) != sorted(str(v) for v in current_val):
                return True
        elif isinstance(value, bool):
            if current_val != value:
                return True
        elif str(current_val) != str(value):
            return True
    return False


def run_module():
    arg_spec = dict(
        auth_path=dict(type="str", required=True),
        name=dict(type="str", required=True),
        config=dict(type="dict", required=False, default={}),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    auth_path = module.params["auth_path"].strip("/")
    name = module.params["name"]
    config = module.params["config"]
    state = module.params["state"]

    result = dict(changed=False, role=name, auth_path=auth_path)

    try:
        current = _read_role(client, auth_path, name)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read role '{name}' on '{auth_path}': {exc}")
        return

    if state == "present":
        if current is None:
            result["changed"] = True
            result["diff"] = dict(before="", after=str(config))
            if not module.check_mode:
                try:
                    client.adapter.post(f"/v1/auth/{auth_path}/role/{name}", json=config)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to create role '{name}': {exc}")
        elif _config_differs(current, config):
            result["changed"] = True
            result["diff"] = dict(
                before=str({k: current.get(k) for k in config}),
                after=str(config),
            )
            if not module.check_mode:
                try:
                    client.adapter.post(f"/v1/auth/{auth_path}/role/{name}", json=config)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to update role '{name}': {exc}")
    else:
        if current is not None:
            result["changed"] = True
            result["diff"] = dict(before=str(current), after="")
            if not module.check_mode:
                try:
                    client.adapter.delete(f"/v1/auth/{auth_path}/role/{name}")
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to delete role '{name}': {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
