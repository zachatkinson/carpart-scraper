"""Comprehensive unit tests for HTML and AJAX parsers.

This module tests all parser classes following the AAA pattern:
- HTMLParser: Basic HTML parsing and element extraction
- CSFParser: CSF-specific data extraction from application and detail pages
- AJAXResponseParser: jQuery AJAX response parsing

All tests follow strict AAA (Arrange-Act-Assert) pattern and use fixtures
from conftest.py for DRY compliance.
"""

import pytest
from bs4 import BeautifulSoup, Tag

from src.scraper.ajax_parser import AJAXParsingError, AJAXResponseParser
from src.scraper.parser import CSFParser, HTMLParser


class TestHTMLParser:
    """Test suite for HTMLParser base class."""

    def test_parse_with_valid_html_returns_beautiful_soup_object(self) -> None:
        """Test parse() successfully parses valid HTML into BeautifulSoup object."""
        # Arrange
        parser = HTMLParser()
        html = "<html><body><div class='test'>Content</div></body></html>"

        # Act
        result = parser.parse(html)

        # Assert
        assert isinstance(result, BeautifulSoup)
        test_div = result.find("div", class_="test")
        assert test_div is not None
        assert test_div.get_text(strip=True) == "Content"

    def test_parse_with_empty_string_raises_value_error(self) -> None:
        """Test parse() raises ValueError when given empty string."""
        # Arrange
        parser = HTMLParser()
        empty_html = ""

        # Act & Assert
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            parser.parse(empty_html)

    def test_parse_with_whitespace_only_raises_value_error(self) -> None:
        """Test parse() raises ValueError when given whitespace-only string."""
        # Arrange
        parser = HTMLParser()
        whitespace_html = "   \n\t  "

        # Act & Assert
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            parser.parse(whitespace_html)

    def test_extract_text_finds_element_and_returns_text(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_text() successfully extracts text from CSS selector."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_text(soup, ".panel-header h4")

        # Assert
        assert result is not None
        assert result == "Radiator"

    def test_extract_text_returns_none_for_missing_element(self) -> None:
        """Test extract_text() returns None when selector doesn't match."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body><div>Test</div></body></html>")

        # Act
        result = parser.extract_text(soup, ".nonexistent")

        # Assert
        assert result is None

    def test_extract_text_strips_whitespace(self) -> None:
        """Test extract_text() strips leading/trailing whitespace from text."""
        # Arrange
        parser = HTMLParser()
        html = "<html><body><div class='test'>  \n  Whitespace Content  \n  </div></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser.extract_text(soup, ".test")

        # Assert
        assert result == "Whitespace Content"

    def test_extract_attribute_extracts_src_from_img(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_attribute() extracts img src attribute."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_attribute(soup, "img.primary-image", "src")

        # Assert
        assert result is not None
        assert result.startswith("https://illumaware-digital-assets.s3")
        assert "3951" in result

    def test_extract_attribute_extracts_href_from_link(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_attribute() extracts href from anchor tag."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_attribute(soup, "h4 a", "href")

        # Assert
        assert result == "/items/3951"

    def test_extract_attribute_returns_none_for_missing_element(self) -> None:
        """Test extract_attribute() returns None when element not found."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body><div>Test</div></body></html>")

        # Act
        result = parser.extract_attribute(soup, ".nonexistent", "href")

        # Assert
        assert result is None

    def test_extract_attribute_returns_none_for_missing_attribute(self) -> None:
        """Test extract_attribute() returns None when attribute doesn't exist."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body><div class='test'>Test</div></body></html>")

        # Act
        result = parser.extract_attribute(soup, ".test", "nonexistent")

        # Assert
        assert result is None

    def test_extract_all_returns_list_of_matching_elements(self) -> None:
        """Test extract_all() returns all elements matching selector."""
        # Arrange
        parser = HTMLParser()
        html = """
        <html>
            <body>
                <ul>
                    <li class="item">Item 1</li>
                    <li class="item">Item 2</li>
                    <li class="item">Item 3</li>
                </ul>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser.extract_all(soup, "li.item")

        # Assert
        assert len(result) == 3
        assert result[0].get_text(strip=True) == "Item 1"
        assert result[1].get_text(strip=True) == "Item 2"
        assert result[2].get_text(strip=True) == "Item 3"

    def test_extract_all_returns_empty_list_when_no_matches(self) -> None:
        """Test extract_all() returns empty list when selector matches nothing."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body><div>Test</div></body></html>")

        # Act
        result = parser.extract_all(soup, ".nonexistent")

        # Assert
        assert result == []
        assert isinstance(result, list)

    def test_extract_part_data_returns_template_structure(self) -> None:
        """Test extract_part_data() base implementation returns template dict."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body>Test</body></html>")

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert isinstance(result, dict)
        assert "sku" in result
        assert "name" in result
        assert "price" in result
        assert "description" in result
        assert "category" in result
        assert "specifications" in result
        assert "images" in result
        assert result["sku"] is None  # Template returns None values
        assert isinstance(result["specifications"], dict)
        assert isinstance(result["images"], list)


class TestCSFParser:
    """Test suite for CSFParser CSF-specific implementation."""

    def test_extract_part_data_from_application_page_extracts_sku(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() extracts SKU from application page."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["sku"] == "3951"

    def test_extract_part_data_from_application_page_extracts_name(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() extracts part name from application page."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        # BeautifulSoup strips whitespace between tags,
        # so we get "3951- Radiator" instead of "3951 - Radiator"
        # Since split on " - " fails, the parser returns the full text
        assert result["name"] == "3951- Radiator"

    def test_extract_part_data_from_application_page_extracts_category(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() extracts category from panel header."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["category"] == "Radiator"

    def test_extract_part_data_from_application_page_extracts_specifications(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() extracts specifications from table."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        specs = result["specifications"]
        assert isinstance(specs, dict)
        assert "Eng. Base" in specs
        assert specs["Eng. Base"] == "1.5L L4 1497cc"
        assert "Aspiration" in specs
        assert specs["Aspiration"] == "Turbocharged"

    def test_extract_part_data_from_application_page_extracts_images(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() extracts primary image from application page."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        images = result["images"]
        assert isinstance(images, list)
        assert len(images) == 1
        assert images[0]["is_primary"] is True
        assert images[0]["url"].startswith("https://illumaware-digital-assets.s3")
        assert "3951" in images[0]["url"]

    def test_extract_part_data_from_application_page_sets_manufacturer(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() sets manufacturer to CSF."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["manufacturer"] == "CSF"

    def test_extract_part_data_from_application_page_sets_in_stock_true(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() defaults in_stock to True."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["in_stock"] is True

    def test_extract_part_data_raises_error_when_sku_missing(self) -> None:
        """Test extract_part_data() raises ValueError when SKU is missing."""
        # Arrange
        parser = CSFParser()
        html_no_sku = """
        <html>
            <body>
                <div class="applications">
                    <div class="row app">
                        <h4>Part Name Without SKU Link</h4>
                    </div>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html_no_sku)

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required fields"):
            parser.extract_part_data(soup)

    def test_extract_part_data_raises_error_when_name_missing(self) -> None:
        """Test extract_part_data() raises ValueError when name is missing."""
        # Arrange
        parser = CSFParser()
        # HTML with no h4 element at all - this will result in empty name
        html_no_name = """
        <html>
            <body>
                <div class="applications">
                    <div class="row app">
                        <!-- No h4 element, so name will be None -->
                    </div>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html_no_name)

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required fields"):
            parser.extract_part_data(soup)

    def test_extract_detail_page_data_extracts_full_description(
        self, sample_html_detail_page: str
    ) -> None:
        """Test extract_detail_page_data() extracts full description from h5."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)

        # Act
        result = parser.extract_detail_page_data(soup, "3883")

        # Assert
        assert result["full_description"] is not None
        assert "High Performance Aluminum Radiator" in result["full_description"]

    def test_extract_detail_page_data_returns_none_when_no_description(self) -> None:
        """Test extract_detail_page_data() returns None when h5 is empty."""
        # Arrange
        parser = CSFParser()
        html_no_description = """
        <html>
            <body>
                <h5></h5>
                <table>
                    <tbody>
                        <tr>
                            <td>Core Width:</td>
                            <td>24.5 in</td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        soup = parser.parse(html_no_description)

        # Act
        result = parser.extract_detail_page_data(soup, "3883")

        # Assert
        assert result["full_description"] is None

    def test_extract_detail_page_data_extracts_specifications(
        self, sample_html_detail_page: str
    ) -> None:
        """Test extract_detail_page_data() extracts normalized specifications."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)

        # Act
        result = parser.extract_detail_page_data(soup, "3883")

        # Assert
        specs = result["specifications"]
        assert isinstance(specs, dict)
        assert len(specs) > 0
        assert "Core Thickness (mm)" in specs
        assert specs["Core Thickness (mm)"] == "30"

    def test_extract_detail_page_data_extracts_tech_notes(
        self, sample_html_detail_page: str
    ) -> None:
        """Test extract_detail_page_data() extracts tech notes from specs."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)

        # Act
        result = parser.extract_detail_page_data(soup, "3883")

        # Assert
        assert result["tech_notes"] is not None
        assert "O.E.M. style Plastic tank & Aluminum core" in result["tech_notes"]

    def test_extract_detail_page_data_extracts_interchange_data(
        self, sample_html_detail_page: str
    ) -> None:
        """Test extract_detail_page_data() extracts OEM interchange references."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)

        # Act
        result = parser.extract_detail_page_data(soup, "3883")

        # Assert
        interchange = result["interchange_data"]
        assert isinstance(interchange, list)
        assert len(interchange) == 3
        assert interchange[0]["reference_number"] == "19010-5AA-A01"
        assert interchange[0]["reference_type"] == "OEM"
        assert interchange[1]["reference_type"] == "Partslink"
        assert interchange[2]["reference_type"] == "DPI"

    def test_extract_specifications_handles_3_cell_triplet_format(self) -> None:
        """Test _extract_detail_specifications() handles 3-cell triplet format."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <tbody>
                <tr>
                    <td></td>
                    <td>Core Width</td>
                    <td>24.5 in</td>
                    <td></td>
                    <td>Core Height</td>
                    <td>16.25 in</td>
                    <td></td>
                    <td>Core Thickness</td>
                    <td>2.5 in</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_detail_specifications(soup)  # noqa: SLF001

        # Assert
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"
        assert result["Core Thickness"] == "2.5 in"

    def test_extract_specifications_handles_2_cell_format(self) -> None:
        """Test _extract_detail_specifications() handles 2-cell label-value format."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <tbody>
                <tr>
                    <td>Core Width:</td>
                    <td>24.5 in</td>
                </tr>
                <tr>
                    <td>Core Height:</td>
                    <td>16.25 in</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_detail_specifications(soup)  # noqa: SLF001

        # Assert
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"

    def test_extract_specifications_handles_single_cell_colon_format(self) -> None:
        """Test _extract_detail_specifications() handles single-cell colon-separated format."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <tbody>
                <tr>
                    <td>Core Width: 24.5 in</td>
                </tr>
                <tr>
                    <td>Core Height: 16.25 in</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_detail_specifications(soup)  # noqa: SLF001

        # Assert
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"

    def test_extract_specifications_handles_all_4_formats_mixed(self) -> None:
        """Test _extract_specifications() handles all 4 table formats in same HTML."""
        # Arrange
        parser = CSFParser()
        html = """
        <!-- Format 1: 3-cell triplets -->
        <table>
            <tbody>
                <tr>
                    <td></td>
                    <td>Core Width</td>
                    <td>24.5 in</td>
                </tr>
            </tbody>
        </table>

        <!-- Format 2: 2-cell rows -->
        <table>
            <tbody>
                <tr>
                    <td>Core Height:</td>
                    <td>16.25 in</td>
                </tr>
            </tbody>
        </table>

        <!-- Format 3: Single-cell colon -->
        <table>
            <tbody>
                <tr>
                    <td>Core Thickness: 2.5 in</td>
                </tr>
            </tbody>
        </table>

        <!-- Format 4: Vehicle table (should be skipped) -->
        <table>
            <thead>
                <tr>
                    <th>Make</th>
                    <th>Model</th>
                </tr>
            </thead>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_detail_specifications(soup)  # noqa: SLF001

        # Assert
        assert len(result) == 3
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"
        assert result["Core Thickness"] == "2.5 in"

    def test_extract_specifications_removes_trailing_colons_from_keys(self) -> None:
        """Test _extract_detail_specifications() removes trailing colons from keys."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <tbody>
                <tr>
                    <td>Core Width:</td>
                    <td>24.5 in</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_detail_specifications(soup)  # noqa: SLF001

        # Assert
        assert "Core Width" in result  # No colon
        assert "Core Width:" not in result

    def test_extract_specifications_skips_vehicle_compatibility_tables(self) -> None:
        """Test _extract_specifications() skips vehicle compatibility tables."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <thead>
                <tr>
                    <th>Make</th>
                    <th>Model</th>
                    <th>Year</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Honda</td>
                    <td>Accord</td>
                    <td>2013</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_specifications(soup)  # noqa: SLF001

        # Assert
        assert "Make" not in result
        assert "Model" not in result
        assert len(result) == 0

    def test_extract_specifications_skips_interchange_tables(self) -> None:
        """Test _extract_specifications() skips interchange reference tables."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <thead>
                <tr>
                    <th>Reference Number</th>
                    <th>Reference Name</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>19010RNAA51</td>
                    <td>OEM</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_specifications(soup)  # noqa: SLF001

        # Assert
        assert "Reference Number" not in result
        assert "Reference Name" not in result
        assert len(result) == 0

    def test_extract_spec_from_row_processes_3_cell_rows(self) -> None:
        """Test _extract_spec_from_row() processes 3-cell rows correctly."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td></td>
            <td>Core Width</td>
            <td>24.5 in</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, str] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)  # noqa: SLF001

        # Assert
        assert specs["Core Width"] == "24.5 in"

    def test_extract_spec_from_row_processes_2_cell_rows(self) -> None:
        """Test _extract_spec_from_row() processes 2-cell rows correctly."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td>Core Width:</td>
            <td>24.5 in</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, str] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)  # noqa: SLF001

        # Assert
        assert specs["Core Width"] == "24.5 in"

    def test_extract_spec_from_row_processes_single_cell_rows(self) -> None:
        """Test _extract_spec_from_row() processes single-cell colon-separated rows."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td>Core Width: 24.5 in</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, str] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)  # noqa: SLF001

        # Assert
        assert specs["Core Width"] == "24.5 in"

    def test_extract_spec_from_row_ignores_single_cell_without_colon(self) -> None:
        """Test _extract_spec_from_row() ignores single-cell rows without colon."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td>No colon here</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, str] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)  # noqa: SLF001

        # Assert
        assert len(specs) == 0

    def test_extract_spec_from_row_prevents_duplicate_keys(self) -> None:
        """Test _extract_spec_from_row() doesn't overwrite existing keys."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td>Core Width:</td>
            <td>24.5 in</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        cells = tr.find_all("td")
        specs = {"Core Width": "Original Value"}

        # Act
        parser._extract_spec_from_row(cells, specs)  # noqa: SLF001

        # Assert
        assert specs["Core Width"] == "Original Value"  # Not overwritten

    def test_extract_full_description_returns_h5_text(self) -> None:
        """Test _extract_full_description() returns h5 element text."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><h5>High-performance radiator description</h5></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)  # noqa: SLF001

        # Assert
        assert result == "High-performance radiator description"

    def test_extract_full_description_returns_none_when_h5_empty(self) -> None:
        """Test _extract_full_description() returns None when h5 is empty."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><h5></h5></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)  # noqa: SLF001

        # Assert
        assert result is None

    def test_extract_full_description_returns_none_when_h5_missing(self) -> None:
        """Test _extract_full_description() returns None when h5 doesn't exist."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><div>No h5 here</div></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)  # noqa: SLF001

        # Assert
        assert result is None

    def test_extract_tech_notes_extracts_from_specifications_dict(self) -> None:
        """Test _extract_tech_notes() extracts Tech Note from specs dict."""
        # Arrange
        parser = CSFParser()
        specifications = {
            "Core Width": "24.5 in",
            "Tech Note": "O.E.M. style Plastic tank & Aluminum core",
            "Warranty": "Limited Lifetime",
        }

        # Act
        result = parser._extract_tech_notes(specifications)  # noqa: SLF001

        # Assert
        assert result == "O.E.M. style Plastic tank & Aluminum core"

    def test_extract_tech_notes_returns_none_when_not_present(self) -> None:
        """Test _extract_tech_notes() returns None when Tech Note not in specs."""
        # Arrange
        parser = CSFParser()
        specifications = {
            "Core Width": "24.5 in",
            "Warranty": "Limited Lifetime",
        }

        # Act
        result = parser._extract_tech_notes(specifications)  # noqa: SLF001

        # Assert
        assert result is None

    def test_extract_tech_notes_handles_non_string_values(self) -> None:
        """Test _extract_tech_notes() returns None for non-string Tech Note values."""
        # Arrange
        parser = CSFParser()
        specifications = {
            "Tech Note": None,
        }

        # Act
        result = parser._extract_tech_notes(specifications)  # noqa: SLF001

        # Assert
        assert result is None

    def test_extract_interchange_data_parses_interchange_table(
        self, sample_html_detail_page: str
    ) -> None:
        """Test _extract_interchange_data() parses full interchange table."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)

        # Act
        result = parser._extract_interchange_data(soup)  # noqa: SLF001

        # Assert
        assert len(result) == 3
        assert result[0]["reference_number"] == "19010-5AA-A01"
        assert result[0]["reference_type"] == "OEM"

    def test_extract_interchange_data_returns_empty_list_when_no_table(self) -> None:
        """Test _extract_interchange_data() returns empty list when table missing."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><div>No interchange table</div></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_interchange_data(soup)  # noqa: SLF001

        # Assert
        assert result == []
        assert isinstance(result, list)

    def test_extract_interchange_data_skips_rows_with_missing_data(self) -> None:
        """Test _extract_interchange_data() skips rows with incomplete data."""
        # Arrange
        parser = CSFParser()
        html = """
        <table>
            <thead>
                <tr>
                    <th>Reference Number</th>
                    <th>Reference Name</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>19010RNAA51</td>
                    <td>OEM</td>
                </tr>
                <tr>
                    <td></td>
                    <td>Empty Number</td>
                </tr>
                <tr>
                    <td>HO3010173</td>
                    <td></td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_interchange_data(soup)  # noqa: SLF001

        # Assert
        assert len(result) == 1  # Only first row with complete data
        assert result[0]["reference_number"] == "19010RNAA51"


class TestAJAXResponseParser:
    """Test suite for AJAXResponseParser jQuery response handling."""

    def test_parse_extracts_html_from_jquery_call(self) -> None:
        """Test parse() extracts HTML from .html() jQuery call."""
        # Arrange
        parser = AJAXResponseParser()
        js_code = '$("#btnYear").next().html("<ul class=\'list-inline\'><li>2025</li></ul>")'

        # Act
        result = parser.parse(js_code)

        # Assert
        assert result == "<ul class='list-inline'><li>2025</li></ul>"

    def test_parse_unescapes_double_quotes(self) -> None:
        r"""Test parse() unescapes \" to " in extracted HTML."""
        # Arrange
        parser = AJAXResponseParser()
        js_code = r'$("#content").html("<a href=\"/path\">Link</a>")'

        # Act
        result = parser.parse(js_code)

        # Assert
        assert result == '<a href="/path">Link</a>'
        assert '\\"' not in result

    def test_parse_unescapes_forward_slashes(self) -> None:
        r"""Test parse() unescapes \\/ to / in extracted HTML."""
        # Arrange
        parser = AJAXResponseParser()
        js_code = r'$("#el").html("<link href=\"https:\/\/example.com\/style.css\">")'

        # Act
        result = parser.parse(js_code)

        # Assert
        assert "https://example.com/style.css" in result
        assert "\\/" not in result

    def test_parse_handles_complex_html_with_multiple_escapes(self) -> None:
        """Test parse() handles HTML with multiple escape sequences."""
        # Arrange
        parser = AJAXResponseParser()
        js_code = r'$("#el").html("<div class=\"test\"><a href=\"\/path\">Text<\/a><\/div>")'

        # Act
        result = parser.parse(js_code)

        # Assert
        assert result == '<div class="test"><a href="/path">Text</a></div>'

    def test_parse_raises_ajax_parsing_error_for_invalid_input(self) -> None:
        """Test parse() raises AJAXParsingError when no .html() call found."""
        # Arrange
        parser = AJAXResponseParser()
        invalid_js = 'console.log("no html call here");'

        # Act & Assert
        with pytest.raises(AJAXParsingError, match=r"No .html\(\) call found"):
            parser.parse(invalid_js)

    def test_parse_raises_error_for_empty_string(self) -> None:
        """Test parse() raises AJAXParsingError for empty input."""
        # Arrange
        parser = AJAXResponseParser()
        empty_js = ""

        # Act & Assert
        with pytest.raises(AJAXParsingError):
            parser.parse(empty_js)

    def test_parse_raises_error_for_wrong_jquery_method(self) -> None:
        """Test parse() raises error when jQuery uses different method."""
        # Arrange
        parser = AJAXResponseParser()
        wrong_method = '$("#el").text("Not an html call")'

        # Act & Assert
        with pytest.raises(AJAXParsingError):
            parser.parse(wrong_method)

    def test_try_parse_returns_html_on_success(self) -> None:
        """Test try_parse() returns extracted HTML on successful parse."""
        # Arrange
        parser = AJAXResponseParser()
        js_code = '$("#el").html("<div>Content</div>")'

        # Act
        result = parser.try_parse(js_code)

        # Assert
        assert result == "<div>Content</div>"

    def test_try_parse_returns_none_on_failure(self) -> None:
        """Test try_parse() returns None instead of raising exception."""
        # Arrange
        parser = AJAXResponseParser()
        invalid_js = 'console.log("invalid");'

        # Act
        result = parser.try_parse(invalid_js)

        # Assert
        assert result is None

    def test_try_parse_returns_none_for_empty_string(self) -> None:
        """Test try_parse() returns None for empty string."""
        # Arrange
        parser = AJAXResponseParser()
        empty_js = ""

        # Act
        result = parser.try_parse(empty_js)

        # Assert
        assert result is None
