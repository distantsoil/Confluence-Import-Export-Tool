"""Confluence space importer implementation."""

import os
import json
import logging
import html
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import re
from html.parser import HTMLParser

from ..api.client import ConfluenceAPIClient
from ..utils.helpers import sanitize_filename
from .content_rewriter import ContentRewriter

logger = logging.getLogger(__name__)


class ConfluenceImporter:
    """Robust Confluence space importer with comprehensive error handling."""
    
    def __init__(self, client: ConfluenceAPIClient, import_config: Dict[str, Any]):
        """Initialize importer.
        
        Args:
            client: Confluence API client
            import_config: Import configuration dictionary
        """
        self.client = client
        self.config = import_config
        self.import_stats = {
            'pages_imported': 0,
            'pages_updated': 0,
            'pages_skipped': 0,
            'folders_imported': 0,
            'databases_imported': 0,
            'attachments_imported': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        self.page_mapping = {}      # Maps old page IDs to new page IDs
        self.folder_mapping = {}    # Maps old folder IDs to new folder IDs
        self.database_mapping = {}  # Maps old database IDs to new database IDs
        self.target_space_id = None  # Numeric space ID for the target space (v2 API)
        # {old_page_id: {"parentId": old_parent_id, "parentType": "folder"|"page"|…}}
        # Loaded from v2_page_parents.json when present in the export.
        self.v2_page_parents: Dict[str, Any] = {}
        self.content_rewriter = None  # Will be set if space key remapping is enabled
        self.remapping_stats = {
            'links_rewritten': 0,
            'macros_updated': 0,
            'attachments_updated': 0,
            'wiki_links_updated': 0,
            'html_anchors_updated': 0,
            'pages_with_changes': 0
        }
    
    def enable_space_key_remapping(self, old_space_key: str, new_space_key: str) -> None:
        """Enable space key remapping for import.
        
        Args:
            old_space_key: Original space key from export
            new_space_key: New space key for import
        """
        self.content_rewriter = ContentRewriter(old_space_key, new_space_key)
        logger.info(f"Space key remapping enabled: {old_space_key} -> {new_space_key}")
    
    def import_space(self, export_dir: str, target_space_key: str) -> Dict[str, Any]:
        """Import a complete Confluence space from export directory.
        
        Args:
            export_dir: Path to export directory
            target_space_key: Target space key for import
            
        Returns:
            Import statistics dictionary
            
        Raises:
            Exception: If import fails
        """
        logger.info(f"Starting import to space: {target_space_key}")
        self.import_stats['start_time'] = datetime.now()
        
        try:
            # Validate export directory
            self._validate_export_directory(export_dir)
            
            # Load export metadata
            export_metadata = self._load_export_metadata(export_dir)
            
            # Verify target space exists
            self._verify_target_space(target_space_key)

            # Cache the v2-format space ID for v2 API operations (folders, databases).
            # The v1 integer ID causes 500 errors on Atlassian Cloud v2 endpoints.
            self.target_space_id = (
                self.client.get_space_id_v2(target_space_key)
                or self.client.get_space_id(target_space_key)
            )

            # Import folders first (if available)
            folders_dir = os.path.join(export_dir, 'folders')
            if os.path.exists(folders_dir):
                self._import_folders(folders_dir, target_space_key)

            # Import database stubs (if available — Cloud only)
            # Must happen before pages so database IDs are mapped before child pages import
            databases_dir = os.path.join(export_dir, 'databases')
            if os.path.exists(databases_dir):
                self._import_databases(databases_dir, target_space_key)
            
            # Load v2 page-parent data if present (produced by the folder exporter).
            # Used to reliably detect folder parents during page import, since
            # the v1 ancestors array may not include folder ancestors.
            v2_parents_file = os.path.join(export_dir, 'v2_page_parents.json')
            if os.path.exists(v2_parents_file):
                try:
                    with open(v2_parents_file, 'r', encoding='utf-8') as f:
                        self.v2_page_parents = json.load(f)
                    logger.info(
                        f"Loaded v2 parent info for {len(self.v2_page_parents)} pages"
                    )
                except Exception as e:
                    logger.warning(f"Could not load v2_page_parents.json: {e}")

            # Import pages
            pages_dir = os.path.join(export_dir, 'pages')
            if os.path.exists(pages_dir):
                self._import_pages(pages_dir, target_space_key)
            
            # Import blog posts
            blogposts_dir = os.path.join(export_dir, 'blogposts')
            if os.path.exists(blogposts_dir):
                self._import_pages(blogposts_dir, target_space_key, content_type='blogpost')
            
            # Create import summary
            self._create_import_summary(export_dir, target_space_key, export_metadata)
            
            self.import_stats['end_time'] = datetime.now()
            duration = self.import_stats['end_time'] - self.import_stats['start_time']
            
            logger.info(f"Import completed successfully in {duration}")
            logger.info(f"Imported: {self.import_stats['pages_imported']} pages, "
                       f"Updated: {self.import_stats['pages_updated']} pages, "
                       f"Skipped: {self.import_stats['pages_skipped']} pages, "
                       f"Folders: {self.import_stats['folders_imported']}, "
                       f"Database stubs: {self.import_stats['databases_imported']}, "
                       f"Attachments: {self.import_stats['attachments_imported']}")
            
            if self.import_stats['errors']:
                logger.warning(f"Import completed with {len(self.import_stats['errors'])} errors")
            
            # Log space key remapping statistics if enabled
            if self.content_rewriter:
                logger.info(f"Space key remapping statistics:")
                logger.info(f"  Pages with changes: {self.remapping_stats['pages_with_changes']}")
                logger.info(f"  Links rewritten: {self.remapping_stats['links_rewritten']}")
                logger.info(f"  Wiki links updated: {self.remapping_stats['wiki_links_updated']}")
                logger.info(f"  HTML anchors updated: {self.remapping_stats['html_anchors_updated']}")
                logger.info(f"  Macros updated: {self.remapping_stats['macros_updated']}")
                logger.info(f"  Attachments updated: {self.remapping_stats['attachments_updated']}")
            
            return self.import_stats
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
    
    def _validate_export_directory(self, export_dir: str) -> None:
        """Validate export directory structure.
        
        Args:
            export_dir: Export directory path
            
        Raises:
            ValueError: If directory structure is invalid
        """
        if not os.path.exists(export_dir):
            raise ValueError(f"Export directory does not exist: {export_dir}")
        
        # Check for optional summary file (in parent directory with new naming convention)
        parent_dir = os.path.dirname(export_dir)
        export_dirname = os.path.basename(export_dir)
        summary_file = os.path.join(parent_dir, f'{export_dirname}_summary.json')
        
        if not os.path.exists(summary_file):
            # Also check old location (inside export directory) for backward compatibility
            old_summary_file = os.path.join(export_dir, 'export_summary.json')
            if not os.path.exists(old_summary_file):
                logger.warning(f"Optional file missing: export summary not found at {summary_file} or {old_summary_file}")
        
        # Check for content directories
        content_dirs = ['pages', 'blogposts']
        found_content = False
        for dir_name in content_dirs:
            dir_path = os.path.join(export_dir, dir_name)
            if os.path.exists(dir_path):
                found_content = True
                break
        
        if not found_content:
            raise ValueError(f"No content directories found in export: {export_dir}")
        
        logger.debug(f"Export directory validation passed: {export_dir}")
    
    def _load_export_metadata(self, export_dir: str) -> Dict[str, Any]:
        """Load export metadata.
        
        Args:
            export_dir: Export directory path
            
        Returns:
            Export metadata dictionary
        """
        # The exporter saves the summary file in the parent directory with name {export_dirname}_summary.json
        # Try that location first
        parent_dir = os.path.dirname(export_dir)
        export_dirname = os.path.basename(export_dir)
        metadata_file = os.path.join(parent_dir, f'{export_dirname}_summary.json')
        
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load export metadata from {metadata_file}: {e}")
        
        # Fallback to old location (inside export directory) for backward compatibility
        old_metadata_file = os.path.join(export_dir, 'export_summary.json')
        if os.path.exists(old_metadata_file):
            try:
                with open(old_metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load export metadata from {old_metadata_file}: {e}")
        
        logger.warning(f"No export metadata found for {export_dir}")
        return {}
    
    def _verify_target_space(self, space_key: str) -> None:
        """Verify target space exists and is accessible.
        
        Args:
            space_key: Target space key
            
        Raises:
            ValueError: If space is not accessible
        """
        try:
            spaces = self.client.get_all_spaces()
            target_space = None
            
            for space in spaces:
                if space['key'] == space_key:
                    target_space = space
                    break
            
            if not target_space:
                raise ValueError(f"Target space '{space_key}' not found or not accessible")
            
            logger.info(f"Target space verified: {target_space['name']} ({space_key})")
            
        except Exception as e:
            logger.error(f"Could not verify target space: {e}")
            raise
    
    def _import_folders(self, folders_dir: str, space_key: str) -> None:
        """Import folders from export directory.
        
        Args:
            folders_dir: Path to folders directory
            space_key: Target space key
        """
        try:
            # Load folders metadata
            metadata_file = os.path.join(folders_dir, 'folders_metadata.json')
            if not os.path.exists(metadata_file):
                logger.info("No folders metadata found, skipping folder import")
                return
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                folders = json.load(f)
            
            if not folders:
                logger.info("No folders to import")
                return
            
            logger.info(f"Found {len(folders)} folders to import")
            
            # Use the cached v2 space ID if available; otherwise fetch it.
            space_id = self.target_space_id or (
                self.client.get_space_id_v2(space_key)
                or self.client.get_space_id(space_key)
            )
            if not space_id:
                logger.warning(f"Could not get space ID for {space_key}, skipping folder import")
                return
            
            # Sort folders by hierarchy (parents first)
            # Folders without parentId should be imported first
            root_folders = [f for f in folders if not f.get('parentId')]
            child_folders = [f for f in folders if f.get('parentId')]
            
            # Import root folders first
            for folder in root_folders:
                try:
                    self._import_single_folder(folder, space_id, None)
                except Exception as e:
                    error_msg = f"Failed to import folder '{folder.get('title', 'Unknown')}': {e}"
                    logger.warning(error_msg)
                    self.import_stats['errors'].append(error_msg)
            
            # Import child folders, potentially in multiple passes
            # since some child folders may have parents that are also children
            max_passes = 10  # Prevent infinite loops
            remaining_folders = child_folders.copy()
            
            for pass_num in range(max_passes):
                if not remaining_folders:
                    break
                
                imported_in_pass = []
                
                for folder in remaining_folders:
                    old_parent_id = folder.get('parentId')
                    
                    # Check if parent has been mapped
                    if old_parent_id in self.folder_mapping:
                        new_parent_id = self.folder_mapping[old_parent_id]
                        try:
                            self._import_single_folder(folder, space_id, new_parent_id)
                            imported_in_pass.append(folder)
                        except Exception as e:
                            error_msg = f"Failed to import folder '{folder.get('title', 'Unknown')}': {e}"
                            logger.warning(error_msg)
                            self.import_stats['errors'].append(error_msg)
                            imported_in_pass.append(folder)  # Remove from list even if failed
                
                # Remove successfully processed folders
                for folder in imported_in_pass:
                    remaining_folders.remove(folder)
                
                # If no folders were imported in this pass, we can't make progress
                if not imported_in_pass:
                    logger.warning(f"Could not import {len(remaining_folders)} folders due to missing parent references")
                    for folder in remaining_folders:
                        error_msg = f"Skipped folder '{folder.get('title', 'Unknown')}' due to missing parent"
                        logger.warning(error_msg)
                        self.import_stats['errors'].append(error_msg)
                    break
            
            logger.info(f"Imported {self.import_stats['folders_imported']} folders")
            
        except Exception as e:
            error_msg = f"Failed to import folders: {e}"
            logger.warning(error_msg)
            # Don't add to errors as folders may not be available in all instances
            logger.debug(f"Folder import error details: {e}", exc_info=True)
    
    def _import_single_folder(self, folder: Dict[str, Any], space_id: str, 
                            parent_id: Optional[str]) -> None:
        """Import a single folder.
        
        Args:
            folder: Folder metadata dictionary
            space_id: Target space ID
            parent_id: New parent folder ID (if any)
        """
        old_folder_id = folder.get('id')
        folder_title = folder.get('title', 'Untitled Folder')
        
        try:
            # Create the folder
            new_folder = self.client.create_folder(space_id, folder_title, parent_id)
            
            # Map old folder ID to new folder ID
            new_folder_id = new_folder.get('id')
            if old_folder_id and new_folder_id:
                self.folder_mapping[old_folder_id] = new_folder_id
            
            self.import_stats['folders_imported'] += 1
            logger.info(f"Created folder: {folder_title} (old ID: {old_folder_id}, new ID: {new_folder_id})")
            
        except Exception as e:
            logger.error(f"Error importing folder {folder_title}: {e}")
            raise
    
    def _import_databases(self, databases_dir: str, space_key: str) -> None:
        """Import database stubs from the export directory.

        Recreates the database container hierarchy so that pages which were
        parented under databases can be moved into them during page import.
        Database *content* (rows, columns, data) cannot be restored via API
        and must be re-entered manually in the Confluence UI.

        Args:
            databases_dir: Path to the databases export directory
            space_key: Target space key
        """
        try:
            metadata_file = os.path.join(databases_dir, 'databases_metadata.json')
            if not os.path.exists(metadata_file):
                logger.info("No databases metadata found, skipping database import")
                return

            with open(metadata_file, 'r', encoding='utf-8') as f:
                databases = json.load(f)

            if not databases:
                logger.info("No databases to import")
                return

            logger.info(
                f"Found {len(databases)} database stubs to import. "
                f"Note: database data (rows/columns) cannot be restored via API."
            )

            space_id = self.target_space_id or (
                self.client.get_space_id_v2(space_key)
                or self.client.get_space_id(space_key)
            )
            if not space_id:
                logger.warning(f"Could not get space ID for {space_key}, skipping database import")
                return

            # Import root databases first (no parentId), then children
            root_databases = [d for d in databases if not d.get('parentId')]
            child_databases = [d for d in databases if d.get('parentId')]

            for database in root_databases:
                try:
                    self._import_single_database(database, space_id, None)
                except Exception as e:
                    error_msg = f"Failed to import database stub '{database.get('title', 'Unknown')}': {e}"
                    logger.warning(error_msg)
                    self.import_stats['errors'].append(error_msg)

            # Multi-pass for nested databases (databases inside folders or under other databases)
            max_passes = 10
            remaining = child_databases.copy()

            for pass_num in range(max_passes):
                if not remaining:
                    break

                imported_in_pass = []

                for database in remaining:
                    old_parent_id = database.get('parentId')

                    # Resolve parent from any of our mappings
                    new_parent_id = (
                        self.database_mapping.get(old_parent_id)
                        or self.folder_mapping.get(old_parent_id)
                        or self.page_mapping.get(old_parent_id)
                    )

                    if new_parent_id:
                        try:
                            self._import_single_database(database, space_id, new_parent_id)
                            imported_in_pass.append(database)
                        except Exception as e:
                            error_msg = f"Failed to import database stub '{database.get('title', 'Unknown')}': {e}"
                            logger.warning(error_msg)
                            self.import_stats['errors'].append(error_msg)
                            imported_in_pass.append(database)

                for database in imported_in_pass:
                    remaining.remove(database)

                if not imported_in_pass:
                    for database in remaining:
                        error_msg = (
                            f"Skipped database stub '{database.get('title', 'Unknown')}' "
                            f"due to missing parent (ID: {database.get('parentId')})"
                        )
                        logger.warning(error_msg)
                        self.import_stats['errors'].append(error_msg)
                    break

            logger.info(f"Imported {self.import_stats['databases_imported']} database stubs")

        except Exception as e:
            error_msg = f"Failed to import databases: {e}"
            logger.warning(error_msg)
            logger.debug(f"Database import error details: {e}", exc_info=True)

    def _import_single_database(self, database: Dict[str, Any], space_id: str,
                                 parent_id: Optional[str]) -> None:
        """Import a single database stub.

        Args:
            database: Database metadata dictionary from export
            space_id: Target space ID (numeric, for v2 API)
            parent_id: New parent content ID (if any)
        """
        old_database_id = database.get('id')
        database_title = database.get('title', 'Untitled Database')

        try:
            new_database = self.client.create_database(space_id, database_title, parent_id)
            new_database_id = new_database.get('id')

            if old_database_id and new_database_id:
                self.database_mapping[old_database_id] = new_database_id

            self.import_stats['databases_imported'] += 1
            logger.info(
                f"Created database stub: '{database_title}' "
                f"(old ID: {old_database_id}, new ID: {new_database_id})"
            )

        except Exception as e:
            logger.error(f"Error importing database stub '{database_title}': {e}")
            raise

    def _import_pages(self, pages_dir: str, space_key: str, content_type: str = 'page') -> None:
            """Import pages from directory.
            
            Args:
                pages_dir: Pages directory path
                space_key: Target space key
                content_type: Content type (page or blogpost)
            """
            # Get list of page files
            page_files = []
            for filename in os.listdir(pages_dir):
                if filename.endswith('.html') and not filename.endswith('_metadata.json'):
                    page_files.append(filename)
            
            if not page_files:
                logger.warning(f"No {content_type} files found in {pages_dir}")
                return
            
            logger.info(f"Found {len(page_files)} {content_type}s to import")
            
            # Load page metadata for all pages
            pages_metadata = self._load_pages_metadata(pages_dir, page_files)
            
            # Sort pages by hierarchy (parents first)
            sorted_pages = self._sort_pages_by_hierarchy(pages_metadata)
            
            # Import pages with progress tracking using multi-pass strategy
            max_workers = self.config.get('max_workers', 3)  # Lower for imports to avoid conflicts
            
            with tqdm(total=len(sorted_pages), desc=f"Importing {content_type}s") as pbar:
                # Import root pages first (no parents)
                root_pages = [p for p in sorted_pages if not p.get('metadata', {}).get('ancestors')]
                
                logger.info(f"Found {len(root_pages)} root pages (no ancestors) to import first")
                logger.debug(f"Root page titles: {[p.get('metadata', {}).get('title', p['filename']) for p in root_pages[:10]]}")
                
                for page_info in root_pages:
                    try:
                        result_id = self._import_single_page(page_info, pages_dir, space_key, content_type)
                        old_id = page_info.get('metadata', {}).get('id')
                        if old_id and old_id in self.page_mapping:
                            logger.debug(f"Mapped root page: {old_id} -> {self.page_mapping[old_id]}")
                    except Exception as e:
                        error_msg = f"Failed to import {content_type} '{page_info['filename']}': {e}"
                        logger.error(error_msg)
                        self.import_stats['errors'].append(error_msg)
                    finally:
                        pbar.update(1)
                
                # Import child pages using multi-pass strategy
                # Some pages may need their parents to be imported first
                child_pages = [p for p in sorted_pages if p.get('metadata', {}).get('ancestors')]
                
                logger.info(f"Starting multi-pass import: {len(child_pages)} child pages to import")
                
                max_passes = 10  # Prevent infinite loops
                remaining_pages = child_pages.copy()
                failed_pages = []  # Track pages that failed to import
                
                for pass_num in range(max_passes):
                    if not remaining_pages:
                        break
                    
                    logger.debug(f"Multi-pass import: Pass {pass_num + 1}, {len(remaining_pages)} pages remaining")
                    logger.debug(f"Page mapping currently has {len(self.page_mapping)} entries")
                    
                    imported_in_pass = []
                    skipped_in_pass = []
                    
                    for page_info in remaining_pages:
                        # Check if parent is available
                        metadata = page_info.get('metadata', {})
                        parent_available = self._is_parent_available(metadata, space_key)
                        
                        if parent_available:
                            try:
                                self._import_single_page(page_info, pages_dir, space_key, content_type)
                                imported_in_pass.append(page_info)
                            except Exception as e:
                                error_msg = f"Failed to import {content_type} '{page_info['filename']}': {e}"
                                logger.error(error_msg)
                                logger.debug(f"Error details for {page_info['filename']}: {e}", exc_info=True)
                                self.import_stats['errors'].append(error_msg)
                                # Track failed pages separately - don't remove them from queue yet
                                failed_pages.append({'page_info': page_info, 'error': str(e), 'pass': pass_num + 1})
                                imported_in_pass.append(page_info)  # Still remove from remaining to avoid infinite retries
                            finally:
                                pbar.update(1)
                        else:
                            # Parent not available yet, try in next pass
                            skipped_in_pass.append(page_info)
                            metadata = page_info.get('metadata', {})
                            ancestors = metadata.get('ancestors', [])
                            if ancestors:
                                parent_info = ancestors[-1]
                                parent_id = parent_info.get('id', 'unknown')
                                logger.debug(f"Skipping {page_info['filename']} in pass {pass_num + 1} - waiting for parent ID: {parent_id}")
                    
                    # Remove successfully processed pages
                    remaining_pages = skipped_in_pass
                    
                    # Log progress of this pass
                    if imported_in_pass:
                        logger.info(f"Pass {pass_num + 1}: Successfully imported {len(imported_in_pass)} pages, {len(skipped_in_pass)} pages still waiting for parents")
                    
                    # If no pages were imported in this pass, we can't make progress
                    if not imported_in_pass:
                        logger.warning(f"Could not import {len(remaining_pages)} {content_type}s due to missing parent references after {pass_num + 1} passes")
                        
                        # Log current state of page_mapping for diagnostics
                        logger.info(f"Current page_mapping contains {len(self.page_mapping)} entries")
                        logger.debug(f"Page mapping IDs: {list(self.page_mapping.keys())[:20]}...")  # Show first 20 for diagnostics
                        
                        # Log detailed info about remaining pages and their missing parents
                        missing_parent_ids = set()
                        for page_info in remaining_pages:
                            metadata = page_info.get('metadata', {})
                            ancestors = metadata.get('ancestors', [])
                            parent_info = ancestors[-1] if ancestors else {}
                            parent_id = parent_info.get('id', 'unknown')
                            parent_title = parent_info.get('title', 'unknown')
                            
                            # Track missing parent IDs
                            if parent_id != 'unknown':
                                missing_parent_ids.add(parent_id)
                            
                            # Check if parent exists in export but wasn't imported
                            parent_in_mapping = parent_id in self.page_mapping if parent_id != 'unknown' else False
                            parent_in_folder_mapping = parent_id in self.folder_mapping if parent_id != 'unknown' else False
                            
                            error_msg = f"Skipped {content_type} '{page_info['filename']}' (title: '{metadata.get('title', 'unknown')}') - parent '{parent_title}' (ID: {parent_id}) not found in page_mapping (checked: page_mapping={parent_in_mapping}, folder_mapping={parent_in_folder_mapping})"
                            logger.warning(error_msg)
                            self.import_stats['errors'].append(error_msg)
                            pbar.update(1)
                        
                        # Log analysis of missing parent IDs
                        logger.error(f"Analysis: {len(missing_parent_ids)} unique parent IDs were referenced but not found in mappings")
                        logger.error(f"Missing parent IDs: {list(missing_parent_ids)[:20]}")  # Show first 20
                        logger.info(f"Available page_mapping IDs (sample): {list(self.page_mapping.keys())[:20]}")
                        
                        # Log summary of failed pages if any
                        if failed_pages:
                            logger.error(f"Additionally, {len(failed_pages)} pages failed to import due to errors:")
                            for failed in failed_pages:
                                logger.error(f"  - {failed['page_info']['filename']}: {failed['error']} (pass {failed['pass']})")
                        
                        # Log diagnostic info about what WAS successfully imported
                        logger.info(f"Successfully imported pages in this multi-pass cycle: {self.import_stats['pages_imported']} pages, {self.import_stats['pages_updated']} updated, {self.import_stats['pages_skipped']} skipped before multi-pass")
                        
                        # Import orphaned pages with synthetic parent pages
                        # Group orphaned pages by their missing parent ID
                        orphaned_by_parent = {}
                        for page_info in remaining_pages:
                            metadata = page_info.get('metadata', {})
                            ancestors = metadata.get('ancestors', [])
                            if ancestors:
                                parent_info = ancestors[-1]
                                parent_id = parent_info.get('id', 'unknown')
                                parent_title = parent_info.get('title', f'Missing Parent ({parent_id})')
                                
                                if parent_id not in orphaned_by_parent:
                                    orphaned_by_parent[parent_id] = {
                                        'title': parent_title,
                                        'pages': []
                                    }
                                orphaned_by_parent[parent_id]['pages'].append(page_info)
                            else:
                                # No ancestors - import as root page
                                if 'no_parent' not in orphaned_by_parent:
                                    orphaned_by_parent['no_parent'] = {
                                        'title': None,
                                        'pages': []
                                    }
                                orphaned_by_parent['no_parent']['pages'].append(page_info)
                        
                        logger.warning(f"Importing {len(remaining_pages)} orphaned pages grouped under {len(orphaned_by_parent)} synthetic parent pages")
                        
                        # Create synthetic parent pages and import orphaned pages under them
                        for parent_id, group_info in orphaned_by_parent.items():
                            if parent_id == 'no_parent':
                                # Import pages without ancestors directly as root pages
                                for page_info in group_info['pages']:
                                    try:
                                        metadata = page_info.get('metadata', {})
                                        self._import_single_page(page_info, pages_dir, space_key, content_type)
                                        logger.info(f"Imported page '{metadata.get('title', page_info['filename'])}' as root page (no ancestors)")
                                    except Exception as e:
                                        error_msg = f"Failed to import page '{page_info['filename']}': {e}"
                                        logger.error(error_msg)
                                        self.import_stats['errors'].append(error_msg)
                                    finally:
                                        pbar.update(1)
                            else:
                                # Create synthetic parent page for this group
                                parent_title = group_info['title']
                                synthetic_parent_id = None
                                
                                try:
                                    # Escape user-controlled data to prevent XSS
                                    escaped_parent_title = html.escape(parent_title)
                                    escaped_parent_id = html.escape(str(parent_id))
                                    
                                    # Create a placeholder parent page with informative content
                                    placeholder_content = f"""<p><strong>Note:</strong> This is a placeholder page created during import.</p>
<p>The original parent page or folder named <strong>"{escaped_parent_title}"</strong> (ID: {escaped_parent_id}) was not included in the export. 
This placeholder was created to preserve the organizational structure of the following {len(group_info['pages'])} child pages:</p>
<ul>"""
                                    for page_info_item in group_info['pages']:
                                        page_title_item = page_info_item.get('metadata', {}).get('title', page_info_item['filename'])
                                        escaped_page_title = html.escape(page_title_item)
                                        placeholder_content += f"\n<li>{escaped_page_title}</li>"
                                    placeholder_content += """
</ul>
<p>You can reorganize these pages or replace this placeholder with the actual parent content.</p>"""
                                    
                                    # Create the synthetic parent page
                                    synthetic_parent = self.client.create_page(
                                        space_key, 
                                        f"[Recovered] {parent_title}", 
                                        placeholder_content, 
                                        None  # Create as root page
                                    )
                                    synthetic_parent_id = synthetic_parent['id']
                                    
                                    # Map the old parent ID to the new synthetic parent ID
                                    self.page_mapping[parent_id] = synthetic_parent_id
                                    
                                    logger.info(f"Created synthetic parent page '[Recovered] {parent_title}' for {len(group_info['pages'])} orphaned pages")
                                    self.import_stats['pages_imported'] += 1
                                    
                                except Exception as e:
                                    error_msg = f"Failed to create synthetic parent page '{parent_title}': {e}"
                                    logger.error(error_msg)
                                    self.import_stats['errors'].append(error_msg)
                                    # Fall back to importing children as root pages
                                    synthetic_parent_id = None
                                
                                # Now import child pages under the synthetic parent (or as root if parent creation failed)
                                for page_info in group_info['pages']:
                                    try:
                                        metadata = page_info.get('metadata', {})
                                        original_ancestors = metadata.get('ancestors', [])
                                        
                                        if synthetic_parent_id:
                                            # Parent was created - update ancestors to reference synthetic parent
                                            # The old parent ID is now mapped to synthetic_parent_id in page_mapping
                                            # so _import_single_page will find it via _find_parent_page
                                            self._import_single_page(page_info, pages_dir, space_key, content_type)
                                            logger.info(f"Imported orphaned page '{metadata.get('title', page_info['filename'])}' under synthetic parent '[Recovered] {parent_title}'")
                                        else:
                                            # Parent creation failed - import as root page
                                            metadata['ancestors'] = []
                                            self._import_single_page(page_info, pages_dir, space_key, content_type)
                                            metadata['ancestors'] = original_ancestors
                                            logger.info(f"Imported orphaned page '{metadata.get('title', page_info['filename'])}' as root page (synthetic parent creation failed)")
                                    except Exception as e:
                                        error_msg = f"Failed to import orphaned page '{page_info['filename']}': {e}"
                                        logger.error(error_msg)
                                        self.import_stats['errors'].append(error_msg)
                                    finally:
                                        pbar.update(1)
                        
                        break
        
    def _load_pages_metadata(self, pages_dir: str, page_files: List[str]) -> List[Dict[str, Any]]:
        """Load metadata for all pages.
        
        Args:
            pages_dir: Pages directory path
            page_files: List of page filenames
            
        Returns:
            List of page information dictionaries
        """
        pages_info = []
        
        for filename in page_files:
            try:
                # Try to load corresponding metadata file
                base_name = os.path.splitext(filename)[0]
                metadata_file = os.path.join(pages_dir, f"{base_name}_metadata.json")
                
                page_info = {
                    'filename': filename,
                    'html_path': os.path.join(pages_dir, filename),
                    'metadata': {}
                }
                
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        page_info['metadata'] = json.load(f)
                
                pages_info.append(page_info)
                
            except Exception as e:
                logger.warning(f"Could not load metadata for {filename}: {e}")
                # Add page without metadata
                pages_info.append({
                    'filename': filename,
                    'html_path': os.path.join(pages_dir, filename),
                    'metadata': {}
                })
        
        return pages_info
    
    def _sort_pages_by_hierarchy(self, pages_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort pages by hierarchy (parents before children).
        
        Args:
            pages_metadata: List of page metadata dictionaries
            
        Returns:
            Sorted list of page metadata dictionaries
        """
        # Create a simple sort: pages without ancestors first, then others
        root_pages = []
        child_pages = []
        
        for page_info in pages_metadata:
            ancestors = page_info.get('metadata', {}).get('ancestors', [])
            if not ancestors:
                root_pages.append(page_info)
            else:
                child_pages.append(page_info)
        
        # Sort child pages by ancestor count (closer to root first)
        child_pages.sort(key=lambda x: len(x.get('metadata', {}).get('ancestors', [])))
        
        return root_pages + child_pages
    
    def _import_single_page(self, page_info: Dict[str, Any], pages_dir: str, 
                          space_key: str, content_type: str) -> Optional[str]:
        """
        Import a single page and return its new page ID if created or updated.
    
        Args:
            page_info (Dict[str, Any]): Dictionary containing page filename, path, and metadata.
            pages_dir (str): Directory containing page files.
            space_key (str): Confluence space key to import into.
            content_type (str): Type of content being imported (e.g., 'page').
    
        Returns:
            Optional[str]: The new page ID if the page was created or updated, otherwise None.
    
        Raises:
            Exception: If an unexpected error occurs during import.
        """
        filename = page_info['filename']
        html_path = page_info['html_path']
        metadata = page_info['metadata']
        
        # Get the old page ID from metadata for mapping
        old_page_id = metadata.get('id')
        
        # Validate old_page_id exists and is not empty
        if not old_page_id or old_page_id == '':
            logger.warning(f"Page {filename} has no valid ID in metadata - cannot track for parent lookup")
    
        try:
            # Extract title and content from HTML
            title, content = self._extract_page_content(html_path)
    
            if not title:
                title = os.path.splitext(filename)[0]
    
            # Handle conflict resolution
            existing_page = self._find_existing_page(space_key, title, content_type)
    
            if existing_page:
                conflict_resolution = self.config.get('conflict_resolution', 'skip')
    
                if conflict_resolution == 'skip':
                    logger.info(f"Skipping existing {content_type}: {title}")
                    self.import_stats['pages_skipped'] += 1
                    # Map old page ID to existing page ID for child page imports
                    if old_page_id and old_page_id != '':
                        self.page_mapping[old_page_id] = existing_page['id']
                        logger.debug(f"Mapped skipped page ID: {old_page_id} -> {existing_page['id']}")
                    return existing_page['id']
    
                elif conflict_resolution == 'overwrite':
                    version_number = existing_page['version']['number'] + 1
                    updated_page = self.client.update_page(
                        existing_page['id'], title, content, version_number
                    )
                    logger.info(f"Updated existing {content_type}: {title}")
                    self.import_stats['pages_updated'] += 1
                    # Map old page ID to updated page ID for child page imports
                    if old_page_id and old_page_id != '':
                        self.page_mapping[old_page_id] = updated_page['id']
                        logger.debug(f"Mapped updated page ID: {old_page_id} -> {updated_page['id']}")
                    return updated_page['id']
    
                elif conflict_resolution == 'update_newer':
                    should_update = self._should_update_page(metadata, existing_page)
    
                    if should_update:
                        version_number = existing_page['version']['number'] + 1
                        updated_page = self.client.update_page(
                            existing_page['id'], title, content, version_number
                        )
                        logger.info(f"Updated newer {content_type}: {title}")
                        self.import_stats['pages_updated'] += 1
                        # Map old page ID to updated page ID for child page imports
                        if old_page_id and old_page_id != '':
                            self.page_mapping[old_page_id] = updated_page['id']
                            logger.debug(f"Mapped updated (newer) page ID: {old_page_id} -> {updated_page['id']}")
                        return updated_page['id']
                    else:
                        logger.info(f"Skipping {content_type} (target is newer or same): {title}")
                        self.import_stats['pages_skipped'] += 1
                        # Map old page ID to existing page ID for child page imports
                        if old_page_id and old_page_id != '':
                            self.page_mapping[old_page_id] = existing_page['id']
                            logger.debug(f"Mapped skipped (newer) page ID: {old_page_id} -> {existing_page['id']}")
                        return existing_page['id']
    
                elif conflict_resolution == 'rename':
                    title = f"{title} (Imported {datetime.now().strftime('%Y-%m-%d %H:%M')})"
    
            # Determine parent page
            parent_id = self._find_parent_page(metadata, space_key)
    
            # Create new page.
            # When the intended parent is a folder or database, the v1 API
            # silently ignores the ancestor and creates the page at root level.
            # We correct this immediately after creation with a move call.
            new_page = self.client.create_page(space_key, title, content, parent_id)
            logger.info(f"Created new {content_type}: {title}")
            self.import_stats['pages_imported'] += 1

            # Map old page ID to new page ID for child page imports
            if old_page_id and old_page_id != '':
                self.page_mapping[old_page_id] = new_page['id']
                logger.debug(f"Mapped page ID: {old_page_id} -> {new_page['id']}")

            # If the intended parent is a folder or database, the v1 create_page
            # endpoint cannot place pages there directly.  Use the v1 move
            # endpoint as the confirmed workaround (Cloud only).
            #
            # Detection priority:
            #   1. v2_page_parents (authoritative — folders only exist in v2 API)
            #   2. v1 ancestors fallback (covers databases and any edge cases)
            move_target_id = None
            move_parent_type = None

            # 1. v2 parent info (primary)
            if self.v2_page_parents and old_page_id:
                v2_info = self.v2_page_parents.get(str(old_page_id), {})
                v2_parent_type = v2_info.get('parentType')
                v2_old_parent_id = str(v2_info.get('parentId', '')) if v2_info.get('parentId') else None
                if v2_parent_type == 'folder' and v2_old_parent_id:
                    if v2_old_parent_id in self.folder_mapping:
                        move_target_id = self.folder_mapping[v2_old_parent_id]
                        move_parent_type = 'folder'
                elif v2_parent_type == 'folder' and v2_old_parent_id:
                    # parentType folder but not in folder_mapping — folder not yet imported
                    logger.warning(
                        f"Page '{title}' has a folder parent (ID: {v2_old_parent_id}) "
                        f"that was not found in the folder mapping. "
                        f"It may not have been exported/imported correctly."
                    )

            # 2. v1 ancestors fallback (databases, and spaces without v2 parent data)
            if not move_target_id:
                ancestors = metadata.get('ancestors', [])
                old_parent_id = ancestors[-1].get('id') if ancestors else None
                if old_parent_id:
                    if old_parent_id in self.folder_mapping:
                        move_target_id = self.folder_mapping[old_parent_id]
                        move_parent_type = 'folder'
                    elif old_parent_id in self.database_mapping:
                        move_target_id = self.database_mapping[old_parent_id]
                        move_parent_type = 'database'

            if move_target_id:
                moved = self.client.move_content(
                    new_page['id'], move_target_id, position='append'
                )
                if moved:
                    logger.info(f"Moved '{title}' into {move_parent_type} (ID: {move_target_id})")
                else:
                    logger.warning(
                        f"Could not move '{title}' into {move_parent_type} "
                        f"(ID: {move_target_id}); page remains at its default position."
                    )

            # Import attachments if enabled
            if self.config.get('import_attachments', True):
                self._import_page_attachments(new_page['id'], pages_dir, filename, title)

            return new_page['id']
    
        except Exception as e:
            logger.error(f"Error importing {content_type} {filename}: {e}")
            raise
    
    def _extract_div_content(self, html_content: str, class_name: str) -> str:
        """Extract content from a div with the given class name, handling nested divs.
        
        This method uses HTMLParser to properly track div nesting depth and extract
        the complete content of a div, even when it contains nested div elements or
        text that contains '<div>' or '</div>' strings.
        
        Args:
            html_content: Full HTML content
            class_name: CSS class name to search for
            
        Returns:
            Content inside the div, or empty string if not found
        """
        class DivContentExtractor(HTMLParser):
            """Extract content from a specific div by tracking nesting depth."""
            
            def __init__(self, target_class):
                super().__init__()
                self.target_class = target_class
                self.in_target = False
                self.depth = 0
                self.content_parts = []
                
            def handle_starttag(self, tag, attrs):
                if tag == 'div':
                    # Check if this is the target div
                    if not self.in_target:
                        attrs_dict = dict(attrs)
                        if 'class' in attrs_dict:
                            classes = attrs_dict.get('class', '').split()
                            if self.target_class in classes:
                                self.in_target = True
                                self.depth = 1
                                return
                    else:
                        # We're already in target, track depth
                        self.depth += 1
                
                # Capture the tag if we're in target div
                if self.in_target:
                    attrs_str = ''.join([f' {name}="{value}"' if value else f' {name}' 
                                        for name, value in attrs])
                    self.content_parts.append(f'<{tag}{attrs_str}>')
            
            def handle_endtag(self, tag):
                if self.in_target and tag == 'div':
                    self.depth -= 1
                    
                    if self.depth == 0:
                        # We've closed the target div
                        self.in_target = False
                        return
                
                # Capture the tag if we're in target div
                if self.in_target:
                    self.content_parts.append(f'</{tag}>')
            
            def handle_data(self, data):
                if self.in_target:
                    self.content_parts.append(data)
            
            def handle_startendtag(self, tag, attrs):
                if self.in_target:
                    attrs_str = ''.join([f' {name}="{value}"' if value else f' {name}' 
                                        for name, value in attrs])
                    self.content_parts.append(f'<{tag}{attrs_str} />')
            
            def handle_comment(self, data):
                if self.in_target:
                    self.content_parts.append(f'<!--{data}-->')
            
            def handle_entityref(self, name):
                if self.in_target:
                    self.content_parts.append(f'&{name};')
            
            def handle_charref(self, name):
                if self.in_target:
                    self.content_parts.append(f'&#{name};')
            
            def unknown_decl(self, data):
                """Handle CDATA sections which Confluence uses for code blocks."""
                if self.in_target:
                    # CDATA sections come as 'CDATA[content]'
                    if data.startswith('CDATA['):
                        cdata_content = data[6:-1] if data.endswith(']') else data[6:]
                        self.content_parts.append(f'<![CDATA[{cdata_content}]]>')
                    else:
                        # Other declarations
                        self.content_parts.append(f'<!{data}>')
            
            def get_content(self):
                return ''.join(self.content_parts).strip()
        
        try:
            parser = DivContentExtractor(class_name)
            parser.feed(html_content)
            return parser.get_content()
        except Exception as e:
            logger.warning(f"HTMLParser failed for class '{class_name}': {e}. Falling back to regex.")
            # Fallback to the original regex-based approach if HTMLParser fails
            return self._extract_div_content_regex(html_content, class_name)
    
    def _extract_div_content_regex(self, html_content: str, class_name: str) -> str:
        """Fallback regex-based extraction (original implementation).
        
        Args:
            html_content: Full HTML content
            class_name: CSS class name to search for
            
        Returns:
            Content inside the div, or empty string if not found
        """
        # Find the start of the target div
        start_pattern = rf'<div[^>]*class="[^"]*{re.escape(class_name)}[^"]*"[^>]*>'
        start_match = re.search(start_pattern, html_content, re.DOTALL)
        
        if not start_match:
            return ""
        
        # Start searching after the opening tag
        pos = start_match.end()
        depth = 1
        end_pos = pos
        
        # Track nested divs by counting opening and closing tags
        while depth > 0 and end_pos < len(html_content):
            # Find next div tag (opening or closing)
            next_open = html_content.find('<div', end_pos)
            next_close = html_content.find('</div>', end_pos)
            
            # If no more closing tags found, break
            if next_close == -1:
                break
                
            # If opening tag comes before closing tag (or no opening tag found)
            if next_open != -1 and next_open < next_close:
                depth += 1
                end_pos = next_open + 1
            else:
                depth -= 1
                if depth == 0:
                    # Found the matching closing tag
                    return html_content[pos:next_close].strip()
                end_pos = next_close + 1
        
        # If we couldn't find matching closing tag, return what we found
        return html_content[pos:].strip()
    
    def _extract_page_content(self, html_path: str) -> Tuple[str, str]:
        """Extract title and content from HTML file.
        
        Args:
            html_path: Path to HTML file
            
        Returns:
            Tuple of (title, content)
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract title from HTML
            title_match = re.search(r'<h1[^>]*class="page-title"[^>]*>(.*?)</h1>', html_content, re.DOTALL)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html_content)
            
            title = title_match.group(1).strip() if title_match else ""
            
            # Extract content from page-content div
            # Use proper div matching to handle nested divs correctly
            content = self._extract_div_content(html_content, 'page-content')
            
            if not content:
                # Fallback: extract body content
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
                content = body_match.group(1).strip() if body_match else html_content
            
            # Clean up content - remove metadata div if present
            # Simple approach: if metadata div exists, just use regex to remove it
            # since we know it's a simple div at the end
            metadata_pattern = r'<div[^>]*class="[^"]*metadata[^"]*"[^>]*>.*?</div>'
            content = re.sub(metadata_pattern, '', content, flags=re.DOTALL)
            
            # Apply space key remapping if enabled
            if self.content_rewriter:
                content, stats = self.content_rewriter.rewrite_content(content)
                
                # Update cumulative statistics
                if sum(stats.values()) > 0:
                    self.remapping_stats['pages_with_changes'] += 1
                    for key, value in stats.items():
                        self.remapping_stats[key] += value
                    
                    logger.debug(f"Rewrote content for page from {html_path}: {stats}")
            
            return title, content
            
        except Exception as e:
            logger.error(f"Error extracting content from {html_path}: {e}")
            return "", ""
    
    def _find_existing_page(self, space_key: str, title: str, content_type: str) -> Optional[Dict[str, Any]]:
        """Find existing page with same title.
        
        Args:
            space_key: Space key
            title: Page title
            content_type: Content type
            
        Returns:
            Existing page dictionary or None
        """
        try:
            # Get all content of this type from space
            content_list = self.client.get_all_space_content(space_key, content_type)
            
            # Look for exact title match
            for content_item in content_list:
                if content_item['title'] == title:
                    return content_item
            
            return None
            
        except Exception as e:
            logger.warning(f"Error searching for existing page '{title}': {e}")
            return None
    
    def _is_parent_available(self, metadata: Dict[str, Any], space_key: str) -> bool:
        """Check if parent page is available for import.
        
        Args:
            metadata: Page metadata
            space_key: Target space key
            
        Returns:
            True if parent is available or no parent needed, False otherwise
        """
        if not self.config.get('create_missing_parents', True):
            return True  # No parent needed
        
        ancestors = metadata.get('ancestors', [])
        if not ancestors:
            return True  # No parent needed
        
        # Get immediate parent (last ancestor)
        parent_info = ancestors[-1]
        old_parent_id = parent_info.get('id')
        
        # Check if we've already mapped this parent (could be a page, folder, or database)
        if old_parent_id in self.page_mapping:
            return True

        # Check if this is a folder reference
        if old_parent_id in self.folder_mapping:
            return True

        # Check if this is a database reference
        if old_parent_id in self.database_mapping:
            return True

        # Try to find parent by title
        parent_title = parent_info.get('title', '')
        if parent_title:
            existing_parent = self._find_existing_page(space_key, parent_title, 'page')
            if existing_parent:
                self.page_mapping[old_parent_id] = existing_parent['id']
                return True

        # Parent not available yet
        return False
    
    def _find_parent_page(self, metadata: Dict[str, Any], space_key: str) -> Optional[str]:
        """Find parent page ID for imported page.
        
        Args:
            metadata: Page metadata
            space_key: Target space key
            
        Returns:
            Parent page ID or None
        """
        if not self.config.get('create_missing_parents', True):
            return None
        
        ancestors = metadata.get('ancestors', [])
        if not ancestors:
            return None
        
        # Get immediate parent (last ancestor)
        parent_info = ancestors[-1]
        old_parent_id = parent_info.get('id')
        
        # Check if we've already mapped this parent (could be a page, folder, or database)
        if old_parent_id in self.page_mapping:
            return self.page_mapping[old_parent_id]

        # Check if this is a folder reference
        if old_parent_id in self.folder_mapping:
            return self.folder_mapping[old_parent_id]

        # Check if this is a database reference
        if old_parent_id in self.database_mapping:
            return self.database_mapping[old_parent_id]

        # Try to find parent by title
        parent_title = parent_info.get('title', '')
        if parent_title:
            existing_parent = self._find_existing_page(space_key, parent_title, 'page')
            if existing_parent:
                self.page_mapping[old_parent_id] = existing_parent['id']
                return existing_parent['id']

        # Parent not found, return None (page will be created as root page)
        logger.warning(f"Parent page not found for ancestors: {ancestors}")
        return None
    
    def _should_update_page(self, source_metadata: Dict[str, Any], 
                           target_page: Dict[str, Any]) -> bool:
        """Determine if source page should update target page based on version.
        
        Args:
            source_metadata: Metadata from exported page
            target_page: Existing page in target space
        
        Returns:
            True if source should update target, False otherwise
        """
        # If source has version info, compare versions
        source_version_info = source_metadata.get('version', {})
        target_version_info = target_page.get('version', {})
        
        # Check if we have 'when' timestamp for comparison
        if 'when' in source_version_info and 'when' in target_version_info:
            from dateutil import parser
            try:
                source_date = parser.parse(source_version_info['when'])
                target_date = parser.parse(target_version_info['when'])
                
                # Update if source is newer
                return source_date > target_date
            except Exception as e:
                logger.warning(f"Could not compare dates: {e}")
        
        # If we can't compare dates, check version numbers
        source_number = source_version_info.get('number', 0)
        target_number = target_version_info.get('number', 0)
        
        if source_number > 0 and target_number > 0:
            return source_number > target_number
        
        # Default to updating if we can't determine
        logger.debug("Unable to determine version comparison, defaulting to update")
        return True
    
    def _import_page_attachments(self, page_id: str, pages_dir: str, 
                               page_filename: str, page_title: str) -> None:
        """Import attachments for a page.
        
        Args:
            page_id: New page ID
            pages_dir: Pages directory
            page_filename: Page filename
            page_title: Page title
        """
        try:
            # Look for attachments directory for this page
            # Attachments are stored at export_dir/attachments/safe_title, not pages_dir/attachments/safe_title
            safe_title = sanitize_filename(page_title)
            export_dir = os.path.dirname(pages_dir)  # Go up from pages_dir to export_dir
            attach_dir = os.path.join(export_dir, 'attachments', safe_title)
            
            if not os.path.exists(attach_dir):
                return
            
            # Get list of attachment files (exclude metadata)
            attachment_files = []
            for filename in os.listdir(attach_dir):
                if filename != 'attachments_metadata.json' and os.path.isfile(os.path.join(attach_dir, filename)):
                    attachment_files.append(filename)
            
            if not attachment_files:
                return
            
            # Upload each attachment
            for filename in attachment_files:
                try:
                    file_path = os.path.join(attach_dir, filename)
                    self.client.upload_attachment(page_id, file_path, f"Imported attachment: {filename}")
                    self.import_stats['attachments_imported'] += 1
                    logger.debug(f"Uploaded attachment: {filename}")
                except Exception as e:
                    error_msg = f"Failed to upload attachment {filename}: {e}"
                    logger.warning(error_msg)
                    self.import_stats['errors'].append(error_msg)
            
            logger.info(f"Imported {len(attachment_files)} attachments for page: {page_title}")
            
        except Exception as e:
            error_msg = f"Failed to import attachments for page {page_title}: {e}"
            logger.warning(error_msg)
            self.import_stats['errors'].append(error_msg)
    
    def _create_import_summary(self, export_dir: str, target_space_key: str, 
                             export_metadata: Dict[str, Any]) -> None:
        """Create import summary report.
        
        Args:
            export_dir: Export directory
            target_space_key: Target space key
            export_metadata: Original export metadata
        """
        summary = {
            'import_info': {
                'target_space_key': target_space_key,
                'source_export_dir': export_dir,
                'import_date': datetime.now().isoformat(),
                'import_duration': str(self.import_stats['end_time'] - self.import_stats['start_time']) if self.import_stats['end_time'] else 'In progress'
            },
            'source_export': export_metadata.get('export_info', {}),
            'statistics': {
                'pages_imported': self.import_stats['pages_imported'],
                'pages_updated': self.import_stats['pages_updated'],
                'pages_skipped': self.import_stats['pages_skipped'],
                'folders_imported': self.import_stats['folders_imported'],
                'databases_imported': self.import_stats['databases_imported'],
                'attachments_imported': self.import_stats['attachments_imported'],
                'total_errors': len(self.import_stats['errors'])
            },
            'configuration': self.config,
            'page_mapping': self.page_mapping,
            'folder_mapping': self.folder_mapping,
            'database_mapping': self.database_mapping,
            'errors': self.import_stats['errors']
        }
        
        # Save import summary in export directory
        summary_file = os.path.join(export_dir, 'import_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Create readable HTML summary
        self._create_html_import_summary(summary, export_dir)
        
        logger.info(f"Import summary saved to {summary_file}")
    
    def _create_html_import_summary(self, summary: Dict[str, Any], export_dir: str) -> None:
        """Create HTML version of import summary.
        
        Args:
            summary: Summary dictionary
            export_dir: Export directory
        """
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Import Summary - {summary['import_info']['target_space_key']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .summary-header {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .error {{ color: #d32f2f; }}
        .success {{ color: #388e3c; }}
        .warning {{ color: #f57c00; }}
    </style>
</head>
<body>
    <h1 class="summary-header">Import Summary</h1>
    
    <div class="section">
        <h2>Import Information</h2>
        <p><strong>Target Space:</strong> {summary['import_info']['target_space_key']}</p>
        <p><strong>Import Date:</strong> {summary['import_info']['import_date']}</p>
        <p><strong>Duration:</strong> {summary['import_info']['import_duration']}</p>
        <p><strong>Source Export:</strong> {summary['import_info']['source_export_dir']}</p>
    </div>
    
    <div class="section stats">
        <h2>Import Statistics</h2>
        <ul>
            <li class="success"><strong>Pages Imported:</strong> {summary['statistics']['pages_imported']}</li>
            <li class="warning"><strong>Pages Updated:</strong> {summary['statistics']['pages_updated']}</li>
            <li class="warning"><strong>Pages Skipped:</strong> {summary['statistics']['pages_skipped']}</li>
            <li class="success"><strong>Folders Imported:</strong> {summary['statistics']['folders_imported']}</li>
            <li class="success"><strong>Database Stubs Imported:</strong> {summary['statistics'].get('databases_imported', 0)} (data not restored — re-enter manually in Confluence)</li>
            <li class="success"><strong>Attachments Imported:</strong> {summary['statistics']['attachments_imported']}</li>
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
        
        html_summary_file = os.path.join(export_dir, 'import_summary.html')
        with open(html_summary_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
