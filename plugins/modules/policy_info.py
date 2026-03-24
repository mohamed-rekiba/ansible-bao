#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao ACL policy information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: policy_info
short_description: Read an OpenBao ACL policy.
description:
  - Return information about an ACL policy in OpenBao, including its HCL content.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  name:
    description: Name of the ACL policy.
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
- name: Check if a policy exists
  mrekiba.bao.policy_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: app-read
  register: pol

- name: Show policy content
  ansible.builtin.debug:
    msg: "{{ pol.rules }}"
  when: pol.exists
"""

RETURN = r"""
exists:
  description: Whether the policy exists.
  type: bool
  returned: always
name:
  description: The policy name that was queried.
  type: str
  returned: always
rules:
  description: The policy HCL content (empty string when the policy does not exist).
  type: str
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def run_module():
    arg_spec = dict(
        name=dict(type="str", required=True),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    name = module.params["name"]

    try:
        current_policy = client.sys.read_acl_policy(name=name)
        if isinstance(current_policy, dict):
            rules = current_policy.get("data", current_policy).get("rules", "")
        else:
            rules = current_policy or ""
        exists = True
    except hvac.exceptions.InvalidPath:
        rules = ""
        exists = False
    except hvac.exceptions.VaultError as exc:
        if "no policy named" in str(exc).lower() or "404" in str(exc):
            rules = ""
            exists = False
        else:
            module.fail_json(msg=f"Failed to read policy '{name}': {exc}")
            return

    result = dict(
        changed=False,
        exists=exists,
        name=name,
        rules=rules,
    )
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
