#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao ACL policies."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: policy
short_description: Create, update, or delete an OpenBao ACL policy.
description:
  - Manage ACL policies in OpenBao.
  - Supports inline HCL content or Jinja2-rendered templates via C(lookup('template', ...)).
  - Idempotent -- compares normalized policy content before applying changes.
version_added: "1.0.0"
options:
  name:
    description: Name of the ACL policy.
    required: true
    type: str
  content:
    description: >-
      HCL policy content. Supports Jinja2 templates when passed through
      C(lookup('template', ...)).
      Required when I(state=present).
    required: false
    type: str
  state:
    description: Whether the policy should be present or absent.
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
- name: Create read policy from template
  mrekiba.bao.policy:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    name: app-read
    content: "{{ lookup('template', 'policies/app-read.hcl.j2') }}"
    state: present

- name: Create policy with inline content
  mrekiba.bao.policy:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: admin
    content: |
      path "sys/*" {
        capabilities = ["create", "read", "update", "delete", "list", "sudo"]
      }
    state: present

- name: Delete a policy
  mrekiba.bao.policy:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: old-policy
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the policy was modified.
  type: bool
  returned: always
name:
  description: The policy name that was managed.
  type: str
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _normalize_hcl(text: str) -> str:
    """Strip leading/trailing whitespace from each line and collapse blank lines."""
    lines = [line.strip() for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line)


def run_module():
    arg_spec = dict(
        name=dict(type="str", required=True),
        content=dict(type="str", required=False, default=None),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=arg_spec,
        required_if=[("state", "present", ["content"])],
        supports_check_mode=True,
    )
    client = bao_client(module)

    name = module.params["name"]
    content = module.params["content"]
    state = module.params["state"]

    result = dict(changed=False, name=name)

    try:
        current_policy = client.sys.read_acl_policy(name=name)
        if isinstance(current_policy, dict):
            current_rules = current_policy.get("data", current_policy).get("rules", "")
        else:
            current_rules = current_policy or ""
    except hvac.exceptions.InvalidPath:
        current_rules = None
    except hvac.exceptions.VaultError as exc:
        if "no policy named" in str(exc).lower() or "404" in str(exc):
            current_rules = None
        else:
            module.fail_json(msg=f"Failed to read policy '{name}': {exc}")
            return

    if state == "present":
        desired_norm = _normalize_hcl(content)

        if current_rules is None:
            result["changed"] = True
            result["diff"] = dict(before="", after=content)
        else:
            current_norm = _normalize_hcl(current_rules)
            if current_norm != desired_norm:
                result["changed"] = True
                result["diff"] = dict(before=current_rules, after=content)

        if result["changed"] and not module.check_mode:
            try:
                client.sys.create_or_update_acl_policy(name=name, policy=content)
            except hvac.exceptions.VaultError as exc:
                module.fail_json(msg=f"Failed to write policy '{name}': {exc}")
    else:
        if current_rules is not None:
            result["changed"] = True
            result["diff"] = dict(before=current_rules, after="")
            if not module.check_mode:
                try:
                    client.sys.delete_acl_policy(name=name)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to delete policy '{name}': {exc}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
