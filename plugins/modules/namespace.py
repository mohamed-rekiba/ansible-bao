#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao namespaces."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: namespace
short_description: Create or delete an OpenBao namespace.
description:
  - Manage namespaces in OpenBao. Namespaces provide isolated environments
    within a single instance, each with its own secrets engines, auth methods,
    policies, and identity store.
  - Supports nested namespaces (e.g. C(team-a/project-x)).
  - Idempotent -- skips creation if the namespace already exists.
version_added: "1.0.0"
options:
  path:
    description: >-
      Namespace path (without leading or trailing slashes).
      Use forward slashes for nested namespaces (e.g. C(team-a/project-x)).
    required: true
    type: str
  state:
    description: Whether the namespace should be present or absent.
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
    description: >-
      Parent namespace to operate in. When creating nested namespaces,
      set this to the parent and C(path) to the child name.
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
- name: Create a namespace
  mrekiba.bao.namespace:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: team-a
    state: present

- name: Create a nested namespace
  mrekiba.bao.namespace:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: team-a/project-x
    state: present

- name: Delete a namespace
  mrekiba.bao.namespace:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: old-team
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the namespace was modified.
  type: bool
  returned: always
path:
  description: The namespace path that was managed.
  type: str
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _get_namespace(client, path):
    """Read a namespace. Returns None if it doesn't exist."""
    try:
        resp = client.adapter.get(f"/v1/sys/namespaces/{path}")
        if isinstance(resp, dict):
            return resp.get("data", {})
        return resp.json().get("data", {})
    except hvac.exceptions.InvalidPath:
        return None
    except Exception as exc:
        if "404" in str(exc) or "unsupported path" in str(exc).lower():
            return None
        raise


def run_module():
    arg_spec = dict(
        path=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    path = module.params["path"].strip("/")
    state = module.params["state"]

    result = dict(changed=False, path=path)

    try:
        current = _get_namespace(client, path)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read namespace '{path}': {exc}")
        return

    if state == "present":
        if current is None:
            result["changed"] = True
            result["diff"] = dict(
                before="",
                after=f"Namespace '{path}'",
            )
            if not module.check_mode:
                try:
                    client.adapter.post(f"/v1/sys/namespaces/{path}")
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to create namespace '{path}': {exc}")
    else:
        if current is not None:
            result["changed"] = True
            result["diff"] = dict(
                before=f"Namespace '{path}'",
                after="",
            )
            if not module.check_mode:
                try:
                    client.adapter.delete(f"/v1/sys/namespaces/{path}")
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to delete namespace '{path}': {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
