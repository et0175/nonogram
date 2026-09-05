# Development Directory

Development setup, contribution guidelines, and troubleshooting.

## Subdirectories

### setup/
Environment setup and installation procedures.

**Key Topics:**
- Python virtual environment setup
- Dependency installation
- IDE configuration (PyCharm, VSCode)
- Git configuration
- Pre-commit hooks setup

### troubleshooting/
Common issues and their solutions.

**Key Topics:**
- Common errors and fixes
- Dependency issues
- Environment problems
- Build/test failures
- Performance issues

## Quick Start

1. **Initial Setup:**
   ```bash
   python3.14 -m venv .venv
   ./.venv/bin/pip install -e '.[dev]'
   ```

2. **Running Tests:**
   ```bash
   ./.venv/bin/python -m pytest
   ```

3. **Running CLI:**
   ```bash
   nonogram generate --size 20 --density 30 --seed 42 --export json
   ```

## Development Tools

### Project Structure
- `src/nonogram/` - Main package
- `tests/` - Test suite
- `meta/` - Architecture, kanban, releases
- `docs/` - Documentation (this directory)

### Key Commands

**Tests:**
- Run all tests: `pytest`
- Run specific test: `pytest tests/test_solver.py::test_name -v`
- Run tests matching keyword: `pytest -k density`

**CLI:**
- Generate puzzle: `nonogram generate --size 20 --density 30 --seed 42`
- Export formats: json, csv, svg, png, pdf

**Web:**
- Start web server: See deployment guides

## Code Organization

The project follows a layered architecture:
- **CLI Layer** (cli.py) - Command line interface
- **Orchestration** (orchestrator.py) - Puzzle generation workflow
- **Capabilities** - Modular components (sourcing, clues, solver, export, etc.)
- **Domain** - Core business logic

For details, see ../architecture/

## Contributing Guidelines

1. **Code Style**
   - Follow Python conventions
   - Use clear variable names
   - Keep functions focused and small

2. **Testing**
   - Write tests for new features
   - Maintain test coverage
   - Test edge cases

3. **Documentation**
   - Update relevant docs
   - Add comments for complex logic
   - Link to related code/docs

4. **Git Workflow**
   - Create feature branches
   - Write descriptive commit messages
   - Create pull requests for review

## Common Issues

### ImportError: No module named 'nonogram'
- Ensure you've run: `./.venv/bin/pip install -e '.`
- Check PYTHONPATH in pyproject.toml

### Tests Failing
- Check ../reports/test-reports/ for recent failures
- See troubleshooting/ directory for solutions
- Verify all dependencies installed: `pip install -e '.[dev]'`

### Performance Issues
- Check solver timeouts (configurable in solver/)
- Profile with: `python -m cProfile`
- See algorithms.md for optimization notes

## Testing Strategy

### Test Types
- **Unit tests** - Individual functions
- **Integration tests** - Component interaction
- **E2E tests** - Full workflow
- **Property tests** - Solver correctness verification

### Mandatory Tests
- Solver uniqueness verification (EC-001)
- Web UI functionality
- CLI argument parsing

See ../tests/test-cases.md for complete test coverage.

## Related Documentation

- See ../guides/ for feature documentation
- See ../deployment/ for production setup
- See ../tests/ for requirements and test cases
- See ../architecture/ for system design

---
Last updated: 2026-09-05
