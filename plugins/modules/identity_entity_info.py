#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao identity entity information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: identity_entity_info
short_description: Read an OpenBao identity entity.
description:
  - Return information about an identity entity in OpenBao, including its
    policies, metadata, and aliases.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  name:
    description: Name of the identity entity.
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
- name: Check if an entity exists
  mrekiba.bao.identity_entity_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: my-app
  register: entity

- name: Use the entity ID
  ansible.builtin.debug:
    msg: "Entity ID: {{ entity.entity_id }}"
  when: entity.exists
"""

RETURN = r"""
exists:
  description: Whether the entity exists.
  type: bool
  returned: always
name:
  description: The entity name that was queried.
  type: str
  returned: always
entity_id:
  description: The entity ID (empty string when the entity does not exist).
  type: str
  returned: always
policies:
  description: Policies attached to the entity.
  type: list
  elements: str
  returned: when exists
metadata:
  description: Entity metadata key-value pairs.
  type: dict
  returned: when exists
aliases:
  description: Entity aliases (each with name, mount_accessor, mount_type, etc.).
  type: list
  elements: dict
  returned: when exists
data:
  description: Raw entity data from the API (empty dict when the entity does not exist).
  type: dict
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _get_entity(client, name):
    """Read an entity by name. Returns None if it doesn't exist."""
    try:
        resp = client.adapter.get(f"/v1/identity/entity/name/{name}")
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
        current = _get_entity(client, name)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read entity '{name}': {exc}")
        return

    exists = current is not None

    result = dict(
        changed=False,
        exists=exists,
        name=name,
        entity_id=current.get("id", "") if current else "",
        data=current or {},
    )

    if current:
        result["policies"] = current.get("policies") or []
        result["metadata"] = current.get("metadata") or {}
        result["aliases"] = current.get("aliases") or []

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
