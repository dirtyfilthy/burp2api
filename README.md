# Burp2API

Author: github.com/dirtyfilthy

A Python tool to convert Burp Suite export files to OpenAPI 3.0 documentation. 




```bash
# Start interactive Swagger UI at http://localhost:8080
burp2api burp_export.xml --swagger
```


## Features


- Generate OpenAPI 3.0 specification
- **Interactive Swagger UI web interface to explore and test your API**
- Group endpoints by path patterns (e.g., `/api/users/{id}`)
- Extract request/response schemas from JSON bodies
- Detect authentication mechanisms (Bearer tokens, API keys, Basic auth, cookies)

## Installation

### From source

```bash
pip install -e .
```

