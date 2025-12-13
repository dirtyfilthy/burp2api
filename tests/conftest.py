"""
Pytest configuration and shared fixtures for burp2api tests.
"""

import pytest
import os
from pathlib import Path
import tempfile

from burp2api.parser import BurpParser, BurpItem, HTTPRequest, HTTPResponse


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_burp_file(fixtures_dir):
    """Return path to sample Burp export file."""
    return fixtures_dir / "sample_burp_export.xml"


@pytest.fixture
def burp_with_json_file(fixtures_dir):
    """Return path to Burp export with JSON bodies."""
    return fixtures_dir / "burp_with_json.xml"


@pytest.fixture
def burp_with_auth_file(fixtures_dir):
    """Return path to Burp export with auth headers."""
    return fixtures_dir / "burp_with_auth.xml"


@pytest.fixture
def invalid_burp_file(fixtures_dir):
    """Return path to invalid Burp export file."""
    return fixtures_dir / "invalid_burp.xml"


@pytest.fixture
def sample_burp_xml():
    """Return a minimal valid Burp export XML string."""
    return """<?xml version="1.0"?>
<items burpVersion="2023.10.3.4" exportTime="Wed Dec 10 12:00:00 UTC 2025">
  <item>
    <time>Wed Dec 10 12:00:00 UTC 2025</time>
    <url>https://api.example.com/test</url>
    <host ip="93.184.216.34">api.example.com</host>
    <port>443</port>
    <protocol>https</protocol>
    <method>GET</method>
    <path>/test</path>
    <extension></extension>
    <request base64="false">GET /test HTTP/1.1
Host: api.example.com

</request>
    <status>200</status>
    <responselength>100</responselength>
    <mimetype>application/json</mimetype>
    <response base64="false">HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ok"}
</response>
    <comment></comment>
  </item>
</items>
"""


@pytest.fixture
def temp_xml_file(sample_burp_xml):
    """Create a temporary XML file with sample data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(sample_burp_xml)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_request():
    """Return a sample HTTPRequest object."""
    return HTTPRequest(
        method='GET',
        path='/api/users/123',
        headers={'Host': 'api.example.com', 'Accept': 'application/json'},
        body=None,
        query_params={}
    )


@pytest.fixture
def sample_response():
    """Return a sample HTTPResponse object."""
    return HTTPResponse(
        status=200,
        headers={'Content-Type': 'application/json'},
        body='{"id":123,"username":"testuser"}'
    )


@pytest.fixture
def sample_burp_item(sample_request, sample_response):
    """Return a sample BurpItem object."""
    return BurpItem(
        time='Wed Dec 10 12:00:00 UTC 2025',
        url='https://api.example.com/api/users/123',
        host='api.example.com',
        host_ip='93.184.216.34',
        port=443,
        protocol='https',
        method='GET',
        path='/api/users/123',
        extension=None,
        request=sample_request,
        response=sample_response,
        mimetype='application/json',
        comment=None
    )


@pytest.fixture
def burp_items(sample_burp_file):
    """Return parsed BurpItem objects from sample file."""
    parser = BurpParser(str(sample_burp_file))
    return parser.parse()


@pytest.fixture
def burp_items_with_json(burp_with_json_file):
    """Return parsed BurpItem objects with JSON bodies."""
    parser = BurpParser(str(burp_with_json_file))
    return parser.parse()


@pytest.fixture
def burp_items_with_auth(burp_with_auth_file):
    """Return parsed BurpItem objects with auth headers."""
    parser = BurpParser(str(burp_with_auth_file))
    return parser.parse()


@pytest.fixture
def api_item():
    """Return a BurpItem representing an API endpoint."""
    return BurpItem(
        time='Wed Dec 10 12:00:00 UTC 2025',
        url='https://api.example.com/api/users',
        host='api.example.com',
        host_ip='93.184.216.34',
        port=443,
        protocol='https',
        method='GET',
        path='/api/users',
        extension=None,
        request=HTTPRequest(
            method='GET',
            path='/api/users',
            headers={'Host': 'api.example.com'},
            body=None,
            query_params={}
        ),
        response=HTTPResponse(
            status=200,
            headers={'Content-Type': 'application/json'},
            body='[{"id":1,"username":"user1"}]'
        ),
        mimetype='application/json',
        comment=None
    )


@pytest.fixture
def static_item():
    """Return a BurpItem representing a static asset."""
    return BurpItem(
        time='Wed Dec 10 12:00:00 UTC 2025',
        url='https://example.com/static/app.js',
        host='example.com',
        host_ip='93.184.216.34',
        port=443,
        protocol='https',
        method='GET',
        path='/static/app.js',
        extension='js',
        request=HTTPRequest(
            method='GET',
            path='/static/app.js',
            headers={'Host': 'example.com'},
            body=None,
            query_params={}
        ),
        response=HTTPResponse(
            status=200,
            headers={'Content-Type': 'application/javascript'},
            body='console.log("test");'
        ),
        mimetype='application/javascript',
        comment=None
    )

