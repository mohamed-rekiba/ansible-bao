#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao authentication methods."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: auth_method
short_description: Enable, configure, or disable an OpenBao auth method.
description:
  - Enable or disable an authentication method in OpenBao.
  - Optionally apply configuration after enabling.
  - Idempotent -- skips enable if already present, applies config only when changed.
version_added: "1.0.0"
options:
  path:
    description: Mount path for the auth method (without trailing slash).
    required: true
    type: str
  type:
    description: Auth method type (e.g., approle, ldap, userpass, jwt).
    required: true
    type: str
  config:
    description: >-
      Auth method configuration dict (written to auth/:path/config).
      Only applied when state is present. Keys depend on the auth method type.
    required: false
    type: dict
    default: {}
  description:
    description: Human-readable description of the auth method.
    required: false
    type: str
    default: ""
  state:
    description: Whether the auth method should be present or absent.
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
- name: Enable AppRole auth method
  mrekiba.bao.auth_method:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    path: approle
    type: approle
    state: present

- name: Enable LDAP auth with config
  mrekiba.bao.auth_method:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: ldap
    type: ldap
    config:
      url: ldaps://ldap.example.com
      userdn: ou=Users,dc=example,dc=com
    state: present

- name: Disable an auth method
  mrekiba.bao.auth_method:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: old-method
    type: userpass
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the auth method was modified.
  type: bool
  returned: always
auth_path:
  description: The auth mount path that was managed.
  type: str
  returned: always
config_changed:
  description: Whether the configuration was updated.
  type: bool
  returned: when state is present
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _auth_key(path: str) -> str:
    return path.rstrip("/") + "/"


def _read_config(client, path: str) -> dict:
    """Read auth method config, return empty dict on 404."""
    try:
        resp = client.adapter.get(f"/v1/auth/{path}/config")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except Exception:
        return {}


def _config_differs(current: dict, desired: dict) -> bool:
    """Check if any desired key differs from current config."""
    if not desired:
        return False
    for key, value in desired.items():
        current_val = current.get(key)
        if isinstance(value, bool):
            if current_val != value:
                return True
        elif str(current_val) != str(value):
            return True
    return False


def run_module():
    arg_spec = dict(
        path=dict(type="str", required=True),
        type=dict(type="str", required=True),
        config=dict(type="dict", required=False, default={}),
        description=dict(type="str", required=False, default=""),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    path = module.params["path"].strip("/")
    auth_type = module.params["type"]
    config = module.params["config"]
    description = module.params["description"]
    state = module.params["state"]
    key = _auth_key(path)

    result = dict(changed=False, auth_path=path, config_changed=False)

    try:
        auth_methods = client.sys.list_auth_methods()
        existing = auth_methods.get("data", auth_methods).get(key)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to list auth methods: {exc}")
        return

    if state == "present":
        if not existing:
            result["changed"] = True
            result["diff"] = dict(
                before=f"No auth method at '{path}'",
                after=f"Auth method '{auth_type}' at '{path}'",
            )
            if not module.check_mode:
                try:
                    client.sys.enable_auth_method(
                        method_type=auth_type,
                        path=path,
                        description=description,
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to enable auth method: {exc}")

        elif existing.get("type") != auth_type:
            module.fail_json(
                msg=f"Auth method at '{path}' has type '{existing.get('type')}', "
                f"expected '{auth_type}'. Disable it first to change the type."
            )

        if config and state == "present":
            current_config = {} if module.check_mode and not existing else _read_config(client, path)
            if _config_differs(current_config, config):
                result["changed"] = True
                result["config_changed"] = True
                result["diff"] = dict(
                    before=str({k: current_config.get(k) for k in config}),
                    after=str(config),
                )
                if not module.check_mode:
                    try:
                        client.adapter.post(f"/v1/auth/{path}/config", json=config)
                    except hvac.exceptions.VaultError as exc:
                        module.fail_json(msg=f"Failed to configure auth method: {exc}")
    else:
        if existing:
            result["changed"] = True
            result["diff"] = dict(
                before=f"Auth method '{existing.get('type')}' at '{path}'",
                after=f"No auth method at '{path}'",
            )
            if not module.check_mode:
                try:
                    client.sys.disable_auth_method(path=path)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to disable auth method: {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
