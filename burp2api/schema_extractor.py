"""
Schema extraction from HTTP request/response bodies.
"""

import json
import re
from typing import Any, Dict, Optional, List
from urllib.parse import parse_qs


class SchemaExtractor:
    """Extract and infer schemas from HTTP bodies."""

    @staticmethod
    def extract_request_schema(body: Optional[str], content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract schema from request body.
        
        Args:
            body: Request body content
            content_type: Content-Type header value
            
        Returns:
            OpenAPI schema object or None
        """
        if not body:
            return None

        # Try JSON
        if SchemaExtractor._is_json_content(content_type):
            try:
                data = json.loads(body)
                return SchemaExtractor._infer_schema_from_value(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try form data
        if content_type and 'application/x-www-form-urlencoded' in content_type:
            try:
                params = parse_qs(body)
                if params:
                    properties = {}
                    for key, values in params.items():
                        # If multiple values, it's an array
                        if len(values) > 1:
                            properties[key] = {
                                'type': 'array',
                                'items': {'type': 'string'}
                            }
                        else:
                            properties[key] = {'type': 'string'}
                    return {
                        'type': 'object',
                        'properties': properties
                    }
            except Exception:
                pass

        # Try multipart form data
        if content_type and 'multipart/form-data' in content_type:
            # Simple detection of field names
            fields = re.findall(r'name="([^"]+)"', body)
            if fields:
                properties = {field: {'type': 'string'} for field in fields}
                return {
                    'type': 'object',
                    'properties': properties
                }

        # If we can't parse it, return a generic string schema
        return {'type': 'string'}

    @staticmethod
    def extract_response_schema(body: Optional[str], content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract schema from response body.
        
        Args:
            body: Response body content
            content_type: Content-Type header value
            
        Returns:
            OpenAPI schema object or None
        """
        if not body:
            return None

        # Try JSON
        if SchemaExtractor._is_json_content(content_type):
            try:
                data = json.loads(body)
                return SchemaExtractor._infer_schema_from_value(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # HTML responses
        if content_type and 'text/html' in content_type:
            return {'type': 'string', 'format': 'html'}

        # Default to string
        return {'type': 'string'}

    @staticmethod
    def _is_json_content(content_type: Optional[str]) -> bool:
        """Check if content type is JSON."""
        if not content_type:
            return False
        json_types = ['application/json', 'application/ld+json', 'application/vnd.api+json']
        return any(jt in content_type.lower() for jt in json_types)

    @staticmethod
    def _infer_schema_from_value(value: Any) -> Dict[str, Any]:
        """
        Infer OpenAPI schema from a Python value.
        
        Args:
            value: Python value (from parsed JSON)
            
        Returns:
            OpenAPI schema object
        """
        if value is None:
            return {'type': 'null', 'nullable': True}

        if isinstance(value, bool):
            return {'type': 'boolean'}

        if isinstance(value, int):
            return {'type': 'integer'}

        if isinstance(value, float):
            return {'type': 'number'}

        if isinstance(value, str):
            # Try to detect formats
            if SchemaExtractor._is_datetime(value):
                return {'type': 'string', 'format': 'date-time'}
            if SchemaExtractor._is_date(value):
                return {'type': 'string', 'format': 'date'}
            if SchemaExtractor._is_email(value):
                return {'type': 'string', 'format': 'email'}
            if SchemaExtractor._is_uri(value):
                return {'type': 'string', 'format': 'uri'}
            if SchemaExtractor._is_uuid(value):
                return {'type': 'string', 'format': 'uuid'}
            return {'type': 'string'}

        if isinstance(value, list):
            if not value:
                return {
                    'type': 'array',
                    'items': {}
                }
            # Infer schema from first item
            item_schema = SchemaExtractor._infer_schema_from_value(value[0])
            return {
                'type': 'array',
                'items': item_schema
            }

        if isinstance(value, dict):
            properties = {}
            required = []
            for key, val in value.items():
                properties[key] = SchemaExtractor._infer_schema_from_value(val)
                if val is not None:
                    required.append(key)
            
            schema = {
                'type': 'object',
                'properties': properties
            }
            if required:
                schema['required'] = required
            return schema

        return {}

    @staticmethod
    def merge_schemas(schema1: Dict[str, Any], schema2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two schemas to create a more comprehensive schema.
        
        Args:
            schema1: First schema
            schema2: Second schema
            
        Returns:
            Merged schema
        """
        if not schema1:
            return schema2
        if not schema2:
            return schema1

        # If types differ, create a union (oneOf)
        if schema1.get('type') != schema2.get('type'):
            return {'oneOf': [schema1, schema2]}

        # Merge objects
        if schema1.get('type') == 'object':
            properties1 = schema1.get('properties', {})
            properties2 = schema2.get('properties', {})
            
            merged_properties = properties1.copy()
            for key, val in properties2.items():
                if key in merged_properties:
                    merged_properties[key] = SchemaExtractor.merge_schemas(
                        merged_properties[key], val
                    )
                else:
                    merged_properties[key] = val

            required1 = set(schema1.get('required', []))
            required2 = set(schema2.get('required', []))
            required = list(required1.intersection(required2))

            result = {
                'type': 'object',
                'properties': merged_properties
            }
            if required:
                result['required'] = required
            return result

        # Merge arrays
        if schema1.get('type') == 'array':
            items1 = schema1.get('items', {})
            items2 = schema2.get('items', {})
            merged_items = SchemaExtractor.merge_schemas(items1, items2)
            return {
                'type': 'array',
                'items': merged_items
            }

        # For primitives, return the first schema
        return schema1

    @staticmethod
    def _is_datetime(value: str) -> bool:
        """Check if string looks like a datetime."""
        datetime_pattern = r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
        return bool(re.match(datetime_pattern, value))

    @staticmethod
    def _is_date(value: str) -> bool:
        """Check if string looks like a date."""
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        return bool(re.match(date_pattern, value))

    @staticmethod
    def _is_email(value: str) -> bool:
        """Check if string looks like an email."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))

    @staticmethod
    def _is_uri(value: str) -> bool:
        """Check if string looks like a URI."""
        uri_pattern = r'^https?://'
        return bool(re.match(uri_pattern, value))

    @staticmethod
    def _is_uuid(value: str) -> bool:
        """Check if string looks like a UUID."""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

