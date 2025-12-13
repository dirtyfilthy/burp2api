"""
Tests for burp2api.parser module.
"""

import pytest
import tempfile
import os
from pathlib import Path

from burp2api.parser import BurpParser, BurpItem, HTTPRequest, HTTPResponse


class TestBurpParser:
    """Tests for BurpParser class."""

    def test_parse_valid_burp_export(self, sample_burp_file):
        """Test parsing a valid Burp Suite export file."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        assert len(items) == 5
        assert all(isinstance(item, BurpItem) for item in items)
    
    def test_parse_single_item(self, temp_xml_file):
        """Test parsing file with single item."""
        parser = BurpParser(temp_xml_file)
        items = parser.parse()
        
        assert len(items) == 1
        item = items[0]
        assert item.method == 'GET'
        assert item.path == '/test'
        assert item.host == 'api.example.com'
    
    def test_parse_base64_encoded_request(self, sample_burp_file):
        """Test parsing base64-encoded request data."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # First two items have base64 encoded requests
        item = items[0]
        assert item.request.method == 'GET'
        assert item.request.path == '/users'
        assert 'Host' in item.request.headers
    
    def test_parse_base64_encoded_response(self, sample_burp_file):
        """Test parsing base64-encoded response data."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.response.status == 200
        assert 'Content-Type' in item.response.headers
        assert item.response.body is not None
    
    def test_parse_non_base64_request(self, sample_burp_file):
        """Test parsing non-base64 encoded request."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # Third item is not base64 encoded
        item = items[2]
        assert item.request.method == 'GET'
        assert '/posts' in item.request.path
    
    def test_parse_request_with_body(self, sample_burp_file):
        """Test parsing request with body content."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # POST request has a body
        post_item = items[4]
        assert post_item.method == 'POST'
        assert post_item.request.body is not None
        assert 'username' in post_item.request.body
        assert 'newuser' in post_item.request.body
    
    def test_parse_response_with_body(self, sample_burp_file):
        """Test parsing response with body content."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.response.body is not None
        assert len(item.response.body) > 0
    
    def test_parse_query_parameters(self, sample_burp_file):
        """Test extraction of query parameters from URL."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # Third item has query params
        item = items[2]
        assert 'page' in item.request.query_params
        assert 'limit' in item.request.query_params
        assert item.request.query_params['page'] == ['1']
        assert item.request.query_params['limit'] == ['10']
    
    def test_parse_headers_in_request(self, sample_burp_file):
        """Test parsing headers from request."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert 'Host' in item.request.headers
        assert item.request.headers['Host'] == 'api.example.com'
        assert 'Accept' in item.request.headers
    
    def test_parse_headers_in_response(self, sample_burp_file):
        """Test parsing headers from response."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert 'Content-Type' in item.response.headers
        assert 'application/json' in item.response.headers['Content-Type']
    
    def test_parse_item_with_extension(self, sample_burp_file):
        """Test parsing item with file extension."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        # Fourth item is a JS file
        js_item = items[3]
        assert js_item.extension == 'js'
        assert js_item.path == '/static/app.js'
    
    def test_parse_item_without_extension(self, sample_burp_file):
        """Test parsing item without file extension."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.extension == ''
    
    def test_parse_different_http_methods(self, sample_burp_file):
        """Test parsing different HTTP methods."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        methods = [item.method for item in items]
        assert 'GET' in methods
        assert 'POST' in methods
    
    def test_parse_different_status_codes(self, sample_burp_file):
        """Test parsing different response status codes."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        status_codes = [item.response.status for item in items]
        assert 200 in status_codes
        assert 201 in status_codes
    
    def test_parse_protocol_and_port(self, sample_burp_file):
        """Test parsing protocol and port information."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.protocol == 'https'
        assert item.port == 443
    
    def test_parse_host_with_ip(self, sample_burp_file):
        """Test parsing host with IP address attribute."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.host == 'api.example.com'
        assert item.host_ip == '93.184.216.34'
    
    def test_parse_mimetype(self, sample_burp_file):
        """Test parsing MIME type."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.mimetype == 'application/json'
        
        js_item = items[3]
        assert js_item.mimetype == 'application/javascript'
    
    def test_parse_empty_comment(self, sample_burp_file):
        """Test parsing empty comment field."""
        parser = BurpParser(str(sample_burp_file))
        items = parser.parse()
        
        item = items[0]
        assert item.comment == ''
    
    def test_parse_file_not_found(self):
        """Test handling of non-existent file."""
        parser = BurpParser('/nonexistent/file.xml')
        
        with pytest.raises(FileNotFoundError):
            parser.parse()
    
    def test_parse_malformed_xml(self, invalid_burp_file):
        """Test handling of malformed XML."""
        parser = BurpParser(str(invalid_burp_file))
        
        with pytest.raises(Exception):
            parser.parse()
    
    def test_parse_empty_xml(self):
        """Test parsing XML with no items."""
        xml_content = '<?xml version="1.0"?><items></items>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            parser = BurpParser(temp_path)
            items = parser.parse()
            assert len(items) == 0
        finally:
            os.unlink(temp_path)


class TestHTTPRequest:
    """Tests for HTTPRequest dataclass."""
    
    def test_http_request_creation(self):
        """Test creating HTTPRequest object."""
        request = HTTPRequest(
            method='POST',
            path='/api/test',
            headers={'Content-Type': 'application/json'},
            body='{"test": true}',
            query_params={'key': ['value']}
        )
        
        assert request.method == 'POST'
        assert request.path == '/api/test'
        assert request.headers['Content-Type'] == 'application/json'
        assert request.body == '{"test": true}'
        assert request.query_params['key'] == ['value']


class TestHTTPResponse:
    """Tests for HTTPResponse dataclass."""
    
    def test_http_response_creation(self):
        """Test creating HTTPResponse object."""
        response = HTTPResponse(
            status=200,
            headers={'Content-Type': 'application/json'},
            body='{"status": "ok"}'
        )
        
        assert response.status == 200
        assert response.headers['Content-Type'] == 'application/json'
        assert response.body == '{"status": "ok"}'


class TestBurpItem:
    """Tests for BurpItem dataclass."""
    
    def test_burp_item_creation(self, sample_request, sample_response):
        """Test creating BurpItem object."""
        item = BurpItem(
            time='Wed Dec 10 12:00:00 UTC 2025',
            url='https://api.example.com/test',
            host='api.example.com',
            host_ip='93.184.216.34',
            port=443,
            protocol='https',
            method='GET',
            path='/test',
            extension='',
            request=sample_request,
            response=sample_response,
            mimetype='application/json',
            comment=None
        )
        
        assert item.host == 'api.example.com'
        assert item.method == 'GET'
        assert item.protocol == 'https'
        assert isinstance(item.request, HTTPRequest)
        assert isinstance(item.response, HTTPResponse)

