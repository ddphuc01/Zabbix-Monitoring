# Testing Guide

## Setup

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Or install in development mode
pip install -e ".[dev]"
```

## Running Tests

### All Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ai-services --cov-report=html
```

### Specific Test Types
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_webhook_handler.py

# Specific test function
pytest tests/unit/test_webhook_handler.py::TestGroqAnalyzer::test_determine_alert_type_cpu
```

### Test Markers
```bash
# Run only fast tests
pytest -m "not slow"

# Run async tests
pytest -m asyncio
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── requirements.txt         # Test dependencies
├── unit/                    # Unit tests
│   ├── test_webhook_handler.py
│   └── test_telegram_bot.py
├── integration/             # Integration tests
│   └── test_telegram_workflow.py
└── fixtures/                # Test data
```

## Writing Tests

### Unit Test Example
```python
def test_determine_alert_type_cpu():
    """Test CPU alert detection"""
    from webhook import GroqAnalyzer
    
    assert GroqAnalyzer.determine_alert_type('High CPU usage') == 'CPU'
```

### Async Test Example
```python
@pytest.mark.asyncio
async def test_start_command(sample_telegram_update, sample_telegram_context):
    """Test /start command"""
    from bot import start
    
    await start(sample_telegram_update, sample_telegram_context)
    
    # Assertions...
```

### Using Fixtures
```python
def test_with_env_vars(mock_env_vars):
    """Test uses mocked environment variables"""
    import os
    assert os.getenv('GROQ_API_KEY') == 'test_groq_key_123'
```

## Coverage Reports

After running tests with coverage:
```bash
# View in terminal
pytest --cov=ai-services --cov-report=term-missing

# Generate HTML report
pytest --cov=ai-services --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

For GitHub Actions:
```yaml
- name: Run tests
  run: |
    pip install -r tests/requirements.txt
    pytest --cov=ai-services --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Mock External Dependencies**: Don't call real APIs
3. **Clear Test Names**: Describe what you're testing
4. **Use Fixtures**: Reuse test data
5. **Test Edge Cases**: Not just happy paths
6. **Keep Tests Fast**: Mock slow operations

## Troubleshooting

### Import Errors
Make sure project root is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Async Test Warnings
Install pytest-asyncio:
```bash
pip install pytest-asyncio
```

### Coverage Not Working
Ensure source paths are correct in pytest.ini
