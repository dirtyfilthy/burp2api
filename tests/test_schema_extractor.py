"""
Tests for burp2api.schema_extractor module.
"""

import pytest
from burp2api.schema_extractor import SchemaExtractor


class TestSchemaExtractor:
    """Tests for SchemaExtractor class."""
    
    def test_extract_simple_json_object_schema(self):
        """Test extracting schema from simple JSON object."""
        body = '{"name": "John", "age": 30}'
        schema = SchemaExtractor.extract_request_schema(body, 'application/json')
        
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'name' in schema['properties']
        assert schema['properties']['name']['type'] == 'string'
        assert schema['properties']['age']['type'] == 'integer'
    
    def test_extract_nested_json_object_schema(self):
        """Test extracting schema from nested JSON object."""
        body = '{"user": {"name": "John", "email": "john@example.com"}, "count": 5}'
        schema = SchemaExtractor.extract_request_schema(body, 'application/json')
        
        assert schema['type'] == 'object'
        assert 'user' in schema['properties']
        assert schema['properties']['user']['type'] == 'object'
        assert 'name' in schema['properties']['user']['properties']
        assert schema['properties']['count']['type'] == 'integer'
    
    def test_extract_json_array_schema(self):
        """Test extracting schema from JSON array."""
        body = '[{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}]'
        schema = SchemaExtractor.extract_request_schema(body, 'application/json')
        
        assert schema['type'] == 'array'
        assert 'items' in schema
        assert schema['items']['type'] == 'object'
        assert 'id' in schema['items']['properties']
    
    def test_extract_empty_array_schema(self):
        """Test extracting schema from empty array."""
        body = '[]'
        schema = SchemaExtractor.extract_request_schema(body, 'application/json')
        
        assert schema['type'] == 'array'
        assert 'items' in schema
        assert schema['items'] == {}
    
    def test_type_inference_string(self):
        """Test type inference for strings."""
        schema = SchemaExtractor._infer_schema_from_value("test string")
        assert schema['type'] == 'string'
    
    def test_type_inference_integer(self):
        """Test type inference for integers."""
        schema = SchemaExtractor._infer_schema_from_value(42)
        assert schema['type'] == 'integer'
    
    def test_type_inference_number(self):
        """Test type inference for floats."""
        schema = SchemaExtractor._infer_schema_from_value(3.14)
        assert schema['type'] == 'number'
    
    def test_type_inference_boolean(self):
        """Test type inference for booleans."""
        schema = SchemaExtractor._infer_schema_from_value(True)
        assert schema['type'] == 'boolean'
        
        schema = SchemaExtractor._infer_schema_from_value(False)
        assert schema['type'] == 'boolean'
    
    def test_type_inference_null(self):
        """Test type inference for null values."""
        schema = SchemaExtractor._infer_schema_from_value(None)
        assert schema['type'] == 'null'
        assert schema['nullable'] is True
    
    def test_format_detection_datetime(self):
        """Test format detection for datetime strings."""
        schema = SchemaExtractor._infer_schema_from_value("2025-12-10T12:00:00Z")
        assert schema['type'] == 'string'
        assert schema['format'] == 'date-time'
    
    def test_format_detection_date(self):
        """Test format detection for date strings."""
        schema = SchemaExtractor._infer_schema_from_value("2025-12-10")
        assert schema['type'] == 'string'
        assert schema['format'] == 'date'
    
    def test_format_detection_email(self):
        """Test format detection for email strings."""
        schema = SchemaExtractor._infer_schema_from_value("user@example.com")
        assert schema['type'] == 'string'
        assert schema['format'] == 'email'
    
    def test_format_detection_uri(self):
        """Test format detection for URI strings."""
        schema = SchemaExtractor._infer_schema_from_value("https://example.com/path")
        assert schema['type'] == 'string'
        assert schema['format'] == 'uri'
    
    def test_format_detection_uuid(self):
        """Test format detection for UUID strings."""
        schema = SchemaExtractor._infer_schema_from_value("550e8400-e29b-41d4-a716-446655440000")
        assert schema['type'] == 'string'
        assert schema['format'] == 'uuid'
    
    def test_extract_form_urlencoded_schema(self):
        """Test extracting schema from form-urlencoded data."""
        body = 'username=testuser&email=test@example.com&age=25'
        schema = SchemaExtractor.extract_request_schema(body, 'application/x-www-form-urlencoded')
        
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'username' in schema['properties']
        assert schema['properties']['username']['type'] == 'string'
    
    def test_extract_form_with_array_values(self):
        """Test extracting schema from form data with multiple values."""
        body = 'tags=tag1&tags=tag2&tags=tag3'
        schema = SchemaExtractor.extract_request_schema(body, 'application/x-www-form-urlencoded')
        
        assert schema['type'] == 'object'
        assert 'tags' in schema['properties']
        assert schema['properties']['tags']['type'] == 'array'
        assert schema['properties']['tags']['items']['type'] == 'string'
    
    def test_extract_multipart_form_schema(self):
        """Test extracting schema from multipart form data."""
        body = '''------WebKitFormBoundary
Content-Disposition: form-data; name="username"

testuser
------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="test.txt"

file content
------WebKitFormBoundary--'''
        schema = SchemaExtractor.extract_request_schema(body, 'multipart/form-data')
        
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'username' in schema['properties']
        assert 'file' in schema['properties']
    
    def test_extract_response_schema_json(self):
        """Test extracting response schema from JSON."""
        body = '{"status": "success", "data": {"id": 123}}'
        schema = SchemaExtractor.extract_response_schema(body, 'application/json')
        
        assert schema['type'] == 'object'
        assert 'status' in schema['properties']
        assert 'data' in schema['properties']
        assert schema['properties']['data']['type'] == 'object'
    
    def test_extract_response_schema_html(self):
        """Test extracting response schema from HTML."""
        body = '<html><body>Hello</body></html>'
        schema = SchemaExtractor.extract_response_schema(body, 'text/html')
        
        assert schema['type'] == 'string'
        assert schema['format'] == 'html'
    
    def test_handle_invalid_json(self):
        """Test handling of invalid JSON."""
        body = '{invalid json}'
        schema = SchemaExtractor.extract_request_schema(body, 'application/json')
        
        # Should fall back to string type
        assert schema['type'] == 'string'
    
    def test_handle_empty_body(self):
        """Test handling of empty body."""
        schema = SchemaExtractor.extract_request_schema(None, 'application/json')
        assert schema is None
        
        schema = SchemaExtractor.extract_request_schema('', 'application/json')
        assert schema is None
    
    def test_merge_schemas_with_same_properties(self):
        """Test merging schemas with same properties."""
        schema1 = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'integer'}
            },
            'required': ['name', 'age']
        }
        schema2 = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'integer'}
            },
            'required': ['name']
        }
        
        merged = SchemaExtractor.merge_schemas(schema1, schema2)
        
        assert merged['type'] == 'object'
        assert 'name' in merged['properties']
        assert 'age' in merged['properties']
        # Only common required fields should be in merged
        assert merged['required'] == ['name']
    
    def test_merge_schemas_with_different_properties(self):
        """Test merging schemas with different properties."""
        schema1 = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'}
            }
        }
        schema2 = {
            'type': 'object',
            'properties': {
                'email': {'type': 'string'}
            }
        }
        
        merged = SchemaExtractor.merge_schemas(schema1, schema2)
        
        assert merged['type'] == 'object'
        assert 'name' in merged['properties']
        assert 'email' in merged['properties']
    
    def test_merge_schemas_with_conflicting_types(self):
        """Test merging schemas with conflicting types."""
        schema1 = {'type': 'string'}
        schema2 = {'type': 'integer'}
        
        merged = SchemaExtractor.merge_schemas(schema1, schema2)
        
        # Should create a oneOf union
        assert 'oneOf' in merged
        assert len(merged['oneOf']) == 2
    
    def test_merge_array_schemas(self):
        """Test merging array schemas."""
        schema1 = {
            'type': 'array',
            'items': {'type': 'string'}
        }
        schema2 = {
            'type': 'array',
            'items': {'type': 'string'}
        }
        
        merged = SchemaExtractor.merge_schemas(schema1, schema2)
        
        assert merged['type'] == 'array'
        assert merged['items']['type'] == 'string'
    
    def test_merge_with_empty_schema(self):
        """Test merging with empty schemas."""
        schema1 = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
        schema2 = {}
        
        merged = SchemaExtractor.merge_schemas(schema1, schema2)
        assert merged == schema1
        
        merged = SchemaExtractor.merge_schemas({}, schema1)
        assert merged == schema1
    
    def test_is_json_content_type(self):
        """Test JSON content type detection."""
        assert SchemaExtractor._is_json_content('application/json')
        assert SchemaExtractor._is_json_content('application/ld+json')
        assert SchemaExtractor._is_json_content('application/vnd.api+json')
        assert SchemaExtractor._is_json_content('application/json; charset=utf-8')
        assert not SchemaExtractor._is_json_content('text/html')
        assert not SchemaExtractor._is_json_content(None)
    
    def test_extract_complex_nested_schema(self):
        """Test extracting complex nested schema with arrays and objects."""
        body = '''{
            "user": {
                "id": 123,
                "name": "John",
                "emails": ["john@example.com", "john2@example.com"],
                "address": {
                    "street": "123 Main St",
                    "city": "New York"
                }
            },
            "active": true
        }'''
        schema = SchemaExtractor.extract_request_schema(body, 'application/json')
        
        assert schema['type'] == 'object'
        assert 'user' in schema['properties']
        assert schema['properties']['user']['type'] == 'object'
        assert 'emails' in schema['properties']['user']['properties']
        assert schema['properties']['user']['properties']['emails']['type'] == 'array'
        assert 'address' in schema['properties']['user']['properties']
        assert schema['properties']['user']['properties']['address']['type'] == 'object'
        assert schema['properties']['active']['type'] == 'boolean'


class TestFormatDetection:
    """Tests for format detection helper methods."""
    
    def test_is_datetime(self):
        """Test datetime detection."""
        assert SchemaExtractor._is_datetime("2025-12-10T12:00:00Z")
        assert SchemaExtractor._is_datetime("2025-12-10 12:00:00")
        assert not SchemaExtractor._is_datetime("2025-12-10")
        assert not SchemaExtractor._is_datetime("not a date")
    
    def test_is_date(self):
        """Test date detection."""
        assert SchemaExtractor._is_date("2025-12-10")
        assert not SchemaExtractor._is_date("2025-12-10T12:00:00")
        assert not SchemaExtractor._is_date("12/10/2025")
    
    def test_is_email(self):
        """Test email detection."""
        assert SchemaExtractor._is_email("user@example.com")
        assert SchemaExtractor._is_email("test.user+tag@example.co.uk")
        assert not SchemaExtractor._is_email("not an email")
        assert not SchemaExtractor._is_email("@example.com")
    
    def test_is_uri(self):
        """Test URI detection."""
        assert SchemaExtractor._is_uri("https://example.com")
        assert SchemaExtractor._is_uri("http://example.com/path")
        assert not SchemaExtractor._is_uri("ftp://example.com")
        assert not SchemaExtractor._is_uri("example.com")
    
    def test_is_uuid(self):
        """Test UUID detection."""
        assert SchemaExtractor._is_uuid("550e8400-e29b-41d4-a716-446655440000")
        assert SchemaExtractor._is_uuid("123e4567-e89b-12d3-a456-426614174000")
        assert not SchemaExtractor._is_uuid("not-a-uuid")
        assert not SchemaExtractor._is_uuid("123-456-789")

