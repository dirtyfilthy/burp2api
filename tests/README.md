# Test Suite for burp2api

This directory contains comprehensive tests for the burp2api package.

## Test Coverage

**Overall Coverage: 95.18%** (exceeds target of 85%)

### Module Coverage Breakdown

| Module | Statements | Missed | Coverage | Status |
|--------|-----------|---------|----------|--------|
| auth_detector.py | - | - | 100.00% | ✓ Complete |
| filters.py | - | - | 100.00% | ✓ Complete |
| __init__.py | - | - | 100.00% | ✓ Complete |
| cli.py | 49 | 4 | 91.84% | ✓ Excellent |
| parser.py | 139 | 11 | 92.09% | ✓ Excellent |
| openapi_generator.py | 189 | 12 | 93.65% | ✓ Excellent |
| schema_extractor.py | 137 | 4 | 97.08% | ✓ Outstanding |

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                  # Shared pytest fixtures
├── fixtures/                    # Test data
│   ├── __init__.py
│   ├── sample_burp_export.xml   # Basic Burp export (5 items)
│   ├── burp_with_json.xml       # Export with JSON bodies
│   ├── burp_with_auth.xml       # Export with auth headers
│   └── invalid_burp.xml         # Malformed XML for error testing
├── test_parser.py              # 24 tests for BurpParser
├── test_schema_extractor.py    # 33 tests for SchemaExtractor
├── test_filters.py             # 19 tests for StaticAssetFilter
├── test_auth_detector.py       # 18 tests for AuthDetector
├── test_openapi_generator.py   # 24 tests for OpenAPIGenerator
├── test_cli.py                 # 19 tests for CLI
└── test_integration.py         # 14 tests for end-to-end workflows
```

## Test Count

**Total: 151 tests**

- test_parser.py: 24 tests
- test_schema_extractor.py: 33 tests
- test_openapi_generator.py: 24 tests
- test_filters.py: 19 tests
- test_cli.py: 19 tests
- test_auth_detector.py: 18 tests
- test_integration.py: 14 tests

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run with Coverage Report

```bash
pytest tests/ --cov=burp2api --cov-report=html --cov-report=term-missing
```

Coverage HTML report will be generated in `htmlcov/index.html`.

### Run Specific Test File

```bash
pytest tests/test_parser.py -v
```

### Run Specific Test

```bash
pytest tests/test_parser.py::TestBurpParser::test_parse_valid_burp_export -v
```

### Run Tests Matching Pattern

```bash
pytest tests/ -k "auth" -v
```

## Test Categories

### Unit Tests

- **test_parser.py**: XML parsing, base64 decoding, HTTP request/response parsing
- **test_schema_extractor.py**: JSON schema inference, type detection, format detection, schema merging
- **test_filters.py**: Static asset filtering, pattern matching, MIME type detection
- **test_auth_detector.py**: Authentication scheme detection (Bearer, Basic, API keys, cookies)
- **test_openapi_generator.py**: OpenAPI spec generation, endpoint grouping, path parameterization

### Integration Tests

- **test_cli.py**: Command-line interface with Click's CliRunner
- **test_integration.py**: End-to-end workflows, library API usage

## Fixtures

The `conftest.py` file provides reusable fixtures:

- `sample_burp_file`: Path to basic Burp export
- `burp_with_json_file`: Path to export with JSON bodies
- `burp_with_auth_file`: Path to export with auth headers
- `invalid_burp_file`: Path to malformed XML
- `sample_burp_xml`: Valid Burp export XML string
- `temp_xml_file`: Temporary XML file
- `sample_request`: HTTPRequest object
- `sample_response`: HTTPResponse object
- `sample_burp_item`: Single BurpItem object
- `burp_items`: Parsed BurpItem list
- `api_item`: BurpItem representing API endpoint
- `static_item`: BurpItem representing static asset

## Configuration

Test configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "--cov=burp2api",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=85",
    "--verbose"
]
```

## Test Coverage Details

### What's Tested

✅ **Parser (92.09%)**
- Valid and invalid XML parsing
- Base64 encoding/decoding
- HTTP request/response parsing
- Query parameter extraction
- Missing fields handling
- Error conditions

✅ **Schema Extractor (97.08%)**
- JSON schema inference
- Type detection (string, number, boolean, array, object, null)
- Format detection (date-time, date, email, uri, uuid)
- Nested objects and arrays
- Schema merging
- Form data extraction
- Invalid JSON handling

✅ **Filters (100%)**
- File extension filtering
- MIME type filtering
- Path pattern filtering
- Include/exclude patterns
- Static asset detection

✅ **Auth Detector (100%)**
- Bearer token detection
- Basic auth detection
- API key detection (headers and query params)
- Session cookie detection
- OpenAPI security scheme generation

✅ **OpenAPI Generator (93.65%)**
- Basic OpenAPI structure generation
- Endpoint grouping by path pattern
- ID detection (UUID, numeric, ObjectId)
- Path parameter extraction
- Query parameter extraction
- Request/response schema generation
- Multiple status codes
- Server URL extraction
- Authentication scheme integration

✅ **CLI (91.84%)**
- Command execution
- Option parsing (title, version, description)
- Include/exclude patterns
- Static filtering toggle
- JSON output (pretty/compact)
- Verbose mode
- Error handling

✅ **Integration (100% via test_integration.py)**
- Complete parse → filter → generate workflow
- Library API usage
- Error handling
- File I/O

## Continuous Improvement

To maintain high test coverage:

1. Run tests before committing: `pytest tests/`
2. Check coverage report: Open `htmlcov/index.html`
3. Add tests for new features
4. Keep coverage above 85% threshold
5. Test both success and failure paths

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure new tests pass
3. Maintain coverage threshold
4. Update this README if test structure changes

