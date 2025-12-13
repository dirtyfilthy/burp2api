"""
OpenAPI 3.0 specification generator from Burp Suite items.
"""

import json
import re
import inflect
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from urllib.parse import urlparse

from burp2api.parser import BurpItem
from burp2api.filters import StaticAssetFilter
from burp2api.schema_extractor import SchemaExtractor
from burp2api.auth_detector import AuthDetector


class OpenAPIGenerator:
    """Generate OpenAPI 3.0 specification from Burp Suite items."""

    def __init__(self, 
                 items: List[BurpItem],
                 filter_static: bool = True,
                 include_patterns: List[str] = None,
                 exclude_patterns: List[str] = None,
                 title: str = "API Documentation",
                 version: str = "1.0.0",
                 description: str = "API documentation generated from Burp Suite export"):
        """
        Initialize the OpenAPI generator.
        
        Args:
            items: List of BurpItem objects
            filter_static: Whether to filter out static assets
            include_patterns: Patterns to include
            exclude_patterns: Patterns to exclude
            title: API title
            version: API version
            description: API description
        """
        self.items = items
        self.title = title
        self.version = version
        self.description = description
        
        # Apply filtering
        self.filter = StaticAssetFilter(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            filter_static=filter_static
        )
        self.filtered_items = self.filter.filter_items(items)
        
        # Detectors and extractors
        self.auth_detector = AuthDetector()
        self.schema_extractor = SchemaExtractor()
        
        # Inflect engine for singularization
        self.inflect_engine = inflect.engine()
        
        # OpenAPI structure
        self.openapi_spec: Dict[str, Any] = {}

    def generate(self) -> Dict[str, Any]:
        """
        Generate the OpenAPI specification.
        
        Returns:
            OpenAPI 3.0 specification dictionary
        """
        # Detect authentication schemes
        auth_schemes = self.auth_detector.detect_auth_schemes(self.filtered_items)
        
        # Group items by endpoint
        endpoints = self._group_by_endpoint(self.filtered_items)
        
        # Extract servers
        servers = self._extract_servers(self.filtered_items)
        
        # Build paths
        paths = self._build_paths(endpoints)
        
        # Build components
        components = self._build_components(auth_schemes)
        
        # Construct OpenAPI spec
        self.openapi_spec = {
            'openapi': '3.0.3',
            'info': {
                'title': self.title,
                'version': self.version,
                'description': self.description
            },
            'servers': servers,
            'paths': paths
        }
        
        if components:
            self.openapi_spec['components'] = components
        
        return self.openapi_spec

    def _group_by_endpoint(self, items: List[BurpItem]) -> Dict[Tuple[str, str], List[BurpItem]]:
        """
        Group items by endpoint (path pattern and method).
        
        Args:
            items: List of BurpItem objects
            
        Returns:
            Dictionary mapping (path_pattern, method) to list of items
        """
        endpoints: Dict[Tuple[str, str], List[BurpItem]] = defaultdict(list)
        
        for item in items:
            path_pattern = self._extract_path_pattern(item.path)
            key = (path_pattern, item.method.upper())
            endpoints[key].append(item)
        
        return endpoints

    def _extract_path_pattern(self, path: str) -> str:
        """
        Extract path pattern by replacing IDs with parameters.
        
        Args:
            path: Original path
            
        Returns:
            Path pattern with parameters
        """
        # Remove query string
        if '?' in path:
            path = path.split('?')[0]
        
        # Split into segments
        segments = path.split('/')
        pattern_segments = []
        
        for segment in segments:
            if not segment:
                pattern_segments.append(segment)
                continue
            
            # Check if segment looks like an ID
            if self._is_id_segment(segment):
                # Try to guess parameter name from previous segment
                if pattern_segments:
                    prev = pattern_segments[-1]
                    if prev and prev != '':
                        # Singularize using inflect for proper conversion (e.g., 'entities' -> 'entity')
                        singular = self.inflect_engine.singular_noun(prev)
                        # singular_noun returns False if the word is already singular or not a noun
                        if singular:
                            param_name = singular + 'Id'
                        else:
                            param_name = prev + 'Id'
                    else:
                        param_name = 'id'
                else:
                    param_name = 'id'
                pattern_segments.append('{' + param_name + '}')
            else:
                pattern_segments.append(segment)
        
        return '/'.join(pattern_segments)

    def _is_id_segment(self, segment: str) -> bool:
        """
        Check if a path segment looks like an ID.
        
        Args:
            segment: Path segment
            
        Returns:
            True if segment looks like an ID
        """
        # Exclude common non-ID patterns
        # Version numbers (v1, v2, v3, etc)
        if re.match(r'^v\d+$', segment, re.IGNORECASE):
            return False
        
        # Common words that might have numbers (api, app, etc)
        if segment.lower() in ['api', 'app', 'v1', 'v2', 'v3', 'v4', 'v5']:
            return False
        
        # UUID pattern
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', 
                   segment, re.IGNORECASE):
            return True
        
        # Pure numbers
        if re.match(r'^\d+$', segment):
            return True
        
        # MongoDB ObjectId
        if re.match(r'^[0-9a-f]{24}$', segment, re.IGNORECASE):
            return True
        
        # Base62-style IDs (8-15 chars, mixed case, alphanumeric)
        # Common in short ID systems like YouTube, Firebase, etc.
        if 8 <= len(segment) <= 15 and re.match(r'^[a-zA-Z0-9_-]+$', segment):
            # Check for mixed case (strong indicator of ID)
            if segment != segment.lower() and segment != segment.upper():
                return True
            # Or high ratio of numbers (60%+)
            num_count = sum(c.isdigit() for c in segment)
            if num_count / len(segment) >= 0.6:
                return True
        
        # Longer alphanumeric IDs (16+ chars)
        if len(segment) >= 16 and re.match(r'^[a-zA-Z0-9_-]+$', segment):
            return True
        
        # Short hex-like IDs (f0, f1, a1b2, etc - 2-4 chars with numbers)
        if 2 <= len(segment) <= 4 and re.match(r'^[a-zA-Z0-9]+$', segment):
            # Must contain at least one digit
            if any(c.isdigit() for c in segment):
                # But not if it looks like a version (v1, v2)
                if not re.match(r'^v\d+$', segment, re.IGNORECASE):
                    return True
        
        return False

    def _extract_servers(self, items: List[BurpItem]) -> List[Dict[str, str]]:
        """
        Extract unique servers from items.
        
        Args:
            items: List of BurpItem objects
            
        Returns:
            List of server objects
        """
        servers_set = set()
        
        for item in items:
            server_url = f"{item.protocol}://{item.host}"
            if (item.protocol == 'https' and item.port != 443) or \
               (item.protocol == 'http' and item.port != 80):
                server_url += f":{item.port}"
            servers_set.add(server_url)
        
        return [{'url': url} for url in sorted(servers_set)]

    def _build_paths(self, endpoints: Dict[Tuple[str, str], List[BurpItem]]) -> Dict[str, Any]:
        """
        Build OpenAPI paths object.
        
        Args:
            endpoints: Grouped endpoints
            
        Returns:
            OpenAPI paths object
        """
        paths = {}
        
        for (path_pattern, method), items in endpoints.items():
            if path_pattern not in paths:
                paths[path_pattern] = {}
            
            paths[path_pattern][method.lower()] = self._build_operation(items, path_pattern)
        
        return paths

    def _build_operation(self, items: List[BurpItem], path_pattern: str) -> Dict[str, Any]:
        """
        Build OpenAPI operation object from items.
        
        Args:
            items: List of items for this operation
            path_pattern: Path pattern
            
        Returns:
            OpenAPI operation object
        """
        # Use first item for basic info
        first_item = items[0]
        
        operation = {
            'summary': f"{first_item.method} {path_pattern}",
            'description': f"Endpoint: {path_pattern}",
            'responses': {}
        }
        
        # Extract path parameters
        path_params = re.findall(r'\{([^}]+)\}', path_pattern)
        if path_params:
            operation['parameters'] = []
            for param in path_params:
                operation['parameters'].append({
                    'name': param,
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'}
                })
        
        # Extract query parameters
        query_params_map = {}
        for item in items:
            for param_name, param_values in item.request.query_params.items():
                if param_name not in query_params_map:
                    query_params_map[param_name] = []
                query_params_map[param_name].extend(param_values)
        
        if query_params_map:
            if 'parameters' not in operation:
                operation['parameters'] = []
            for param_name in sorted(query_params_map.keys()):
                operation['parameters'].append({
                    'name': param_name,
                    'in': 'query',
                    'schema': {'type': 'string'}
                })
        
        # Build request body (if applicable)
        request_bodies = []
        for item in items:
            if item.request.body:
                content_type = item.request.headers.get('Content-Type', 'application/json')
                schema = self.schema_extractor.extract_request_schema(
                    item.request.body, 
                    content_type
                )
                if schema:
                    request_bodies.append((content_type, schema, item.request.body))
        
        if request_bodies:
            # Merge schemas for the same content type
            content_type_schemas = defaultdict(list)
            content_type_examples = defaultdict(list)
            for ct, schema, body in request_bodies:
                ct_base = ct.split(';')[0].strip()
                content_type_schemas[ct_base].append(schema)
                content_type_examples[ct_base].append(body)
            
            request_body = {'content': {}}
            for ct_base, schemas in content_type_schemas.items():
                merged_schema = schemas[0]
                for schema in schemas[1:]:
                    merged_schema = self.schema_extractor.merge_schemas(merged_schema, schema)
                
                request_body['content'][ct_base] = {'schema': merged_schema}
                
                # Add example
                if content_type_examples[ct_base]:
                    example_body = content_type_examples[ct_base][0]
                    if 'json' in ct_base:
                        try:
                            request_body['content'][ct_base]['example'] = json.loads(example_body)
                        except:
                            request_body['content'][ct_base]['example'] = example_body
                    else:
                        request_body['content'][ct_base]['example'] = example_body
            
            operation['requestBody'] = request_body
        
        # Build responses
        responses_by_status = defaultdict(list)
        for item in items:
            responses_by_status[item.response.status].append(item)
        
        for status, status_items in responses_by_status.items():
            response_obj = self._build_response(status_items)
            operation['responses'][str(status)] = response_obj
        
        return operation

    def _build_response(self, items: List[BurpItem]) -> Dict[str, Any]:
        """
        Build OpenAPI response object.
        
        Args:
            items: List of items with same response status
            
        Returns:
            OpenAPI response object
        """
        first_item = items[0]
        status = first_item.response.status
        
        # Get description from status code
        status_descriptions = {
            200: 'OK',
            201: 'Created',
            204: 'No Content',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            500: 'Internal Server Error'
        }
        
        response = {
            'description': status_descriptions.get(status, f'Response {status}')
        }
        
        # Build response content
        content_type_schemas = defaultdict(list)
        content_type_examples = defaultdict(list)
        
        for item in items:
            if item.response.body:
                content_type = item.response.headers.get('Content-Type', 'application/json')
                ct_base = content_type.split(';')[0].strip()
                
                schema = self.schema_extractor.extract_response_schema(
                    item.response.body,
                    content_type
                )
                if schema:
                    content_type_schemas[ct_base].append(schema)
                    content_type_examples[ct_base].append(item.response.body)
        
        if content_type_schemas:
            response['content'] = {}
            for ct_base, schemas in content_type_schemas.items():
                merged_schema = schemas[0]
                for schema in schemas[1:]:
                    merged_schema = self.schema_extractor.merge_schemas(merged_schema, schema)
                
                response['content'][ct_base] = {'schema': merged_schema}
                
                # Add example
                if content_type_examples[ct_base]:
                    example_body = content_type_examples[ct_base][0]
                    if 'json' in ct_base:
                        try:
                            response['content'][ct_base]['example'] = json.loads(example_body)
                        except:
                            response['content'][ct_base]['example'] = example_body
                    else:
                        # Truncate long non-JSON responses
                        if len(example_body) > 500:
                            response['content'][ct_base]['example'] = example_body[:500] + '...'
                        else:
                            response['content'][ct_base]['example'] = example_body
        
        return response

    def _build_components(self, auth_schemes: Dict) -> Dict[str, Any]:
        """
        Build OpenAPI components object.
        
        Args:
            auth_schemes: Detected authentication schemes
            
        Returns:
            OpenAPI components object
        """
        components = {}
        
        if auth_schemes:
            security_schemes = self.auth_detector.to_openapi_security_schemes()
            if security_schemes:
                components['securitySchemes'] = security_schemes
        
        return components

    def save(self, filepath: str, pretty: bool = True):
        """
        Save OpenAPI specification to file.
        
        Args:
            filepath: Output file path
            pretty: Whether to pretty-print JSON
        """
        if not self.openapi_spec:
            self.generate()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.openapi_spec, f, indent=2, ensure_ascii=False)
            else:
                json.dump(self.openapi_spec, f, ensure_ascii=False)

    def to_json(self, pretty: bool = True) -> str:
        """
        Convert OpenAPI specification to JSON string.
        
        Args:
            pretty: Whether to pretty-print JSON
            
        Returns:
            JSON string
        """
        if not self.openapi_spec:
            self.generate()
        
        if pretty:
            return json.dumps(self.openapi_spec, indent=2, ensure_ascii=False)
        else:
            return json.dumps(self.openapi_spec, ensure_ascii=False)

