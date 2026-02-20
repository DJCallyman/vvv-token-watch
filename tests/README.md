# VVV Token Watch - Test Suite

Comprehensive test suite for the VVV Token Watch application.

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_config.py

# Run with verbose output
python -m pytest tests/ -v
```

## Test Structure

- `conftest.py` - Shared fixtures and configuration
- `test_config.py` - Configuration module tests
- `test_utils.py` - Utility function tests
- `test_theme.py` - Theme system tests
- `test_venice_api_client.py` - API client tests
- `test_workers.py` - Worker thread tests
- `test_widgets.py` - UI widget tests

## Writing Tests

When adding new tests:
1. Use descriptive test names
2. Follow AAA pattern: Arrange, Act, Assert
3. Use fixtures from conftest.py
4. Mock external API calls
5. Test both success and error cases
