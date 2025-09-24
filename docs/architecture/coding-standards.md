# Coding Standards

### Core Standards

- **Languages & Runtimes:** Python 3.12.4
- **Style & Linting:** We will use `ruff` for linting and `black` for code formatting. A `pyproject.toml` file will contain the configurations for these tools to ensure consistency.
- **Test Organization:** Test files will be located in the `tests/` directory of each service. Test filenames will be prefixed with `test_`.

### Naming Conventions

We will follow the standard Python PEP 8 naming conventions. No project-specific deviations are necessary at this time.

| Element | Convention | Example |
| :--- | :--- | :--- |
| Variable | `snake_case` | `incident_id` |
| Function | `snake_case` | `create_incident` |
| Class | `PascalCase` | `IncidentModel` |
| Module | `snake_case` | `correlation_engine.py` |

### Critical Rules

- **Rule 1:** All API endpoints must use FastAPI's dependency injection system to acquire dependencies (like service clients). Do not instantiate clients directly in endpoint functions.
- **Rule 2:** All public functions and methods must have a docstring explaining their purpose, arguments, and return values.
- **Rule 3:** All business logic must be covered by unit tests with a target of 80% code coverage.
- **Rule 4:** Never log sensitive information, such as API keys or secrets.

### Language-Specific Guidelines

- **Python Specifics:**
    - Use Pydantic models for all data validation and serialization in the API layer.
    - Use type hints for all function signatures.
