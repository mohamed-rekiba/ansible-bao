# Contributing

Thanks for your interest in improving this collection.

## Getting started

1. Fork and clone the repo
2. Create a virtual environment and install dev dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:

   ```bash
   pre-commit install
   ```

4. Create a branch off `main`:

   ```bash
   git switch -c feat/my-change
   ```

## Making changes

- Each module lives in `plugins/modules/` and shares the client factory in `plugins/module_utils/_client.py`.
- Modules must be idempotent, support `check_mode` and `supports_check_mode=True`, and never log sensitive data (`no_log=True` on tokens and secrets).
- Follow the existing module structure -- read current state, compare, write only if different.

## Running checks

```bash
make lint      # ruff check + format
make format    # auto-fix formatting
```

Or let pre-commit handle it:

```bash
pre-commit run --all-files
```

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(auth_method): add OIDC config support
fix(kv2_secret): handle missing mount gracefully
docs: update namespace examples
```

## Pull requests

- Keep PRs focused -- one feature or fix per PR
- Include a short description of what changed and why
- Make sure `make lint` passes before opening the PR
- The CI pipeline runs ruff and ansible sanity tests automatically

## Adding a new module

1. Create `plugins/modules/your_module.py` following the existing pattern
2. Use `BAO_COMMON_ARGS` from `_client.py` for connection parameters
3. Add `DOCUMENTATION`, `EXAMPLES`, and `RETURN` docstrings
4. Add an entry to the module table in `README.md`
5. Run `make lint` to verify

## Questions?

Open an issue -- happy to help.
