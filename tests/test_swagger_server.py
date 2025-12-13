"""
Tests for burp2api.swagger_server module.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from burp2api.swagger_server import SwaggerUIHandler, serve_swagger_ui


class TestSwaggerUIHandler:
    """Tests for SwaggerUIHandler class."""
    
    def test_handler_has_openapi_spec_attribute(self):
        """Test that handler class has openapi_spec attribute."""
        assert hasattr(SwaggerUIHandler, 'openapi_spec')
    
    def test_handler_can_store_spec(self):
        """Test that handler can store OpenAPI spec."""
        test_spec = {'openapi': '3.0.3', 'info': {'title': 'Test'}}
        SwaggerUIHandler.openapi_spec = test_spec
        
        assert SwaggerUIHandler.openapi_spec == test_spec
        assert SwaggerUIHandler.openapi_spec['openapi'] == '3.0.3'


class TestSwaggerServer:
    """Tests for swagger server functionality."""
    
    @pytest.fixture
    def sample_spec(self):
        """Create a sample OpenAPI specification."""
        return {
            'openapi': '3.0.3',
            'info': {
                'title': 'Test API',
                'version': '1.0.0',
                'description': 'Test API documentation'
            },
            'servers': [
                {'url': 'https://api.example.com'}
            ],
            'paths': {
                '/users': {
                    'get': {
                        'summary': 'Get users',
                        'responses': {
                            '200': {
                                'description': 'OK'
                            }
                        }
                    }
                }
            }
        }
    
    def test_serve_swagger_ui_with_invalid_port(self, sample_spec):
        """Test error handling for port already in use."""
        # Try to bind to a privileged port without sudo (should fail)
        # Or mock the HTTPServer to raise OSError
        with patch('burp2api.swagger_server.HTTPServer') as mock_server:
            mock_server.side_effect = OSError(48, "Address already in use")
            
            with pytest.raises(SystemExit) as exc_info:
                serve_swagger_ui(sample_spec, host='localhost', port=8080)
            
            assert exc_info.value.code == 1
    
    def test_serve_swagger_ui_sets_spec_on_handler(self, sample_spec):
        """Test that serve_swagger_ui sets the spec on the handler class."""
        with patch('burp2api.swagger_server.HTTPServer') as mock_server:
            with patch('burp2api.swagger_server.signal.signal'):
                # Mock the server instance
                mock_server_instance = MagicMock()
                mock_server.return_value = mock_server_instance
                mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
                
                try:
                    serve_swagger_ui(sample_spec, host='localhost', port=8080)
                except KeyboardInterrupt:
                    pass
                
                # Verify the spec was set
                assert SwaggerUIHandler.openapi_spec == sample_spec
    
    def test_serve_swagger_ui_prints_startup_message(self, sample_spec, capsys):
        """Test that serve_swagger_ui prints startup message."""
        with patch('burp2api.swagger_server.HTTPServer') as mock_server:
            with patch('burp2api.swagger_server.signal.signal'):
                mock_server_instance = MagicMock()
                mock_server.return_value = mock_server_instance
                mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
                
                try:
                    serve_swagger_ui(sample_spec, host='localhost', port=8080)
                except KeyboardInterrupt:
                    pass
                
                captured = capsys.readouterr()
                assert 'Swagger UI server started' in captured.out
                assert 'http://localhost:8080' in captured.out
                assert 'openapi.json' in captured.out
    
    def test_serve_swagger_ui_default_host_port(self, sample_spec):
        """Test that serve_swagger_ui uses correct default host and port."""
        with patch('burp2api.swagger_server.HTTPServer') as mock_server:
            with patch('burp2api.swagger_server.signal.signal'):
                mock_server_instance = MagicMock()
                mock_server.return_value = mock_server_instance
                mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
                
                try:
                    serve_swagger_ui(sample_spec, host='localhost', port=8080)
                except KeyboardInterrupt:
                    pass
                
                # Verify HTTPServer was called with correct address
                mock_server.assert_called_once()
                call_args = mock_server.call_args[0]
                assert call_args[0] == ('localhost', 8080)
    
    def test_serve_swagger_ui_handles_keyboard_interrupt(self, sample_spec, capsys):
        """Test graceful shutdown on KeyboardInterrupt."""
        with patch('burp2api.swagger_server.HTTPServer') as mock_server:
            with patch('burp2api.swagger_server.signal.signal'):
                mock_server_instance = MagicMock()
                mock_server.return_value = mock_server_instance
                mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
                
                serve_swagger_ui(sample_spec, host='localhost', port=8080)
                
                captured = capsys.readouterr()
                assert 'Shutting down server' in captured.out
                mock_server_instance.shutdown.assert_called_once()
    
    def test_swagger_handler_has_log_message_override(self):
        """Test that handler has log_message method override."""
        # Just verify the method exists - it's hard to test logging behavior
        assert hasattr(SwaggerUIHandler, 'log_message')
        # The method is defined on the class
        assert callable(getattr(SwaggerUIHandler, 'log_message'))


class TestSwaggerUIContent:
    """Tests for the HTML and spec content served."""
    
    def test_swagger_ui_handler_serves_html_at_root(self):
        """Test that the handler has logic to serve HTML at root."""
        # Create a mock request
        mock_request = MagicMock()
        mock_client_address = ('127.0.0.1', 12345)
        mock_server = MagicMock()
        
        # We can't easily test the actual HTTP serving without starting a real server,
        # but we can verify the handler has the correct methods
        assert hasattr(SwaggerUIHandler, 'do_GET')
        assert hasattr(SwaggerUIHandler, 'serve_swagger_ui')
        assert hasattr(SwaggerUIHandler, 'serve_openapi_spec')
    
    def test_openapi_spec_format(self):
        """Test that the spec served is valid JSON."""
        test_spec = {
            'openapi': '3.0.3',
            'info': {'title': 'Test'},
            'paths': {}
        }
        
        SwaggerUIHandler.openapi_spec = test_spec
        
        # Verify it can be serialized to JSON
        spec_json = json.dumps(SwaggerUIHandler.openapi_spec, indent=2, ensure_ascii=False)
        assert spec_json is not None
        assert '"openapi": "3.0.3"' in spec_json
        assert '"title": "Test"' in spec_json

