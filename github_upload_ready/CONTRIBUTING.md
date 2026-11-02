# Contributing to CaptureTrust

Thank you for your interest in improving CaptureTrust! Contributions of all
kinds are welcome: bug reports, documentation, new checks, better heuristics,
and test coverage.

## Getting started

1. Fork and clone the repository.

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

3. Install the package with development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

## Development workflow

Before opening a pull request, make sure the full quality gate passes locally:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

- **Ruff** handles linting and formatting.
- **Mypy** handles static type checking.
- **Pytest** runs the test suite against synthetic NumPy images.

To auto-format your changes:

```bash
ruff format .
ruff check . --fix
```

## Guidelines

- **Keep it lightweight.** Avoid adding heavy runtime dependencies. The core
  library depends only on `numpy` and `opencv-python-headless`.
- **Checks must fail safely.** A single failing optional check must never crash
  the whole inspection. Guard risky logic and return a structured result.
- **Careful language.** CaptureTrust never claims an image is "fake",
  "fraudulent", or "tampered". Use estimative, non-accusatory wording.
- **Add tests.** New behaviour needs a synthetic-image test in `tests/`.
- **Type everything.** Public functions must be fully type-annotated.
- **Document.** Update the README and `docs/` when you change behaviour.

## Commit and PR conventions

- Write clear, descriptive commit messages.
- Reference related issues in the PR description.
- Keep pull requests focused; smaller PRs are reviewed faster.

## Reporting issues

Use the GitHub issue tracker. For suspected security issues, follow
[SECURITY.md](SECURITY.md) instead of filing a public issue.

By contributing, you agree that your contributions will be licensed under the
MIT License.
