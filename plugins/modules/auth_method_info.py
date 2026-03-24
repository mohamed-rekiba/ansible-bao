#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao auth method information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: auth_method_info
short_description: Read an OpenBao auth method.
description:
  - Return information about an authentication method in OpenBao,
    including its configuration, tune settings, and the list of roles
    configured on it.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  path:
    description: Mount path of the auth method (without trailing slash).
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
- name: Check if an auth method is enabled
  mrekiba.bao.auth_method_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: approle
  register: auth

- name: Show auth method details
  ansible.builtin.debug:
    msg: "Type: {{ auth.type }}, Accessor: {{ auth.accessor }}, Roles: {{ auth.roles }}"
  when: auth.exists
"""

RETURN = r"""
exists:
  description: Whether the auth method mount exists.
  type: bool
  returned: always
auth_path:
  description: The auth mount path that was queried.
  type: str
  returned: always
type:
  description: The auth method type (e.g. approle, ldap, oidc).
  type: str
  returned: when exists
accessor:
  description: The mount accessor.
  type: str
  returned: when exists
description:
  description: Human-readable description of the auth method.
  type: str
  returned: when exists
config:
  description: Auth method configuration from C(/auth/:path/config).
  type: dict
  returned: when exists
tune:
  description: Mount tune settings from C(/sys/auth/:path/tune).
  type: dict
  returned: when exists
roles:
  description: List of role names configured on this auth method.
  type: list
  elements: str
  returned: when exists
data:
  description: Raw mount data from the API (empty dict when the mount does not exist).
  type: dict
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _read_config(client, path: str) -> dict:
    """Read auth method config, return empty dict on 404."""
    try:
        resp = client.adapter.get(f"/v1/auth/{path}/config")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except Exception:
        return {}


def _read_tune(client, path: str) -> dict:
    """Read auth method tune settings, return empty dict on error."""
    try:
        resp = client.adapter.get(f"/v1/sys/auth/{path}/tune")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except Exception:
        return {}


def _list_roles(client, path: str) -> list[str]:
    """List role names on an auth method. Returns empty list when none exist."""
    try:
        resp = client.adapter.list(f"/v1/auth/{path}/role")
        if isinstance(resp, dict):
            return resp.get("data", {}).get("keys", [])
        return resp.json().get("data", {}).get("keys", [])
    except Exception:
        return []


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
        auth_methods = client.sys.list_auth_methods()
        existing = auth_methods.get("data", auth_methods).get(key)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to list auth methods: {exc}")
        return

    result = dict(
        changed=False,
        exists=existing is not None,
        auth_path=path,
        data=existing or {},
    )

    if existing:
        result["type"] = existing.get("type", "")
        result["accessor"] = existing.get("accessor", "")
        result["description"] = existing.get("description", "")
        result["config"] = _read_config(client, path)
        result["tune"] = _read_tune(client, path)
        result["roles"] = _list_roles(client, path)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
