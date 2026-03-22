#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao identity entities and their aliases."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: identity_entity
short_description: Manage an OpenBao identity entity and its aliases.
description:
  - Create, update, or delete an identity entity in OpenBao.
  - Optionally manage entity aliases inline -- each alias maps the entity
    to a login on a specific auth method.
version_added: "1.0.0"
options:
  name:
    description: Name of the identity entity.
    required: true
    type: str
  policies:
    description: List of policies to attach directly to the entity.
    required: false
    type: list
    elements: str
    default: []
  metadata:
    description: Arbitrary key-value metadata for the entity.
    required: false
    type: dict
    default: {}
  aliases:
    description: >-
      List of aliases to attach to this entity. Each alias is a dict with
      C(name) (the auth method login name) and C(auth_path) (mount path of
      the auth method, e.g. C(approle), C(ldap)). The module resolves the
      mount accessor automatically.
    required: false
    type: list
    elements: dict
    default: []
  state:
    description: Whether the entity should be present or absent.
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
- name: Create an entity with an AppRole alias
  mrekiba.bao.identity_entity:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: my-app
    policies:
      - app-read
    metadata:
      team: platform
    aliases:
      - name: my-app
        auth_path: approle
    state: present

- name: Create an entity with multiple aliases
  mrekiba.bao.identity_entity:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: jane
    policies:
      - dev-read
    aliases:
      - name: jane@example.com
        auth_path: ldap
      - name: jane-token
        auth_path: userpass

- name: Delete an entity
  mrekiba.bao.identity_entity:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: old-entity
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the entity was modified.
  type: bool
  returned: always
entity_id:
  description: The ID of the entity.
  type: str
  returned: when state is present
name:
  description: The entity name.
  type: str
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


def _get_mount_accessor(client, auth_path):
    """Look up the mount accessor for an auth method path."""
    auth_methods = client.sys.list_auth_methods()
    data = auth_methods.get("data", auth_methods)
    key = auth_path.strip("/") + "/"
    mount = data.get(key)
    if not mount:
        return None
    return mount.get("accessor")


def _get_entity_aliases(client, entity_id):
    """Get all aliases for an entity, keyed by mount_accessor."""
    entity = _get_entity_by_id(client, entity_id)
    if not entity:
        return {}
    aliases = entity.get("aliases") or []
    return {a["mount_accessor"]: a for a in aliases}


def _get_entity_by_id(client, entity_id):
    """Read an entity by ID."""
    try:
        resp = client.adapter.get(f"/v1/identity/entity/id/{entity_id}")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except Exception:
        return None


def _lists_equal(a, b):
    return sorted(a or []) == sorted(b or [])


def _entity_differs(current, policies, metadata):
    if not _lists_equal(current.get("policies"), policies):
        return True
    current_meta = current.get("metadata") or {}
    if current_meta != (metadata or {}):
        return True
    return False


def run_module():
    arg_spec = dict(
        name=dict(type="str", required=True),
        policies=dict(type="list", elements="str", required=False, default=[]),
        metadata=dict(type="dict", required=False, default={}),
        aliases=dict(type="list", elements="dict", required=False, default=[]),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    name = module.params["name"]
    policies = module.params["policies"]
    metadata = module.params["metadata"]
    desired_aliases = module.params["aliases"]
    state = module.params["state"]

    result = dict(changed=False, name=name)

    try:
        current = _get_entity(client, name)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read entity '{name}': {exc}")
        return

    if state == "absent":
        if current:
            result["changed"] = True
            result["diff"] = dict(before=f"Entity '{name}' exists", after="")
            if not module.check_mode:
                try:
                    client.adapter.delete(f"/v1/identity/entity/name/{name}")
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to delete entity '{name}': {exc}")
        module.exit_json(**result)
        return

    # state == present
    if current is None:
        result["changed"] = True
        result["diff"] = dict(before="", after=f"Entity '{name}' with {len(desired_aliases)} alias(es)")
        if not module.check_mode:
            try:
                resp = client.adapter.post(
                    "/v1/identity/entity",
                    json=dict(
                        name=name,
                        policies=policies,
                        metadata=metadata,
                    ),
                )
                if isinstance(resp, dict):
                    entity_id = resp.get("data", {}).get("id", "")
                else:
                    entity_id = resp.json().get("data", {}).get("id", "")
                result["entity_id"] = entity_id
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to create entity '{name}': {exc}")
                return
        else:
            module.exit_json(**result)
            return
    else:
        entity_id = current.get("id", "")
        result["entity_id"] = entity_id

        if _entity_differs(current, policies, metadata):
            result["changed"] = True
            result["diff"] = dict(
                before=str({"policies": current.get("policies"), "metadata": current.get("metadata")}),
                after=str({"policies": policies, "metadata": metadata}),
            )
            if not module.check_mode:
                try:
                    client.adapter.post(
                        f"/v1/identity/entity/name/{name}",
                        json=dict(
                            policies=policies,
                            metadata=metadata,
                        ),
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to update entity '{name}': {exc}")

    # Manage aliases
    if module.check_mode:
        if desired_aliases:
            result["changed"] = True
        module.exit_json(**result)
        return

    entity_id = result.get("entity_id", "")
    if not entity_id:
        module.exit_json(**result)
        return

    current_aliases = _get_entity_aliases(client, entity_id)

    desired_by_accessor = {}
    for alias in desired_aliases:
        alias_name = alias.get("name")
        auth_path = alias.get("auth_path", "").strip("/")
        if not alias_name or not auth_path:
            module.fail_json(msg="Each alias needs both 'name' and 'auth_path'.")
            return
        accessor = _get_mount_accessor(client, auth_path)
        if not accessor:
            module.fail_json(msg=f"Auth method at '{auth_path}' not found. Enable it first.")
            return
        desired_by_accessor[accessor] = dict(name=alias_name, mount_accessor=accessor)

    # Create or update aliases
    for accessor, desired in desired_by_accessor.items():
        existing = current_aliases.get(accessor)
        if existing:
            if existing.get("name") != desired["name"]:
                result["changed"] = True
                try:
                    client.adapter.post(
                        f"/v1/identity/entity-alias/id/{existing['id']}",
                        json=dict(
                            name=desired["name"],
                            mount_accessor=accessor,
                            canonical_id=entity_id,
                        ),
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to update alias '{desired['name']}': {exc}")
        else:
            result["changed"] = True
            try:
                client.adapter.post(
                    "/v1/identity/entity-alias",
                    json=dict(
                        name=desired["name"],
                        mount_accessor=accessor,
                        canonical_id=entity_id,
                    ),
                )
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to create alias '{desired['name']}': {exc}")

    # Remove aliases not in desired list
    for accessor, existing in current_aliases.items():
        if accessor not in desired_by_accessor:
            result["changed"] = True
            try:
                client.adapter.delete(f"/v1/identity/entity-alias/id/{existing['id']}")
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to delete alias '{existing.get('name')}': {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
