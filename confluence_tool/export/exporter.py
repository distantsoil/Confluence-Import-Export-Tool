"""Confluence space exporter implementation."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import concurrent.futures
from tqdm import tqdm

from ..api.client import ConfluenceAPIClient
from ..utils.helpers import (
    sanitize_filename, create_directory_structure, 
    get_safe_page_filename
)

logger = logging.getLogger(__name__)


class ConfluenceExporter:
    """Robust Confluence space exporter with comprehensive error handling."""
    
    def __init__(self, client: ConfluenceAPIClient, export_config: Dict[str, Any]):
        """Initialize exporter.
        
        Args:
            client: Confluence API client
            export_config: Export configuration dictionary
        """
        self.client = client
        self.config = export_config
        self.export_stats = {
            'pages_exported': 0,
            'folders_exported': 0,
            'databases_exported': 0,
            'attachments_exported': 0,
            'comments_exported': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
    
    def export_space(self, space_key: str) -> str:
        """Export a complete Confluence space.
        
        Args:
            space_key: Key of the space to export
            
        Returns:
            Path to the export directory
            
        Raises:
            Exception: If export fails
        """
        logger.info(f"Starting export of space: {space_key}")
        self.export_stats['start_time'] = datetime.now()
        
        try:
            # Create export directory structure
            export_dir = self._create_export_directory(space_key)
            
            # Export space metadata
            space_info = self._export_space_metadata(space_key, export_dir)
            
            # Export folders and databases if available (Cloud only via v2 API)
            space_id = space_info.get('id')
            if space_id:
                self._export_folders(space_id, export_dir)
                self._export_databases(space_id, export_dir)
            
            # Get all pages in the space
            pages = self.client.get_all_space_content(space_key, 'page')
            logger.info(f"Found {len(pages)} pages to export")
            
            # Export pages with progress tracking
            if pages:
                self._export_pages(pages, export_dir)
            
            # Export blog posts if they exist
            blog_posts = self.client.get_all_space_content(space_key, 'blogpost')
            if blog_posts:
                logger.info(f"Found {len(blog_posts)} blog posts to export")
                self._export_pages(blog_posts, export_dir, content_type='blogpost')
            
            # Create export summary
            self._create_export_summary(export_dir, space_info)
            
            self.export_stats['end_time'] = datetime.now()
            duration = self.export_stats['end_time'] - self.export_stats['start_time']
            
            logger.info(f"Export completed successfully in {duration}")
            logger.info(f"Exported: {self.export_stats['pages_exported']} pages, "
                       f"{self.export_stats['folders_exported']} folders, "
                       f"{self.export_stats['databases_exported']} database stubs, "
                       f"{self.export_stats['attachments_exported']} attachments, "
                       f"{self.export_stats['comments_exported']} comments")
            
            if self.export_stats['errors']:
                logger.warning(f"Export completed with {len(self.export_stats['errors'])} errors")
            
            return export_dir
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
    
    def _create_export_directory(self, space_key: str) -> str:
        """Create directory structure for export.
        
        Args:
            space_key: Space key
            
        Returns:
            Path to export directory
        """
        base_dir = self.config.get('output_directory', './exports')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dirname = f"{space_key}_{timestamp}"
        
        export_dir = create_directory_structure(base_dir, export_dirname)
        logger.info(f"Created export directory: {export_dir}")
        
        return export_dir
    
    def _export_space_metadata(self, space_key: str, export_dir: str) -> Dict[str, Any]:
        """Export space metadata.
        
        Args:
            space_key: Space key
            export_dir: Export directory path
            
        Returns:
            Space metadata dictionary
        """
        try:
            # Get space information
            spaces = self.client.get_spaces(limit=1, start=0)
            space_info = None
            
            # Find the specific space
            all_spaces = self.client.get_all_spaces()
            for space in all_spaces:
                if space['key'] == space_key:
                    space_info = space
                    break
            
            if not space_info:
                raise ValueError(f"Space {space_key} not found")
            
            # Save space metadata
            metadata_file = os.path.join(export_dir, 'metadata', 'space_info.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(space_info, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Exported space metadata to {metadata_file}")
            return space_info
            
        except Exception as e:
            error_msg = f"Failed to export space metadata: {e}"
            logger.error(error_msg)
            self.export_stats['errors'].append(error_msg)
            return {}
    
    def _export_folders(self, space_id: str, export_dir: str) -> None:
        """Export folders from a space.
        
        Args:
            space_id: Space ID
            export_dir: Export directory path
        """
        try:
            # Get all folders in the space
            folders = self.client.get_folders(space_id)
            
            if not folders:
                logger.info("No folders found in space (may not be available in this Confluence instance)")
                return
            
            logger.info(f"Found {len(folders)} folders to export")
            
            # Create folders directory
            folders_dir = os.path.join(export_dir, 'folders')
            os.makedirs(folders_dir, exist_ok=True)
            
            # Save folders metadata as JSON
            folders_metadata_file = os.path.join(folders_dir, 'folders_metadata.json')
            with open(folders_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(folders, f, indent=2, ensure_ascii=False)
            
            # Update export stats
            self.export_stats['folders_exported'] = len(folders)
            
            logger.info(f"Exported {len(folders)} folders to {folders_metadata_file}")
            
        except Exception as e:
            error_msg = f"Failed to export folders: {e}"
            logger.warning(error_msg)
            # Don't add to errors as folders may not be available in all instances
            logger.debug(f"Folder export error details: {e}", exc_info=True)

    def _export_databases(self, space_id: str, export_dir: str) -> None:
        """Export database stubs from a space.

        Exports database metadata (title, id, parentId hierarchy) so that empty
        database containers can be recreated during import, preserving the
        sidebar structure.  Database *content* (rows, columns, data) cannot be
        exported via the REST API and is not captured here.

        Args:
            space_id: Space ID
            export_dir: Export directory path
        """
        try:
            databases = self.client.get_databases(space_id)

            if not databases:
                logger.info(
                    "No databases found in space "
                    "(may not be available in this Confluence instance)"
                )
                return

            logger.info(f"Found {len(databases)} databases to export (structure only — data cannot be exported via API)")

            databases_dir = os.path.join(export_dir, 'databases')
            os.makedirs(databases_dir, exist_ok=True)

            databases_metadata_file = os.path.join(databases_dir, 'databases_metadata.json')
            with open(databases_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(databases, f, indent=2, ensure_ascii=False)

            self.export_stats['databases_exported'] = len(databases)

            logger.info(
                f"Exported {len(databases)} database stubs to {databases_metadata_file}. "
                f"Note: database content (rows/data) was not exported."
            )

        except Exception as e:
            error_msg = f"Failed to export databases: {e}"
            logger.warning(error_msg)
            # Don't add to errors — databases may not be available in all instances
            logger.debug(f"Database export error details: {e}", exc_info=True)

    def _export_pages(self, pages: List[Dict[str, Any]], export_dir: str, 
                     content_type: str = 'page') -> None:
        """Export pages with multithreading support.
        
        Args:
            pages: List of page dictionaries
            export_dir: Export directory path
            content_type: Type of content (page or blogpost)
        """
        max_workers = self.config.get('max_workers', 5)
        
        # Create subdirectory for this content type
        content_dir = os.path.join(export_dir, f"{content_type}s")
        os.makedirs(content_dir, exist_ok=True)
        
        # Export pages with progress bar
        with tqdm(total=len(pages), desc=f"Exporting {content_type}s") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all page export tasks
                future_to_page = {
                    executor.submit(self._export_single_page, page, content_dir): page 
                    for page in pages
                }
                
                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        future.result()
                        self.export_stats['pages_exported'] += 1
                    except Exception as e:
                        error_msg = f"Failed to export {content_type} '{page.get('title', 'Unknown')}': {e}"
                        logger.error(error_msg)
                        self.export_stats['errors'].append(error_msg)
                    finally:
                        pbar.update(1)
    
    def _export_single_page(self, page: Dict[str, Any], content_dir: str) -> None:
        """Export a single page with all its components.
        
        Args:
            page: Page dictionary from Confluence API
            content_dir: Directory to save page content
        """
        page_id = page['id']
        title = page['title']
        
        try:
            # Create safe filename
            include_id = self.config.get('naming', {}).get('include_page_id', False)
            filename = get_safe_page_filename(title, page_id, include_id)
            page_file = os.path.join(content_dir, filename)
            
            # Export page content as HTML
            if self.config.get('format', {}).get('html', True):
                self._export_page_html(page, page_file)
            
            # Export page metadata
            metadata_file = os.path.join(content_dir, f"{os.path.splitext(filename)[0]}_metadata.json")
            self._export_page_metadata(page, metadata_file)
            
            # Export attachments if enabled
            if self.config.get('format', {}).get('attachments', True):
                self._export_page_attachments(page_id, content_dir, title)
            
            # Export comments if enabled
            if self.config.get('format', {}).get('comments', True):
                self._export_page_comments(page_id, content_dir, title)
            
            logger.debug(f"Successfully exported page: {title}")
            
        except Exception as e:
            logger.error(f"Error exporting page {title}: {e}")
            raise
    
    def _export_page_html(self, page: Dict[str, Any], page_file: str) -> None:
        """Export page content as HTML.
        
        Args:
            page: Page dictionary
            page_file: Output file path
        """
        title = page['title']
        
        # Get page content
        body_storage = page.get('body', {}).get('storage', {}).get('value', '')
        
        # Create HTML structure
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .page-title {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .page-content {{ margin-top: 20px; }}
        .metadata {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 20px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1 class="page-title">{title}</h1>
    <div class="page-content">
        {body_storage}
    </div>
    <div class="metadata">
        <strong>Page ID:</strong> {page['id']}<br>
        <strong>Space:</strong> {page['space']['key']}<br>
        <strong>Version:</strong> {page['version']['number']}<br>
        <strong>Created:</strong> {page['version']['when']}<br>
        <strong>Author:</strong> {page['version']['by']['displayName']}
    </div>
</body>
</html>"""
        
        # Write HTML file
        with open(page_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _export_page_metadata(self, page: Dict[str, Any], metadata_file: str) -> None:
        """Export page metadata as JSON.
        
        Args:
            page: Page dictionary
            metadata_file: Output metadata file path
        """
        # Clean up page data for JSON serialization
        metadata = {
            'id': page['id'],
            'title': page['title'],
            'type': page['type'],
            'space': page['space'],
            'version': page['version'],
            'ancestors': page.get('ancestors', []),
            'children': page.get('children', {}),
            'descendants': page.get('descendants', {}),
            'metadata': page.get('metadata', {}),
            'restrictions': page.get('restrictions', {}),
            'export_date': datetime.now().isoformat()
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _export_page_attachments(self, page_id: str, content_dir: str, page_title: str) -> None:
        """Export attachments for a page.
        
        Args:
            page_id: Page ID
            content_dir: Content directory
            page_title: Page title for directory naming
        """
        try:
            attachments = self.client.get_page_attachments(page_id)
            
            if not attachments:
                return
            
            # Create attachments directory for this page
            # content_dir is export_dir/pages, go up one level to get export_dir
            safe_title = sanitize_filename(page_title)
            export_dir = os.path.dirname(content_dir)
            attach_dir = os.path.join(export_dir, 'attachments', safe_title)
            os.makedirs(attach_dir, exist_ok=True)
            
            # Download each attachment
            for attachment in attachments:
                try:
                    self._download_attachment(attachment, attach_dir)
                    self.export_stats['attachments_exported'] += 1
                except Exception as e:
                    error_msg = f"Failed to download attachment {attachment.get('title', 'Unknown')}: {e}"
                    logger.warning(error_msg)
                    self.export_stats['errors'].append(error_msg)
            
            # Save attachments metadata
            metadata_file = os.path.join(attach_dir, 'attachments_metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(attachments, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_msg = f"Failed to export attachments for page {page_title}: {e}"
            logger.warning(error_msg)
            self.export_stats['errors'].append(error_msg)
    
    def _download_attachment(self, attachment: Dict[str, Any], attach_dir: str) -> None:
        """Download a single attachment.
        
        Args:
            attachment: Attachment dictionary
            attach_dir: Attachment directory
        """
        title = attachment['title']
        attachment_id = attachment.get('id', 'unknown')
        download_url = attachment['_links']['download']
        
        # Log attachment details for debugging
        logger.debug(f"Attempting to download attachment: {title} (ID: {attachment_id})")
        logger.debug(f"  Download URL from API: {download_url}")
        
        # Create safe filename
        safe_filename = sanitize_filename(title)
        
        # Log sanitization for debugging problematic filenames
        if title != safe_filename:
            logger.debug(f"  Sanitized filename: '{title}' -> '{safe_filename}'")
        
        file_path = os.path.join(attach_dir, safe_filename)
        
        # Download attachment content using the download URL from Confluence API
        # The client will handle prepending /wiki for Cloud instances
        content = self.client.download_attachment(download_url)
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.debug(f"Successfully downloaded attachment: {title} (ID: {attachment_id})")
    
    def _export_page_comments(self, page_id: str, content_dir: str, page_title: str) -> None:
        """Export comments for a page.
        
        Args:
            page_id: Page ID
            content_dir: Content directory
            page_title: Page title for directory naming
        """
        try:
            comments = self.client.get_page_comments(page_id)
            
            if not comments:
                return
            
            # Create comments directory for this page
            safe_title = sanitize_filename(page_title)
            comments_dir = os.path.join(content_dir, 'comments', safe_title)
            os.makedirs(comments_dir, exist_ok=True)
            
            # Save comments as JSON
            comments_file = os.path.join(comments_dir, 'comments.json')
            with open(comments_file, 'w', encoding='utf-8') as f:
                json.dump(comments, f, indent=2, ensure_ascii=False)
            
            # Create HTML version of comments
            self._create_comments_html(comments, comments_dir, page_title)
            
            self.export_stats['comments_exported'] += len(comments)
            logger.debug(f"Exported {len(comments)} comments for page: {page_title}")
            
        except Exception as e:
            error_msg = f"Failed to export comments for page {page_title}: {e}"
            logger.warning(error_msg)
            self.export_stats['errors'].append(error_msg)
    
    def _create_comments_html(self, comments: List[Dict[str, Any]], 
                            comments_dir: str, page_title: str) -> None:
        """Create HTML version of comments.
        
        Args:
            comments: List of comment dictionaries
            comments_dir: Comments directory
            page_title: Page title
        """
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comments for: {page_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .comment {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .comment-author {{ font-weight: bold; color: #333; }}
        .comment-date {{ color: #666; font-size: 0.9em; }}
        .comment-content {{ margin-top: 10px; }}
    </style>
</head>
<body>
    <h1>Comments for: {page_title}</h1>
"""
        
        for comment in comments:
            author = comment.get('version', {}).get('by', {}).get('displayName', 'Unknown')
            date = comment.get('version', {}).get('when', 'Unknown')
            content = comment.get('body', {}).get('view', {}).get('value', '')
            
            html_content += f"""
    <div class="comment">
        <div class="comment-author">{author}</div>
        <div class="comment-date">{date}</div>
        <div class="comment-content">{content}</div>
    </div>
"""
        
        html_content += """
</body>
</html>"""
        
        comments_html_file = os.path.join(comments_dir, 'comments.html')
        with open(comments_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _create_export_summary(self, export_dir: str, space_info: Dict[str, Any]) -> None:
        """Create export summary report.
        
        Args:
            export_dir: Export directory
            space_info: Space metadata
        """
        summary = {
            'export_info': {
                'space_key': space_info.get('key', 'Unknown'),
                'space_name': space_info.get('name', 'Unknown'),
                'export_date': datetime.now().isoformat(),
                'export_duration': str(self.export_stats['end_time'] - self.export_stats['start_time']) if self.export_stats['end_time'] else 'In progress'
            },
            'statistics': {
                'pages_exported': self.export_stats['pages_exported'],
                'folders_exported': self.export_stats['folders_exported'],
                'databases_exported': self.export_stats['databases_exported'],
                'attachments_exported': self.export_stats['attachments_exported'],
                'comments_exported': self.export_stats['comments_exported'],
                'total_errors': len(self.export_stats['errors'])
            },
            'configuration': self.config,
            'errors': self.export_stats['errors']
        }
        
        # Save summary files in the parent directory (outside the export data directory)
        # This prevents the summary from being imported with the data
        parent_dir = os.path.dirname(export_dir)
        export_dirname = os.path.basename(export_dir)
        
        # Save as JSON
        summary_file = os.path.join(parent_dir, f'{export_dirname}_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Create readable HTML summary
        self._create_html_summary(summary, parent_dir, export_dirname)
        
        logger.info(f"Export summary saved to {summary_file}")
    
    def _create_html_summary(self, summary: Dict[str, Any], parent_dir: str, export_dirname: str) -> None:
        """Create HTML version of export summary.
        
        Args:
            summary: Summary dictionary
            parent_dir: Parent directory where summary should be saved
            export_dirname: Name of the export directory
        """
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Export Summary - {summary['export_info']['space_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .summary-header {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .error {{ color: #d32f2f; }}
        .success {{ color: #388e3c; }}
    </style>
</head>
<body>
    <h1 class="summary-header">Export Summary</h1>
    
    <div class="section">
        <h2>Space Information</h2>
        <p><strong>Space:</strong> {summary['export_info']['space_name']} ({summary['export_info']['space_key']})</p>
        <p><strong>Export Date:</strong> {summary['export_info']['export_date']}</p>
        <p><strong>Duration:</strong> {summary['export_info']['export_duration']}</p>
    </div>
    
    <div class="section stats">
        <h2>Export Statistics</h2>
        <ul>
            <li><strong>Pages Exported:</strong> {summary['statistics']['pages_exported']}</li>
            <li><strong>Folders Exported:</strong> {summary['statistics']['folders_exported']}</li>
            <li><strong>Database Stubs Exported:</strong> {summary['statistics'].get('databases_exported', 0)} (structure only — data not exported)</li>
            <li><strong>Attachments Exported:</strong> {summary['statistics']['attachments_exported']}</li>
            <li><strong>Comments Exported:</strong> {summary['statistics']['comments_exported']}</li>
            <li class="{'error' if summary['statistics']['total_errors'] > 0 else 'success'}">
                <strong>Errors:</strong> {summary['statistics']['total_errors']}
            </li>
        </ul>
    </div>
"""
        
        if summary['errors']:
            html_content += """
    <div class="section">
        <h2>Errors</h2>
        <ul>
"""
            for error in summary['errors']:
                html_content += f"            <li class='error'>{error}</li>\n"
            
            html_content += """        </ul>
    </div>
"""
        
        html_content += """
</body>
</html>"""
        
        html_summary_file = os.path.join(parent_dir, f'{export_dirname}_summary.html')
        with open(html_summary_file, 'w', encoding='utf-8') as f:
            f.write(html_content)