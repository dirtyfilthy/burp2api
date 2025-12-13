"""
Tests for burp2api.cli module.
"""

import pytest
import json
import threading
import time
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from burp2api.cli import main


class TestCLI:
    """Tests for command-line interface."""
    
    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()
    
    def test_help_message(self, runner):
        """Test displaying help message."""
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'Parse Burp Suite XML export' in result.output
        assert '--output' in result.output
        assert '--title' in result.output
    
    def test_basic_command_execution(self, runner, sample_burp_file, tmp_path):
        """Test basic CLI execution with required arguments."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        
        # Verify it's valid JSON
        with open(output_file) as f:
            spec = json.load(f)
            assert 'openapi' in spec
    
    def test_custom_title_version_description(self, runner, sample_burp_file, tmp_path):
        """Test CLI with custom title, version, and description."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--title', 'My Custom API',
            '--version', '2.0.0',
            '--description', 'Custom API documentation'
        ])
        
        assert result.exit_code == 0
        
        with open(output_file) as f:
            spec = json.load(f)
            assert spec['info']['title'] == 'My Custom API'
            assert spec['info']['version'] == '2.0.0'
            assert spec['info']['description'] == 'Custom API documentation'
    
    def test_verbose_output(self, runner, sample_burp_file, tmp_path):
        """Test verbose output flag."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--verbose'
        ])
        
        assert result.exit_code == 0
        assert 'Reading Burp Suite export from' in result.output
        assert 'Parsed' in result.output
        assert 'Generating OpenAPI specification' in result.output
    
    def test_include_pattern(self, runner, sample_burp_file, tmp_path):
        """Test include pattern option."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--include', r'/users.*',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        
        with open(output_file) as f:
            spec = json.load(f)
            paths = spec.get('paths', {})
            # Should only include paths matching /users.* pattern
            # Note: Include pattern overrides static filtering, so should have user paths
            if paths:
                # At least some paths should contain 'users'
                has_users = any('users' in path.lower() or 'user' in path.lower() for path in paths)
                assert has_users or len(paths) == 0
    
    def test_exclude_pattern(self, runner, sample_burp_file, tmp_path):
        """Test exclude pattern option."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--exclude', r'/static/.*',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        
        with open(output_file) as f:
            spec = json.load(f)
            paths = spec.get('paths', {})
            # Should not include paths matching /static/.*
            for path in paths:
                assert '/static/' not in path
    
    def test_multiple_include_patterns(self, runner, sample_burp_file, tmp_path):
        """Test multiple include patterns."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--include', r'/users.*',
            '--include', r'/posts.*'
        ])
        
        assert result.exit_code == 0
    
    def test_no_filter_static(self, runner, sample_burp_file, tmp_path):
        """Test disabling static asset filtering."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--no-filter-static',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        
        with open(output_file) as f:
            spec = json.load(f)
            paths = spec.get('paths', {})
            # Should include static assets when not filtering
            assert len(paths) > 0
    
    def test_compact_json_output(self, runner, sample_burp_file, tmp_path):
        """Test compact JSON output."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--compact'
        ])
        
        assert result.exit_code == 0
        
        # Compact JSON should not have indentation
        with open(output_file) as f:
            content = f.read()
            # Compact JSON has fewer newlines
            assert content.count('\n') < 10
    
    def test_pretty_json_output(self, runner, sample_burp_file, tmp_path):
        """Test pretty-printed JSON output (default)."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--pretty'
        ])
        
        assert result.exit_code == 0
        
        # Pretty JSON should have indentation
        with open(output_file) as f:
            content = f.read()
            # Pretty JSON has more newlines
            assert content.count('\n') > 10
    
    def test_missing_required_output_option(self, runner, sample_burp_file):
        """Test error when neither output nor swagger option is provided."""
        result = runner.invoke(main, [str(sample_burp_file)])
        
        assert result.exit_code != 0
        assert 'Error' in result.output
    
    def test_invalid_input_file(self, runner, tmp_path):
        """Test error handling for non-existent input file."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            '/nonexistent/file.xml',
            '-o', str(output_file)
        ])
        
        assert result.exit_code != 0
    
    def test_malformed_xml_input(self, runner, invalid_burp_file, tmp_path):
        """Test error handling for malformed XML."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(invalid_burp_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code != 0
        assert 'Error' in result.output
    
    def test_verbose_shows_auth_schemes(self, runner, burp_with_auth_file, tmp_path):
        """Test that verbose output shows detected auth schemes."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(burp_with_auth_file),
            '-o', str(output_file),
            '--verbose'
        ])
        
        assert result.exit_code == 0
        assert 'authentication scheme' in result.output.lower() or 'Detected' in result.output
    
    def test_verbose_shows_filtered_count(self, runner, sample_burp_file, tmp_path):
        """Test that verbose output shows filtered item count."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--verbose'
        ])
        
        assert result.exit_code == 0
        assert 'Filtered to' in result.output or 'endpoints' in result.output.lower()
    
    def test_output_file_created_with_correct_name(self, runner, sample_burp_file, tmp_path):
        """Test that output file is created with correct name."""
        output_file = tmp_path / "my-custom-api.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.name == "my-custom-api.json"
    
    def test_success_message(self, runner, sample_burp_file, tmp_path):
        """Test that success message is displayed."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert 'saved to' in result.output.lower() or 'OpenAPI specification saved' in result.output


class TestCLIWithRealData:
    """Tests using actual fixture files with JSON data."""
    
    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()
    
    def test_parse_burp_with_json_bodies(self, runner, burp_with_json_file, tmp_path):
        """Test parsing Burp export with JSON request/response bodies."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(burp_with_json_file),
            '-o', str(output_file),
            '--verbose'
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        
        with open(output_file) as f:
            spec = json.load(f)
            # Should have extracted schemas from JSON bodies
            assert 'paths' in spec
            assert len(spec['paths']) > 0
    
    def test_parse_burp_with_auth_headers(self, runner, burp_with_auth_file, tmp_path):
        """Test parsing Burp export with various auth headers."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(burp_with_auth_file),
            '-o', str(output_file),
            '--verbose'
        ])
        
        assert result.exit_code == 0
        
        with open(output_file) as f:
            spec = json.load(f)
            # Should have detected auth schemes
            assert 'components' in spec
            assert 'securitySchemes' in spec['components']
            assert len(spec['components']['securitySchemes']) > 0


class TestCLISwaggerMode:
    """Tests for Swagger UI server mode."""
    
    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()
    
    def test_swagger_help_flag_present(self, runner):
        """Test that --swagger flag is present in help."""
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert '--swagger' in result.output
        assert 'web server' in result.output.lower() or 'Swagger UI' in result.output
    
    @patch('burp2api.cli.serve_swagger_ui')
    def test_swagger_mode_with_output_file(self, mock_serve, runner, sample_burp_file, tmp_path):
        """Test swagger mode with explicit output file."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--swagger'
        ])
        
        # Should save file and call serve_swagger_ui
        assert output_file.exists()
        mock_serve.assert_called_once()
        
        # Verify the spec was passed to serve_swagger_ui
        call_args = mock_serve.call_args
        assert call_args is not None
        spec_arg = call_args[0][0]
        assert 'openapi' in spec_arg
        assert spec_arg['openapi'] == '3.0.3'
    
    @patch('burp2api.cli.serve_swagger_ui')
    def test_swagger_mode_without_output_file(self, mock_serve, runner, sample_burp_file):
        """Test swagger mode without output file (uses temp file)."""
        result = runner.invoke(main, [
            str(sample_burp_file),
            '--swagger'
        ])
        
        # Should call serve_swagger_ui even without output file
        mock_serve.assert_called_once()
        
        # Verify server was configured correctly
        call_args = mock_serve.call_args
        assert call_args[1]['host'] == 'localhost'
        assert call_args[1]['port'] == 8080
    
    @patch('burp2api.cli.serve_swagger_ui')
    def test_swagger_mode_verbose(self, mock_serve, runner, sample_burp_file, tmp_path):
        """Test swagger mode with verbose output."""
        output_file = tmp_path / "output.json"
        
        result = runner.invoke(main, [
            str(sample_burp_file),
            '-o', str(output_file),
            '--swagger',
            '--verbose'
        ])
        
        assert 'Reading Burp Suite export from' in result.output
        assert 'Generating OpenAPI specification' in result.output
        mock_serve.assert_called_once()
    
    @patch('burp2api.cli.serve_swagger_ui')
    def test_swagger_mode_with_custom_title(self, mock_serve, runner, sample_burp_file):
        """Test swagger mode with custom API title."""
        result = runner.invoke(main, [
            str(sample_burp_file),
            '--swagger',
            '--title', 'My Custom API'
        ])
        
        mock_serve.assert_called_once()
        spec_arg = mock_serve.call_args[0][0]
        assert spec_arg['info']['title'] == 'My Custom API'
    
    @patch('burp2api.cli.serve_swagger_ui')
    def test_swagger_mode_with_filters(self, mock_serve, runner, sample_burp_file):
        """Test swagger mode with include/exclude filters."""
        result = runner.invoke(main, [
            str(sample_burp_file),
            '--swagger',
            '--include', r'/api/.*',
            '--exclude', r'/admin/.*'
        ])
        
        # Should successfully call serve_swagger_ui
        mock_serve.assert_called_once()
    
    def test_neither_output_nor_swagger_specified(self, runner, sample_burp_file):
        """Test error when neither -o nor --swagger is specified."""
        result = runner.invoke(main, [str(sample_burp_file)])
        
        assert result.exit_code != 0
        assert 'Error' in result.output
        assert 'output' in result.output.lower() or 'swagger' in result.output.lower()
    
    @patch('burp2api.cli.serve_swagger_ui')
    def test_swagger_mode_spec_has_all_components(self, mock_serve, runner, burp_with_json_file):
        """Test that spec passed to swagger server has all expected components."""
        result = runner.invoke(main, [
            str(burp_with_json_file),
            '--swagger'
        ])
        
        mock_serve.assert_called_once()
        spec_arg = mock_serve.call_args[0][0]
        
        # Verify spec structure
        assert 'openapi' in spec_arg
        assert 'info' in spec_arg
        assert 'paths' in spec_arg
        assert 'servers' in spec_arg
        assert spec_arg['openapi'] == '3.0.3'
