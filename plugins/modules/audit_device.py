#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao audit devices."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: audit_device
short_description: Enable or disable an OpenBao audit device.
description:
  - Enable or disable an audit device in OpenBao.
  - Idempotent -- skips enable if the device already exists at the given path.
  - Supports file (including stdout/stderr), syslog, and socket audit types.
version_added: "1.2.0"
options:
  name:
    description: Name (path) for the audit device (e.g., C(file), C(stdout)).
    required: true
    type: str
  type:
    description: Audit device type (C(file), C(syslog), or C(socket)).
    required: true
    type: str
    choices: [file, syslog, socket]
  description:
    description: Human-readable description of the audit device.
    required: false
    type: str
    default: ""
  options:
    description:
      - Device-specific options.
      - For C(file) type, C(file_path) is required (e.g., C(/openbao/audit/audit.log) or C(/dev/stdout)).
      - For C(syslog) type, optional keys include C(facility) and C(tag).
      - For C(socket) type, C(address) is required.
    required: false
    type: dict
    default: {}
  local:
    description: If true, the audit device is only enabled on the local node (not replicated).
    required: false
    type: bool
    default: false
  state:
    description: Whether the audit device should be present or absent.
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
    description: OpenBao namespace to operate in.
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
- name: Enable file audit device
  mrekiba.bao.audit_device:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    name: file
    type: file
    options:
      file_path: /openbao/audit/audit.log

- name: Enable stdout audit device for log aggregation
  mrekiba.bao.audit_device:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    name: stdout
    type: file
    description: Audit logs to stdout for container log scraping
    options:
      file_path: /dev/stdout

- name: Disable an audit device
  mrekiba.bao.audit_device:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    name: old-audit
    type: file
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the audit device was modified.
  type: bool
  returned: always
name:
  description: The audit device name that was managed.
  type: str
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _device_key(name: str) -> str:
    """Normalize name to the key format returned by /sys/audit (trailing slash)."""
    return name.rstrip("/") + "/"


def run_module():
    arg_spec = dict(
        name=dict(type="str", required=True),
        type=dict(type="str", required=True, choices=["file", "syslog", "socket"]),
        description=dict(type="str", required=False, default=""),
        options=dict(type="dict", required=False, default={}),
        local=dict(type="bool", required=False, default=False),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    name = module.params["name"].strip("/")
    device_type = module.params["type"]
    description = module.params["description"]
    options = module.params["options"]
    local = module.params["local"]
    state = module.params["state"]
    key = _device_key(name)

    result = dict(changed=False, name=name)

    try:
        devices = client.sys.list_enabled_audit_devices()
        existing = devices.get("data", devices).get(key)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to list audit devices: {exc}")
        return

    if state == "present":
        if existing:
            result["changed"] = False
        else:
            result["changed"] = True
            result["diff"] = dict(
                before=f"No audit device at '{name}'",
                after=f"Audit device '{device_type}' at '{name}'",
            )
            if not module.check_mode:
                try:
                    client.sys.enable_audit_device(
                        device_type=device_type,
                        path=name,
                        description=description,
                        options=options,
                        local=local,
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to enable audit device: {exc}")
    else:
        if existing:
            result["changed"] = True
            result["diff"] = dict(
                before=f"Audit device '{existing.get('type')}' at '{name}'",
                after=f"No audit device at '{name}'",
            )
            if not module.check_mode:
                try:
                    client.sys.disable_audit_device(path=name)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to disable audit device: {exc}")
        else:
            result["changed"] = False

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
