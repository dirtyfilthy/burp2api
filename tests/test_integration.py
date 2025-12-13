"""
Integration tests for burp2api.

These tests validate end-to-end workflows from parsing to OpenAPI generation.
"""

import pytest
import json
from pathlib import Path

from burp2api import BurpParser, OpenAPIGenerator, StaticAssetFilter, AuthDetector, SchemaExtractor


class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    def test_complete_workflow_parse_filter_generate(self, sample_burp_file):
        """Test complete workflow: parse → filter → generate."""
        # Step 1: Parse
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        assert len(items) > 0
        
        # Step 2: Filter
        filter_obj = StaticAssetFilter(filter_static=True)
        filtered_items = filter_obj.filter_items(items)
        
        assert len(filtered_items) <= len(items)
        
        # Step 3: Generate OpenAPI
        generator = OpenAPIGenerator(items=filtered_items, filter_static=False)
        spec = generator.generate()
        
        # Verify complete spec
        assert spec['openapi'] == '3.0.3'
        assert 'info' in spec
        assert 'paths' in spec
        assert 'servers' in spec
        assert len(spec['paths']) > 0
    
    def test_workflow_with_json_bodies(self, burp_with_json_file):
        """Test workflow with JSON request/response bodies."""
        # Parse
        parser = BurpParser(str(burp_with_json_file))
        items = parser.parse()
        
        # Generate without filtering (no static assets in this file)
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        # Verify schemas were extracted
        assert 'paths' in spec
        paths = spec['paths']
        
        # Check that at least one operation has request body with schema
        has_request_body = False
        for path_obj in paths.values():
            for operation in path_obj.values():
                if 'requestBody' in operation:
                    has_request_body = True
                    assert 'content' in operation['requestBody']
                    break
        
        assert has_request_body
    
    def test_workflow_with_authentication(self, burp_with_auth_file):
        """Test workflow with authentication detection."""
        # Parse
        parser = BurpParser(str(burp_with_auth_file))
        items = parser.parse()
        
        # Detect auth manually
        auth_detector = AuthDetector()
        auth_schemes = auth_detector.detect_auth_schemes(items)
        
        assert len(auth_schemes) > 0
        
        # Generate OpenAPI with auth
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        # Verify auth schemes in components
        assert 'components' in spec
        assert 'securitySchemes' in spec['components']
        assert len(spec['components']['securitySchemes']) > 0
    
    def test_verify_openapi_spec_structure(self, sample_burp_file):
        """Test that generated spec has all required OpenAPI 3.0.3 fields."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        generator = OpenAPIGenerator(items=items)
        spec = generator.generate()
        
        # Required OpenAPI 3.0.3 fields
        assert 'openapi' in spec
        assert spec['openapi'] == '3.0.3'
        
        # Info object
        assert 'info' in spec
        assert 'title' in spec['info']
        assert 'version' in spec['info']
        
        # Paths object
        assert 'paths' in spec
        assert isinstance(spec['paths'], dict)
        
        # Servers array
        assert 'servers' in spec
        assert isinstance(spec['servers'], list)
        assert len(spec['servers']) > 0
    
    def test_verify_paths_and_operations(self, sample_burp_file):
        """Test that paths and operations are correctly structured."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        generator = OpenAPIGenerator(items=items)
        spec = generator.generate()
        
        paths = spec['paths']
        assert len(paths) > 0
        
        for path, path_item in paths.items():
            # Path should be a string starting with /
            assert isinstance(path, str)
            assert path.startswith('/')
            
            # Path item should have at least one operation
            assert len(path_item) > 0
            
            # Check operation structure
            for method, operation in path_item.items():
                assert method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']
                assert 'responses' in operation
                assert len(operation['responses']) > 0
    
    def test_verify_response_schemas(self, burp_with_json_file):
        """Test that response schemas are properly extracted."""
        parser = BurpParser(str(burp_with_json_file))
        items = parser.parse()
        
        generator = OpenAPIGenerator(items=items, filter_static=False)
        spec = generator.generate()
        
        # Find operations with responses that have bodies
        has_response_schema = False
        for path_obj in spec['paths'].values():
            for operation in path_obj.values():
                for status_code, response in operation['responses'].items():
                    if 'content' in response:
                        has_response_schema = True
                        content = response['content']
                        
                        # Should have at least one content type
                        assert len(content) > 0
                        
                        # Each content type should have a schema
                        for content_type, content_obj in content.items():
                            assert 'schema' in content_obj
                            assert 'type' in content_obj['schema']
        
        assert has_response_schema
    
    def test_verify_servers_extracted(self, sample_burp_file):
        """Test that servers are correctly extracted from Burp items."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        generator = OpenAPIGenerator(items=items)
        spec = generator.generate()
        
        servers = spec['servers']
        assert len(servers) > 0
        
        for server in servers:
            assert 'url' in server
            assert server['url'].startswith('http://') or server['url'].startswith('https://')
    
    def test_workflow_with_custom_filtering(self, sample_burp_file):
        """Test workflow with custom include/exclude patterns."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # Filter with exclude pattern to remove unwanted paths
        generator = OpenAPIGenerator(
            items=items,
            filter_static=True,
            exclude_patterns=[r'/posts']
        )
        spec = generator.generate()
        
        paths = spec['paths']
        # Excluded paths should not be present
        for path in paths:
            assert '/posts' not in path
    
    def test_save_and_load_generated_spec(self, sample_burp_file, tmp_path):
        """Test saving generated spec to file and loading it back."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        generator = OpenAPIGenerator(items=items)
        spec_original = generator.generate()
        
        # Save to file
        output_file = tmp_path / "openapi.json"
        generator.save(str(output_file), pretty=True)
        
        assert output_file.exists()
        
        # Load from file
        with open(output_file) as f:
            spec_loaded = json.load(f)
        
        # Should be identical
        assert spec_loaded['openapi'] == spec_original['openapi']
        assert spec_loaded['info'] == spec_original['info']
        assert len(spec_loaded['paths']) == len(spec_original['paths'])


class TestLibraryAPI:
    """Test the public library API."""
    
    def test_import_main_classes(self):
        """Test that main classes can be imported from burp2api."""
        from burp2api import (
            BurpParser,
            OpenAPIGenerator,
            StaticAssetFilter,
            SchemaExtractor,
            AuthDetector
        )
        
        assert BurpParser is not None
        assert OpenAPIGenerator is not None
        assert StaticAssetFilter is not None
        assert SchemaExtractor is not None
        assert AuthDetector is not None
    
    def test_library_api_workflow(self, sample_burp_file):
        """Test using the library API as documented in README."""
        from burp2api import BurpParser, OpenAPIGenerator
        
        # Parse Burp Suite export
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        assert len(items) > 0
        
        # Generate OpenAPI specification
        generator = OpenAPIGenerator(
            items=items,
            filter_static=True,
            title="Test API",
            version="1.0.0",
            description="Test API documentation"
        )
        
        # Generate the spec
        openapi_spec = generator.generate()
        
        assert openapi_spec is not None
        assert openapi_spec['info']['title'] == "Test API"
        
        # Get as JSON string
        json_string = generator.to_json(pretty=True)
        
        assert isinstance(json_string, str)
        assert len(json_string) > 0
    
    def test_manual_filtering_workflow(self, sample_burp_file):
        """Test manual filtering and schema extraction workflow."""
        from burp2api import (
            BurpParser,
            StaticAssetFilter,
            SchemaExtractor,
            AuthDetector
        )
        
        # Parse
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # Filter
        filter_obj = StaticAssetFilter(filter_static=True)
        filtered_items = filter_obj.filter_items(items)
        
        assert len(filtered_items) <= len(items)
        
        # Detect authentication
        auth_detector = AuthDetector()
        auth_schemes = auth_detector.detect_auth_schemes(filtered_items)
        
        assert isinstance(auth_schemes, dict)
        
        # Extract schemas from individual items
        schema_extractor = SchemaExtractor()
        for item in filtered_items[:5]:  # Check first 5 items
            if item.request.body:
                schema = schema_extractor.extract_request_schema(
                    item.request.body,
                    item.request.headers.get('Content-Type')
                )
                assert schema is not None or item.request.body == ''


class TestErrorHandling:
    """Test error handling in integration scenarios."""
    
    def test_handle_empty_burp_export(self, tmp_path):
        """Test handling of empty Burp export file."""
        # Create empty items file
        empty_file = tmp_path / "empty.xml"
        empty_file.write_text('<?xml version="1.0"?><items></items>')
        
        parser = BurpParser(str(empty_file))
        items = parser.parse()
        
        assert len(items) == 0
        
        # Should still generate valid (but empty) OpenAPI spec
        generator = OpenAPIGenerator(items=items)
        spec = generator.generate()
        
        assert spec['openapi'] == '3.0.3'
        assert len(spec['paths']) == 0
    
    def test_handle_all_items_filtered(self, sample_burp_file):
        """Test when all items are filtered out."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # Filter with pattern that matches nothing
        generator = OpenAPIGenerator(
            items=items,
            filter_static=True,
            include_patterns=[r'/nonexistent/.*']
        )
        spec = generator.generate()
        
        # Should generate valid spec with no paths
        assert spec['openapi'] == '3.0.3'
        assert 'paths' in spec

