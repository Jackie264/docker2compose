# Docker2Compose Test Suite

This directory contains comprehensive unit tests for the docker2compose project.

## Overview

The test suite covers the core functionality of the docker2compose application, including:

- **Configuration management** (loading, validation, defaults)
- **Container analysis and grouping** (network relationships, container conversion)
- **CRON expression utilities** (normalization, validation)
- **Scheduler functionality** (signal handling, configuration loading)
- **Web UI utilities** (file management, subprocess handling)

## Test Structure

### `test_d2c.py`
Tests for the main `d2c.py` module:
- `TestLoadConfig`: Configuration loading from files and environment variables
- `TestEnsureConfigFile`: Configuration file creation and directory management
- `TestGroupContainersByNetwork`: Container grouping logic based on network relationships
- `TestConvertContainerToService`: Container to docker-compose service conversion

### `test_cron_utils.py`
Tests for the `cron_utils.py` module:
- `TestCronUtils`: CRON expression normalization and debug functionality
- `TestCronUtilsValidation`: CRON expression validation and format handling

### `test_scheduler.py`
Tests for the `scheduler.py` module:
- `TestD2CScheduler`: Scheduler initialization, configuration loading, signal handling
- `TestD2CSchedulerIntegration`: Integration tests with CronUtils

### `test_web_ui.py`
Tests for the `web_ui.py` module:
- `TestWebUIUtilities`: Utility functions for timestamp generation and file management
- `TestWebUIConfiguration`: Configuration handling and subprocess management

## Running Tests

### Using pytest directly:
```bash
cd /path/to/docker2compose
python -m pytest tests/ -v
```

### Using the test runner script:
```bash
cd /path/to/docker2compose
python run_tests.py
```

### Running specific test files:
```bash
python -m pytest tests/test_d2c.py -v
python -m pytest tests/test_cron_utils.py -v
python -m pytest tests/test_scheduler.py -v
python -m pytest tests/test_web_ui.py -v
```

## Test Coverage

The test suite includes **40 comprehensive tests** covering:

- ✅ Configuration loading and validation
- ✅ Error handling and fallback mechanisms
- ✅ Container network analysis and grouping
- ✅ Docker-compose service conversion
- ✅ CRON expression normalization and validation
- ✅ Scheduler signal handling and lifecycle management
- ✅ Web UI utility functions
- ✅ Subprocess execution and error handling

## Dependencies

The tests require the following additional packages (included in `requirements.txt`):
- `pytest>=8.0.0`
- `pytest-mock>=3.14.0`

## Test Philosophy

The tests follow these principles:

1. **Isolation**: Each test is independent and doesn't rely on external systems
2. **Mocking**: External dependencies (file system, subprocess calls, Docker) are mocked
3. **Coverage**: Focus on testing business logic and error handling paths
4. **Maintainability**: Clear test names and documentation for easy maintenance

## Adding New Tests

When adding new functionality to the project:

1. Create corresponding test cases in the appropriate test file
2. Use descriptive test method names that explain what is being tested
3. Mock external dependencies to ensure test isolation
4. Test both success and failure scenarios
5. Update this README if adding new test categories

## Notes

- Tests use extensive mocking to avoid dependencies on Docker, file system, or network resources
- The test suite can run in any environment without requiring Docker to be installed
- All tests pass consistently and provide good coverage of the core functionality