# Tests Directory

This directory contains all test-related documentation including requirements, test plans, and test cases.

## Contents

- **requirements.md** - Complete system requirements and acceptance criteria
- **test-cases.md** - Comprehensive test cases organized by feature
- **requirements-and-test-plan.html** - HTML version combining requirements and test planning

## Purpose

Use this directory to:
- Understand system requirements and expected behavior
- Review test coverage and test cases
- Plan testing activities
- Track acceptance criteria

## Related Documentation

- See [../reports/test-reports/](../reports/test-reports/) for test execution results
- See [../deployment/guides/](../deployment/guides/) for deployment test procedures
- See [../guides/](../guides/) for feature-specific documentation

## Test Organization

Tests are organized by:
- **Feature area** - Grouped by functionality (e.g., generation, solving, export)
- **Test type** - Unit, integration, E2E, UI tests
- **Status** - Passing, failing, or pending tests

## Running Tests

Refer to the project's CLAUDE.md for test execution commands:
```bash
./.venv/bin/python -m pytest              # Run all tests
./.venv/bin/python -m pytest -k keyword   # Run tests matching keyword
./.venv/bin/python -m pytest tests/       # Run specific test directory
```

---
Last updated: 2026-09-05
