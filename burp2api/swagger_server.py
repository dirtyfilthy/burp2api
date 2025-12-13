"""
Web server for serving Swagger UI interface with OpenAPI specification.
"""

import json
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any


class SwaggerUIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for serving Swagger UI and OpenAPI spec."""
    
    openapi_spec: Dict[str, Any] = {}
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        # Only log errors and important messages
        if args[1] != '200':
            super().log_message(format, *args)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.serve_swagger_ui()
        elif self.path == '/openapi.json':
            self.serve_openapi_spec()
        elif self.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def serve_swagger_ui(self):
        """Serve the Swagger UI HTML page with standard Swagger styling."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
    <link rel="icon" type="image/png" href="https://petstore.swagger.io/favicon-32x32.png" sizes="32x32" />
    <link rel="icon" type="image/png" href="https://petstore.swagger.io/favicon-16x16.png" sizes="16x16" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin: 0;
            padding: 0;
            background: #fafafa;
        }
        
        /* Custom topbar styling */
        .topbar {
            background-color: #89bf04;
            padding: 10px 0;
        }
        .topbar-wrapper {
            max-width: 1460px;
            margin: 0 auto;
            padding: 0 20px;
        }
        .topbar-wrapper a {
            display: flex;
            align-items: center;
            text-decoration: none;
        }
        .topbar-wrapper .link {
            font-size: 1.5em;
            font-weight: bold;
            color: #fff;
            font-family: sans-serif;
            display: flex;
            align-items: center;
        }
        .topbar-wrapper .link::before {
            content: "";
            display: inline-block;
            width: 40px;
            height: 40px;
            margin-right: 10px;
            background-image: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMDAgMjAwIj48cGF0aCBmaWxsPSIjZmZmIiBkPSJNMTAwIDIwYzQ0LjIgMCA4MCAzNS44IDgwIDgwcy0zNS44IDgwLTgwIDgwLTgwLTM1LjgtODAtODAgMzUuOC04MCA4MC04MG0wLTIwQzQ0LjggMCAwIDQ0LjggMCAxMDBzNDQuOCAxMDAgMTAwIDEwMCAxMDAtNDQuOCAxMDAtMTAwUzE1NS4yIDAgMTAwIDB6Ii8+PHBhdGggZmlsbD0iI2ZmZiIgZD0iTTEwMCA2MGMtMjIuMSAwLTQwIDE3LjktNDAgNDBzMTcuOSA0MCA0MCA0MCA0MC0xNy45IDQwLTQwLTE3LjktNDAtNDAtNDB6Ii8+PC9zdmc+');
            background-size: contain;
            background-repeat: no-repeat;
        }
        
        #swagger-ui {
            max-width: 1460px;
            margin: 0 auto;
        }
        
        /* Enhanced styling for better readability */
        .swagger-ui .info {
            margin: 50px 0;
        }
        .swagger-ui .info .title {
            font-size: 36px;
            margin-bottom: 10px;
        }
        .swagger-ui .scheme-container {
            background: #fff;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.15);
            margin: 0 0 20px;
            padding: 20px;
        }
        
        /* Operation styling */
        .swagger-ui .opblock {
            border-radius: 4px;
            box-shadow: 0 0 3px rgba(0,0,0,0.19);
            margin: 0 0 15px;
        }
        .swagger-ui .opblock.opblock-get {
            border-color: #61affe;
            background: rgba(97,175,254,0.1);
        }
        .swagger-ui .opblock.opblock-post {
            border-color: #49cc90;
            background: rgba(73,204,144,0.1);
        }
        .swagger-ui .opblock.opblock-put {
            border-color: #fca130;
            background: rgba(252,161,48,0.1);
        }
        .swagger-ui .opblock.opblock-delete {
            border-color: #f93e3e;
            background: rgba(249,62,62,0.1);
        }
        
        /* Try it out button styling */
        .swagger-ui .btn.execute {
            background-color: #4990e2;
            border-color: #4990e2;
        }
        .swagger-ui .btn.execute:hover {
            background-color: #1f69c0;
            border-color: #1f69c0;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div class="topbar-wrapper">
            <a href="/">
                <span class="link">Swagger UI</span>
            </a>
        </div>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                displayRequestDuration: true,
                displayOperationId: false,
                filter: true,
                showExtensions: true,
                showCommonExtensions: true,
                tryItOutEnabled: true,
                requestSnippetsEnabled: true,
                persistAuthorization: true,
                docExpansion: "list",
                operationsSorter: "alpha",
                tagsSorter: "alpha"
            });
            window.ui = ui;
        };
    </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_openapi_spec(self):
        """Serve the OpenAPI specification JSON."""
        spec_json = json.dumps(self.openapi_spec, indent=2, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(spec_json.encode('utf-8'))


def serve_swagger_ui(openapi_spec: Dict[str, Any], host: str = 'localhost', port: int = 8080):
    """
    Start HTTP server to serve Swagger UI with OpenAPI specification.
    
    Args:
        openapi_spec: The OpenAPI specification dictionary
        host: Host to bind to (default: localhost)
        port: Port to bind to (default: 8080)
    """
    # Set the OpenAPI spec in the handler class
    SwaggerUIHandler.openapi_spec = openapi_spec
    
    # Create server
    server_address = (host, port)
    try:
        httpd = HTTPServer(server_address, SwaggerUIHandler)
    except OSError as e:
        if e.errno == 48 or e.errno == 98:  # Address already in use
            print(f"Error: Port {port} is already in use.", file=sys.stderr)
            print(f"Please try a different port or stop the process using port {port}.", file=sys.stderr)
            sys.exit(1)
        raise
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nShutting down server...")
        httpd.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print startup message
    url = f"http://{host}:{port}"
    print(f"\n{'='*60}")
    print(f"Swagger UI server started!")
    print(f"{'='*60}")
    print(f"\nOpen your browser and navigate to:")
    print(f"  {url}")
    print(f"\nAPI Specification available at:")
    print(f"  {url}/openapi.json")
    print(f"\nPress Ctrl+C to stop the server")
    print(f"{'='*60}\n")
    
    # Start server
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()

