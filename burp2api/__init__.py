"""
Burp2API - Burp Suite to OpenAPI Converter

A tool to parse Burp Suite exports and generate OpenAPI documentation.
"""

__version__ = "0.1.0"

from burp2api.parser import BurpParser
from burp2api.openapi_generator import OpenAPIGenerator
from burp2api.filters import StaticAssetFilter
from burp2api.schema_extractor import SchemaExtractor
from burp2api.auth_detector import AuthDetector

__all__ = [
    "BurpParser",
    "OpenAPIGenerator",
    "StaticAssetFilter",
    "SchemaExtractor",
    "AuthDetector",
]

