"""HTML parser for extracting part data.

This module provides HTML parsing functionality using BeautifulSoup.
Follows Single Responsibility Principle - only concerned with parsing HTML.
"""

from typing import Any

import structlog
from bs4 import BeautifulSoup, Tag

logger = structlog.get_logger()


class HTMLParser:
    """HTML parser using BeautifulSoup.

    Parses HTML content and extracts structured data.
    Uses lxml parser for speed and robustness.
    """

    def __init__(self) -> None:
        """Initialize parser."""
        self.parser = "lxml"

    def parse(self, html: str) -> BeautifulSoup:
        """Parse HTML into BeautifulSoup object.

        Args:
            html: Raw HTML string

        Returns:
            Parsed BeautifulSoup object

        Raises:
            ValueError: If HTML is empty or invalid

        Example:
            >>> parser = HTMLParser()
            >>> soup = parser.parse("<html><body>Test</body></html>")
            >>> soup.find("body").text
            'Test'
        """
        if not html or not html.strip():
            msg = "HTML content cannot be empty"
            raise ValueError(msg)

        try:
            soup = BeautifulSoup(html, self.parser)
            logger.debug("html_parsed", length=len(html))

        except Exception as e:
            logger.exception("parse_error", error=str(e))
            msg = f"Failed to parse HTML: {e}"
            raise ValueError(msg) from e
        else:
            return soup

    def extract_text(self, soup: BeautifulSoup, selector: str) -> str | None:
        """Extract text from element matching CSS selector.

        Args:
            soup: Parsed HTML
            selector: CSS selector

        Returns:
            Extracted text or None if not found

        Example:
            >>> parser = HTMLParser()
            >>> soup = parser.parse('<div class="name">Radiator</div>')
            >>> parser.extract_text(soup, ".name")
            'Radiator'
        """
        element = soup.select_one(selector)
        if element:
            text = element.get_text(strip=True)
            logger.debug("text_extracted", selector=selector, text=text)
            return text
        return None

    def extract_attribute(self, soup: BeautifulSoup, selector: str, attribute: str) -> str | None:
        """Extract attribute value from element.

        Args:
            soup: Parsed HTML
            selector: CSS selector
            attribute: Attribute name to extract

        Returns:
            Attribute value or None if not found

        Example:
            >>> parser = HTMLParser()
            >>> soup = parser.parse('<img src="/image.jpg" alt="Part">')
            >>> parser.extract_attribute(soup, "img", "src")
            '/image.jpg'
        """
        element = soup.select_one(selector)
        if element:
            value = element.get(attribute)
            if value:
                logger.debug(
                    "attribute_extracted",
                    selector=selector,
                    attribute=attribute,
                    value=value,
                )
                return str(value)
        return None

    def extract_all(self, soup: BeautifulSoup, selector: str) -> list[Tag]:
        """Extract all elements matching selector.

        Args:
            soup: Parsed HTML
            selector: CSS selector

        Returns:
            List of matching elements

        Example:
            >>> parser = HTMLParser()
            >>> soup = parser.parse('<ul><li>A</li><li>B</li></ul>')
            >>> items = parser.extract_all(soup, "li")
            >>> len(items)
            2
        """
        elements = soup.select(selector)
        logger.debug("elements_extracted", selector=selector, count=len(elements))
        return elements

    def extract_part_data(self, soup: BeautifulSoup) -> dict[str, Any]:  # noqa: ARG002
        """Extract part data from parsed HTML.

        This is a template method that should be overridden for specific
        site implementations. Default implementation extracts common fields.

        Args:
            soup: Parsed HTML

        Returns:
            Dict of part data

        Raises:
            ValueError: If required data cannot be extracted
        """
        # This will be implemented based on actual CSF site structure
        # For now, return template structure
        logger.warning("using_default_extraction", message="Override this method")

        data: dict[str, Any] = {
            "sku": None,
            "name": None,
            "price": None,
            "description": None,
            "category": None,
            "specifications": {},
            "images": [],
        }

        return data


class CSFParser(HTMLParser):
    """Parser specifically for CSF MyCarParts website.

    Extends HTMLParser with CSF-specific extraction logic.
    Follows Open/Closed Principle - extended, not modified.
    """

    def extract_parts_from_application_page(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract all parts from an application page.

        Application pages list multiple parts in .row.app containers.
        This method finds all such containers and extracts each part.

        Args:
            soup: Parsed HTML from application page

        Returns:
            List of part data dicts

        Note:
            Each .row.app container represents one part listing.
            Returns empty list if no parts found.
        """
        logger.info("extracting_all_parts_from_application_page")

        parts_data: list[dict[str, Any]] = []
        part_containers = soup.select(".row.app")

        logger.debug("found_part_containers", count=len(part_containers))

        for idx, container in enumerate(part_containers, 1):
            try:
                part_data = self._extract_single_part_from_container(container)
                parts_data.append(part_data)
                logger.debug(
                    "part_extracted_from_container",
                    index=idx,
                    sku=part_data.get("sku"),
                )
            except ValueError as e:
                logger.warning(
                    "failed_to_extract_part",
                    index=idx,
                    error=str(e),
                )
                continue

        logger.info("application_page_extraction_complete", parts_found=len(parts_data))
        return parts_data

    def _extract_single_part_from_container(self, container: Tag) -> dict[str, Any]:
        """Extract part data from a single .row.app container.

        Args:
            container: BeautifulSoup Tag for .row.app element

        Returns:
            Dict of part data

        Raises:
            ValueError: If required fields are missing
        """
        # Extract SKU from h4 a link
        sku_link = container.select_one("h4 a")
        sku = sku_link.get_text(strip=True) if sku_link else None

        # Extract part name (text after " - " in h4)
        h4 = container.select_one("h4")
        full_text = h4.get_text(strip=True) if h4 else ""
        name = full_text.split(" - ", 1)[1] if " - " in full_text else full_text

        # Extract category from parent panel header
        panel = container.find_parent("div", class_="panel")
        category = None
        if panel and isinstance(panel, Tag):
            category_h4 = panel.select_one(".panel-header h4")
            category = category_h4.get_text(strip=True) if category_h4 else None

        # Create temporary soup for extracting specs/images from this container
        container_soup = BeautifulSoup(str(container), "lxml")

        data: dict[str, Any] = {
            "sku": f"CSF-{sku}" if sku and not sku.startswith("CSF-") else sku,
            "name": name,
            "price": None,  # Not available on application pages
            "description": None,  # Not available on application pages
            "category": category or "Unknown",  # Default if not found
            "specifications": self._extract_specifications(container_soup),
            "images": self._extract_images(container_soup),
            "manufacturer": "CSF",
            "in_stock": self._extract_stock_status(container_soup),
        }

        # Validate that we got at least the critical fields
        if not data["sku"] or not data["name"]:
            msg = "Missing required fields: SKU and Name are mandatory"
            raise ValueError(msg)

        return data

    def extract_part_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract part data from CSF HTML.

        Args:
            soup: Parsed HTML from CSF website

        Returns:
            Dict of part data with CSF-specific fields

        Raises:
            ValueError: If required fields are missing

        Note:
            Expects HTML from application pages (/applications/[ID]) where
            parts are displayed in .row.app containers within .applications div.
            For extracting multiple parts, use extract_parts_from_application_page().
        """
        logger.info("extracting_csf_part_data")

        # Extract SKU from h4 a link (e.g., "3951")
        sku_link = soup.select_one(".row.app h4 a")
        sku = sku_link.get_text(strip=True) if sku_link else None

        # Extract part name (text after " - " in h4)
        h4 = soup.select_one(".row.app h4")
        full_text = h4.get_text(strip=True) if h4 else ""
        name = full_text.split(" - ", 1)[1] if " - " in full_text else full_text

        # Extract category from parent panel header
        category_header = soup.find("div", class_="panel")
        category = None
        if category_header and isinstance(category_header, Tag):
            category_h4 = category_header.select_one(".panel-header h4")
            category = category_h4.get_text(strip=True) if category_h4 else None

        data: dict[str, Any] = {
            "sku": sku,
            "name": name,
            "price": None,  # Not available on application pages
            "description": None,  # Not available on application pages
            "category": category,
            "specifications": self._extract_specifications(soup),
            "images": self._extract_images(soup),
            "manufacturer": "CSF",
            "in_stock": self._extract_stock_status(soup),
        }

        # Validate that we got at least the critical fields
        if not data["sku"] or not data["name"]:
            msg = "Missing required fields: SKU and Name are mandatory"
            raise ValueError(msg)

        logger.info("csf_part_extracted", sku=data["sku"], name=data["name"])
        return data

    def _extract_specifications(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract product specifications.

        Args:
            soup: Parsed HTML

        Returns:
            Dict of specifications

        Note:
            On application pages, specs are in table.table-borderless tbody tr td
            Format: "Key: Value" within each td cell
        """
        specs: dict[str, Any] = {}

        # Find all spec rows in the part's table
        spec_rows = soup.select(".row.app table.table-borderless tbody tr")
        for spec_row in spec_rows:
            cells = spec_row.select("td")
            for cell in cells:
                text = cell.get_text(strip=True)
                # Parse "Key: Value" format
                if ": " in text:
                    key, value = text.split(": ", 1)
                    # Clean value (remove HTML tags if any)
                    # BeautifulSoup already strips tags, but ensure clean text
                    value_clean = BeautifulSoup(value, "lxml").get_text(strip=True)
                    specs[key] = value_clean

        logger.debug("specifications_extracted", count=len(specs))
        return specs

    def _extract_images(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract product images.

        Args:
            soup: Parsed HTML

        Returns:
            List of image dicts with url, alt_text, is_primary

        Note:
            On application pages, primary image is in img.img-thumbnail.primary-image
            Images are hosted on S3: https://illumaware-digital-assets.s3.us-east-2.amazonaws.com/...
        """
        images: list[dict[str, Any]] = []

        # Extract primary image from .row.app
        img_element = soup.select_one(".row.app img.primary-image")

        if img_element:
            src = img_element.get("src") or img_element.get("data-src")
            if src:
                images.append(
                    {
                        "url": str(src),
                        "alt_text": str(img_element.get("alt", "")),
                        "is_primary": True,
                    }
                )

        logger.debug("images_extracted", count=len(images))
        return images

    def _extract_stock_status(self, soup: BeautifulSoup) -> bool:  # noqa: ARG002
        """Extract stock availability status.

        Args:
            soup: Parsed HTML

        Returns:
            True if in stock, False otherwise

        Note:
            Stock status is not displayed on application pages.
            Default to True since parts are listed if available.
            This may need to be updated after inspecting part detail pages.
            The soup parameter is unused but required to maintain consistent
            interface with other extraction methods.
        """
        # Stock status not available on application pages
        # Default to True (assume in stock if listed)
        in_stock = True
        logger.debug("stock_status_extracted", in_stock=in_stock)
        return in_stock

    def extract_detail_page_data(self, soup: BeautifulSoup, sku: str) -> dict[str, Any]:
        """Extract comprehensive part data from detail page.

        Detail pages (/items/{SKU}) contain full specifications, tech notes,
        interchange data, and optional full product descriptions.

        Args:
            soup: Parsed HTML from detail page
            sku: Part SKU (for logging and validation)

        Returns:
            Dict with complete part data including:
            - full_description: str | None
            - specifications: dict[str, Any] (normalized, ~22 specs)
            - tech_notes: str | None
            - interchange_data: list[dict[str, str]]

        Note:
            Detail pages have complex table structures requiring normalization.
            See RECONNAISSANCE.md for table format variations and strategy.
        """
        logger.info("extracting_detail_page_data", sku=sku)

        specifications = self._extract_detail_specifications(soup)
        tech_notes = self._extract_tech_notes(specifications)
        interchange_data = self._extract_interchange_data(soup)
        full_description = self._extract_full_description(soup)

        data: dict[str, Any] = {
            "sku": sku,
            "full_description": full_description,
            "specifications": specifications,
            "tech_notes": tech_notes,
            "interchange_data": interchange_data,
        }

        logger.info(
            "detail_page_extracted",
            sku=sku,
            has_description=bool(full_description),
            spec_count=len(specifications),
            has_tech_notes=bool(tech_notes),
            interchange_count=len(interchange_data),
        )

        return data

    def _extract_full_description(self, soup: BeautifulSoup) -> str | None:
        """Extract full part description from h5 element.

        Args:
            soup: Parsed HTML

        Returns:
            Full description or None if not present

        Note:
            Only ~20% of parts have full descriptions.
            Most have empty h5 elements.
        """
        h5 = soup.find("h5")
        if h5 and isinstance(h5, Tag):
            description = h5.get_text(strip=True)
            if description:
                logger.debug("extracted_full_description", description=description[:60])
                return description
        return None

    def _extract_spec_from_row(self, cells: list[Tag], specs: dict[str, Any]) -> None:
        """Extract specifications from a table row based on cell count.

        Handles 4 different table formats found in detail pages:
        - 3-cell triplets: [display, label, value] x N
        - 2-cell rows: [label, value]
        - Single-cell rows: "Label: Value"

        Args:
            cells: List of table cells (td/th elements)
            specs: Dictionary to populate with extracted specs

        Note:
            Modifies specs dict in-place. See RECONNAISSANCE.md for
            detailed table format variations and normalization strategy.
        """
        # Handle multi-column rows with 3-cell groups
        if len(cells) >= 3 and len(cells) % 3 == 0:  # noqa: PLR2004
            for i in range(0, len(cells), 3):
                if i + 2 < len(cells):
                    key = cells[i + 1].get_text(strip=True).rstrip(":")
                    value = cells[i + 2].get_text(strip=True)
                    if key and value and key not in specs:
                        specs[key] = value

        elif len(cells) == 2:  # noqa: PLR2004
            key = cells[0].get_text(strip=True).rstrip(":")
            value = cells[1].get_text(strip=True)
            if key and value and key not in specs:
                specs[key] = value

        elif len(cells) == 1:
            text = cells[0].get_text(strip=True)
            if ":" in text and len(text) > 3:  # noqa: PLR2004
                parts = text.split(":", 1)
                if len(parts) == 2:  # noqa: PLR2004
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value and key not in specs:
                        specs[key] = value

    def _extract_detail_specifications(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract specifications from detail page tables with normalization.

        Detail pages have ~25 tables with specifications in multiple inconsistent
        formats. This method normalizes the data by:
        1. Handling 3-cell triplets (display, label, value)
        2. Handling 2-cell rows (label, value)
        3. Handling single-cell rows ("Label: Value")
        4. Removing trailing colons from keys
        5. Preventing duplicate keys
        6. Skipping vehicle compatibility tables
        7. Skipping interchange reference tables

        Args:
            soup: Parsed HTML

        Returns:
            Dict of normalized specifications (~22 clean specs per part)

        Note:
            Raw extraction yields 33-36 specs with duplicates.
            Normalization reduces to ~22 clean specs (33% improvement).
        """
        specs: dict[str, Any] = {}
        tables = soup.find_all("table")

        logger.debug("found_detail_tables", count=len(tables))

        for idx, table in enumerate(tables):
            # Skip interchange table (has specific headers)
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "Reference Number" in headers or "Reference Name" in headers:
                logger.debug("skipping_interchange_table", table_index=idx)
                continue

            # Skip vehicle compatibility tables
            if "Make" in headers and "Model" in headers:
                logger.debug("skipping_vehicle_table", table_index=idx)
                continue

            # Extract data from table rows
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                self._extract_spec_from_row(cells, specs)

        logger.debug("detail_specifications_extracted", count=len(specs))
        return specs

    def _extract_tech_notes(self, specifications: dict[str, Any]) -> str | None:
        """Extract tech notes from specifications dict.

        Tech notes are embedded in specification tables with key "Tech Note",
        not in a separate div element.

        Args:
            specifications: Parsed specifications dict

        Returns:
            Tech notes or None

        Note:
            100% of parts tested have tech notes.
            Common examples: "O.E.M. style Plastic tank & Aluminum core"
        """
        tech_note = specifications.get("Tech Note")
        if tech_note is not None and isinstance(tech_note, str):
            logger.debug("extracted_tech_note", note=tech_note[:80])
            return str(tech_note)
        return None

    def _extract_interchange_data(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Extract OEM and interchange reference numbers.

        Args:
            soup: Parsed HTML

        Returns:
            List of interchange references with reference_number and reference_type

        Note:
            Reference types include: "OEM", "Partslink", "DPI"
            Parts typically have 1-5 interchange references
        """
        interchange_data: list[dict[str, str]] = []

        # Find the interchange table by headers
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "Reference Number" in headers and "Reference Name" in headers:
                logger.debug("found_interchange_table")

                rows = table.find_all("tr")[1:]  # Skip header row
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:  # noqa: PLR2004
                        ref_num = cells[0].get_text(strip=True)
                        ref_name = cells[1].get_text(strip=True)
                        if ref_num and ref_name:
                            interchange_data.append(
                                {"reference_number": ref_num, "reference_type": ref_name}
                            )

                break  # Only one interchange table per page

        logger.debug("interchange_data_extracted", count=len(interchange_data))
        return interchange_data
