# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0](https://github.com/mohamed-rekiba/ansible-bao/compare/v1.4.0...v1.5.0) (2026-03-24)


### Features

* **auth_method_info:** return list of roles ([e6bdb04](https://github.com/mohamed-rekiba/ansible-bao/commit/e6bdb0458dace7a99c3a7a16d10e110b8a6db313))

## [1.4.0](https://github.com/mohamed-rekiba/ansible-bao/compare/v1.3.0...v1.4.0) (2026-03-24)


### Features

* **modules:** add info modules for all resources ([40f2a9c](https://github.com/mohamed-rekiba/ansible-bao/commit/40f2a9c24711f98f6bbcf32411446d6285914f57))

## [1.3.0](https://github.com/mohamed-rekiba/ansible-bao/compare/v1.2.0...v1.3.0) (2026-03-23)


### Features

* **kv2_secret:** add custom_metadata support for ESO tag-based discovery ([3495780](https://github.com/mohamed-rekiba/ansible-bao/commit/3495780c3d9de071c1f26b72db681faf14136c50))

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
