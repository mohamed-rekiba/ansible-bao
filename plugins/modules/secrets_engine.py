#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage OpenBao secrets engines."""

from __future__ import annotations

DOCUMENTATION = r"""
---
module: secrets_engine
short_description: Enable or disable an OpenBao secrets engine.
description:
  - Enable, tune, or disable a secrets engine mount in OpenBao.
  - Idempotent -- skips enable if the mount already exists with the correct type.
version_added: "1.0.0"
options:
  path:
    description: Mount path for the secrets engine (without trailing slash).
    required: true
    type: str
  type:
    description: Secrets engine type (e.g., kv, transit, pki).
    required: true
    type: str
  options:
    description: Engine-specific options (e.g., C(version) for KV).
    required: false
    type: dict
    default: {}
  description:
    description: Human-readable description of the mount.
    required: false
    type: str
    default: ""
  state:
    description: Whether the engine should be present or absent.
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
- name: Enable KV v2 secrets engine
  mrekiba.bao.secrets_engine:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    bao_skip_verify: true
    path: secret
    type: kv
    options:
      version: "2"
    state: present

- name: Disable a secrets engine
  mrekiba.bao.secrets_engine:
    bao_addr: https://bao.example.com:8200
    bao_token: "{{ root_token }}"
    path: old-engine
    type: kv
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the engine mount was modified.
  type: bool
  returned: always
mount:
  description: The mount path that was managed.
  type: str
  returned: always
"""

import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.mrekiba.bao.plugins.module_utils._client import BAO_COMMON_ARGS, bao_client


def _mount_key(path: str) -> str:
    """Normalize path to the key format returned by /sys/mounts (trailing slash)."""
    return path.rstrip("/") + "/"


def run_module():
    arg_spec = dict(
        path=dict(type="str", required=True),
        type=dict(type="str", required=True),
        options=dict(type="dict", required=False, default={}),
        description=dict(type="str", required=False, default=""),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        **BAO_COMMON_ARGS,
    )

    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)
    client = bao_client(module)

    path = module.params["path"].strip("/")
    engine_type = module.params["type"]
    options = module.params["options"]
    description = module.params["description"]
    state = module.params["state"]
    key = _mount_key(path)

    result = dict(changed=False, mount=path)

    try:
        mounts = client.sys.list_mounted_secrets_engines()
        existing = mounts.get("data", mounts).get(key)
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to list secrets engines: {exc}")
        return

    if state == "present":
        if existing:
            if existing.get("type") != engine_type:
                module.fail_json(
                    msg=f"Mount '{path}' exists with type '{existing.get('type')}', "
                    f"expected '{engine_type}'. Disable it first to change the type."
                )
            result["changed"] = False
        else:
            result["changed"] = True
            result["diff"] = dict(
                before=f"No secrets engine at '{path}'",
                after=f"Secrets engine '{engine_type}' at '{path}'",
            )
            if not module.check_mode:
                try:
                    client.sys.enable_secrets_engine(
                        backend_type=engine_type,
                        path=path,
                        description=description,
                        options=options,
                    )
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to enable secrets engine: {exc}")
    else:
        if existing:
            result["changed"] = True
            result["diff"] = dict(
                before=f"Secrets engine '{existing.get('type')}' at '{path}'",
                after=f"No secrets engine at '{path}'",
            )
            if not module.check_mode:
                try:
                    client.sys.disable_secrets_engine(path=path)
                except hvac.exceptions.VaultError as exc:
                    module.fail_json(msg=f"Failed to disable secrets engine: {exc}")
        else:
            result["changed"] = False

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
