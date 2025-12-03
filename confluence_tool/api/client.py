"""Confluence API client implementation."""

import requests
import logging
import time
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin, quote
import json

logger = logging.getLogger(__name__)


class ConfluenceAPIClient:
    """Robust Confluence REST API client with error handling and rate limiting."""
    
    def __init__(self, base_url: str, username: str, auth_token: str = None, 
                 password: str = None, timeout: int = 30, max_retries: int = 3,
                 rate_limit: float = 10.0):
        """Initialize Confluence API client.
        
        Args:
            base_url: Base URL of Confluence instance
            username: Username or email for authentication
            auth_token: API token (preferred for cloud instances)
            password: Password (for server instances or if no token available)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per second
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self._last_request_time = 0
        
        # Detect if this is a Confluence Cloud instance (atlassian.net domain)
        # Cloud instances require /wiki/rest/api/ path, while Server/Data Center use /rest/api/
        self.is_cloud = 'atlassian.net' in self.base_url.lower()
        self.api_path = '/wiki/rest/api/' if self.is_cloud else '/rest/api/'
        
        # Set up authentication
        if auth_token:
            self.auth = (username, auth_token)
        elif password:
            self.auth = (username, password)
        else:
            raise ValueError("Either auth_token or password must be provided")
        
        # Set up session with common headers
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Confluence-Export-Import-Tool/1.0'
        })
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self.rate_limit > 0:
            time_since_last = time.time() - self._last_request_time
            min_interval = 1.0 / self.rate_limit
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retries and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional arguments for requests
        
        Returns:
            Response object
        
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        url = urljoin(f"{self.base_url}{self.api_path}", endpoint.lstrip('/'))
        
        for attempt in range(self.max_retries + 1):
            try:
                self._rate_limit()
                
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                # Check for authentication errors
                if response.status_code == 401:
                    raise requests.exceptions.HTTPError(
                        "Authentication failed. Please check your credentials."
                    )
                
                # Check for permission errors
                if response.status_code == 403:
                    raise requests.exceptions.HTTPError(
                        "Permission denied. Check if you have access to the requested resource."
                    )
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries:
                    raise
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt + 1}")
                if attempt == self.max_retries:
                    raise
                
            except requests.exceptions.HTTPError as e:
                if response.status_code in [401, 403]:
                    raise  # Don't retry auth errors
                # Log response body for debugging
                try:
                    error_body = response.text
                    logger.warning(f"HTTP error {response.status_code} on attempt {attempt + 1}: {e}")
                    if error_body:
                        logger.debug(f"Response body: {error_body}")
                except:
                    logger.warning(f"HTTP error {response.status_code} on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries:
                    raise
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                wait_time = (2 ** attempt) * 1.0
                logger.debug(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        raise requests.exceptions.RequestException("Max retries exceeded")
    
    def test_connection(self) -> bool:
        """Test the connection to Confluence.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self._make_request('GET', 'space')
            logger.info("Successfully connected to Confluence")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_spaces(self, limit: int = 50, start: int = 0) -> List[Dict[str, Any]]:
        """Get list of Confluence spaces.
        
        Args:
            limit: Maximum number of spaces to return
            start: Starting index for pagination
        
        Returns:
            List of space dictionaries
        """
        params = {
            'limit': limit,
            'start': start,
            'expand': 'description,homepage,metadata.labels'
        }
        
        response = self._make_request('GET', 'space', params=params)
        data = response.json()
        
        return data.get('results', [])
    
    def get_all_spaces(self) -> List[Dict[str, Any]]:
        """Get all Confluence spaces using pagination.
        
        Returns:
            List of all space dictionaries
        """
        all_spaces = []
        start = 0
        limit = 50
        
        while True:
            spaces = self.get_spaces(limit=limit, start=start)
            if not spaces:
                break
            
            all_spaces.extend(spaces)
            start += limit
            
            logger.debug(f"Retrieved {len(all_spaces)} spaces so far...")
        
        logger.info(f"Retrieved {len(all_spaces)} total spaces")
        return all_spaces
    
    def get_space_content(self, space_key: str, content_type: str = 'page', 
                         limit: int = 50, start: int = 0) -> List[Dict[str, Any]]:
        """Get content from a specific space.
        
        Args:
            space_key: Space key
            content_type: Type of content (page, blogpost, etc.)
            limit: Maximum number of items to return
            start: Starting index for pagination
        
        Returns:
            List of content dictionaries
        """
        endpoint = f"space/{space_key}/content/{content_type}"
        params = {
            'limit': limit,
            'start': start,
            'expand': 'version,space,body.storage,ancestors,children,descendants,metadata.labels,restrictions'
        }
        
        response = self._make_request('GET', endpoint, params=params)
        data = response.json()
        
        return data.get('results', [])
    
    def get_all_space_content(self, space_key: str, content_type: str = 'page') -> List[Dict[str, Any]]:
        """Get all content from a space using pagination.
        
        Args:
            space_key: Space key
            content_type: Type of content (page, blogpost, etc.)
        
        Returns:
            List of all content dictionaries
        """
        all_content = []
        start = 0
        limit = 50
        
        while True:
            content = self.get_space_content(space_key, content_type, limit=limit, start=start)
            if not content:
                break
            
            all_content.extend(content)
            start += limit
            
            logger.debug(f"Retrieved {len(all_content)} {content_type}s from space {space_key}")
        
        logger.info(f"Retrieved {len(all_content)} total {content_type}s from space {space_key}")
        return all_content
    
    def get_page_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """Get attachments for a specific page.
        
        Args:
            page_id: Page ID
        
        Returns:
            List of attachment dictionaries
        """
        endpoint = f"content/{page_id}/child/attachment"
        params = {
            'expand': 'version,metadata'
        }
        
        response = self._make_request('GET', endpoint, params=params)
        data = response.json()
        
        return data.get('results', [])
    
    def download_attachment(self, download_url: str) -> bytes:
        """Download attachment content.
        
        Args:
            download_url: Download URL from attachment's _links.download field
        
        Returns:
            Attachment content as bytes
        
        Notes:
            The Confluence API returns download URLs in the _links.download field.
            For Cloud instances, these URLs need /wiki prepended to work with API authentication.
            
            Example transformations:
            - /download/attachments/123/file.png -> /wiki/download/attachments/123/file.png (Cloud)
            - /download/attachments/123/file.png -> /download/attachments/123/file.png (Server/DC)
        """
        # Check if download_url is a relative path
        if download_url.startswith('/'):
            # For Cloud instances, prepend /wiki to the download path
            if self.is_cloud and not download_url.startswith('/wiki/'):
                download_url = f"/wiki{download_url}"
            
            # Prepend base_url
            full_url = f"{self.base_url}{download_url}"
        else:
            # It's already a full URL
            full_url = download_url
        
        logger.debug(f"Downloading attachment from: {full_url}")
        
        # Make the request with authentication and retry logic
        for attempt in range(self.max_retries + 1):
            try:
                self._rate_limit()
                
                response = self.session.get(full_url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                
                return response.content
                
            except requests.exceptions.Timeout:
                logger.warning(f"Attachment download timeout on attempt {attempt + 1}: {full_url}")
                if attempt == self.max_retries:
                    raise
                    
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Attachment download HTTP error {response.status_code} on attempt {attempt + 1}: {e}")
                logger.warning(f"  URL: {full_url}")
                if attempt == self.max_retries:
                    raise
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                wait_time = (2 ** attempt) * 1.0
                logger.debug(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        raise requests.exceptions.RequestException(f"Max retries exceeded for attachment download: {full_url}")
    
    def get_page_comments(self, page_id: str) -> List[Dict[str, Any]]:
        """Get comments for a specific page.
        
        Args:
            page_id: Page ID
        
        Returns:
            List of comment dictionaries
        """
        endpoint = f"content/{page_id}/child/comment"
        params = {
            'expand': 'body.view,version'
        }
        
        response = self._make_request('GET', endpoint, params=params)
        data = response.json()
        
        return data.get('results', [])
    
    def create_page(self, space_key: str, title: str, content: str, 
                   parent_id: str = None) -> Dict[str, Any]:
        """Create a new page in Confluence.
        
        Args:
            space_key: Space key where to create the page
            title: Page title
            content: Page content in storage format
            parent_id: Parent page ID (optional)
        
        Returns:
            Created page dictionary
        """
        data = {
            "type": "page",
            "title": title,
            "space": {
                "key": space_key
            },
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            data["ancestors"] = [{"id": parent_id}]
        
        response = self._make_request('POST', 'content', json=data)
        return response.json()
    
    def update_page(self, page_id: str, title: str, content: str, 
                   version_number: int) -> Dict[str, Any]:
        """Update an existing page.
        
        Args:
            page_id: Page ID to update
            title: New page title
            content: New page content in storage format
            version_number: Current version number + 1
        
        Returns:
            Updated page dictionary
        """
        data = {
            "version": {
                "number": version_number
            },
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        response = self._make_request('PUT', f'content/{page_id}', json=data)
        return response.json()
    
    def upload_attachment(self, page_id: str, file_path: str, 
                         comment: str = "") -> Dict[str, Any]:
        """Upload an attachment to a page.
        
        Args:
            page_id: Page ID to attach file to
            file_path: Path to file to upload
            comment: Optional comment for the attachment
        
        Returns:
            Attachment dictionary
        """
        import os
        import mimetypes
        from ..utils.helpers import sanitize_filename
        
        endpoint = f"content/{page_id}/child/attachment"
        
        # Get the correct MIME type for the file
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # Sanitize the filename before sending to API to handle HTML entities and URL encoding
        original_filename = os.path.basename(file_path)
        sanitized_filename = sanitize_filename(original_filename)
        
        # Log sanitization for debugging problematic filenames
        if original_filename != sanitized_filename:
            logger.debug(f"Upload: Sanitized filename '{original_filename}' -> '{sanitized_filename}'")
        
        files = {
            'file': (sanitized_filename, open(file_path, 'rb'), mime_type),
        }
        
        data = {}
        if comment:
            data['comment'] = comment
        
        # X-Atlassian-Token header is required to prevent CSRF errors
        # We need to explicitly remove Content-Type to let requests set it for multipart/form-data
        headers = {
            'X-Atlassian-Token': 'no-check'
        }
        
        # Temporarily remove session-level Content-Type header for this request
        original_content_type = self.session.headers.pop('Content-Type', None)
        
        try:
            response = self.session.post(
                urljoin(f"{self.base_url}{self.api_path}", endpoint),
                files=files,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        finally:
            files['file'][1].close()
            # Restore the original Content-Type header
            if original_content_type:
                self.session.headers['Content-Type'] = original_content_type
    
    def create_space(self, space_key: str, space_name: str, 
                    description: str = "") -> Dict[str, Any]:
        """Create a new Confluence space.
        
        Args:
            space_key: Space key (unique identifier)
            space_name: Space name (display name)
            description: Optional space description
        
        Returns:
            Created space dictionary
        
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        data = {
            "key": space_key,
            "name": space_name,
            "type": "global",  # Required for Confluence Cloud
            "description": {
                "plain": {
                    "value": description,
                    "representation": "plain"
                }
            }
        }
        
        logger.debug(f"Creating space with data: {json.dumps(data, indent=2)}")
        response = self._make_request('POST', 'space', json=data)
        logger.info(f"Created new space: {space_name} ({space_key})")
        return response.json()
    
    def update_space(self, space_key: str, space_name: str = None, 
                    description: str = None) -> Dict[str, Any]:
        """Update an existing Confluence space.
        
        Args:
            space_key: Space key to update
            space_name: New space name (optional)
            description: New space description (optional)
        
        Returns:
            Updated space dictionary
        
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        # Get current space info
        response = self._make_request('GET', f'space/{space_key}')
        current_space = response.json()
        
        # Build update data
        data = {
            "name": space_name if space_name else current_space['name']
        }
        
        if description is not None:
            data["description"] = {
                "plain": {
                    "value": description,
                    "representation": "plain"
                }
            }
        
        response = self._make_request('PUT', f'space/{space_key}', json=data)
        logger.info(f"Updated space: {space_key}")
        return response.json()
    
    def get_space(self, space_key: str) -> Dict[str, Any]:
        """Get details of a specific space.
        
        Args:
            space_key: Space key
        
        Returns:
            Space dictionary
        
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        response = self._make_request('GET', f'space/{space_key}', 
                                     params={'expand': 'description,homepage'})
        return response.json()
    
    def delete_page(self, page_id: str) -> bool:
        """Delete a page from Confluence.
        
        Args:
            page_id: Page ID to delete
        
        Returns:
            True if deletion was successful
        
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        try:
            response = self._make_request('DELETE', f'content/{page_id}')
            logger.info(f"Deleted page with ID: {page_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete page {page_id}: {e}")
    def get_space_id(self, space_key: str) -> Optional[str]:
        """Get space ID from space key.
        
        Args:
            space_key: Space key
        
        Returns:
            Space ID or None if not found
        """
        try:
            space = self.get_space(space_key)
            return space.get('id')
        except Exception as e:
            logger.warning(f"Could not get space ID for {space_key}: {e}")
            return None
    
    def get_folders(self, space_id: str) -> List[Dict[str, Any]]:
        """Get folders in a space using v2 API.
        
        Args:
            space_id: Space ID (not space key)
        
        Returns:
            List of folder dictionaries
        
        Raises:
            requests.exceptions.RequestException: On request failure
        
        Notes:
            Folders are only available in Confluence Cloud via the v2 API.
            The endpoint is /wiki/api/v2/folders with spaceId parameter.
        """
        # For v2 API, we need to use a different base path
        # Construct the v2 API URL directly
        v2_api_path = '/wiki/api/v2/' if self.is_cloud else '/api/v2/'
        v2_url = urljoin(self.base_url, v2_api_path)
        
        endpoint_url = urljoin(v2_url, 'folders')
        
        params = {
            'spaceId': space_id,  # v2 API uses camelCase for parameters
            'limit': 250  # Maximum allowed by API
        }
        
        all_folders = []
        cursor = None
        
        try:
            while True:
                if cursor:
                    params['cursor'] = cursor
                
                self._rate_limit()
                logger.debug(f"Getting folders from {endpoint_url} with params {params}")
                
                response = self.session.get(
                    endpoint_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                results = data.get('results', [])
                all_folders.extend(results)
                
                # Check for next page - v2 API may return cursor in _links
                links = data.get('_links', {})
                next_link = links.get('next')
                
                if not next_link:
                    break
                
                # If next_link is a full URL, extract cursor from it
                # If it's just a cursor string, use it directly
                if isinstance(next_link, str):
                    if '?' in next_link:
                        # Extract cursor from query string
                        from urllib.parse import urlparse, parse_qs
                        parsed = urlparse(next_link)
                        query_params = parse_qs(parsed.query)
                        cursor = query_params.get('cursor', [None])[0]
                    else:
                        cursor = next_link
                else:
                    break
                
                if not cursor:
                    break
                
                logger.debug(f"Retrieved {len(all_folders)} folders so far...")
            
            logger.info(f"Retrieved {len(all_folders)} total folders from space {space_id}")
            return all_folders
            
        except requests.exceptions.HTTPError as e:
            # Folders may not be available (Server/DC or old Cloud instances)
            if e.response.status_code == 404:
                logger.info(f"Folders API not available (likely Server/DC instance or old Cloud): {e}")
                return []
            # Handle 500 errors gracefully - may indicate folder API not fully supported
            elif e.response.status_code == 500:
                logger.info(f"Folders API returned server error (may not be enabled or supported): {e}")
                return []
            raise
        except Exception as e:
            logger.warning(f"Error retrieving folders: {e}")
            return []
    
    def create_folder(self, space_id: str, folder_name: str, 
                     parent_id: str = None) -> Dict[str, Any]:
        """Create a folder in a space using v2 API.
        
        Args:
            space_id: Space ID (not space key) 
            folder_name: Name of the folder to create
            parent_id: Optional parent folder ID
        
        Returns:
            Created folder dictionary
        
        Raises:
            requests.exceptions.RequestException: On request failure
        
        Notes:
            Folders are only available in Confluence Cloud via the v2 API.
            The endpoint is /wiki/api/v2/folders.
        """
        # For v2 API, we need to use a different base path
        v2_api_path = '/wiki/api/v2/' if self.is_cloud else '/api/v2/'
        v2_url = urljoin(self.base_url, v2_api_path)
        
        endpoint_url = urljoin(v2_url, 'folders')
        
        data = {
            "spaceId": space_id,
            "title": folder_name
        }
        
        if parent_id:
            data["parentId"] = parent_id
        
        try:
            self._rate_limit()
            logger.debug(f"Creating folder '{folder_name}' in space {space_id}")
            
            response = self.session.post(
                endpoint_url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            folder = response.json()
            logger.info(f"Created folder: {folder_name} (ID: {folder.get('id')})")
            return folder
            
        except requests.exceptions.HTTPError as e:
            # Folders may not be available (Server/DC or old Cloud instances)
            if e.response.status_code == 404:
                logger.warning(f"Folders API not available (likely Server/DC instance or old Cloud): {e}")
                raise
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise