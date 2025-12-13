"""
Authentication mechanism detection from HTTP requests.
"""

import re
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from burp2api.parser import BurpItem


@dataclass
class AuthScheme:
    """Represents a detected authentication scheme."""
    scheme_type: str  # bearer, apiKey, http, oauth2
    scheme_name: str  # Name for the security scheme
    description: Optional[str] = None
    in_location: Optional[str] = None  # header, query, cookie
    parameter_name: Optional[str] = None  # Name of the header/query/cookie


class AuthDetector:
    """Detect authentication mechanisms from HTTP traffic."""

    def __init__(self):
        """Initialize the authentication detector."""
        self.detected_schemes: Dict[str, AuthScheme] = {}

    def detect_auth_schemes(self, items: List[BurpItem]) -> Dict[str, AuthScheme]:
        """
        Detect authentication schemes from a list of Burp items.
        
        Args:
            items: List of BurpItem objects
            
        Returns:
            Dictionary of detected authentication schemes
        """
        self.detected_schemes = {}
        
        bearer_tokens: Set[str] = set()
        api_keys: Dict[str, Set[str]] = {}  # location -> set of names
        basic_auth: bool = False
        cookies: Set[str] = set()

        for item in items:
            # Check Authorization header
            auth_header = item.request.headers.get('Authorization', '')
            if auth_header:
                if auth_header.startswith('Bearer '):
                    bearer_tokens.add('Authorization')
                elif auth_header.startswith('Basic '):
                    basic_auth = True

            # Check for API keys in headers
            for header_name in item.request.headers.keys():
                if self._is_api_key_header(header_name):
                    if 'header' not in api_keys:
                        api_keys['header'] = set()
                    api_keys['header'].add(header_name)

            # Check for API keys in query parameters
            for param_name in item.request.query_params.keys():
                if self._is_api_key_param(param_name):
                    if 'query' not in api_keys:
                        api_keys['query'] = set()
                    api_keys['query'].add(param_name)

            # Check for session cookies
            cookie_header = item.request.headers.get('Cookie', '')
            if cookie_header:
                cookie_names = self._extract_cookie_names(cookie_header)
                for cookie_name in cookie_names:
                    if self._is_session_cookie(cookie_name):
                        cookies.add(cookie_name)

        # Add detected schemes
        if bearer_tokens:
            self.detected_schemes['bearerAuth'] = AuthScheme(
                scheme_type='http',
                scheme_name='bearerAuth',
                description='Bearer token authentication',
                in_location='header',
                parameter_name='Authorization'
            )

        if basic_auth:
            self.detected_schemes['basicAuth'] = AuthScheme(
                scheme_type='http',
                scheme_name='basicAuth',
                description='Basic HTTP authentication',
                in_location='header',
                parameter_name='Authorization'
            )

        # Add API key schemes
        for location, names in api_keys.items():
            for name in names:
                scheme_name = f'apiKey_{name}'
                self.detected_schemes[scheme_name] = AuthScheme(
                    scheme_type='apiKey',
                    scheme_name=scheme_name,
                    description=f'API key in {location}: {name}',
                    in_location=location,
                    parameter_name=name
                )

        # Add cookie schemes
        for cookie_name in cookies:
            scheme_name = f'cookie_{cookie_name}'
            self.detected_schemes[scheme_name] = AuthScheme(
                scheme_type='apiKey',
                scheme_name=scheme_name,
                description=f'Session cookie: {cookie_name}',
                in_location='cookie',
                parameter_name=cookie_name
            )

        return self.detected_schemes

    def _is_api_key_header(self, header_name: str) -> bool:
        """Check if a header name looks like an API key."""
        header_lower = header_name.lower()
        api_key_patterns = [
            'api-key', 'apikey', 'x-api-key',
            'x-api-token', 'api-token', 'apitoken',
            'x-auth-token', 'auth-token', 'authtoken',
            'x-access-token', 'access-token', 'accesstoken',
            'x-client-id', 'client-id',
        ]
        return any(pattern in header_lower for pattern in api_key_patterns)

    def _is_api_key_param(self, param_name: str) -> bool:
        """Check if a query parameter name looks like an API key."""
        param_lower = param_name.lower()
        api_key_patterns = [
            'apikey', 'api_key', 'key',
            'token', 'access_token', 'accesstoken',
            'auth', 'auth_token', 'authtoken',
            'client_id', 'clientid',
        ]
        return param_lower in api_key_patterns

    def _is_session_cookie(self, cookie_name: str) -> bool:
        """Check if a cookie name looks like a session cookie."""
        cookie_lower = cookie_name.lower()
        session_patterns = [
            'session', 'sessionid', 'sess', 'sid',
            'jsessionid', 'phpsessid', 'aspsessionid',
            'connect.sid', 'jwt', 'token', 'auth',
        ]
        return any(pattern in cookie_lower for pattern in session_patterns)

    def _extract_cookie_names(self, cookie_header: str) -> List[str]:
        """Extract cookie names from Cookie header value."""
        names = []
        for cookie in cookie_header.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name = cookie.split('=')[0].strip()
                names.append(name)
        return names

    def to_openapi_security_schemes(self) -> Dict[str, Dict]:
        """
        Convert detected auth schemes to OpenAPI security schemes format.
        
        Returns:
            Dictionary of OpenAPI security scheme definitions
        """
        schemes = {}
        
        for scheme_name, scheme in self.detected_schemes.items():
            if scheme.scheme_type == 'http':
                if 'bearer' in scheme_name.lower():
                    schemes[scheme_name] = {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT',
                        'description': scheme.description or 'Bearer token authentication'
                    }
                elif 'basic' in scheme_name.lower():
                    schemes[scheme_name] = {
                        'type': 'http',
                        'scheme': 'basic',
                        'description': scheme.description or 'Basic HTTP authentication'
                    }
            elif scheme.scheme_type == 'apiKey':
                schemes[scheme_name] = {
                    'type': 'apiKey',
                    'in': scheme.in_location,
                    'name': scheme.parameter_name,
                    'description': scheme.description or f'API key authentication'
                }

        return schemes

