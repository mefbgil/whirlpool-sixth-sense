# AGENTS.md - Guidelines for AI Coding Agents

This document provides essential information for AI coding agents working in this repository.

## Project Overview

- **Language**: Python 3.14+
- **Type**: Asyncio-based API library for Whirlpool 6th Sense smart appliances
- **Package**: `whirlpool_sixth_sense`

## Build & Development Commands

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest --log-cli-level=debug

# Run a single test file
pytest tests/test_auth.py

# Run a single test function
pytest tests/test_auth.py::test_auth_success

# Run tests matching a pattern
pytest -k "test_attributes"

# Linting and formatting
ruff check .              # Check for lint errors
ruff check . --fix        # Auto-fix lint errors
ruff format .             # Format code

# Type checking
basedpyright

# Run all lint, format, type-check and workflow-audit hooks
prek --all-files
```

## Code Style Guidelines

### Imports
- Order: standard library, third-party, local
- Use relative imports within `whirlpool` package: `from .appliance import Appliance`
- Use absolute imports for external packages: `import aiohttp`

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `Appliance`, `AppliancesManager` |
| Functions/Methods | snake_case | `get_machine_state`, `send_attributes` |
| Constants | UPPER_SNAKE_CASE | `ATTR_MODE`, `REQUEST_RETRY_COUNT` |
| Private members | Leading underscore | `_get_attribute`, `_data_dict` |
| Enums | PascalCase class & members | `Mode.Cool`, `FanSpeed.Auto` |

### Type Annotations
- Use full type annotations throughout
- Use Python 3.11+ union syntax: `str | None` (not `Optional[str]`)
- Use `collections.abc` for generic types: `Callable`, `Generator`, `AsyncGenerator`
- Examples:
  ```python
  def get_value(self) -> int | None:
  async def fetch_data(self, timeout: float = 30.0) -> dict[str, str]:
  ```

### Async Patterns
- Use `async`/`await` for all I/O operations
- Use `aiohttp.ClientSession` for HTTP requests
- Use `async_timeout` for request timeouts
- Pass session objects rather than creating new ones

### Error Handling
- Use custom exceptions for specific error cases (e.g., `AccountLockedError`)
- Log errors using the module logger
- Return `False` or `None` for recoverable failures rather than raising exceptions
- Implement retry logic for network requests (`REQUEST_RETRY_COUNT = 3`)

### Logging
- Define module-level logger: `LOGGER = logging.getLogger(__name__)`
- Use appropriate log levels: `debug` for verbose, `error` for failures
- Use f-strings in log messages

### Class Design
- Base `Appliance` class with common functionality in `appliance.py`
- Appliance-specific classes inherit and extend with device-specific methods
- Use `@property` for computed values, `@dataclass` for data containers, `Enum` for constants

## Testing Guidelines

### Framework
- pytest with pytest-asyncio (async tests auto-detected via `asyncio_mode = auto`)
- Use `aioresponses` for mocking HTTP requests

### Test Structure
```python
async def test_feature_success(
    auth: Auth, backend_selector: BackendSelector, aioresponses_mock: aioresponses
):
    # Arrange
    aioresponses_mock.post(url, payload=mock_data)
    # Act
    result = await auth.do_auth(store=False)
    # Assert
    assert result is True
    assert auth.is_access_token_valid()
```

### Available Fixtures (from `tests/conftest.py`)
- `aioresponses_mock` - Mock HTTP responses
- `client_session_fixture` - Shared aiohttp session
- `backend_selector` - BackendSelector instance
- `auth` - Auth instance with mock credentials
- `appliances_manager` - Fully configured manager

### Mock Data
- Store mock JSON responses in `tests/data/`
- Load with: `DATA_DIR / "filename.json"`

## Linting Configuration (ruff)

Enabled rules: `E` (pycodestyle), `F` (Pyflakes), `UP` (pyupgrade), `B` (flake8-bugbear), `I` (isort)

Max complexity: 25

## CI/CD Pipeline

GitHub Actions runs on push/PR (`.github/workflows/ci.yml`):
1. **prek** - Lint, format and type checks (ruff, basedpyright) plus a zizmor
   workflow audit
2. **pytest** - Tests (Python 3.14)
3. **zizmor** - Static analysis of the GitHub Actions workflows

Other workflows:
- **pr-labels** - Requires every PR to carry one of the release-drafter labels
  (`breaking-change`, `bugfix`, `ci`, `dependencies`, `documentation`,
  `enhancement`, `maintenance`, `new-feature`)
- **release-drafter** - Keeps a draft release up to date on every push to
  `master`, resolving the next version from the merged PRs' labels
- **publish** - Triggered when a release is published: injects the release tag
  as the package version, builds, and uploads to PyPI via trusted publishing

### Releasing

Releases are manual: publish the draft release that release-drafter maintains,
and `publish.yml` takes it from there. The `version` in `pyproject.toml` is a
`0.0.0` placeholder — the release tag is the source of truth, so do not bump it
by hand.

Dependency and action updates are handled by Renovate (`.github/renovate.json`);
GitHub Actions are pinned to commit digests.

## Reverse Engineering and AI-Assisted Development

Some appliance capabilities in this project are undocumented. They may need to be discovered from the official Whirlpool application, observed API/MQTT behavior, appliance state, and controlled experiments against a physical appliance.

Development may be performed interactively with an AI coding assistant such as ChatGPT. The human developer runs commands locally or in a GitHub Codespace, copies relevant output to the assistant, and applies small, reviewable changes suggested by the assistant.

### Recommended workflow

1. **Start with observed state**
   - Inspect raw appliance state before attempting a command.
   - Identify the state field associated with the feature.
   - Record its initial value so the change can be verified.

2. **Use the official application as a protocol reference**
   - Static analysis of the official Whirlpool application may be used to determine command names, fields, types, addressees, and serialization.
   - Preserve important findings instead of relying on temporary decompilation directories.
   - Treat inferred behavior as a hypothesis until verified on an appliance.

3. **Work in small copy/paste iterations**
   - Prefer narrowly scoped commands with manageable output.
   - Avoid broad searches or large dumps when a smaller query answers the immediate question.
   - Inspect diffs before running experimental code.
   - Never expose passwords, tokens, or other credentials in chat, source files, commits, or tests.

4. **Test the smallest possible command**
   - Temporary CLI controls are useful for controlled experiments.
   - Read state before sending the command.
   - Send one command and wait for the appliance response or state update.
   - Read state again and verify the expected field changed.
   - For Boolean controls, test both directions.
   - Do not blindly try payload variations after a failure.

5. **Separate verified facts from assumptions**
   - Distinguish behavior proven on a real appliance from behavior inferred from application code or protocol structure.
   - Successful MQTT publication alone does not prove appliance support. Verify resulting state whenever practical.

6. **Convert successful experiments into library code**
   - Expose verified commands through an appropriate public appliance method.
   - CLI and application code should use that method rather than private transport helpers such as `_send_command`.
   - Remove temporary experimental shortcuts when no longer needed.

7. **Add regression coverage**
   - Add an automated test for the exact verified command payload.
   - Test both directions where applicable.
   - Run the focused test first, followed by the complete test suite.
   - Physical validation and automated testing complement rather than replace each other.

### Example: AWS IoT Refrigerator Vacation Mode

Vacation Mode was developed using this workflow.

Raw appliance state showed:

```json
{
  "refrigerator": {
    "vacation": false
  }
}
```

Static analysis of the Whirlpool application showed that Vacation Mode is a Boolean complementary command. The candidate command was then tested against a physical refrigerator.

The verified command payload is:

```json
{
  "payload": {
    "addressee": "refrigerator",
    "command": "set",
    "vacation": true
  }
}
```

The inverse command uses `"vacation": false`.

Both transitions were physically verified:

- `false -> true`, followed by state reporting `"vacation": true`
- `true -> false`, followed by state reporting `"vacation": false`

The appliance emitted an attribute update after each command.

After physical verification, the command was implemented as `Refrigerator.set_vacation_mode()`. The CLI was changed to use that public method, and an AWS IoT refrigerator regression test was added for both ON and OFF payloads.

The resulting full test suite passed with 169 tests.

For future undocumented capabilities, prefer this sequence:

**protocol evidence -> minimal experiment -> physical state verification -> public API -> regression test**
