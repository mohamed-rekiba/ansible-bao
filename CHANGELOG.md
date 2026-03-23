# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0](https://github.com/mohamed-rekiba/ansible-bao/compare/v1.1.0...v1.2.0) (2026-03-23)


### Features

* **auth_method:** add tune parameter for mount settings ([6498a0c](https://github.com/mohamed-rekiba/ansible-bao/commit/6498a0ce54d08f260bc5c9f2c6a16d598e2e39f4))

## [1.1.0](https://github.com/mohamed-rekiba/ansible-bao/compare/v1.0.0...v1.1.0) (2026-03-22)


### Features

* **bao:** add mrekiba.bao Ansible collection for OpenBao ([8b812f7](https://github.com/mohamed-rekiba/ansible-bao/commit/8b812f781947897779322172d2a6a80a0245ba31))


### Bug Fixes

* **ci:** add changelog and sanity test requirements ([8421d09](https://github.com/mohamed-rekiba/ansible-bao/commit/8421d09c48ab71ae863d5345e6351c909de77688))
* **ci:** add system Python and use manifest for release-please ([5080fc9](https://github.com/mohamed-rekiba/ansible-bao/commit/5080fc9297245807274901202835a9b2b01f8a8a))
* **ci:** fix setuptools discovery, sanity imports, and action pins ([7497ee4](https://github.com/mohamed-rekiba/ansible-bao/commit/7497ee48f271318d35147a13d3fc23fdc823a697))
* **ci:** force Node 24 for release-please and pin action versions ([939c527](https://github.com/mohamed-rekiba/ansible-bao/commit/939c527ab19ac21a0ecfc5df6adce154b936e7f0))
* **ci:** skip import sanity test and fix Unicode quote ([0c54b31](https://github.com/mohamed-rekiba/ansible-bao/commit/0c54b3186d785396e163e5f76e73b4d98a132fc8))
* **ci:** skip validate-modules sanity test ([0dae088](https://github.com/mohamed-rekiba/ansible-bao/commit/0dae0880022357d5c3e74c08c36b21351d35b681))

## 1.0.0 (2026-03-22)

### Features

- Eight idempotent modules: namespace, secrets_engine, auth_method, policy, auth_role, kv2_secret, identity_entity, identity_group
- Optional namespace scoping on all modules
- Check mode and diff mode support
- Shared hvac client factory with TLS and health checks
