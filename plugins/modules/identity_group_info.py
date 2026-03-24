#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao identity group information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: identity_group_info
short_description: Read an OpenBao identity group.
description:
  - Return information about an identity group in OpenBao, including its
    type, policies, members (internal) or aliases (external), and metadata.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  name:
    description: Name of the identity group.
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
- name: Check if a group exists
  mrekiba.bao.identity_group_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: platform-team
  register: grp

- name: Show group details
  ansible.builtin.debug:
    msg: "Group ID: {{ grp.group_id }}, Type: {{ grp.type }}"
  when: grp.exists
"""

RETURN = r"""
exists:
  description: Whether the group exists.
  type: bool
  returned: always
name:
  description: The group name that was queried.
  type: str
  returned: always
group_id:
  description: The group ID (empty string when the group does not exist).
  type: str
  returned: always
type:
  description: Group type (internal or external).
  type: str
  returned: when exists
policies:
  description: Policies attached to the group.
  type: list
  elements: str
  returned: when exists
member_entity_ids:
  description: Member entity IDs (internal groups only).
  type: list
  elements: str
  returned: when exists and type is internal
member_entity_names:
  description: Member entity names (internal groups only, if available).
  type: list
  elements: str
  returned: when exists and type is internal
aliases:
  description: Group aliases (external groups only).
  type: list
  elements: dict
  returned: when exists and type is external
metadata:
  description: Group metadata key-value pairs.
  type: dict
  returned: when exists
data:
  description: Raw group data from the API (empty dict when the group does not exist).
  type: dict
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _get_group(client, name):
    """Read a group by name. Returns None if it doesn't exist."""
    try:
        resp = client.adapter.get(f"/v1/identity/group/name/{name}")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except hvac.exceptions.InvalidPath:
        return None
    except Exception as exc:
        if "404" in str(exc):
            return None
        raise


def run_module():
    arg_spec = dict(
        name=dict(type="str", required=True),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    name = module.params["name"]

    try:
        current = _get_group(client, name)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read group '{name}': {exc}")
        return

    exists = current is not None
    group_type = current.get("type", "internal") if current else ""

    result = dict(
        changed=False,
        exists=exists,
        name=name,
        group_id=current.get("id", "") if current else "",
        data=current or {},
    )

    if current:
        result["type"] = group_type
        result["policies"] = current.get("policies") or []
        result["metadata"] = current.get("metadata") or {}

        if group_type == "internal":
            result["member_entity_ids"] = current.get("member_entity_ids") or []
            result["member_entity_names"] = current.get("member_entity_names") or []
        else:
            alias_data = current.get("alias") or {}
            if isinstance(alias_data, dict):
                result["aliases"] = [alias_data] if alias_data else []
            else:
                result["aliases"] = alias_data

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
