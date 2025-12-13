"""
Tests for burp2api.filters module.
"""

import pytest
from burp2api.filters import StaticAssetFilter
from burp2api.parser import BurpItem, HTTPRequest, HTTPResponse


class TestStaticAssetFilter:
    """Tests for StaticAssetFilter class."""
    
    def test_filter_javascript_by_extension(self):
        """Test filtering JavaScript files by extension."""
        item = self._create_item(path='/app.js', extension='js')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
        assert filter_obj.should_include(item) is False
    
    def test_filter_css_by_extension(self):
        """Test filtering CSS files by extension."""
        item = self._create_item(path='/styles.css', extension='css')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
        assert filter_obj.should_include(item) is False
    
    def test_filter_images_by_extension(self):
        """Test filtering image files by extension."""
        for ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'ico']:
            item = self._create_item(path=f'/image.{ext}', extension=ext)
            filter_obj = StaticAssetFilter(filter_static=True)
            
            assert filter_obj._is_static_asset(item) is True
    
    def test_filter_fonts_by_extension(self):
        """Test filtering font files by extension."""
        for ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']:
            item = self._create_item(path=f'/font.{ext}', extension=ext)
            filter_obj = StaticAssetFilter(filter_static=True)
            
            assert filter_obj._is_static_asset(item) is True
    
    def test_filter_by_image_mimetype(self):
        """Test filtering by image MIME type."""
        item = self._create_item(path='/logo', mimetype='image/png')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
        assert filter_obj.should_include(item) is False
    
    def test_filter_by_video_mimetype(self):
        """Test filtering by video MIME type."""
        item = self._create_item(path='/video.mp4', mimetype='video/mp4')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
    
    def test_filter_by_javascript_mimetype(self):
        """Test filtering by JavaScript MIME type."""
        item = self._create_item(path='/app.js', mimetype='application/javascript')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
    
    def test_filter_by_static_path_pattern(self):
        """Test filtering by static path patterns."""
        paths = ['/static/app.js', '/assets/image.png', '/images/logo.png',
                '/js/main.js', '/css/style.css', '/fonts/font.woff']
        
        for path in paths:
            item = self._create_item(path=path)
            filter_obj = StaticAssetFilter(filter_static=True)
            
            assert filter_obj._is_static_asset(item) is True
    
    def test_include_api_endpoint(self):
        """Test that API endpoints are included."""
        item = self._create_item(path='/api/users', mimetype='application/json')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is False
        assert filter_obj.should_include(item) is True
    
    def test_include_pattern_overrides_static_filter(self):
        """Test that include pattern overrides static filtering."""
        item = self._create_item(path='/special/config.js', extension='js')
        filter_obj = StaticAssetFilter(
            filter_static=True,
            include_patterns=[r'/special/.*']
        )
        
        # JS would normally be filtered, but include pattern overrides
        assert filter_obj.should_include(item) is True
    
    def test_exclude_pattern(self):
        """Test exclude pattern functionality."""
        item = self._create_item(path='/api/admin/users')
        filter_obj = StaticAssetFilter(
            filter_static=False,
            exclude_patterns=[r'/admin/.*']
        )
        
        assert filter_obj.should_include(item) is False
    
    def test_multiple_exclude_patterns(self):
        """Test multiple exclude patterns."""
        filter_obj = StaticAssetFilter(
            filter_static=False,
            exclude_patterns=[r'/admin/.*', r'/internal/.*']
        )
        
        admin_item = self._create_item(path='/api/admin/users')
        internal_item = self._create_item(path='/api/internal/config')
        public_item = self._create_item(path='/api/public/data')
        
        assert filter_obj.should_include(admin_item) is False
        assert filter_obj.should_include(internal_item) is False
        assert filter_obj.should_include(public_item) is True
    
    def test_disable_static_filtering(self):
        """Test disabling static asset filtering."""
        item = self._create_item(path='/static/app.js', extension='js')
        filter_obj = StaticAssetFilter(filter_static=False)
        
        assert filter_obj.should_include(item) is True
    
    def test_filter_items_list(self, api_item, static_item):
        """Test filtering a list of items."""
        items = [api_item, static_item]
        filter_obj = StaticAssetFilter(filter_static=True)
        
        filtered = filter_obj.filter_items(items)
        
        assert len(filtered) == 1
        assert filtered[0] == api_item
    
    def test_filter_empty_list(self):
        """Test filtering empty list."""
        filter_obj = StaticAssetFilter(filter_static=True)
        filtered = filter_obj.filter_items([])
        
        assert filtered == []
    
    def test_combined_include_exclude_patterns(self):
        """Test combining include and exclude patterns - exclude wins."""
        filter_obj = StaticAssetFilter(
            filter_static=True,
            include_patterns=[r'/api/.*'],
            exclude_patterns=[r'/api/admin/.*']
        )
        
        # Include pattern matches and exclude doesn't - should include
        api_item = self._create_item(path='/api/users')
        assert filter_obj.should_include(api_item) is True
        
        # Both patterns match - EXCLUDE WINS (highest priority)
        admin_item = self._create_item(path='/api/admin/users')
        assert filter_obj.should_include(admin_item) is False
        
        # Static asset with no include match - should filter
        static_item = self._create_item(path='/static/app.js', extension='js')
        assert filter_obj.should_include(static_item) is False
    
    def test_case_insensitive_extension(self):
        """Test case-insensitive extension matching."""
        item = self._create_item(path='/app.JS', extension='JS')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
    
    def test_source_map_files(self):
        """Test filtering source map files."""
        item = self._create_item(path='/app.js.map', extension='map')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
    
    def test_nextjs_static_path(self):
        """Test filtering Next.js static paths."""
        item = self._create_item(path='/_next/static/chunks/main.js')
        filter_obj = StaticAssetFilter(filter_static=True)
        
        assert filter_obj._is_static_asset(item) is True
    
    def test_exclude_always_wins_over_include(self):
        """Test that exclude patterns have highest priority over include."""
        filter_obj = StaticAssetFilter(
            filter_static=False,
            include_patterns=[r'/special/.*'],
            exclude_patterns=[r'/special/secret/.*']
        )
        
        # Include matches but exclude also matches - exclude wins
        secret_item = self._create_item(path='/special/secret/config')
        assert filter_obj.should_include(secret_item) is False
        
        # Only include matches - should be included
        special_item = self._create_item(path='/special/public/data')
        assert filter_obj.should_include(special_item) is True
    
    def test_include_overrides_static_filtering(self):
        """Test that include patterns override static filtering."""
        filter_obj = StaticAssetFilter(
            filter_static=True,
            include_patterns=[r'/important/.*']
        )
        
        # JS file that matches include pattern - should be included despite being static
        important_js = self._create_item(path='/important/config.js', extension='js')
        assert filter_obj.should_include(important_js) is True
        
        # JS file that doesn't match include - should be filtered
        other_js = self._create_item(path='/other/app.js', extension='js')
        assert filter_obj.should_include(other_js) is False
    
    # Helper method
    def _create_item(self, path='/', extension='', mimetype='', url='https://example.com'):
        """Helper to create a BurpItem for testing."""
        return BurpItem(
            time='Wed Dec 10 12:00:00 UTC 2025',
            url=url + path,
            host='example.com',
            host_ip='1.2.3.4',
            port=443,
            protocol='https',
            method='GET',
            path=path,
            extension=extension,
            request=HTTPRequest(method='GET', path=path, headers={}, query_params={}),
            response=HTTPResponse(status=200, headers={}, body=None),
            mimetype=mimetype if mimetype else None,
            comment=None
        )

