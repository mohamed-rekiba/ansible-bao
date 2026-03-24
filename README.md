# mrekiba.bao

Ansible collection for managing [OpenBao](https://openbao.org/) through its HTTP API. Also works with HashiCorp Vault since the API is compatible.

Eight action modules manage resources (create, update, delete) and eight info modules read them. Everything is idempotent, supports `--check` and `--diff`, and never logs sensitive data.

## Requirements

- Python >= 3.12
- [`hvac`](https://python-hvac.org/) >= 2.4.0
- Ansible >= 2.17
- OpenBao >= 2.0

## Install

From the latest GitHub Release:

```bash
ansible-galaxy collection install \
  https://github.com/mohamed-rekiba/ansible-bao/releases/latest/download/mrekiba-bao-latest.tar.gz
pip install hvac>=2.4.0
```

Or via `requirements.yml`:

```yaml
collections:
  - name: https://github.com/mohamed-rekiba/ansible-bao.git
    type: git
    version: main
```

```bash
ansible-galaxy collection install -r requirements.yml
pip install -r ~/.ansible/collections/ansible_collections/mrekiba/bao/meta/requirements.txt
```

Pinned releases are also available as `mrekiba-bao-x.y.z.tar.gz` on the [Releases](https://github.com/mohamed-rekiba/ansible-bao/releases) page. For [Execution Environments](https://docs.ansible.com/automation-controller/latest/html/userguide/execution_environments.html), `ansible-builder` picks up the Python dependency from `meta/execution-environment.yml`.

## Modules

### Action modules

Manage resources with `state: present` or `state: absent`.

| Module | Description |
|--------|------------|
| `mrekiba.bao.namespace` | Create or delete a namespace (supports nesting) |
| `mrekiba.bao.secrets_engine` | Enable or disable a secrets engine |
| `mrekiba.bao.auth_method` | Enable, configure, or disable an auth method |
| `mrekiba.bao.policy` | Manage ACL policies (inline HCL or from templates) |
| `mrekiba.bao.auth_role` | Manage roles on any auth method |
| `mrekiba.bao.kv2_secret` | Write or delete KV v2 secrets |
| `mrekiba.bao.identity_entity` | Manage identity entities and their aliases |
| `mrekiba.bao.identity_group` | Manage identity groups (internal/external) and their aliases |

### Info modules

Read-only. Return `exists` (bool) and resource data. Never modify state.

| Module | Description |
|--------|------------|
| `mrekiba.bao.namespace_info` | Read a namespace |
| `mrekiba.bao.secrets_engine_info` | Read a secrets engine mount (type, accessor, options) |
| `mrekiba.bao.auth_method_info` | Read an auth method (type, accessor, config, tune) |
| `mrekiba.bao.policy_info` | Read an ACL policy (HCL content) |
| `mrekiba.bao.auth_role_info` | Read a role on an auth method |
| `mrekiba.bao.kv2_secret_info` | Read KV v2 secret metadata (optionally data with `include_data`) |
| `mrekiba.bao.identity_entity_info` | Read an identity entity (policies, metadata, aliases) |
| `mrekiba.bao.identity_group_info` | Read an identity group (type, policies, members/aliases) |

### Connection parameters

All modules share these:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `bao_addr` | str | yes | -- | Server URL (e.g. `https://bao.example.com:8200`) |
| `bao_token` | str | yes | -- | Auth token (never logged) |
| `bao_namespace` | str | no | -- | Namespace to scope all API calls to |
| `bao_ca_cert` | path | no | -- | CA cert for TLS verification |
| `bao_skip_verify` | bool | no | false | Skip TLS verification |

## Examples

### Setting up a full stack

```yaml
- name: Set up OpenBao
  hosts: localhost
  gather_facts: false
  vars:
    bao_addr: "https://bao.example.com:8200"
    bao_token: "{{ lookup('env', 'BAO_TOKEN') }}"
  tasks:
    - name: Enable KV v2
      mrekiba.bao.secrets_engine:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        path: secret
        type: kv
        options:
          version: "2"

    - name: Enable AppRole auth
      mrekiba.bao.auth_method:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        path: approle
        type: approle

    - name: Create a read-only policy
      mrekiba.bao.policy:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        name: app-read
        content: |
          path "secret/data/myapp/*" {
            capabilities = ["read"]
          }

    - name: Create an AppRole role
      mrekiba.bao.auth_role:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        auth_path: approle
        name: my-app
        config:
          token_policies: app-read
          token_ttl: 1h

    - name: Write a secret
      mrekiba.bao.kv2_secret:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        mount: secret
        path: myapp/config
        data:
          db_password: "{{ db_password }}"

    - name: Create an entity with an alias
      mrekiba.bao.identity_entity:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        name: my-app
        policies:
          - app-read
        aliases:
          - name: my-app
            auth_path: approle

    - name: Create a group for the team
      mrekiba.bao.identity_group:
        bao_addr: "{{ bao_addr }}"
        bao_token: "{{ bao_token }}"
        name: platform-team
        type: internal
        policies:
          - admin-read
        member_entity_names:
          - my-app
```

### Namespaces

```yaml
- name: Create a team namespace
  mrekiba.bao.namespace:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    path: team-a

- name: Enable KV inside that namespace
  mrekiba.bao.secrets_engine:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    bao_namespace: team-a
    path: secret
    type: kv
    options:
      version: "2"
```

### Reading resources

```yaml
- name: Check if the KV engine is mounted
  mrekiba.bao.secrets_engine_info:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    path: secret
  register: engine

- name: Enable KV only if missing
  mrekiba.bao.secrets_engine:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    path: secret
    type: kv
    options:
      version: "2"
  when: not engine.exists

- name: Check if a secret exists (metadata only)
  mrekiba.bao.kv2_secret_info:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    mount: secret
    path: myapp/config
  register: secret

- name: Read the secret data when needed
  mrekiba.bao.kv2_secret_info:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    mount: secret
    path: myapp/config
    include_data: true
  register: secret_data
  no_log: true
  when: secret.exists
```

### Policies from Jinja2 templates

```yaml
- name: Create policy from template
  mrekiba.bao.policy:
    bao_addr: "{{ bao_addr }}"
    bao_token: "{{ bao_token }}"
    name: app-read
    content: "{{ lookup('template', 'policies/app-read.hcl.j2') }}"
```

## How it works

Every action module follows the same pattern:

1. Connect to OpenBao via `hvac`
2. Read current state from the API
3. Compare to desired state
4. Write only if something differs

Info modules do steps 1-2 and return the result. All modules fail with a clear message on API errors. Tokens and secret data never appear in logs or output.

## Roadmap

- `bao_status` -- check seal/init state
- `bao_transit` -- encrypt, decrypt, rewrap
- `bao_pki` -- issue and revoke certificates
- Integration tests with `ansible-test`
- Publish to Galaxy

## License

MIT
