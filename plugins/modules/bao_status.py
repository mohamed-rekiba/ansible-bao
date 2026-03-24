#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Check OpenBao health and seal status."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: bao_status
short_description: Check OpenBao health, seal, and init status.
description:
  - Query the C(/v1/sys/health) endpoint and return the server's current
    state -- initialized, sealed, standby, version, and cluster info.
  - Unlike other modules in this collection, C(bao_status) does NOT fail
    when the server is sealed or uninitialized. That's the whole point --
    use it to wait for readiness before running other modules.
  - Does not require C(bao_token) -- the health endpoint is unauthenticated.
  - Read-only -- never modifies state.
version_added: "1.5.0"
options:
  bao_addr:
    description: OpenBao server URL.
    required: true
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
- name: Wait for OpenBao to be reachable and unsealed
  mrekiba.bao.bao_status:
    bao_addr: https://bao.example.com:8200
    bao_skip_verify: true
  register: bao
  until: bao.reachable and not bao.sealed
  retries: 30
  delay: 5

- name: Check health (don't fail if sealed)
  mrekiba.bao.bao_status:
    bao_addr: https://bao.example.com:8200
  register: bao

- name: Show status
  ansible.builtin.debug:
    msg: >-
      Reachable: {{ bao.reachable }},
      Initialized: {{ bao.initialized }},
      Sealed: {{ bao.sealed }},
      Version: {{ bao.version }}

- name: Wait for init before bootstrapping
  mrekiba.bao.bao_status:
    bao_addr: https://bao.example.com:8200
  register: bao
  until: bao.reachable and bao.initialized
  retries: 30
  delay: 5
"""

RETURN = r"""
reachable:
  description: Whether the server responded to the health request.
  type: bool
  returned: always
initialized:
  description: Whether the server is initialized.
  type: bool
  returned: when reachable
sealed:
  description: Whether the server is sealed.
  type: bool
  returned: when reachable
standby:
  description: Whether the server is a standby node.
  type: bool
  returned: when reachable
version:
  description: OpenBao server version string.
  type: str
  returned: when reachable
cluster_name:
  description: Name of the cluster.
  type: str
  returned: when reachable
cluster_id:
  description: ID of the cluster.
  type: str
  returned: when reachable
data:
  description: Raw health response from the API (empty dict when unreachable).
  type: dict
  returned: always
"""

import traceback

try:
    import hvac
    import hvac.exceptions

    HAS_HVAC = True
    HVAC_IMPORT_ERROR = None
except ImportError:
    HAS_HVAC = False
    HVAC_IMPORT_ERROR = traceback.format_exc()

from ansible.module_utils.basic import AnsibleModule


def run_module():
    arg_spec = dict(
        bao_addr=dict(type="str", required=True),
        bao_ca_cert=dict(type="path", required=False, default=None),
        bao_skip_verify=dict(type="bool", required=False, default=False),
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)

    if not HAS_HVAC:
        module.fail_json(
            msg="The 'hvac' Python library is required. Install it with: pip install hvac",
            exception=HVAC_IMPORT_ERROR,
        )

    params = module.params
    verify = params["bao_ca_cert"] if params["bao_ca_cert"] else (not params["bao_skip_verify"])

    client = hvac.Client(url=params["bao_addr"], verify=verify)

    result = dict(changed=False, reachable=False, data={})

    try:
        health = client.sys.read_health_status(method="GET")

        if isinstance(health, dict):
            data = health
        else:
            data = health.json()

        result["reachable"] = True
        result["initialized"] = data.get("initialized", False)
        result["sealed"] = data.get("sealed", True)
        result["standby"] = data.get("standby", False)
        result["version"] = data.get("version", "")
        result["cluster_name"] = data.get("cluster_name", "")
        result["cluster_id"] = data.get("cluster_id", "")
        result["data"] = data

    except Exception:
        result["reachable"] = False

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
