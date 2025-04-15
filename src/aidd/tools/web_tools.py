import os
import requests
from typing import List, Optional
from urllib.parse import urlparse

from mcp.types import TextContent
from .state import state


def web_fetch_tool():
    return {
        "name": "web_fetch",
        "description": "Fetches content from a URL. "
                    "WHEN TO USE: When you need to retrieve data from web APIs, download documentation, "
                    "check external resources, or gather information from websites. Useful for getting "
                    "real-time data, documentation, or referencing external content. "
                    "WHEN NOT TO USE: When you need to interact with complex websites requiring authentication "
                    "or session management, when the data needs to be processed in a specific format not supported, "
                    "or when you need to make authenticated API calls with OAuth. "
                    "RETURNS: The content of the URL as text. For HTML pages, returns the raw HTML content. "
                    "For JSON endpoints, returns the JSON content as a string. Successful response includes HTTP "
                    "status code. Failed requests include error details. Maximum request size enforced for safety.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from. Must be a valid URL with supported protocol "
                                   "(http or https). Examples: 'https://example.com', 'https://api.github.com/repos/user/repo'. "
                                   "The URL must be publicly accessible."
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers to include in the request. Useful for API calls that "
                                   "require specific headers like User-Agent or Accept. Example: {'User-Agent': 'SkyDeckAI', "
                                   "'Accept': 'application/json'}.",
                    "default": {}
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds. Maximum time to wait for the server to respond before "
                                   "aborting the request. Defaults to 10 seconds.",
                    "default": 10
                },
                "save_to_file": {
                    "type": "string",
                    "description": "Optional path to save the response content to a file. If provided, the content "
                                   "will be saved to this location. Must be within the allowed directory. Example: "
                                   "'downloads/page.html', 'data/api_response.json'.",
                    "default": None
                },
                "convert_html_to_markdown": {
                    "type": "boolean",
                    "description": "If set to true and the content is HTML, it will be converted to markdown format "
                                   "for better readability. This is especially useful for web pages with a lot of content.",
                    "default": True
                }
            },
            "required": ["url"]
        }
    }


async def handle_web_fetch(arguments: dict) -> List[TextContent]:
    """Handle fetching content from a URL."""
    url = arguments.get("url")
    headers = arguments.get("headers", {})
    timeout = arguments.get("timeout", 10)
    save_to_file = arguments.get("save_to_file")
    convert_html_to_markdown = arguments.get("convert_html_to_markdown", True)

    if not url:
        raise ValueError("URL must be provided")

    # Basic URL validation
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {url}. Must include scheme (http/https) and domain.")

    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}. Only http and https are supported.")

    # Add a default User-Agent if not provided
    if "User-Agent" not in headers:
        headers["User-Agent"] = "SkyDeckAI-Web-Fetch/1.0"

    # Validate and prepare file path if saving to file
    full_save_path = None
    if save_to_file:
        if os.path.isabs(save_to_file):
            full_save_path = os.path.abspath(save_to_file)
        else:
            full_save_path = os.path.abspath(os.path.join(state.allowed_directory, save_to_file))

        # Security check
        if not full_save_path.startswith(state.allowed_directory):
            raise ValueError(f"Access denied: Path ({full_save_path}) must be within allowed directory")

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_save_path), exist_ok=True)

    try:
        # Make the request with a maximum size limit to prevent abuse
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True  # Use streaming for better control over large responses
        )

        # Check if response is successful
        response.raise_for_status()

        # Get content type from headers
        content_type = response.headers.get("Content-Type", "").lower()

        # Maximum size limit (10MB)
        max_size = 10 * 1024 * 1024
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size:
                raise ValueError(f"Response too large. Maximum size is {max_size // (1024 * 1024)}MB.")

        # Save to file if requested
        if full_save_path:
            with open(full_save_path, 'wb') as f:
                f.write(content)

        # Try to decode the content
        try:
            text_content = content.decode('utf-8')

            # Convert HTML to markdown if requested and content appears to be HTML
            if convert_html_to_markdown and ("html" in content_type or text_content.strip().startswith(("<!DOCTYPE", "<html"))):
                try:
                    # Using the html2text library to convert HTML to markdown
                    # Need to import here to avoid dependency issues if the library is not installed
                    import html2text
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.ignore_emphasis = False
                    h.body_width = 0  # Don't wrap text
                    text_content = h.handle(text_content)
                except ImportError:
                    # Add note that html2text needs to be installed
                    text_content = f"NOTE: Could not convert HTML to markdown because html2text library is not installed.\n\n{text_content}"

        except UnicodeDecodeError:
            # If content can't be decoded as utf-8, provide info about binary content
            if full_save_path:
                return [TextContent(
                    type="text",
                    text=f"Binary content saved to {save_to_file} (size: {len(content)} bytes, type: {content_type})"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Binary content received (size: {len(content)} bytes, type: {content_type})"
                )]

        # Success message
        status_info = f"HTTP {response.status_code}"
        size_info = f"{len(content)} bytes"
        save_info = f", saved to {save_to_file}" if full_save_path else ""
        format_info = " (converted to markdown)" if convert_html_to_markdown and ("html" in content_type or text_content.strip().startswith(("<!DOCTYPE", "<html"))) else ""

        result = [TextContent(
            type="text",
            text=f"{status_info}, {size_info}{save_info}{format_info}:\n\n{text_content}"
        )]

        return result

    except requests.exceptions.RequestException as e:
        # Handle request-related errors
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message = f"HTTP {e.response.status_code}: {error_message}"

        raise ValueError(f"Error fetching URL ({url}): {error_message}")
    except Exception as e:
        # Handle other errors
        raise ValueError(f"Error processing content from {url}: {str(e)}")
