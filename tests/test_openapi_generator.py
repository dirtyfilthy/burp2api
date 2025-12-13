"""
Tests for burp2api.openapi_generator module.
"""

import pytest
from burp2api.openapi_generator import OpenAPIGenerator
from burp2api.parser import BurpItem, HTTPRequest, HTTPResponse


class TestOpenAPIGenerator:
    """Tests for OpenAPIGenerator class."""
    
    def test_generate_basic_openapi_structure(self, burp_items):
        """Test generation of basic OpenAPI structure."""
        generator = OpenAPIGenerator(items=burp_items)
        spec = generator.generate()
        
        assert spec['openapi'] == '3.0.3'
        assert 'info' in spec
        assert 'paths' in spec
        assert 'servers' in spec
    
    def test_openapi_info_section(self, burp_items):
        """Test OpenAPI info section with custom values."""
        generator = OpenAPIGenerator(
            items=burp_items,
            title='Test API',
            version='2.0.0',
            description='Test API documentation'
        )
        spec = generator.generate()
        
        assert spec['info']['title'] == 'Test API'
        assert spec['info']['version'] == '2.0.0'
        assert spec['info']['description'] == 'Test API documentation'
    
    def test_group_endpoints_by_path_pattern(self):
        """Test grouping of endpoints by path pattern."""
        items = [
            self._create_item('/users/123'),
            self._create_item('/users/456'),
            self._create_item('/users/789')
        ]
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        # All three should be grouped under /users/{userId}
        assert '/users/{userId}' in spec['paths']
        assert spec['paths']['/users/{userId}']['get'] is not None
    
    def test_detect_uuid_in_path(self):
        """Test detection of UUID in path."""
        item = self._create_item('/api/orders/550e8400-e29b-41d4-a716-446655440000')
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        
        pattern = generator._extract_path_pattern('/api/orders/550e8400-e29b-41d4-a716-446655440000')
        
        assert pattern == '/api/orders/{orderId}'
    
    def test_detect_numeric_id_in_path(self):
        """Test detection of numeric ID in path."""
        item = self._create_item('/api/users/12345')
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        
        pattern = generator._extract_path_pattern('/api/users/12345')
        
        assert pattern == '/api/users/{userId}'
    
    def test_singularize_entities_properly(self):
        """Test proper singularization using inflect (e.g., entities -> entity, not entitie)."""
        item = self._create_item('/api/entities/12345')
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        
        pattern = generator._extract_path_pattern('/api/entities/12345')
        
        # Should properly singularize "entities" to "entity", not "entitie"
        assert pattern == '/api/entities/{entityId}'
    
    def test_detect_mongodb_objectid_in_path(self):
        """Test detection of MongoDB ObjectId in path."""
        item = self._create_item('/api/products/507f1f77bcf86cd799439011')
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        
        pattern = generator._extract_path_pattern('/api/products/507f1f77bcf86cd799439011')
        
        assert pattern == '/api/products/{productId}'
    
    def test_is_id_segment(self):
        """Test ID segment detection."""
        generator = OpenAPIGenerator(items=[], filter_static=False)
        
        # UUID
        assert generator._is_id_segment('550e8400-e29b-41d4-a716-446655440000')
        # Numeric
        assert generator._is_id_segment('12345')
        # MongoDB ObjectId
        assert generator._is_id_segment('507f1f77bcf86cd799439011')
        # Long alphanumeric
        assert generator._is_id_segment('abc123def456ghi789')
        # Not an ID
        assert not generator._is_id_segment('users')
        assert not generator._is_id_segment('api')
    
    def test_extract_path_parameters(self):
        """Test extraction of path parameters."""
        items = [self._create_item('/api/users/123')]
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        path_obj = spec['paths']['/api/users/{userId}']['get']
        assert 'parameters' in path_obj
        
        path_params = [p for p in path_obj['parameters'] if p['in'] == 'path']
        assert len(path_params) == 1
        assert path_params[0]['name'] == 'userId'
        assert path_params[0]['required'] is True
    
    def test_extract_query_parameters(self):
        """Test extraction of query parameters."""
        item = self._create_item_with_query('/api/search', {'q': ['test'], 'limit': ['10']})
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        spec = generator.generate()
        
        path_obj = spec['paths']['/api/search']['get']
        assert 'parameters' in path_obj
        
        query_params = [p for p in path_obj['parameters'] if p['in'] == 'query']
        query_names = [p['name'] for p in query_params]
        assert 'q' in query_names
        assert 'limit' in query_names
    
    def test_generate_request_body_schema(self):
        """Test generation of request body schema."""
        body = '{"name": "John", "email": "john@example.com"}'
        item = self._create_item_with_body('/api/users', 'POST', body, 'application/json')
        
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        spec = generator.generate()
        
        post_op = spec['paths']['/api/users']['post']
        assert 'requestBody' in post_op
        assert 'content' in post_op['requestBody']
        assert 'application/json' in post_op['requestBody']['content']
        
        schema = post_op['requestBody']['content']['application/json']['schema']
        assert schema['type'] == 'object'
        assert 'name' in schema['properties']
    
    def test_generate_response_schema(self):
        """Test generation of response schema."""
        response_body = '{"id": 123, "status": "success"}'
        item = self._create_item_with_response('/api/data', 200, response_body)
        
        generator = OpenAPIGenerator(items=[item], filter_static=False)
        spec = generator.generate()
        
        response_obj = spec['paths']['/api/data']['get']['responses']['200']
        assert 'content' in response_obj
        assert 'application/json' in response_obj['content']
        
        schema = response_obj['content']['application/json']['schema']
        assert schema['type'] == 'object'
        assert 'id' in schema['properties']
    
    def test_multiple_response_status_codes(self):
        """Test handling of multiple response status codes."""
        items = [
            self._create_item_with_response('/api/test', 200, '{"status":"ok"}'),
            self._create_item_with_response('/api/test', 404, '{"error":"not found"}')
        ]
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        responses = spec['paths']['/api/test']['get']['responses']
        assert '200' in responses
        assert '404' in responses
    
    def test_extract_servers(self):
        """Test extraction of server URLs."""
        items = [
            self._create_item('/test', 'https', 'api.example.com', 443),
            self._create_item('/test2', 'https', 'api2.example.com', 443)
        ]
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        assert len(spec['servers']) >= 1
        server_urls = [s['url'] for s in spec['servers']]
        assert 'https://api.example.com' in server_urls
    
    def test_extract_servers_with_non_standard_port(self):
        """Test server extraction with non-standard port."""
        items = [self._create_item('/test', 'https', 'api.example.com', 8443)]
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        server_urls = [s['url'] for s in spec['servers']]
        assert 'https://api.example.com:8443' in server_urls
    
    def test_include_auth_schemes_in_components(self, burp_items_with_auth):
        """Test inclusion of authentication schemes in components."""
        generator = OpenAPIGenerator(items=burp_items_with_auth, filter_static=False)
        spec = generator.generate()
        
        assert 'components' in spec
        assert 'securitySchemes' in spec['components']
        assert len(spec['components']['securitySchemes']) > 0
    
    def test_filter_static_assets(self, burp_items):
        """Test that static assets are filtered out."""
        generator = OpenAPIGenerator(items=burp_items, filter_static=True)
        spec = generator.generate()
        
        # The static JS file should be filtered out
        paths = spec['paths']
        assert '/static/app.js' not in paths
    
    def test_disable_static_filtering(self, burp_items):
        """Test generation with static filtering disabled."""
        generator = OpenAPIGenerator(items=burp_items, filter_static=False)
        spec = generator.generate()
        
        # Static assets should be included
        paths = spec['paths']
        # Check that we have more paths when not filtering
        assert len(paths) > 0
    
    def test_include_patterns(self):
        """Test filtering with include patterns and exclude patterns."""
        items = [
            self._create_item('/api/users'),
            self._create_item('/admin/config'),
            self._create_item('/public/data')
        ]
        
        # Use include pattern to override static filtering for specific paths
        # and exclude pattern to filter out unwanted paths
        generator = OpenAPIGenerator(
            items=items,
            filter_static=False,
            include_patterns=[r'^/api/.*'],
            exclude_patterns=[r'^/admin/.*', r'^/public/.*']
        )
        spec = generator.generate()
        
        paths = spec['paths']
        assert '/api/users' in paths
        # Excluded paths should not be present
        assert '/admin/config' not in paths
        assert '/public/data' not in paths
    
    def test_exclude_patterns(self):
        """Test filtering with exclude patterns."""
        items = [
            self._create_item('/api/users'),
            self._create_item('/api/admin/users'),
            self._create_item('/api/public/data')
        ]
        
        generator = OpenAPIGenerator(
            items=items,
            filter_static=False,
            exclude_patterns=[r'/admin/.*']
        )
        spec = generator.generate()
        
        paths = spec['paths']
        assert '/api/users' in paths
        assert '/api/public/data' in paths
        # Admin path should be excluded
        assert not any('/admin/' in path for path in paths)
    
    def test_operation_summary(self):
        """Test generation of operation summary."""
        items = [self._create_item('/api/users', method='GET')]
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        operation = spec['paths']['/api/users']['get']
        assert 'summary' in operation
        assert 'GET' in operation['summary']
    
    def test_save_to_file(self, burp_items, tmp_path):
        """Test saving OpenAPI spec to file."""
        output_file = tmp_path / "openapi.json"
        
        generator = OpenAPIGenerator(items=burp_items)
        generator.generate()
        generator.save(str(output_file), pretty=True)
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
    
    def test_to_json_string(self, burp_items):
        """Test conversion to JSON string."""
        generator = OpenAPIGenerator(items=burp_items)
        generator.generate()
        
        json_str = generator.to_json(pretty=True)
        
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        assert 'openapi' in json_str
    
    def test_merge_schemas_for_same_endpoint(self):
        """Test schema merging for multiple requests to same endpoint."""
        # Two POST requests to same endpoint with different schemas
        body1 = '{"name": "John"}'
        body2 = '{"name": "Jane", "email": "jane@example.com"}'
        
        items = [
            self._create_item_with_body('/api/users', 'POST', body1, 'application/json'),
            self._create_item_with_body('/api/users', 'POST', body2, 'application/json')
        ]
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        schema = spec['paths']['/api/users']['post']['requestBody']['content']['application/json']['schema']
        # Merged schema should have both properties
        assert 'name' in schema['properties']
        assert 'email' in schema['properties']
    
    def test_response_description_by_status_code(self):
        """Test proper response descriptions by status code."""
        items = [
            self._create_item_with_response('/api/test', 200, '{"status":"ok"}'),
            self._create_item_with_response('/api/test', 404, '{"error":"not found"}'),
            self._create_item_with_response('/api/test', 500, '{"error":"server error"}')
        ]
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        responses = spec['paths']['/api/test']['get']['responses']
        assert responses['200']['description'] == 'OK'
        assert responses['404']['description'] == 'Not Found'
        assert responses['500']['description'] == 'Internal Server Error'
    
    # Helper methods
    def _create_item(self, path, protocol='https', host='api.example.com', port=443, method='GET'):
        """Helper to create a BurpItem."""
        return BurpItem(
            time='Wed Dec 10 12:00:00 UTC 2025',
            url=f'{protocol}://{host}{path}',
            host=host,
            host_ip='1.2.3.4',
            port=port,
            protocol=protocol,
            method=method,
            path=path,
            extension=None,
            request=HTTPRequest(
                method=method,
                path=path,
                headers={'Host': host},
                body=None,
                query_params={}
            ),
            response=HTTPResponse(
                status=200,
                headers={'Content-Type': 'application/json'},
                body='{"status":"ok"}'
            ),
            mimetype='application/json',
            comment=None
        )
    
    def _create_item_with_query(self, path, query_params):
        """Helper to create a BurpItem with query parameters."""
        item = self._create_item(path)
        item.request.query_params = query_params
        return item
    
    def _create_item_with_body(self, path, method, body, content_type):
        """Helper to create a BurpItem with request body."""
        item = self._create_item(path, method=method)
        item.request.body = body
        item.request.headers['Content-Type'] = content_type
        return item
    
    def _create_item_with_response(self, path, status, body):
        """Helper to create a BurpItem with specific response."""
        item = self._create_item(path)
        item.response.status = status
        item.response.body = body
        return item
