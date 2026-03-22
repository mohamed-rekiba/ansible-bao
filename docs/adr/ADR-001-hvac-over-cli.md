# ADR-001: Use hvac instead of wrapping the CLI

## Status

Accepted

## Context

The collection needs to talk to OpenBao. Two options:

1. **Wrap the `bao` CLI** -- shell out, parse text output, hope the format doesn't change between versions
2. **Use `hvac`** -- call the HTTP API directly from Python, get structured JSON back

## Decision

Use `hvac` for everything.

## Why

- **Idempotency is straightforward.** The API returns current state as JSON, so comparing desired vs. actual is trivial. Parsing CLI text output is fragile.
- **Real error handling.** `hvac` raises typed exceptions (`Forbidden`, `InvalidPath`, etc.) instead of exit codes and unstructured stderr.
- **Works anywhere.** The modules just need network access to the API. No `bao` binary needed on the controller.
- **Easy to test.** HTTP calls can be mocked. Shell commands can't.
- **One dependency.** `hvac` is pure Python with no transitive surprises.

## Trade-offs

- You need network connectivity to the OpenBao API (but you'd need that anyway).
- `hvac` has to stay compatible with OpenBao's API. Low risk -- OpenBao maintains Vault API compatibility and the `hvac` library tracks it closely.
