"""AJAX response parser for CSF MyCarParts JavaScript responses.

This module provides parsing functionality for CSF website AJAX responses,
which return jQuery-wrapped HTML in JavaScript format instead of JSON.
"""

import re
from typing import Final

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


class AJAXParsingError(Exception):
    """Raised when AJAX response parsing fails."""


class AJAXResponseParser:
    """Parses jQuery-wrapped HTML from JavaScript AJAX responses.

    The CSF MyCarParts website returns AJAX responses as JavaScript code
    that manipulates the DOM, rather than JSON data. This parser extracts
    the HTML content from these JavaScript responses.

    Example AJAX response format:
        $("#btnYear").next().html("<ul class='list-inline'><li>2025</li></ul>")

    The parser extracts the HTML string from the .html("...") call and
    handles JavaScript string escaping (quotes and slashes).

    Attributes:
        HTML_PATTERN: Compiled regex pattern for matching .html("...") calls.
    """

    HTML_PATTERN: Final[re.Pattern[str]] = re.compile(r'\.html\("(.+?)"\)')

    def parse(self, js_code: str) -> str:
        r"""Extract HTML from JavaScript AJAX response.

        Args:
            js_code: JavaScript code from AJAX response containing .html() call.

        Returns:
            Extracted and unescaped HTML string.

        Raises:
            AJAXParsingError: If no .html() call found in JavaScript code.

        Examples:
            >>> parser = AJAXResponseParser()
            >>> js = '$("#btnYear").next().html("<ul><li>2025</li></ul>")'
            >>> parser.parse(js)
            '<ul><li>2025</li></ul>'

            >>> js = '$("#el").html("<a href=\"/path\">Link</a>")'
            >>> parser.parse(js)
            '<a href="/path">Link</a>'
        """
        match = self.HTML_PATTERN.search(js_code)

        if not match:
            logger.warning(
                "ajax_parse_failed",
                reason="no_html_call_found",
                code_snippet=js_code[:200],
            )
            msg = "No .html() call found in JavaScript response"
            raise AJAXParsingError(msg)

        # Extract HTML from regex group
        html = match.group(1)

        # Unescape JavaScript string escaping
        # Common escapes in JavaScript strings:
        # - \\" → "  (escaped double quotes)
        # - \\/ → /  (escaped forward slashes)
        html = html.replace('\\"', '"').replace("\\/", "/")

        logger.debug(
            "ajax_parsed",
            original_length=len(js_code),
            html_length=len(html),
        )

        return html

    def try_parse(self, js_code: str) -> str | None:
        """Attempt to extract HTML, returning None on failure.

        This is a non-throwing variant of parse() that returns None
        instead of raising AJAXParsingError when parsing fails.

        Args:
            js_code: JavaScript code from AJAX response.

        Returns:
            Extracted HTML string if successful, None if parsing fails.

        Examples:
            >>> parser = AJAXResponseParser()
            >>> js = '$("#el").html("<div>Content</div>")'
            >>> parser.try_parse(js)
            '<div>Content</div>'

            >>> invalid_js = 'console.log("no html call here");'
            >>> parser.try_parse(invalid_js) is None
            True
        """
        try:
            return self.parse(js_code)
        except AJAXParsingError:
            return None

    def _parse_dropdown_response(
        self, js_code: str, href_pattern: str, log_type: str
    ) -> dict[int, str]:
        """Parse dropdown AJAX response (DRY helper).

        Extracts options from jQuery dropdown responses by finding links
        that match the given pattern and extracting IDs from their hrefs.

        Args:
            js_code: JavaScript AJAX response
            href_pattern: Pattern to match in href (e.g., "get_model_by_make_year")
            log_type: Type for logging (e.g., "year_id", "application_id")

        Returns:
            Dict mapping ID to text content
        """
        html = self.parse(js_code)
        soup = BeautifulSoup(html, "html.parser")

        results = {}
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # BeautifulSoup can return str or AttributeValueList, ensure string
            href_str = str(href) if not isinstance(href, str) else href
            if href_pattern in href_str:
                id_str = href_str.split("/")[-1]
                try:
                    option_id = int(id_str)
                    text = link.get_text(strip=True)
                    results[option_id] = text
                except ValueError:
                    logger.warning("invalid_%s", log_type, href=href, id_str=id_str)
                    continue

        logger.debug("%s_parsed", log_type, count=len(results))
        return results

    def parse_year_response(self, js_code: str) -> dict[int, str]:
        r"""Parse year dropdown AJAX response.

        Extracts year options from the jQuery response. The HTML contains links like:
        <a data-remote="true" href="remote:/get_model_by_make_year/192">2025</a>

        Args:
            js_code: JavaScript AJAX response

        Returns:
            Dict mapping year_id to year string

        Example:
            >>> parser = AJAXResponseParser()
            >>> js = '$("#btnYear").html("<ul><li>'
            >>> js += '<a href=\\"remote:/get_model_by_make_year/192\\">2025</a></li></ul>")'
            >>> parser.parse_year_response(js)
            {192: '2025'}
        """
        return self._parse_dropdown_response(js_code, "get_model_by_make_year", "years")

    def parse_model_response(self, js_code: str) -> dict[int, str]:
        r"""Parse model dropdown AJAX response.

        Extracts model options from the jQuery response. The HTML contains links like:
        <a data-remote="true" href="/applications/8430">Accord</a>

        Args:
            js_code: JavaScript AJAX response

        Returns:
            Dict mapping application_id to model name

        Example:
            >>> parser = AJAXResponseParser()
            >>> js = '$("#btnModel").html("<ul><li>'
            >>> js += '<a href=\\"/applications/8430\\">Accord</a></li></ul>")'
            >>> parser.parse_model_response(js)
            {8430: 'Accord'}
        """
        return self._parse_dropdown_response(js_code, "/applications/", "models")
