"""
XML parser for Burp Suite export files.
"""

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from urllib.parse import urlparse, parse_qs


@dataclass
class HTTPRequest:
    """Represents an HTTP request."""
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[str] = None
    query_params: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class HTTPResponse:
    """Represents an HTTP response."""
    status: int
    headers: Dict[str, str]
    body: Optional[str] = None


@dataclass
class BurpItem:
    """Represents a single item from Burp Suite export."""
    time: str
    url: str
    host: str
    host_ip: Optional[str]
    port: int
    protocol: str
    method: str
    path: str
    extension: Optional[str]
    request: HTTPRequest
    response: HTTPResponse
    mimetype: Optional[str]
    comment: Optional[str]


class BurpParser:
    """Parser for Burp Suite XML export files."""

    def __init__(self, filepath: str):
        """
        Initialize the parser with a file path.
        
        Args:
            filepath: Path to the Burp Suite XML export file
        """
        self.filepath = filepath
        self.items: List[BurpItem] = []

    def parse(self) -> List[BurpItem]:
        """
        Parse the Burp Suite export file.
        
        Returns:
            List of BurpItem objects
        """
        tree = ET.parse(self.filepath)
        root = tree.getroot()

        self.items = []
        for item_elem in root.findall('item'):
            try:
                item = self._parse_item(item_elem)
                if item:
                    self.items.append(item)
            except Exception as e:
                # Skip items that fail to parse
                print(f"Warning: Failed to parse item: {e}")
                continue

        return self.items

    def _parse_item(self, item_elem: ET.Element) -> Optional[BurpItem]:
        """Parse a single item element."""
        # Extract basic fields
        time = self._get_text(item_elem, 'time')
        url = self._get_text(item_elem, 'url')
        host = self._get_text(item_elem, 'host')
        host_elem = item_elem.find('host')
        host_ip = host_elem.get('ip') if host_elem is not None else None
        port = int(self._get_text(item_elem, 'port', '0'))
        protocol = self._get_text(item_elem, 'protocol')
        method = self._get_text(item_elem, 'method')
        path = self._get_text(item_elem, 'path')
        extension = self._get_text(item_elem, 'extension')
        status = int(self._get_text(item_elem, 'status', '0'))
        mimetype = self._get_text(item_elem, 'mimetype')
        comment = self._get_text(item_elem, 'comment')

        # Parse request
        request_elem = item_elem.find('request')
        request_data = self._decode_data(request_elem)
        request = self._parse_request(request_data, url)

        # Parse response
        response_elem = item_elem.find('response')
        response_data = self._decode_data(response_elem)
        response = self._parse_response(response_data, status)

        return BurpItem(
            time=time,
            url=url,
            host=host,
            host_ip=host_ip,
            port=port,
            protocol=protocol,
            method=method,
            path=path,
            extension=extension,
            request=request,
            response=response,
            mimetype=mimetype,
            comment=comment
        )

    def _get_text(self, element: ET.Element, tag: str, default: str = '') -> str:
        """Get text content of a child element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default

    def _decode_data(self, element: Optional[ET.Element]) -> str:
        """Decode base64-encoded data if necessary."""
        if element is None or not element.text:
            return ''
        
        is_base64 = element.get('base64') == 'true'
        text = element.text.strip()
        
        if is_base64:
            try:
                decoded = base64.b64decode(text)
                return decoded.decode('utf-8', errors='replace')
            except Exception:
                return ''
        
        return text

    def _parse_request(self, request_data: str, url: str) -> HTTPRequest:
        """Parse HTTP request data."""
        if not request_data:
            return HTTPRequest(method='GET', path='/', headers={})

        lines = request_data.split('\n')
        if not lines:
            return HTTPRequest(method='GET', path='/', headers={})

        # Parse request line
        request_line = lines[0].strip()
        parts = request_line.split(' ')
        method = parts[0] if len(parts) > 0 else 'GET'
        path = parts[1] if len(parts) > 1 else '/'

        # Parse headers
        headers = {}
        body_start = 0
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            if not line:
                body_start = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

        # Extract body
        body = None
        if body_start > 0 and body_start < len(lines):
            body = '\n'.join(lines[body_start:]).strip()
            if not body:
                body = None

        # Extract query parameters from URL
        query_params = {}
        parsed_url = urlparse(url)
        if parsed_url.query:
            query_params = parse_qs(parsed_url.query)

        return HTTPRequest(
            method=method,
            path=path,
            headers=headers,
            body=body,
            query_params=query_params
        )

    def _parse_response(self, response_data: str, status: int) -> HTTPResponse:
        """Parse HTTP response data."""
        if not response_data:
            return HTTPResponse(status=status, headers={})

        lines = response_data.split('\n')
        if not lines:
            return HTTPResponse(status=status, headers={})

        # Parse headers
        headers = {}
        body_start = 0
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            if not line:
                body_start = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

        # Extract body
        body = None
        if body_start > 0 and body_start < len(lines):
            body = '\n'.join(lines[body_start:]).strip()
            if not body:
                body = None

        return HTTPResponse(
            status=status,
            headers=headers,
            body=body
        )

