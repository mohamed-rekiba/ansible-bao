"""Shared hvac client factory for all mrekiba.bao modules."""

from __future__ import annotations

import traceback

try:
    import hvac
    import hvac.exceptions

    HAS_HVAC = True
    HVAC_IMPORT_ERROR = None
except ImportError:
    HAS_HVAC = False
    HVAC_IMPORT_ERROR = traceback.format_exc()

BAO_COMMON_ARGS = dict(
    bao_addr=dict(type="str", required=True),
    bao_token=dict(type="str", required=True, no_log=True),
    bao_namespace=dict(type="str", required=False, default=None),
    bao_ca_cert=dict(type="path", required=False, default=None),
    bao_skip_verify=dict(type="bool", required=False, default=False),
)


def bao_client(module):
    """Create and return an authenticated hvac.Client.

    Calls module.fail_json if hvac is missing or the connection fails.
    """
    if not HAS_HVAC:
        module.fail_json(
            msg="The 'hvac' Python library is required. Install it with: pip install hvac",
            exception=HVAC_IMPORT_ERROR,
        )

    params = module.params
    verify = params["bao_ca_cert"] if params["bao_ca_cert"] else (not params["bao_skip_verify"])

    client = hvac.Client(
        url=params["bao_addr"],
        token=params["bao_token"],
        verify=verify,
        namespace=params["bao_namespace"],
    )

    try:
        health = client.sys.read_health_status(method="GET")
        if isinstance(health, dict) and health.get("sealed"):
            module.fail_json(msg="OpenBao is sealed. Unseal it before running this module.")
    except hvac.exceptions.VaultError as exc:
        module.fail_json(msg=f"Failed to connect to OpenBao at {params['bao_addr']}: {exc}")
    except Exception as exc:
        module.fail_json(msg=f"Unexpected error connecting to OpenBao: {exc}")

    return client
