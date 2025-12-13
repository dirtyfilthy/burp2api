"""
Tests for burp2api.auth_detector module.
"""

import pytest
from burp2api.auth_detector import AuthDetector, AuthScheme
from burp2api.parser import BurpItem, HTTPRequest, HTTPResponse


class TestAuthDetector:
    """Tests for AuthDetector class."""
    
    def test_detect_bearer_token(self):
        """Test detection of Bearer token authentication."""
        items = [self._create_item_with_auth('Bearer eyJhbGc...')]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        assert 'bearerAuth' in schemes
        assert schemes['bearerAuth'].scheme_type == 'http'
        assert schemes['bearerAuth'].in_location == 'header'
    
    def test_detect_basic_auth(self):
        """Test detection of Basic authentication."""
        items = [self._create_item_with_auth('Basic dGVzdDp0ZXN0')]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        assert 'basicAuth' in schemes
        assert schemes['basicAuth'].scheme_type == 'http'
    
    def test_detect_api_key_in_header(self):
        """Test detection of API key in custom header."""
        items = [self._create_item_with_header('X-API-Key', 'secret123')]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        assert 'apiKey_X-API-Key' in schemes
        assert schemes['apiKey_X-API-Key'].scheme_type == 'apiKey'
        assert schemes['apiKey_X-API-Key'].in_location == 'header'
        assert schemes['apiKey_X-API-Key'].parameter_name == 'X-API-Key'
    
    def test_detect_api_key_variations_in_header(self):
        """Test detection of various API key header names."""
        header_names = ['X-Api-Key', 'ApiKey', 'X-API-Token', 'X-Auth-Token']
        
        for header_name in header_names:
            items = [self._create_item_with_header(header_name, 'secret')]
            detector = AuthDetector()
            schemes = detector.detect_auth_schemes(items)
            
            assert len(schemes) > 0
            # Should detect at least one API key scheme
            api_key_schemes = [s for s in schemes.values() if s.scheme_type == 'apiKey']
            assert len(api_key_schemes) > 0
    
    def test_detect_api_key_in_query_param(self):
        """Test detection of API key in query parameter."""
        items = [self._create_item_with_query_param('apikey', 'secret123')]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        assert 'apiKey_apikey' in schemes
        assert schemes['apiKey_apikey'].scheme_type == 'apiKey'
        assert schemes['apiKey_apikey'].in_location == 'query'
    
    def test_detect_session_cookie(self):
        """Test detection of session cookies."""
        items = [self._create_item_with_cookie('connect.sid=s%3Aj6dT8...')]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        assert 'cookie_connect.sid' in schemes
        assert schemes['cookie_connect.sid'].scheme_type == 'apiKey'
        assert schemes['cookie_connect.sid'].in_location == 'cookie'
    
    def test_detect_multiple_session_cookies(self):
        """Test detection of multiple session cookies."""
        items = [self._create_item_with_cookie('sessionid=abc123; connect.sid=xyz')]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        # Should detect both session cookies
        assert 'cookie_sessionid' in schemes
        assert 'cookie_connect.sid' in schemes
    
    def test_detect_multiple_auth_schemes(self, burp_items_with_auth):
        """Test detection of multiple authentication schemes."""
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(burp_items_with_auth)
        
        # The auth fixture has Bearer, Basic, API key in query, and cookies
        assert len(schemes) >= 3
        assert any('bearer' in name.lower() for name in schemes.keys())
        assert any('basic' in name.lower() for name in schemes.keys())
    
    def test_no_auth_detection(self):
        """Test handling of items without authentication."""
        items = [self._create_item()]
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes(items)
        
        assert len(schemes) == 0
    
    def test_empty_items_list(self):
        """Test handling of empty items list."""
        detector = AuthDetector()
        schemes = detector.detect_auth_schemes([])
        
        assert len(schemes) == 0
    
    def test_convert_to_openapi_bearer_scheme(self):
        """Test conversion of Bearer auth to OpenAPI format."""
        items = [self._create_item_with_auth('Bearer token123')]
        detector = AuthDetector()
        detector.detect_auth_schemes(items)
        
        openapi_schemes = detector.to_openapi_security_schemes()
        
        assert 'bearerAuth' in openapi_schemes
        assert openapi_schemes['bearerAuth']['type'] == 'http'
        assert openapi_schemes['bearerAuth']['scheme'] == 'bearer'
        assert openapi_schemes['bearerAuth']['bearerFormat'] == 'JWT'
    
    def test_convert_to_openapi_basic_scheme(self):
        """Test conversion of Basic auth to OpenAPI format."""
        items = [self._create_item_with_auth('Basic credentials')]
        detector = AuthDetector()
        detector.detect_auth_schemes(items)
        
        openapi_schemes = detector.to_openapi_security_schemes()
        
        assert 'basicAuth' in openapi_schemes
        assert openapi_schemes['basicAuth']['type'] == 'http'
        assert openapi_schemes['basicAuth']['scheme'] == 'basic'
    
    def test_convert_to_openapi_api_key_scheme(self):
        """Test conversion of API key to OpenAPI format."""
        items = [self._create_item_with_header('X-API-Key', 'secret')]
        detector = AuthDetector()
        detector.detect_auth_schemes(items)
        
        openapi_schemes = detector.to_openapi_security_schemes()
        
        assert 'apiKey_X-API-Key' in openapi_schemes
        assert openapi_schemes['apiKey_X-API-Key']['type'] == 'apiKey'
        assert openapi_schemes['apiKey_X-API-Key']['in'] == 'header'
        assert openapi_schemes['apiKey_X-API-Key']['name'] == 'X-API-Key'
    
    def test_is_api_key_header(self):
        """Test API key header detection method."""
        detector = AuthDetector()
        
        assert detector._is_api_key_header('X-API-Key')
        assert detector._is_api_key_header('x-api-key')
        assert detector._is_api_key_header('ApiKey')
        assert detector._is_api_key_header('X-Auth-Token')
        assert not detector._is_api_key_header('Content-Type')
        assert not detector._is_api_key_header('Authorization')
    
    def test_is_api_key_param(self):
        """Test API key parameter detection method."""
        detector = AuthDetector()
        
        assert detector._is_api_key_param('apikey')
        assert detector._is_api_key_param('api_key')
        assert detector._is_api_key_param('token')
        assert detector._is_api_key_param('access_token')
        assert not detector._is_api_key_param('page')
        assert not detector._is_api_key_param('limit')
    
    def test_is_session_cookie(self):
        """Test session cookie detection method."""
        detector = AuthDetector()
        
        assert detector._is_session_cookie('connect.sid')
        assert detector._is_session_cookie('sessionid')
        assert detector._is_session_cookie('PHPSESSID')
        assert detector._is_session_cookie('session')
        assert not detector._is_session_cookie('preferences')
        assert not detector._is_session_cookie('theme')
    
    def test_extract_cookie_names(self):
        """Test cookie name extraction."""
        detector = AuthDetector()
        cookie_header = 'sessionid=abc123; connect.sid=xyz; token=test'
        
        names = detector._extract_cookie_names(cookie_header)
        
        assert 'sessionid' in names
        assert 'connect.sid' in names
        assert 'token' in names
        assert len(names) == 3
    
    # Helper methods
    def _create_item(self):
        """Create a basic BurpItem without auth."""
        return BurpItem(
            time='Wed Dec 10 12:00:00 UTC 2025',
            url='https://api.example.com/test',
            host='api.example.com',
            host_ip='1.2.3.4',
            port=443,
            protocol='https',
            method='GET',
            path='/test',
            extension=None,
            request=HTTPRequest(
                method='GET',
                path='/test',
                headers={},
                body=None,
                query_params={}
            ),
            response=HTTPResponse(status=200, headers={}, body=None),
            mimetype=None,
            comment=None
        )
    
    def _create_item_with_auth(self, auth_value):
        """Create BurpItem with Authorization header."""
        item = self._create_item()
        item.request.headers['Authorization'] = auth_value
        return item
    
    def _create_item_with_header(self, header_name, header_value):
        """Create BurpItem with custom header."""
        item = self._create_item()
        item.request.headers[header_name] = header_value
        return item
    
    def _create_item_with_query_param(self, param_name, param_value):
        """Create BurpItem with query parameter."""
        item = self._create_item()
        item.request.query_params[param_name] = [param_value]
        return item
    
    def _create_item_with_cookie(self, cookie_value):
        """Create BurpItem with Cookie header."""
        item = self._create_item()
        item.request.headers['Cookie'] = cookie_value
        return item


class TestAuthScheme:
    """Tests for AuthScheme dataclass."""
    
    def test_auth_scheme_creation(self):
        """Test creating AuthScheme object."""
        scheme = AuthScheme(
            scheme_type='http',
            scheme_name='bearerAuth',
            description='Bearer token authentication',
            in_location='header',
            parameter_name='Authorization'
        )
        
        assert scheme.scheme_type == 'http'
        assert scheme.scheme_name == 'bearerAuth'
        assert scheme.in_location == 'header'

