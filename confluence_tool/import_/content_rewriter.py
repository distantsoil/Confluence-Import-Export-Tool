"""Content rewriter for space key remapping during import."""

import re
import logging
from typing import Dict, Any, Tuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class ContentRewriter:
    """Handles rewriting of space key references in Confluence content."""
    
    def __init__(self, old_space_key: str, new_space_key: str):
        """Initialize content rewriter.
        
        Args:
            old_space_key: Original space key to replace
            new_space_key: New space key to use
        """
        self.old_space_key = old_space_key
        self.new_space_key = new_space_key
        self.stats = {
            'links_rewritten': 0,
            'macros_updated': 0,
            'attachments_updated': 0,
            'wiki_links_updated': 0,
            'html_anchors_updated': 0
        }
    
    def rewrite_content(self, content: str) -> Tuple[str, Dict[str, int]]:
        """Rewrite all space key references in content.
        
        Args:
            content: Original HTML/storage format content
            
        Returns:
            Tuple of (rewritten_content, statistics)
        """
        # Initialize per-content stats
        content_stats = {
            'links_rewritten': 0,
            'macros_updated': 0,
            'attachments_updated': 0,
            'wiki_links_updated': 0,
            'html_anchors_updated': 0
        }
        
        if not content:
            return content, content_stats
        
        original_content = content
        
        # 1. Rewrite Confluence XML space key tags: <ri:space-key>KB</ri:space-key>
        content, count = self._rewrite_xml_space_keys(content)
        content_stats['links_rewritten'] += count
        
        # 2. Rewrite wiki-style links: [Page Title|KB:Page Title]
        content, count = self._rewrite_wiki_links(content)
        content_stats['wiki_links_updated'] += count
        
        # 3. Rewrite HTML anchor tags with space URLs: /wiki/spaces/KB/pages/...
        content, count = self._rewrite_html_anchors(content)
        content_stats['html_anchors_updated'] += count
        
        # 4. Rewrite macro parameters with space keys
        content, count = self._rewrite_macro_space_parameters(content)
        content_stats['macros_updated'] += count
        
        # 5. Rewrite attachment space key references
        content, count = self._rewrite_attachment_space_keys(content)
        content_stats['attachments_updated'] += count
        
        # Update cumulative stats
        for key in content_stats:
            self.stats[key] += content_stats[key]
        
        # Log rewriting if changes were made
        if content != original_content:
            total_changes = sum(content_stats.values())
            logger.debug(f"Rewrote {total_changes} space key references in content")
        
        return content, content_stats
    
    def _rewrite_xml_space_keys(self, content: str) -> Tuple[str, int]:
        """Rewrite <ri:space-key>OLD</ri:space-key> tags.
        
        Args:
            content: HTML content
            
        Returns:
            Tuple of (rewritten_content, count)
        """
        count = 0
        
        # Pattern to match <ri:space-key>SPACEKEY</ri:space-key>
        # Use word boundaries to avoid partial matches
        pattern = rf'(<ri:space-key>){re.escape(self.old_space_key)}(</ri:space-key>)'
        
        matches = list(re.finditer(pattern, content))
        count = len(matches)
        
        if count > 0:
            content = re.sub(pattern, rf'\1{self.new_space_key}\2', content)
            logger.debug(f"Rewrote {count} <ri:space-key> tags")
        
        return content, count
    
    def _rewrite_wiki_links(self, content: str) -> Tuple[str, int]:
        """Rewrite wiki-style links [Title|SPACE:PageTitle].
        
        Args:
            content: HTML content
            
        Returns:
            Tuple of (rewritten_content, count)
        """
        count = 0
        
        # Pattern to match [text|SPACE:page] or [SPACE:page]
        # Use word boundary before space key to avoid partial matches
        pattern = rf'\[([^\]]*?\|)?{re.escape(self.old_space_key)}:([^\]]+)\]'
        
        matches = list(re.finditer(pattern, content))
        count = len(matches)
        
        if count > 0:
            # Replace OLD:page with NEW:page
            content = re.sub(
                pattern,
                rf'[\1{self.new_space_key}:\2]',
                content
            )
            logger.debug(f"Rewrote {count} wiki-style links")
        
        return content, count
    
    def _rewrite_html_anchors(self, content: str) -> Tuple[str, int]:
        """Rewrite HTML anchor tags with space URLs.
        
        Args:
            content: HTML content
            
        Returns:
            Tuple of (rewritten_content, count)
        """
        count = 0
        
        # Pattern to match href="/wiki/spaces/SPACE/..."
        # Also match href="https://domain/wiki/spaces/SPACE/..."
        patterns = [
            # Relative URLs: /wiki/spaces/SPACE/
            (rf'(href=["\'])(/wiki/spaces/){re.escape(self.old_space_key)}(/)', rf'\1\2{self.new_space_key}\3'),
            # Absolute URLs: https://domain/wiki/spaces/SPACE/
            (rf'(href=["\'][^"\']*?/wiki/spaces/){re.escape(self.old_space_key)}(/)', rf'\1{self.new_space_key}\2'),
        ]
        
        for pattern, replacement in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                count += len(matches)
                content = re.sub(
                    pattern,
                    replacement,
                    content,
                    flags=re.IGNORECASE
                )
        
        if count > 0:
            logger.debug(f"Rewrote {count} HTML anchor space URLs")
        
        return content, count
    
    def _rewrite_macro_space_parameters(self, content: str) -> Tuple[str, int]:
        """Rewrite space key references in macro parameters.
        
        Args:
            content: HTML content
            
        Returns:
            Tuple of (rewritten_content, count)
        """
        count = 0
        
        # Pattern to match macro parameters with space keys
        # Example: <ac:parameter ac:name="root"><ri:space-key>SPACE</ri:space-key></ac:parameter>
        # This is already handled by _rewrite_xml_space_keys, but we'll also handle
        # plain text space parameters
        
        # Match: <ac:parameter ac:name="...">SPACE:...</ac:parameter>
        pattern = rf'(<ac:parameter[^>]*>){re.escape(self.old_space_key)}:([^<]*</ac:parameter>)'
        
        matches = list(re.finditer(pattern, content))
        if matches:
            count = len(matches)
            content = re.sub(
                pattern,
                rf'\1{self.new_space_key}:\2',
                content
            )
            logger.debug(f"Rewrote {count} macro space parameters")
        
        return content, count
    
    def _rewrite_attachment_space_keys(self, content: str) -> Tuple[str, int]:
        """Rewrite space key references in attachment tags.
        
        Args:
            content: HTML content
            
        Returns:
            Tuple of (rewritten_content, count)
        """
        count = 0
        
        # Pattern to match attachment references with space keys
        # <ri:attachment ...><ri:space-key>SPACE</ri:space-key>...
        # This is handled by _rewrite_xml_space_keys, so just count those
        
        # Additional pattern for attachment URLs in src attributes
        pattern = rf'(src=["\'][^"\']*?/download/attachments/[^/]+/spaces/){re.escape(self.old_space_key)}(/)'
        
        matches = list(re.finditer(pattern, content))
        if matches:
            count = len(matches)
            content = re.sub(
                pattern,
                rf'\1{self.new_space_key}\2',
                content
            )
            logger.debug(f"Rewrote {count} attachment space URLs")
        
        return content, count
    
    def get_stats(self) -> Dict[str, int]:
        """Get cumulative statistics for all rewriting operations.
        
        Returns:
            Statistics dictionary
        """
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics counters."""
        for key in self.stats:
            self.stats[key] = 0
