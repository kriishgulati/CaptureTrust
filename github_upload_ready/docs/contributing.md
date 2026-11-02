# Contributing (documentation)

The authoritative contributor guide lives at the repository root in
[CONTRIBUTING.md](../CONTRIBUTING.md). This page is a short pointer for readers
browsing the `docs/` directory.

## Quick reference

Set up a development environment:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the full quality gate before opening a pull request:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Principles

- Keep the library lightweight; avoid heavy runtime dependencies.
- Checks must fail safely and never crash a whole inspection.
- Use careful, estimative language — never "fake", "fraudulent", or "tampered".
- Add synthetic-image tests for new behaviour and keep public functions typed.

See [CONTRIBUTING.md](../CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) for the full details.
