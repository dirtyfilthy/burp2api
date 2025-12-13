"""
Command-line interface for burp2api.
"""

import click
import sys
import tempfile
import os
from pathlib import Path

from burp2api.parser import BurpParser
from burp2api.openapi_generator import OpenAPIGenerator
from burp2api.swagger_server import serve_swagger_ui


@click.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.option('-o', '--output', 'output_file', 
              type=click.Path(dir_okay=False),
              required=False,
              help='Output file path for OpenAPI specification')
@click.option('--swagger',
              is_flag=True,
              default=False,
              help='Start a web server with Swagger UI to explore the API')
@click.option('--title', 
              default='API Documentation',
              help='API title')
@click.option('--version', 'api_version',
              default='1.0.0',
              help='API version')
@click.option('--description',
              default='API documentation generated from Burp Suite export',
              help='API description')
@click.option('--include', 'include_patterns',
              multiple=True,
              help='Include patterns (regex). Can be specified multiple times.')
@click.option('--exclude', 'exclude_patterns',
              multiple=True,
              help='Exclude patterns (regex). Can be specified multiple times.')
@click.option('--no-filter-static',
              is_flag=True,
              default=False,
              help='Do not filter out static assets')
@click.option('--pretty/--compact',
              default=True,
              help='Pretty-print or compact JSON output')
@click.option('-v', '--verbose',
              is_flag=True,
              help='Verbose output')
def main(input_file, output_file, swagger, title, api_version, description,
         include_patterns, exclude_patterns, no_filter_static, pretty, verbose):
    """
    Parse Burp Suite XML export and generate OpenAPI documentation.
    
    INPUT_FILE: Path to Burp Suite XML export file
    """
    # Validate flags
    if not swagger and not output_file:
        click.echo("Error: Either -o/--output or --swagger must be specified", err=True)
        sys.exit(1)
    
    try:
        if verbose:
            click.echo(f"Reading Burp Suite export from: {input_file}")
        
        # Parse Burp export
        parser = BurpParser(input_file)
        items = parser.parse()
        
        if verbose:
            click.echo(f"Parsed {len(items)} items from Burp export")
        
        if not items:
            click.echo("Warning: No items found in Burp export", err=True)
            sys.exit(1)
        
        # Generate OpenAPI spec
        generator = OpenAPIGenerator(
            items=items,
            filter_static=not no_filter_static,
            include_patterns=list(include_patterns) if include_patterns else None,
            exclude_patterns=list(exclude_patterns) if exclude_patterns else None,
            title=title,
            version=api_version,
            description=description
        )
        
        if verbose:
            click.echo("Generating OpenAPI specification...")
        
        spec = generator.generate()
        
        if verbose:
            filtered_count = len(generator.filtered_items)
            click.echo(f"Filtered to {filtered_count} API endpoints")
            click.echo(f"Found {len(spec.get('paths', {}))} unique paths")
            
            # Show detected auth schemes
            components = spec.get('components', {})
            security_schemes = components.get('securitySchemes', {})
            if security_schemes:
                click.echo(f"Detected {len(security_schemes)} authentication scheme(s):")
                for scheme_name in security_schemes:
                    click.echo(f"  - {scheme_name}")
        
        # Handle output based on mode
        temp_file_path = None
        
        if swagger:
            # Swagger mode
            if output_file:
                # Save to specified file and serve
                generator.save(output_file, pretty=pretty)
                if verbose:
                    click.echo(f"OpenAPI specification saved to: {output_file}")
            else:
                # Save to temporary file for serving
                temp_fd, temp_file_path = tempfile.mkstemp(suffix='.json', prefix='burp2api-')
                os.close(temp_fd)
                generator.save(temp_file_path, pretty=pretty)
                if verbose:
                    click.echo(f"OpenAPI specification saved to temporary file: {temp_file_path}")
            
            # Start Swagger UI server
            try:
                serve_swagger_ui(spec, host='localhost', port=8080)
            finally:
                # Clean up temporary file if created
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                        if verbose:
                            click.echo(f"Cleaned up temporary file: {temp_file_path}")
                    except:
                        pass
        else:
            # File output mode
            generator.save(output_file, pretty=pretty)
            click.echo(f"OpenAPI specification saved to: {output_file}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

