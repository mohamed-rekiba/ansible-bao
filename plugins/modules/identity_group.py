#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao identity groups and their aliases."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: identity_group
short_description: Manage an OpenBao identity group and its aliases.
description:
  - Create, update, or delete an identity group in OpenBao.
  - Supports both internal groups (members are entities) and external groups
    (mapped to auth method groups via aliases).
  - Aliases are managed inline -- for external groups, each alias maps to
    a group name on a specific auth method.
version_added: "1.0.0"
options:
  name:
    description: Name of the identity group.
    required: true
    type: str
  type:
    description: >-
      Group type. C(internal) groups have member entities managed by OpenBao.
      C(external) groups are mapped to auth method groups via aliases.
    choices: [internal, external]
    default: internal
    type: str
  policies:
    description: List of policies to attach to the group.
    required: false
    type: list
    elements: str
    default: []
  member_entity_names:
    description: >-
      Entity names to include as members. Only valid for internal groups.
      Ignored for external groups.
    required: false
    type: list
    elements: str
    default: []
  metadata:
    description: Arbitrary key-value metadata for the group.
    required: false
    type: dict
    default: {}
  aliases:
    description: >-
      List of aliases for this group. Only valid for external groups.
      Each alias is a dict with C(name) (the auth method group name) and
      C(auth_path) (mount path of the auth method). The module resolves
      the mount accessor automatically.
    required: false
    type: list
    elements: dict
    default: []
  state:
    description: Whether the group should be present or absent.
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
- name: Create an internal group with member entities
  mrekiba.bao.identity_group:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: platform-team
    type: internal
    policies:
      - admin-read
    member_entity_names:
      - my-app
      - my-service
    metadata:
      team: platform
    state: present

- name: Create an external group mapped to LDAP
  mrekiba.bao.identity_group:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: ldap-admins
    type: external
    policies:
      - admin-policy
    aliases:
      - name: admins
        auth_path: ldap
    state: present

- name: Delete a group
  mrekiba.bao.identity_group:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: old-group
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the group was modified.
  type: bool
  returned: always
group_id:
  description: The ID of the group.
  type: str
  returned: when state is present
name:
  description: The group name.
  type: str
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


def _get_mount_accessor(client, auth_path):
    """Look up the mount accessor for an auth method path."""
    auth_methods = client.sys.list_auth_methods()
    data = auth_methods.get("data", auth_methods)
    key = auth_path.strip("/") + "/"
    mount = data.get(key)
    if not mount:
        return None
    return mount.get("accessor")


def _lists_equal(a, b):
    return sorted(a or []) == sorted(b or [])


def _group_differs(current, policies, metadata, member_entity_names, group_type):
    if not _lists_equal(current.get("policies"), policies):
        return True
    current_meta = current.get("metadata") or {}
    if current_meta != (metadata or {}):
        return True
    if group_type == "internal":
        if not _lists_equal(current.get("member_entity_ids"), None):
            # Can't compare by ID easily; compare by name if available
            pass
    return False


def run_module():
    arg_spec = dict(
        name=dict(type="str", required=True),
        type=dict(type="str", choices=["internal", "external"], default="internal"),
        policies=dict(type="list", elements="str", required=False, default=[]),
        member_entity_names=dict(type="list", elements="str", required=False, default=[]),
        metadata=dict(type="dict", required=False, default={}),
        aliases=dict(type="list", elements="dict", required=False, default=[]),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    name = module.params["name"]
    group_type = module.params["type"]
    policies = module.params["policies"]
    member_entity_names = module.params["member_entity_names"]
    metadata = module.params["metadata"]
    desired_aliases = module.params["aliases"]
    state = module.params["state"]

    if group_type == "external" and member_entity_names:
        module.fail_json(msg="External groups can't have member_entity_names. Use aliases instead.")
    if group_type == "internal" and desired_aliases:
        module.fail_json(msg="Internal groups can't have aliases. Use member_entity_names instead.")

    result = dict(changed=False, name=name)

    try:
        current = _get_group(client, name)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read group '{name}': {exc}")
        return

    if state == "absent":
        if current:
            result["changed"] = True
            result["diff"] = dict(before=f"Group '{name}' exists", after="")
            if not module.check_mode:
                try:
                    client.adapter.delete(f"/v1/identity/group/name/{name}")
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to delete group '{name}': {exc}")
        module.exit_json(**result)
        return

    # state == present
    group_payload = dict(
        name=name,
        type=group_type,
        policies=policies,
        metadata=metadata,
    )
    if group_type == "internal":
        group_payload["member_entity_names"] = member_entity_names

    if current is None:
        result["changed"] = True
        result["diff"] = dict(before="", after=f"Group '{name}' ({group_type})")
        if not module.check_mode:
            try:
                resp = client.adapter.post("/v1/identity/group", json=group_payload)
                if isinstance(resp, dict):
                    group_id = resp.get("data", {}).get("id", "")
                else:
                    group_id = resp.json().get("data", {}).get("id", "")
                result["group_id"] = group_id
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to create group '{name}': {exc}")
                return
        else:
            module.exit_json(**result)
            return
    else:
        group_id = current.get("id", "")
        result["group_id"] = group_id

        current_type = current.get("type", "internal")
        if current_type != group_type:
            module.fail_json(
                msg=f"Group '{name}' exists as '{current_type}', can't change to '{group_type}'. Delete it first."
            )

        needs_update = False
        if not _lists_equal(current.get("policies"), policies):
            needs_update = True
        if (current.get("metadata") or {}) != (metadata or {}):
            needs_update = True
        if group_type == "internal":
            if not _lists_equal(current.get("member_entity_names"), member_entity_names):
                needs_update = True

        if needs_update:
            result["changed"] = True
            result["diff"] = dict(
                before=str(
                    {
                        "policies": current.get("policies"),
                        "metadata": current.get("metadata"),
                        "member_entity_names": current.get("member_entity_names"),
                    }
                ),
                after=str(
                    {
                        "policies": policies,
                        "metadata": metadata,
                        "member_entity_names": member_entity_names if group_type == "internal" else None,
                    }
                ),
            )
            if not module.check_mode:
                try:
                    group_payload["id"] = group_id
                    client.adapter.post("/v1/identity/group", json=group_payload)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to update group '{name}': {exc}")

    # Manage aliases (external groups only)
    if group_type != "external" or not desired_aliases:
        module.exit_json(**result)
        return

    if module.check_mode:
        result["changed"] = True
        module.exit_json(**result)
        return

    group_id = result.get("group_id", "")
    if not group_id:
        module.exit_json(**result)
        return

    # Re-read group to get current aliases
    try:
        refreshed = _get_group(client, name)
    except hvac.exceptions.VaultError:
        refreshed = current

    current_aliases_list = refreshed.get("alias") if refreshed else {}
    current_aliases = {}
    if current_aliases_list:
        if isinstance(current_aliases_list, dict):
            current_aliases_list = [current_aliases_list]
        current_aliases = {a["mount_accessor"]: a for a in current_aliases_list}

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

    for accessor, desired in desired_by_accessor.items():
        existing = current_aliases.get(accessor)
        if existing:
            if existing.get("name") != desired["name"]:
                result["changed"] = True
                try:
                    client.adapter.post(
                        f"/v1/identity/group-alias/id/{existing['id']}",
                        json=dict(
                            name=desired["name"],
                            mount_accessor=accessor,
                            canonical_id=group_id,
                        ),
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to update group alias '{desired['name']}': {exc}")
        else:
            result["changed"] = True
            try:
                client.adapter.post(
                    "/v1/identity/group-alias",
                    json=dict(
                        name=desired["name"],
                        mount_accessor=accessor,
                        canonical_id=group_id,
                    ),
                )
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to create group alias '{desired['name']}': {exc}")

    for accessor, existing in current_aliases.items():
        if accessor not in desired_by_accessor:
            result["changed"] = True
            try:
                client.adapter.delete(f"/v1/identity/group-alias/id/{existing['id']}")
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to delete group alias '{existing.get('name')}': {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
