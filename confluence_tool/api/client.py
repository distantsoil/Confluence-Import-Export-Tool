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

        # Normalise base_url: if the user included '/wiki' at the end of their URL,
        # strip it — the tool appends '/wiki/rest/api/' automatically for Cloud instances,
        # so leaving it in produces double-/wiki paths that cause 404s.
        if self.base_url.lower().endswith('/wiki'):
            self.base_url = self.base_url[:-5]
            logger.warning(
                "Removed trailing '/wiki' from base_url — it is added automatically. "
                f"Using: {self.base_url}"
            )
        
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

        Makes a single fast request against each possible API path and stops as
        soon as one succeeds.  Always tries both paths regardless of the
        auto-detected is_cloud value, so the tool self-heals for:

          - base_url already containing /wiki  (stripped in __init__)
          - is_cloud mis-detected (proxy / custom domain redirect)
          - Confluence Cloud redirecting /wiki/rest/api/ to /rest/api/

        On success updates self.is_cloud and self.api_path in-place so all
        subsequent requests in this session use the correct path.

        Returns:
            True if connection is successful, False otherwise
        """
        # Always start with the configured path so fast-path succeeds when correct.
        if self.is_cloud:
            paths_to_try = [('/wiki/rest/api/', True), ('/rest/api/', False)]
        else:
            paths_to_try = [('/rest/api/', False), ('/wiki/rest/api/', True)]

        # Use user/current as the probe endpoint: lightweight, auth-aware (returns
        # 401 for bad credentials rather than 404), present on all Confluence Cloud
        # and Server/DC versions, and does not trigger SSO redirects.
        # serverInfo was the original choice but is deprecated on newer Cloud tenants.
        probe_endpoint = 'user/current'

        for api_path, is_cloud in paths_to_try:
            url = urljoin(f"{self.base_url}{api_path}", probe_endpoint)
            try:
                self._rate_limit()
                logger.debug(f"Testing connection: GET {url}")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                if api_path != self.api_path:
                    logger.warning(
                        f"Auto-corrected API path to '{api_path}' "
                        f"(was '{self.api_path}'). "
                        f"Tip: set base_url in config.yaml to the plain "
                        f"atlassian.net URL with no trailing /wiki path."
                    )
                self.is_cloud = is_cloud
                self.api_path = api_path
                logger.info(
                    f"Successfully connected to Confluence "
                    f"({'Cloud' if is_cloud else 'Server/DC'} mode, "
                    f"api_path: {api_path})"
                )
                return True

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status == 404:
                    logger.warning(f"Got 404 on {url} — trying alternative API path...")
                    continue
                # Auth / permission errors — wrong credentials, not a path issue
                logger.error(f"Connection test failed: {e}")
                return False

            except Exception as e:
                logger.error(f"Connection test failed: {e}")
                return False

        logger.error(
            f"Connection test failed: {probe_endpoint} returned 404 on both "
            "/wiki/rest/api/ and /rest/api/. "
            "Check that base_url is correct and that your Confluence instance is accessible."
        )
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

    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder via the v2 API.

        Args:
            folder_id: Folder ID to delete

        Returns:
            True if deletion was successful (including already-deleted 404)

        Raises:
            requests.exceptions.RequestException: On request failure (except 404)
        """
        v2_api_path = '/wiki/api/v2/' if self.is_cloud else '/api/v2/'
        v2_url = urljoin(self.base_url, v2_api_path)
        endpoint_url = urljoin(v2_url, f'folders/{folder_id}')

        try:
            self._rate_limit()
            response = self.session.delete(endpoint_url, timeout=self.timeout)
            if response.status_code == 404:
                logger.debug(f"Folder {folder_id} not found (already deleted)")
                return True
            response.raise_for_status()
            logger.info(f"Deleted folder with ID: {folder_id}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return True  # Already gone — treat as success
            logger.error(f"Failed to delete folder {folder_id}: {e}")
            raise

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

    def get_space_id_v2(self, space_key: str) -> Optional[str]:
        """Get the v2-format space ID for use with the Confluence v2 API.

        The v1 REST API returns a legacy integer space ID (e.g. 131309).
        The v2 REST API (folders, databases, etc.) requires the v2 space ID
        which is retrieved from GET /wiki/api/v2/spaces?keys={space_key}.
        These IDs are often different; passing the v1 ID to v2 endpoints
        causes a 500 Internal Server Error from Atlassian.

        Args:
            space_key: Space key (e.g. 'KB')

        Returns:
            v2 space ID string, or None if not available
        """
        try:
            v2_api_path = '/wiki/api/v2/' if self.is_cloud else '/api/v2/'
            url = urljoin(self.base_url, f"{v2_api_path}spaces")
            self._rate_limit()
            response = self.session.get(
                url,
                params={'keys': space_key, 'limit': 1},
                timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json().get('results', [])
            if results:
                v2_id = str(results[0].get('id', ''))
                logger.info(f"v2 space ID for '{space_key}': {v2_id}")
                return v2_id
            logger.warning(f"v2 spaces API returned no results for key '{space_key}'")
        except Exception as e:
            logger.warning(f"Could not get v2 space ID for {space_key}: {e}")
        return None

    def get_folders(self, space_id: str) -> List[Dict[str, Any]]:
        """Discover folders in a space via v2 page-parent relationships.

        The GET /wiki/api/v2/folders?space-id={id} endpoint returns 500 on
        many Confluence Cloud tenants regardless of the space ID format.
        This method uses a discovery approach instead:

          1. Fetch all pages in the space via GET /wiki/api/v2/pages?space-id={id}.
             Each page carries parentId and parentType fields.
          2. Collect the parentId of every page whose parentType is "folder".
          3. Fetch each discovered folder via GET /wiki/api/v2/folders/{id}.
          4. Walk up: if a folder's own parentType is "folder", enqueue its
             parentId so ancestor folders are also captured.

        As a side-effect, populates self._v2_page_parents with a mapping of
        {page_id -> {"parentId": ..., "parentType": ...}} so the exporter can
        save this alongside page metadata for use during import.

        Args:
            space_id: Space ID

        Returns:
            List of folder dicts (id, title, parentId, parentType, …)
        """
        from urllib.parse import urlparse, parse_qs

        v2_base = self.base_url + ('/wiki/api/v2/' if self.is_cloud else '/api/v2/')

        # ------------------------------------------------------------------ #
        # Step 1: page pass — collect v2 parent info and seed folder ID set   #
        # ------------------------------------------------------------------ #
        self._v2_page_parents: Dict[str, Any] = {}
        folder_ids: set = set()
        cursor = None

        try:
            while True:
                params: Dict[str, Any] = {'space-id': space_id, 'limit': 250}
                if cursor:
                    params['cursor'] = cursor

                self._rate_limit()
                response = self.session.get(
                    v2_base + 'pages', params=params, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()

                for page in data.get('results', []):
                    pid = str(page.get('id', ''))
                    parent_id = str(page.get('parentId', '')) if page.get('parentId') else None
                    parent_type = page.get('parentType')
                    self._v2_page_parents[pid] = {
                        'parentId': parent_id,
                        'parentType': parent_type,
                    }
                    if parent_type == 'folder' and parent_id:
                        folder_ids.add(parent_id)

                next_link = data.get('_links', {}).get('next')
                if not next_link:
                    break
                if isinstance(next_link, str) and '?' in next_link:
                    parsed = urlparse(next_link)
                    cursor = parse_qs(parsed.query).get('cursor', [None])[0]
                else:
                    cursor = next_link if isinstance(next_link, str) else None
                if not cursor:
                    break

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 405):
                logger.info("v2 pages API not available; cannot discover folders")
            else:
                logger.warning(f"Error fetching pages for folder discovery (HTTP {status}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching pages for folder discovery: {e}")
            return []

        if not folder_ids:
            logger.info(
                "No pages with folder parents found in space — "
                "trying direct folder API fallback (BFS from space root)"
            )
            return self._get_folders_by_bfs(space_id, v2_base)

        logger.info(
            f"Found {len(folder_ids)} unique folder parent(s) across "
            f"{len(self._v2_page_parents)} pages; fetching folder details…"
        )

        # ------------------------------------------------------------------ #
        # Step 2: fetch each folder, recursively walk up to ancestor folders  #
        # ------------------------------------------------------------------ #
        all_folders: Dict[str, Any] = {}
        queue = list(folder_ids)

        while queue:
            folder_id = queue.pop(0)
            if folder_id in all_folders:
                continue
            try:
                self._rate_limit()
                response = self.session.get(
                    v2_base + f'folders/{folder_id}', timeout=self.timeout
                )
                if response.status_code == 200:
                    folder = response.json()
                    all_folders[folder_id] = folder
                    # if this folder is itself inside another folder, enqueue the parent
                    if folder.get('parentType') == 'folder' and folder.get('parentId'):
                        parent_id = str(folder['parentId'])
                        if parent_id not in all_folders:
                            queue.append(parent_id)
                else:
                    logger.debug(
                        f"Could not fetch folder {folder_id}: HTTP {response.status_code}"
                    )
            except Exception as e:
                logger.debug(f"Error fetching folder {folder_id}: {e}")

        logger.info(f"Discovered {len(all_folders)} folder(s) in space {space_id}")
        return list(all_folders.values())
    
    def _get_folders_by_bfs(self, space_id: str, v2_base: str) -> List[Dict[str, Any]]:
        """BFS fallback for get_folders when the space has no pages.

        Tries three strategies in order, stopping at the first that yields results:

          1. GET /wiki/api/v2/folders?space-id={id}   — returns all folders in one
             shot (paginated). Returns 500 on some tenants; skipped if so.
          2. GET /wiki/api/v2/folders?parentId={space_id} — root-level folders whose
             parent is the space, then recursively GET …?parentId={folder_id}.
          3. (no further fallback) — log diagnostic info and return [].

        Args:
            space_id: v2 space ID
            v2_base:  base URL for the v2 API (already constructed by caller)

        Returns:
            List of folder dicts, or [] if all strategies are unavailable.
        """
        from urllib.parse import urlparse, parse_qs

        def _paginate(params: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Fetch all pages of results for the given params; return [] on error."""
            results: List[Dict[str, Any]] = []
            cursor = None
            while True:
                p = dict(params)
                if cursor:
                    p['cursor'] = cursor
                try:
                    self._rate_limit()
                    resp = self.session.get(
                        v2_base + 'folders', params=p, timeout=self.timeout
                    )
                    print(f"    [folder API] GET folders {p} → HTTP {resp.status_code}")
                    if resp.status_code != 200:
                        return []
                    data = resp.json()
                except Exception as exc:
                    print(f"    [folder API] error for {p}: {exc}")
                    return []

                batch = data.get('results', [])
                print(f"    [folder API] {len(batch)} result(s) in this page")
                results.extend(batch)
                next_link = data.get('_links', {}).get('next')
                if not next_link:
                    break
                parsed = urlparse(next_link) if isinstance(next_link, str) else None
                cursor = parse_qs(parsed.query).get('cursor', [None])[0] if parsed else None
                if not cursor:
                    break
            return results

        # ── Strategy 1: space-id filter (gets everything in one sweep) ────── #
        print(f"  [folder discovery] strategy 1: space-id={space_id}")
        by_space = _paginate({'space-id': space_id, 'limit': 250})
        if by_space:
            print(f"  [folder discovery] strategy 1 found {len(by_space)} folder(s)")
            return by_space

        # ── Strategy 2: BFS from space root via parentId ──────────────────── #
        print(f"  [folder discovery] strategy 2: parentId BFS from space {space_id}")
        all_folders: Dict[str, Any] = {}
        queue: list = [space_id]

        while queue:
            parent_id = queue.pop(0)
            page_results = _paginate({'parentId': parent_id, 'limit': 250})
            for folder in page_results:
                fid = str(folder.get('id', ''))
                if fid and fid not in all_folders:
                    all_folders[fid] = folder
                    queue.append(fid)

        if all_folders:
            print(f"  [folder discovery] strategy 2 found {len(all_folders)} folder(s)")
        else:
            print(
                f"  [folder discovery] both strategies returned 0 folders "
                f"(space_id={space_id}, v2_base={v2_base})"
            )

        return list(all_folders.values())

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

    def move_content(self, content_id: str, target_id: str,
                     position: str = 'append') -> bool:
        """Move content to be a child of (or sibling of) a target using the v1 move endpoint.

        This is the confirmed workaround for placing pages under non-page content
        types (folders, databases, whiteboards) where the create_page ancestors
        parameter and the v2 API parentId field both fail with 500 errors.

        Args:
            content_id: ID of the content to move
            target_id: ID of the target content (page, folder, database, etc.)
            position: Relationship to target — 'append' (make child of target),
                      'before' (sibling before target), 'after' (sibling after target)

        Returns:
            True if the move succeeded

        Raises:
            requests.exceptions.RequestException: On request failure

        Notes:
            Uses PUT /rest/api/content/{id}/move/{position}/{targetId}.
            Despite the name, this endpoint works for moving content under any
            target content type, not only pages.
            Only available on Confluence Cloud (v2-era feature).
        """
        endpoint = f"content/{content_id}/move/{position}/{target_id}"
        try:
            self._rate_limit()
            logger.debug(f"Moving content {content_id} to {position} {target_id}")
            response = self._make_request('PUT', endpoint)
            logger.info(f"Moved content {content_id} under target {target_id}")
            return True
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 404:
                logger.warning(
                    f"Move endpoint not available (likely Server/DC or content not found): {e}"
                )
            else:
                logger.warning(
                    f"Failed to move content {content_id} under {target_id} "
                    f"(HTTP {status}): {e}"
                )
            return False
        except Exception as e:
            logger.warning(f"Failed to move content {content_id} under {target_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Database API (Confluence Cloud v2 only)
    # ------------------------------------------------------------------

    def get_databases(self, space_id: str) -> List[Dict[str, Any]]:
        """Discover databases in a space via v2 page-parent relationships.

        GET /wiki/api/v2/databases?space-id={id} returns 500 on Confluence
        Cloud for the same reason as the folders endpoint.  Instead, reuse
        the cached _v2_page_parents mapping (populated by get_folders()) to
        find pages whose parentType is "database", then fetch each database
        individually via GET /wiki/api/v2/databases/{id}.

        If get_folders() has not been called first (no cache), falls back to
        returning an empty list with an informational log message.

        Args:
            space_id: Space ID (not space key)

        Returns:
            List of database dicts (id, title, parentId, parentType, …)
        """
        v2_base = self.base_url + ('/wiki/api/v2/' if self.is_cloud else '/api/v2/')

        # Reuse the page-parent data collected during get_folders().
        # Databases are first-class content objects; pages inside a database
        # have parentType == "database".
        v2_page_parents = getattr(self, '_v2_page_parents', {})
        if not v2_page_parents:
            logger.info(
                "No cached v2 page-parent data available for database discovery "
                "(call get_folders() first). Skipping database export."
            )
            return []

        database_ids: set = {
            str(info['parentId'])
            for info in v2_page_parents.values()
            if info.get('parentType') == 'database' and info.get('parentId')
        }

        if not database_ids:
            logger.info("No pages with database parents found in space — no databases to export")
            return []

        logger.info(
            f"Found {len(database_ids)} unique database parent(s) across "
            f"{len(v2_page_parents)} pages; fetching database details…"
        )

        all_databases: Dict[str, Any] = {}
        for db_id in database_ids:
            try:
                self._rate_limit()
                response = self.session.get(
                    v2_base + f'databases/{db_id}', timeout=self.timeout
                )
                if response.status_code == 200:
                    all_databases[db_id] = response.json()
                else:
                    logger.debug(
                        f"Could not fetch database {db_id}: HTTP {response.status_code}"
                    )
            except Exception as e:
                logger.debug(f"Error fetching database {db_id}: {e}")

        logger.info(f"Discovered {len(all_databases)} database(s) in space {space_id}")
        return list(all_databases.values())

    def create_database(self, space_id: str, title: str,
                        parent_id: str = None) -> Dict[str, Any]:
        """Create an empty database stub in a space using the v2 API.

        Creates the database container only.  Database content (rows, columns,
        data) cannot be set via the REST API and must be re-entered manually
        in the Confluence UI after import.

        Args:
            space_id: Space ID (not space key)
            title: Database title
            parent_id: Optional parent content ID (page or folder)

        Returns:
            Created database dictionary (contains at minimum 'id' and 'title')

        Raises:
            requests.exceptions.RequestException: On request failure

        Notes:
            Databases are only available in Confluence Cloud via the v2 API.
            The endpoint is POST /wiki/api/v2/databases.
        """
        v2_api_path = '/wiki/api/v2/' if self.is_cloud else '/api/v2/'
        v2_url = urljoin(self.base_url, v2_api_path)
        endpoint_url = urljoin(v2_url, 'databases')

        data: Dict[str, Any] = {
            "spaceId": space_id,
            "title": title
        }
        if parent_id:
            data["parentId"] = parent_id

        try:
            self._rate_limit()
            logger.debug(f"Creating database '{title}' in space {space_id}")

            response = self.session.post(
                endpoint_url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()

            database = response.json()
            logger.info(f"Created database stub: '{title}' (ID: {database.get('id')})")
            return database

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 404:
                logger.warning(
                    f"Databases API not available (likely Server/DC or old Cloud): {e}"
                )
            logger.error(f"Failed to create database '{title}': {e}")
            raise