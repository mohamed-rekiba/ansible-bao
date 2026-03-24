#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Read OpenBao namespace information."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: namespace_info
short_description: Read an OpenBao namespace.
description:
  - Return information about a namespace in OpenBao.
  - Read-only -- never modifies state.
version_added: "1.4.0"
options:
  path:
    description: >-
      Namespace path (without leading or trailing slashes).
      Use forward slashes for nested namespaces (e.g. C(team-a/project-x)).
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
    description: >-
      Parent namespace to operate in. When reading nested namespaces,
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
- name: Check if a namespace exists
  mrekiba.bao.namespace_info:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: team-a
  register: ns

- name: Use the result
  ansible.builtin.debug:
    msg: "Namespace exists: {{ ns.exists }}"

- name: Conditional task based on namespace existence
  ansible.builtin.debug:
    msg: "Namespace team-a is present"
  when: ns.exists
"""

RETURN = r"""
exists:
  description: Whether the namespace exists.
  type: bool
  returned: always
path:
  description: The namespace path that was queried.
  type: str
  returned: always
data:
  description: Raw namespace data from the API (empty dict when the namespace does not exist).
  type: dict
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
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    path = module.params["path"].strip("/")

    try:
        current = _get_namespace(client, path)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to read namespace '{path}': {exc}")
        return

    result = dict(
        changed=False,
        exists=current is not None,
        path=path,
        data=current or {},
    )
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
