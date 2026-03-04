"""HTML parser for extracting part data.

This module provides HTML parsing functionality using BeautifulSoup.
Follows Single Responsibility Principle - only concerned with parsing HTML.
"""

import re
from typing import Any, ClassVar

import structlog
from bs4 import BeautifulSoup, NavigableString, Tag

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
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "failed_to_extract_part",
                    index=idx,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        logger.info("application_page_extraction_complete", parts_found=len(parts_data))
        return parts_data

    def _extract_single_part_from_container(self, container: Tag) -> dict[str, Any]:
        """Extract part data from a single .row.app container.

        Args:
            container: BeautifulSoup Tag for .row.app element

        Returns:
            Dict of part data including engine qualifier

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

        # Extract vehicle qualifiers (engine, aspiration, qualifiers list)
        vehicle_qualifiers = self._extract_vehicle_qualifiers(container)

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
            "vehicle_qualifiers": vehicle_qualifiers,  # Structured qualifiers data
        }

        # Validate that we got at least the critical fields
        if not data["sku"] or not data["name"]:
            msg = "Missing required fields: SKU and Name are mandatory"
            raise ValueError(msg)

        return data

    def _clean_engine_text(self, text: str) -> str:
        """Clean engine text by removing junk labels and manufacturers.

        Removes:
        - Duplicate displacement units (keep cc, remove ci if both present)
        - Label prefixes like "TRANSMISSION CONTROL TYPE:"
        - Manufacturer names (DENSO, TOYO, BEHR, VALEO, etc.)
        - Trailing junk concatenations (Body Type, OE Style, Radiator specs, etc.)

        Args:
            text: Raw engine text

        Returns:
            Cleaned engine text

        Examples:
            >>> self._clean_engine_text("1.6L L4 1588CC 98CI")
            "1.6L L4 1588cc"
            >>> self._clean_engine_text("TRANSMISSION CONTROL TYPE: MANUAL")
            "Manual"
            >>> self._clean_engine_text("2.0L L4 1984cc DENSO/TOYO")
            "2.0L L4 1984cc"
            >>> self._clean_engine_text("3.2L V6 3210ccBody Type: CoupeMicro, 16 psi")
            "3.2L V6 3210cc"
        """
        # Remove common label prefixes
        text = re.sub(r"^TRANSMISSION\s+CONTROL\s+TYPE:\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^ENG\.\s*BASE:\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^ENGINE:\s*", "", text, flags=re.IGNORECASE)

        # Remove "Eng. Version:" label but keep the version text (VTEC, Duratec, EcoBoost)
        text = re.sub(r"Eng\.\s+Version:\s*", "", text, flags=re.IGNORECASE)

        # Remove manufacturer names (common radiator manufacturers)
        manufacturers = [
            "DENSO",
            "TOYO",
            "BEHR",
            "VALEO",
            "MODINE",
            "NISSENS",
            "DELPHI",
            "MAHLE",
            "CALSONIC",
        ]
        for mfr in manufacturers:
            # Remove manufacturer with optional slash/comma prefix
            text = re.sub(rf"[/,\s]+{mfr}(?:/[A-Z]+)?", "", text, flags=re.IGNORECASE)

        # Handle duplicate displacement units (1588CC 98CI -> keep 1588cc only)
        # Pattern: Keep the cc value, remove the ci value if both present
        # Look for: digits + cc + space + digits + ci
        text = re.sub(r"(\d+cc)\s+\d+ci", r"\1", text, flags=re.IGNORECASE)

        # Remove trailing junk after valid engine info
        # Cut off at common metadata suffixes that shouldn't be in engine string
        cutoff_patterns = [
            r"Body\s+Type:",
            r"OE\s+Style",
            r"Use\s+Mini",
            r"Mini,",
            r"Micro,",
            r"\d+\s+psi",
            r"Radiator\s+&",
            r"Radiator\s+And",
            r"Transmission\s+#\s+of\s+Speeds:",
            r"w/\s*Variable",
            r"w/o\s*Variable",
            r"NBR\s+OF\s+DOORS:",
            r"VALVES\s+PER\s+ENGINE:",
            r"ITEM\s+DETAIL",
            r"UPGRADED",
        ]
        for pattern in cutoff_patterns:
            text = re.sub(rf"\s*{pattern}.*$", "", text, flags=re.IGNORECASE)

        # Normalize cc/CI to lowercase cc for consistency
        text = re.sub(r"\b(\d+)CC\b", r"\1cc", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(\d+)CI\b", r"\1ci", text, flags=re.IGNORECASE)

        # Clean up extra whitespace
        text = " ".join(text.split())

        return text.strip()

    _QUALIFIER_PATTERNS: ClassVar[list[str]] = [
        r"(w\/\s*(?:Heavy Duty |Max Duty )?Towing(?:\s+Package)?)",
        r"(w\/o\s*Towing(?:\s+Package)?)",
        r"(w\/\s*Tow\s+Package)",
        r"(w\/o\s*Tow\s+Package)",
        r"(w\/\s*Off-Road(?:\s+Package)?)",
        r"(w\/o\s*Off-Road(?:\s+Package)?)",
        r"(w\/\s*Ambulance(?:\s+Package)?)",
        r"(w\/o\s*Ambulance(?:\s+Package)?)",
        r"(w\/\s*Air\s+Conditioning)",
    ]

    def _parse_aspiration(self, text: str, result: dict[str, Any]) -> None:
        """Extract aspiration and EcoBoost qualifier from text."""
        aspiration_match = re.search(
            r"Aspiration:\s*([^\n]+?)(?:\n|Item Detail|Upgraded|Denso|$)", text
        )
        if not aspiration_match:
            return

        aspiration_raw = aspiration_match.group(1).strip()
        aspiration_raw = self._clean_engine_text(aspiration_raw)

        if "ecoboost" in aspiration_raw.lower() and "EcoBoost" not in result["qualifiers"]:
            result["qualifiers"].append("EcoBoost")

        aspiration = self._extract_clean_engine_spec(aspiration_raw)
        if not aspiration or aspiration.lower() in ("not applicable", "n/a", ""):
            return

        max_aspiration_length = 50
        if len(aspiration) <= max_aspiration_length:
            result["aspiration"] = aspiration
        else:
            logger.warning("aspiration_too_long", value=aspiration[:80])

    def _parse_transmission(self, text: str, result: dict[str, Any]) -> None:
        """Extract transmission qualifier from text."""
        transmission_match = re.search(
            r"Transmission\s+Control\s+Type:\s*([^\n]+?)"
            r"(?:\n|Item Detail|Upgraded|Denso|$)",
            text,
        )
        if not transmission_match:
            return

        transmission = transmission_match.group(1).strip()
        transmission = self._clean_engine_text(transmission)
        max_transmission_length = 50
        if (
            transmission
            and transmission.lower() not in ("not applicable", "n/a")
            and len(transmission) < max_transmission_length
        ):
            result["qualifiers"].append(transmission)

    def _collect_qualifier_matches(self, text: str, qualifiers: list[str]) -> None:
        """Find qualifier patterns (w/ Package, w/o Package) in text."""
        for pattern in self._QUALIFIER_PATTERNS:
            for match in re.findall(pattern, text, re.IGNORECASE):
                if match and match not in qualifiers:
                    qualifiers.append(match)

    def _extract_vehicle_qualifiers(self, container: Tag) -> dict[str, Any]:
        """Extract vehicle qualifiers and engine data separately.

        Parses the qualifiers table to extract:
        - Clean engine specification (just displacement + config)
        - Aspiration (Turbocharged, Naturally Aspirated)
        - Vehicle qualifiers/packages (Transmission, Towing, etc.)

        Args:
            container: BeautifulSoup Tag for .row.app element

        Returns:
            Dict with 'engine', 'aspiration', and 'qualifiers' keys
        """
        text = container.get_text(separator="\n")

        result: dict[str, Any] = {
            "engine": None,
            "aspiration": None,
            "qualifiers": [],
        }

        # 1. Extract clean engine spec (Eng. Base)
        eng_base_pattern = (
            r"Eng\.\s*Base:\s*([^\n]+?)"
            r"(?:\n|Transmission|Fuel Type|Aspiration|Item Detail|Upgraded|Denso|$)"
        )
        eng_base_match = re.search(eng_base_pattern, text)
        if eng_base_match:
            eng_base = self._clean_engine_text(eng_base_match.group(1).strip())
            if eng_base:
                result["engine"] = self._extract_clean_engine_spec(eng_base)

        # 2. Extract Aspiration
        self._parse_aspiration(text, result)

        # 3. Extract Transmission as qualifier
        self._parse_transmission(text, result)

        # 4. Extract package qualifiers from full text and engine string
        self._collect_qualifier_matches(text, result["qualifiers"])
        if eng_base_match:
            eng_full = eng_base_match.group(1).strip()
            self._collect_qualifier_matches(eng_full, result["qualifiers"])

        logger.debug(
            "extracted_vehicle_qualifiers",
            engine=result["engine"],
            aspiration=result["aspiration"],
            qualifiers=result["qualifiers"],
        )

        return result

    def _extract_clean_engine_spec(self, eng_text: str) -> str:
        """Extract just the clean engine specification.

        Removes product specs and qualifiers, keeping only the engine displacement/config.

        Args:
            eng_text: Raw engine text

        Returns:
            Clean engine spec (e.g., "2.0L L4 1993cc")

        Example:
            >>> parser._extract_clean_engine_spec("2.0L L4 1993ccw/ SUB COOL Design")
            '2.0L L4 1993cc'
        """
        # Fix missing spaces (e.g., "3343ccMax Duty" → "3343cc Max Duty")
        cleaned = re.sub(r"(cc|ci)([A-Z])", r"\1 \2", eng_text)

        # Remove aspiration-related text (should be in aspiration field)
        aspiration_patterns = [
            r"Turbocharged",
            r"Supercharged",
            r"Naturally Aspirated",
            r"EcoBoost",
            r"w\/\s*EcoBoost(?:\s+Engine)?",
        ]
        for pattern in aspiration_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove fuel type info (should be in fuel_type field)
        cleaned = re.sub(r"Fuel Type:\s*\w+", "", cleaned, flags=re.IGNORECASE)

        # Remove radiator position info
        cleaned = re.sub(r"(?:Primary|Secondary)\s+Radiator", "", cleaned, flags=re.IGNORECASE)

        # Remove duty level info (Std/Heavy/Max Duty) — product specs,
        # not vehicle qualifiers. "w/ Max Duty Towing" is extracted
        # separately. No trailing \b: "Duty" may abut "w/" directly.
        cleaned = re.sub(r"\b(?:Std|Standard|Heavy|Max)\s+Duty", "", cleaned, flags=re.IGNORECASE)

        # Remove "Multi-fit Model"
        cleaned = re.sub(r"Multi-fit\s+Model", "", cleaned, flags=re.IGNORECASE)

        # Remove "Pkg" prefix/suffix
        cleaned = re.sub(r"\s*Pkg\s*", " ", cleaned, flags=re.IGNORECASE)

        # First, remove vehicle qualifiers (these will be extracted separately)
        vehicle_qualifier_patterns = [
            r"w\/\s*(?:Heavy Duty |Max Duty )?Towing(?:\s+Package)?",
            r"w\/o\s*Towing(?:\s+Package)?",
            r"w\/\s*Off-Road(?:\s+Package)?",
            r"w\/o\s*Off-Road(?:\s+Package)?",
            r"w\/\s*Ambulance(?:\s+Package)?",
            r"w\/o\s*Ambulance(?:\s+Package)?",
            r"w\/\s*Air\s+Conditioning",
            r"w\/\s*Tow\s+Package",
            r"w\/o\s*Tow\s+Package",
        ]

        for pattern in vehicle_qualifier_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove common product specs
        product_spec_patterns = [
            r"w\/\s*SUB COOL[^w]*",
            r"w\/\s*Heavy Duty Cooling[^w]*",
            r"w\/\s*Standard Duty Cooling[^w]*",
            r"w\/\s*\d+\s*Plate[^w]*",
            r"w\/\s*Plate\s+Type[^w]*",
            r"w\/\s*Built-In Oil Cooler[^w]*",
            r"OE\s+\d+mm[^w]*",
            r"\d+%\s+(?:Stronger|Thicker)[^w]*",
            r"High-Efficiency[^w]*",
            r"B-Tube Technology[^w]*",
            r"Includes\s+[^w]+",
            r"w\/\s*\d+\s+Speed",
            r"w\/\s*\d+\s+Plate",
        ]

        for pattern in product_spec_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove any trailing "w/" or "w/o" with nothing after
        cleaned = re.sub(r"\s*w\/o?\s*$", "", cleaned)

        # Clean up multiple spaces and trim
        return re.sub(r"\s+", " ", cleaned).strip()

    def _extract_engine_qualifier(self, container: Tag) -> str | None:
        """Extract engine qualifier from part container (DEPRECATED).

        This method is deprecated. Use _extract_vehicle_qualifiers() instead.
        Kept for backward compatibility.

        Args:
            container: BeautifulSoup Tag for .row.app element

        Returns:
            Engine qualifier string or None
        """
        qualifiers = self._extract_vehicle_qualifiers(container)
        components = []

        if qualifiers["engine"]:
            components.append(qualifiers["engine"])

        if qualifiers["qualifiers"]:
            components.extend(qualifiers["qualifiers"])

        if components:
            return " ".join(components)

        return None

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

    def _extract_images(self, soup: BeautifulSoup) -> list[dict[str, Any]]:  # noqa: ARG002
        """Extract product images from listing pages.

        Args:
            soup: Parsed HTML

        Returns:
            Empty list - images are extracted from detail page gallery to avoid duplicates

        Note:
            Images are NOT extracted from listing pages to prevent duplicates.
            Full gallery images (including primary) are scraped from detail pages
            via _extract_gallery_images() where we get all images in proper quality.
            The soup parameter is unused but required for consistent interface.
        """
        # Return empty - images extracted from detail page gallery only
        logger.debug("images_skipped", reason="extracted_from_detail_page_gallery")
        return []

    def _extract_gallery_images(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract large product images from detail page gallery.

        Extracts large images only from S3 bucket URLs, filtering for catalog images
        and excluding thumbnails.

        Args:
            soup: Parsed HTML from detail page

        Returns:
            List of dicts with url, alt_text, is_primary (large images only)

        Example:
            >>> images = parser._extract_gallery_images(soup)
            >>> images[0]
            {
                'url': 'https://illumaware-digital-assets.s3...large_3411_1_wm.jpg',
                'alt_text': 'High Performance Radiator',
                'is_primary': True
            }
        """
        images = []

        # Find all S3 image URLs from detail page
        all_imgs = soup.find_all("img")
        for img in all_imgs:
            src_val = img.get("src", "")
            src = src_val if isinstance(src_val, str) else ""

            # Filter for CSF catalog images only (S3 bucket, large images only)
            if "illumaware-digital-assets.s3" in src and "catalog196" in src and "/large/" in src:
                images.append(
                    {
                        "url": src,
                        "alt_text": img.get("alt", ""),
                        "is_primary": False,  # Will be set to True for first image
                    }
                )

        # Mark first image as primary (featured image)
        if images:
            images[0]["is_primary"] = True

        logger.debug("gallery_images_extracted", count=len(images))
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
        interchange data, gallery images, and optional full product descriptions.

        Args:
            soup: Parsed HTML from detail page
            sku: Part SKU (for logging and validation)

        Returns:
            Dict with complete part data including:
            - full_description: str | None
            - specifications: dict[str, Any] (normalized, ~22 specs)
            - tech_notes: str | None
            - interchange_data: list[dict[str, str]]
            - additional_images: list[dict] (gallery images)

        Note:
            Detail pages have complex table structures requiring normalization.
            See RECONNAISSANCE.md for table format variations and strategy.
        """
        logger.info("extracting_detail_page_data", sku=sku)

        specifications = self._extract_detail_specifications(soup)
        tech_notes = self._extract_tech_notes(specifications)
        interchange_data = self._extract_interchange_data(soup)
        full_description = self._extract_full_description(soup)
        additional_images = self._extract_gallery_images(soup)

        data: dict[str, Any] = {
            "sku": sku,
            "full_description": full_description,
            "specifications": specifications,
            "tech_notes": tech_notes,
            "interchange_data": interchange_data,
            "additional_images": additional_images,
        }

        logger.info(
            "detail_page_extracted",
            sku=sku,
            has_description=bool(full_description),
            spec_count=len(specifications),
            has_tech_notes=bool(tech_notes),
            interchange_count=len(interchange_data),
            image_count=len(additional_images),
        )

        return data

    @staticmethod
    def _extract_marketing_html(col6: Tag) -> str | None:
        """Extract marketing copy from bare text nodes in a container."""
        chunks: list[str] = []
        for child in col6.children:
            if isinstance(child, NavigableString) and not isinstance(child, Tag):  # type: ignore[unreachable]
                text = str(child).strip()
                if len(text) > 10:  # noqa: PLR2004
                    chunks.append(text)

        if not chunks:
            return None

        full = " ".join(chunks)
        sentences = [s.strip() for s in full.split(";") if s.strip()]
        formatted = [s + "." if s and s[-1] not in ".!?" else s for s in sentences]
        return "<p>" + " ".join(formatted) + "</p>" if formatted else None

    @staticmethod
    def _extract_feature_list_html(col6: Tag) -> str | None:
        """Extract ``<ul>`` feature list from a container."""
        ul = col6.find("ul")
        if not ul or not isinstance(ul, Tag):
            return None

        items = [
            f"<li>{li.get_text(strip=True)}</li>"
            for li in ul.find_all("li")
            if li.get_text(strip=True)
        ]
        return "<ul>" + "".join(items) + "</ul>" if items else None

    def _extract_full_description(self, soup: BeautifulSoup) -> str | None:
        """Extract full part description from div.col-6 container.

        The detail page has a div.col-6 containing:
        - ``<h5>`` title text (e.g. "1 Row Plastic Tank Aluminum Core")
        - ``<p>`` category/subtitle (e.g. "Radiator")
        - Bare text node with marketing copy (semicolon-separated)
        - ``<ul>`` feature bullet list (not always present)

        Args:
            soup: Parsed HTML

        Returns:
            HTML-formatted description or None if not present
        """
        col6 = soup.find("div", class_="col-6")
        if not col6 or not isinstance(col6, Tag):
            return None

        parts: list[str] = []

        # Extract h5 title.
        h5 = col6.find("h5")
        if h5 and isinstance(h5, Tag):
            title = h5.get_text(strip=True)
            if title:
                parts.append(f"<h5>{title}</h5>")

        # Extract p (category/subtitle).
        p_tag = col6.find("p")
        if p_tag and isinstance(p_tag, Tag):
            subtitle = p_tag.get_text(strip=True)
            if subtitle:
                parts.append(f"<p><strong>{subtitle}</strong></p>")

        marketing = self._extract_marketing_html(col6)
        if marketing:
            parts.append(marketing)

        features = self._extract_feature_list_html(col6)
        if features:
            parts.append(features)

        if not parts:
            return None

        result = "\n".join(parts)
        if result.strip():
            logger.debug("extracted_full_description", length=len(result))
            return result
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
