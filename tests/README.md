# Test Suite Documentation

This directory contains comprehensive tests for the Knowledge Base & Document Management System.

## Test Structure

### Test Types

1. **Unit Tests** (`test_crud.py`, `test_storage.py`)
   - Test individual functions in isolation
   - Use mocked dependencies where appropriate
   - Fast execution, focused on business logic

2. **Integration Tests** (`test_integration.py`)
   - Test complete workflows across API, database, and storage layers
   - Verify components work together correctly
   - Test end-to-end scenarios

3. **API Tests** (`test_documents.py`, `test_search.py`, `test_main.py`)
   - Test HTTP endpoints with full request/response cycle
   - Verify API contracts and response formats
   - Test error handling and validation

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Types
```bash
# Unit tests only
pytest tests/test_crud.py tests/test_storage.py

# Integration tests only
pytest tests/test_integration.py -m integration

# API tests only
pytest tests/test_documents.py tests/test_search.py tests/test_main.py
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test
```bash
pytest tests/test_integration.py::TestCompleteDocumentWorkflow::test_complete_document_lifecycle
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests (can be added)
- `@pytest.mark.slow` - Slow running tests (can be added)

Run tests by marker:
```bash
pytest -m integration
pytest -m "not slow"  # Exclude slow tests
```

## Integration Tests Overview

The integration tests (`test_integration.py`) cover:

1. **Complete Document Workflow** - Full lifecycle: upload → list → versions → download → delete
2. **Search and Filter Workflow** - Multiple documents with various search scenarios
3. **Tag Management Workflow** - Tag reuse and management across documents
4. **Error Handling Integration** - Error propagation across layers
5. **Concurrent Operations** - Multiple versions and consistency
6. **Pagination Integration** - Consistent pagination across operations
7. **Data Integrity** - Cascading deletes and data consistency

## Test Fixtures

Key fixtures in `conftest.py`:

- `db_session` - Fresh database session for each test
- `client` - FastAPI test client with database override
- `temp_storage` - Temporary storage directory for file operations
- `sample_document` - Pre-created document for testing
- `sample_document_with_tags` - Document with tags
- `sample_document_multiple_versions` - Document with multiple versions

## Test Database

Tests use a temporary SQLite database file that is:
- Created fresh for each test run
- Cleaned up after each test
- Isolated from production database

## Coverage Goals

- Target: 90%+ code coverage
- Current: ~97% overall coverage
- Focus areas: Business logic, error handling, edge cases

## Best Practices

1. **Isolation**: Each test is independent and can run in any order
2. **Cleanup**: Tests clean up after themselves (temp files, database state)
3. **Clarity**: Test names clearly describe what is being tested
4. **Coverage**: Tests cover happy paths, error cases, and edge cases
5. **Speed**: Tests run quickly (under 15 seconds for full suite)

