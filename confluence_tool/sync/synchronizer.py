"""Confluence space synchronizer implementation."""

import os
import json
import logging
import tempfile
from typing import Dict, List, Any, Tuple, Set
from datetime import datetime
from tqdm import tqdm

from ..api.client import ConfluenceAPIClient
from ..export.exporter import ConfluenceExporter
from ..import_.importer import ConfluenceImporter
from ..utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


class ConfluenceSynchronizer:
    """Synchronizes content between Confluence spaces in different environments."""
    
    def __init__(self, source_client: ConfluenceAPIClient, target_client: ConfluenceAPIClient,
                 export_config: Dict[str, Any], import_config: Dict[str, Any]):
        """Initialize synchronizer.
        
        Args:
            source_client: Client for source Confluence environment
            target_client: Client for target Confluence environment
            export_config: Configuration for export operations
            import_config: Configuration for import operations
        """
        self.source_client = source_client
        self.target_client = target_client
        self.export_config = export_config
        self.import_config = import_config
        
        self.sync_stats = {
            'pages_analyzed': 0,
            'pages_missing': 0,
            'pages_newer_in_source': 0,
            'pages_copied': 0,
            'pages_updated': 0,
            'attachments_copied': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
    
    def sync_space(self, source_space_key: str, target_space_key: str, 
                   mode: str = "missing_only") -> Dict[str, Any]:
        """Synchronize content between source and target spaces.
        
        Args:
            source_space_key: Source space key
            target_space_key: Target space key
            mode: Sync mode - "missing_only", "newer_only", or "full"
                - missing_only: Copy only pages that don't exist in target
                - newer_only: Copy pages that are newer in source
                - full: Copy all pages, updating existing ones
        
        Returns:
            Synchronization statistics dictionary
        """
        logger.info(f"Starting sync from {source_space_key} to {target_space_key} (mode: {mode})")
        self.sync_stats['start_time'] = datetime.now()
        
        try:
            # Get content from both spaces
            print("Analyzing source space...")
            source_pages = self.source_client.get_all_space_content(source_space_key, 'page')
            
            print("Analyzing target space...")
            target_pages = self.target_client.get_all_space_content(target_space_key, 'page')
            
            # Create lookup dictionaries for efficient comparison
            target_pages_by_title = {page['title']: page for page in target_pages}
            
            # Determine which pages need to be synchronized
            pages_to_sync = self._determine_pages_to_sync(
                source_pages, target_pages_by_title, mode
            )
            
            if not pages_to_sync:
                print(f"No pages need synchronization in mode '{mode}'")
                return self.sync_stats
            
            print(f"Found {len(pages_to_sync)} pages to synchronize")
            
            # Create temporary directory for export/import operations
            with tempfile.TemporaryDirectory() as temp_dir:
                # Export and import each page that needs syncing
                self._sync_pages(pages_to_sync, source_space_key, target_space_key, temp_dir)
            
            self.sync_stats['end_time'] = datetime.now()
            duration = self.sync_stats['end_time'] - self.sync_stats['start_time']
            
            logger.info(f"Sync completed in {duration}")
            logger.info(f"Copied: {self.sync_stats['pages_copied']} pages, "
                       f"Updated: {self.sync_stats['pages_updated']} pages, "
                       f"Attachments: {self.sync_stats['attachments_copied']}")
            
            if self.sync_stats['errors']:
                logger.warning(f"Sync completed with {len(self.sync_stats['errors'])} errors")
            
            return self.sync_stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
    
    def _determine_pages_to_sync(self, source_pages: List[Dict[str, Any]], 
                               target_pages_by_title: Dict[str, Dict[str, Any]], 
                               mode: str) -> List[Dict[str, Any]]:
        """Determine which pages need to be synchronized based on the mode.
        
        Args:
            source_pages: List of pages from source space
            target_pages_by_title: Dictionary of target pages keyed by title
            mode: Sync mode
            
        Returns:
            List of source pages that need to be synchronized
        """
        pages_to_sync = []
        
        for source_page in source_pages:
            self.sync_stats['pages_analyzed'] += 1
            title = source_page['title']
            
            if title not in target_pages_by_title:
                # Page doesn't exist in target
                self.sync_stats['pages_missing'] += 1
                pages_to_sync.append(source_page)
                logger.debug(f"Missing page: {title}")
                
            elif mode in ["newer_only", "full"]:
                # Compare versions to see if source is newer
                target_page = target_pages_by_title[title]
                source_version = source_page.get('version', {}).get('when', '')
                target_version = target_page.get('version', {}).get('when', '')
                
                # Parse dates for comparison
                try:
                    from dateutil.parser import parse
                    source_date = parse(source_version) if source_version else None
                    target_date = parse(target_version) if target_version else None
                    
                    if source_date and target_date and source_date > target_date:
                        self.sync_stats['pages_newer_in_source'] += 1
                        pages_to_sync.append(source_page)
                        logger.debug(f"Newer page: {title}")
                    elif mode == "full":
                        # In full mode, sync all pages regardless of version
                        pages_to_sync.append(source_page)
                        
                except Exception as e:
                    logger.warning(f"Could not compare versions for page {title}: {e}")
                    if mode == "full":
                        pages_to_sync.append(source_page)
        
        return pages_to_sync
    
    def _sync_pages(self, pages_to_sync: List[Dict[str, Any]], 
                   source_space_key: str, target_space_key: str, temp_dir: str) -> None:
        """Synchronize the specified pages.
        
        Args:
            pages_to_sync: List of pages to synchronize
            source_space_key: Source space key
            target_space_key: Target space key
            temp_dir: Temporary directory for operations
        """
        # Create a custom exporter that exports only specific pages
        source_exporter = ConfluenceExporter(self.source_client, self.export_config)
        target_importer = ConfluenceImporter(self.target_client, self.import_config)
        
        with tqdm(total=len(pages_to_sync), desc="Synchronizing pages") as pbar:
            for page in pages_to_sync:
                try:
                    self._sync_single_page(page, source_space_key, target_space_key, 
                                         temp_dir, source_exporter, target_importer)
                    self.sync_stats['pages_copied'] += 1
                except Exception as e:
                    error_msg = f"Failed to sync page '{page.get('title', 'Unknown')}': {e}"
                    logger.error(error_msg)
                    self.sync_stats['errors'].append(error_msg)
                finally:
                    pbar.update(1)
    
    def _sync_single_page(self, page: Dict[str, Any], source_space_key: str, 
                         target_space_key: str, temp_dir: str,
                         exporter: ConfluenceExporter, importer: ConfluenceImporter) -> None:
        """Synchronize a single page.
        
        Args:
            page: Page dictionary from source
            source_space_key: Source space key
            target_space_key: Target space key
            temp_dir: Temporary directory
            exporter: Source exporter instance
            importer: Target importer instance
        """
        page_id = page['id']
        title = page['title']
        
        # Create a temporary export directory for this page
        page_export_dir = os.path.join(temp_dir, sanitize_filename(f"{title}_{page_id}"))
        os.makedirs(page_export_dir, exist_ok=True)
        
        # Create pages subdirectory
        pages_dir = os.path.join(page_export_dir, 'pages')
        os.makedirs(pages_dir, exist_ok=True)
        
        try:
            # Export the single page
            exporter._export_single_page(page, pages_dir)
            
            # Import the page to target environment
            # We need to modify the import process to handle single pages
            page_files = [f for f in os.listdir(pages_dir) if f.endswith('.html')]
            
            if page_files:
                # Load page metadata
                pages_metadata = importer._load_pages_metadata(pages_dir, page_files)
                
                # Import each page
                for page_info in pages_metadata:
                    importer._import_single_page(
                        page_info, pages_dir, target_space_key, 'page'
                    )
                
                logger.debug(f"Successfully synced page: {title}")
            
        except Exception as e:
            logger.error(f"Error syncing page {title}: {e}")
            raise
    
    def compare_spaces(self, source_space_key: str, target_space_key: str) -> Dict[str, Any]:
        """Compare two spaces and return detailed analysis.
        
        Args:
            source_space_key: Source space key
            target_space_key: Target space key
            
        Returns:
            Dictionary with comparison results
        """
        print("Comparing spaces...")
        
        try:
            # Get content from both spaces
            source_pages = self.source_client.get_all_space_content(source_space_key, 'page')
            target_pages = self.target_client.get_all_space_content(target_space_key, 'page')
            
            # Create lookup sets and dictionaries
            source_titles = {page['title'] for page in source_pages}
            target_titles = {page['title'] for page in target_pages}
            
            source_pages_by_title = {page['title']: page for page in source_pages}
            target_pages_by_title = {page['title']: page for page in target_pages}
            
            # Calculate differences
            only_in_source = source_titles - target_titles
            only_in_target = target_titles - source_titles
            common_pages = source_titles & target_titles
            
            # Analyze common pages for version differences
            newer_in_source = []
            newer_in_target = []
            same_version = []
            
            for title in common_pages:
                source_page = source_pages_by_title[title]
                target_page = target_pages_by_title[title]
                
                source_version = source_page.get('version', {}).get('when', '')
                target_version = target_page.get('version', {}).get('when', '')
                
                try:
                    from dateutil.parser import parse
                    source_date = parse(source_version) if source_version else None
                    target_date = parse(target_version) if target_version else None
                    
                    if source_date and target_date:
                        if source_date > target_date:
                            newer_in_source.append(title)
                        elif target_date > source_date:
                            newer_in_target.append(title)
                        else:
                            same_version.append(title)
                    else:
                        same_version.append(title)  # Can't compare, assume same
                        
                except Exception as e:
                    logger.warning(f"Could not compare versions for page {title}: {e}")
                    same_version.append(title)
            
            comparison = {
                'source_space': source_space_key,
                'target_space': target_space_key,
                'source_page_count': len(source_pages),
                'target_page_count': len(target_pages),
                'only_in_source': list(only_in_source),
                'only_in_target': list(only_in_target),
                'common_pages': list(common_pages),
                'newer_in_source': newer_in_source,
                'newer_in_target': newer_in_target,
                'same_version': same_version,
                'comparison_date': datetime.now().isoformat()
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing spaces: {e}")
            raise
    
    def create_sync_report(self, comparison: Dict[str, Any], output_path: str) -> None:
        """Create a detailed sync report.
        
        Args:
            comparison: Comparison results from compare_spaces
            output_path: Path to save the report
        """
        # Create JSON report
        json_report_path = output_path.replace('.html', '.json') if output_path.endswith('.html') else f"{output_path}.json"
        
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        
        # Create HTML report
        html_report_path = output_path if output_path.endswith('.html') else f"{output_path}.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confluence Space Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .header {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .missing {{ color: #d32f2f; }}
        .newer {{ color: #1976d2; }}
        .same {{ color: #388e3c; }}
        .list-item {{ margin: 5px 0; padding: 5px; background-color: #fafafa; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1 class="header">Confluence Space Comparison Report</h1>
    
    <div class="section">
        <h2>Overview</h2>
        <p><strong>Source Space:</strong> {comparison['source_space']}</p>
        <p><strong>Target Space:</strong> {comparison['target_space']}</p>
        <p><strong>Comparison Date:</strong> {comparison['comparison_date']}</p>
    </div>
    
    <div class="section stats">
        <h2>Statistics</h2>
        <ul>
            <li><strong>Source Pages:</strong> {comparison['source_page_count']}</li>
            <li><strong>Target Pages:</strong> {comparison['target_page_count']}</li>
            <li><strong>Common Pages:</strong> {len(comparison['common_pages'])}</li>
            <li class="missing"><strong>Only in Source:</strong> {len(comparison['only_in_source'])}</li>
            <li class="missing"><strong>Only in Target:</strong> {len(comparison['only_in_target'])}</li>
            <li class="newer"><strong>Newer in Source:</strong> {len(comparison['newer_in_source'])}</li>
            <li class="newer"><strong>Newer in Target:</strong> {len(comparison['newer_in_target'])}</li>
            <li class="same"><strong>Same Version:</strong> {len(comparison['same_version'])}</li>
        </ul>
    </div>
"""
        
        # Add sections for different categories
        sections = [
            ('only_in_source', 'Pages Only in Source', 'missing'),
            ('only_in_target', 'Pages Only in Target', 'missing'),
            ('newer_in_source', 'Pages Newer in Source', 'newer'),
            ('newer_in_target', 'Pages Newer in Target', 'newer'),
        ]
        
        for key, title, css_class in sections:
            if comparison[key]:
                html_content += f"""
    <div class="section">
        <h2 class="{css_class}">{title} ({len(comparison[key])} pages)</h2>
        <div>
"""
                for page_title in comparison[key]:
                    html_content += f'            <div class="list-item">{page_title}</div>\n'
                
                html_content += """        </div>
    </div>
"""
        
        html_content += """
</body>
</html>"""
        
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Comparison report saved to {html_report_path}")
        logger.info(f"JSON data saved to {json_report_path}")