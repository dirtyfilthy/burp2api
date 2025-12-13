"""
Static asset filtering for Burp Suite items.
"""

import re
from typing import List, Set
from burp2api.parser import BurpItem


class StaticAssetFilter:
    """Filter to identify and exclude static assets."""

    # Common static file extensions
    STATIC_EXTENSIONS: Set[str] = {
        'js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico',
        'woff', 'woff2', 'ttf', 'eot', 'otf',
        'mp4', 'webm', 'mp3', 'wav', 'ogg',
        'pdf', 'zip', 'tar', 'gz', 'rar',
        'map',  # Source maps
    }

    # Common static MIME types
    STATIC_MIMETYPES: Set[str] = {
        'image', 'video', 'audio', 'font',
        'text/css', 'text/javascript', 'application/javascript',
        'application/x-javascript', 'script',
    }

    # Common static path patterns
    STATIC_PATH_PATTERNS: List[str] = [
        r'/assets/',
        r'/static/',
        r'/images/',
        r'/img/',
        r'/js/',
        r'/css/',
        r'/fonts/',
        r'/media/',
        r'/public/',
        r'/_next/static/',
        r'/dist/',
        r'/build/',
    ]

    def __init__(self, 
                 include_patterns: List[str] = None,
                 exclude_patterns: List[str] = None,
                 filter_static: bool = True):
        """
        Initialize the filter.
        
        Filter priority (from highest to lowest):
        1. exclude_patterns - Hard exclusions, always win
        2. include_patterns - Force-include, overrides static filtering (but not excludes)
        3. filter_static - Default filtering of static assets
        4. Everything else is included
        
        Args:
            include_patterns: List of regex patterns to force-include 
                            (overrides static filtering but not excludes)
            exclude_patterns: List of regex patterns to hard-exclude
                            (highest priority, always respected)
            filter_static: Whether to filter out static assets by default
        """
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]
        self.filter_static = filter_static

    def should_include(self, item: BurpItem) -> bool:
        """
        Determine if an item should be included in the output.
        
        Priority order (clearest semantics):
        1. Exclude patterns (highest priority) - hard exclusions, always respected
        2. Include patterns - force-include even if static, but cannot override excludes
        3. Static filtering - default behavior to filter static assets
        4. Default - include everything else
        
        Args:
            item: BurpItem to check
            
        Returns:
            True if item should be included, False otherwise
        """
        # 1. Exclude patterns have highest priority (hard exclusions)
        #    These paths are NEVER included, even if they match include patterns
        for pattern in self.exclude_patterns:
            if pattern.search(item.path) or pattern.search(item.url):
                return False

        # 2. Include patterns override static filtering
        #    Use these to force-include paths that would otherwise be filtered as static
        for pattern in self.include_patterns:
            if pattern.search(item.path) or pattern.search(item.url):
                return True

        # 3. Apply static filtering if enabled
        if self.filter_static:
            if self._is_static_asset(item):
                return False

        # 4. Default: include everything else
        return True

    def _is_static_asset(self, item: BurpItem) -> bool:
        """
        Check if an item is a static asset.
        
        Args:
            item: BurpItem to check
            
        Returns:
            True if item is a static asset, False otherwise
        """
        # Check file extension
        if item.extension and item.extension.lower() in self.STATIC_EXTENSIONS:
            return True

        # Check MIME type
        if item.mimetype:
            mimetype_lower = item.mimetype.lower()
            for static_mime in self.STATIC_MIMETYPES:
                if static_mime in mimetype_lower:
                    return True

        # Check path patterns
        for pattern in self.STATIC_PATH_PATTERNS:
            if re.search(pattern, item.path, re.IGNORECASE):
                return True

        return False

    def filter_items(self, items: List[BurpItem]) -> List[BurpItem]:
        """
        Filter a list of BurpItems.
        
        Args:
            items: List of BurpItem objects
            
        Returns:
            Filtered list of BurpItem objects
        """
        return [item for item in items if self.should_include(item)]

