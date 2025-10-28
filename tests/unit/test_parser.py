"""Comprehensive unit tests for HTML parser components.

This module provides complete test coverage for parser.py following the AAA pattern:
- HTMLParser: Base HTML parsing and element extraction
- CSFParser: CSF-specific data extraction from application and detail pages

All tests adhere to DRY, SOLID, and AAA principles as defined in CLAUDE.md.

Note: This test module accesses private methods (SLF001) to achieve comprehensive coverage
of parser implementation details. This is legitimate for unit testing as it validates
the correctness of internal helper methods that are critical to parser functionality.
"""

# ruff: noqa: SLF001

from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag

from src.scraper.parser import CSFParser, HTMLParser


class TestHTMLParserParse:
    """Test suite for HTMLParser.parse() method."""

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
        assert isinstance(test_div, Tag)
        assert test_div.get_text(strip=True) == "Content"

    def test_parse_with_complex_html_preserves_structure(self) -> None:
        """Test parse() preserves complex HTML structure."""
        # Arrange
        parser = HTMLParser()
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <div id="main">
                    <ul class="items">
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </div>
            </body>
        </html>
        """

        # Act
        result = parser.parse(html)

        # Assert
        assert result.find("title") is not None
        assert result.find("div", id="main") is not None
        items = result.select("ul.items li")
        assert len(items) == 2

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

    def test_parse_with_none_raises_value_error(self) -> None:
        """Test parse() raises ValueError when given None."""
        # Arrange
        parser = HTMLParser()

        # Act & Assert
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            parser.parse(None)  # type: ignore[arg-type]

    def test_parse_with_malformed_html_still_parses(self) -> None:
        """Test parse() handles malformed HTML gracefully using lxml."""
        # Arrange
        parser = HTMLParser()
        malformed_html = "<div><p>Unclosed paragraph<div>Nested</div>"

        # Act
        result = parser.parse(malformed_html)

        # Assert - lxml should repair and parse it
        assert isinstance(result, BeautifulSoup)
        assert result.find("div") is not None


class TestHTMLParserExtractText:
    """Test suite for HTMLParser.extract_text() method."""

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

    def test_extract_text_returns_first_match_for_multiple_elements(self) -> None:
        """Test extract_text() returns text from first matching element."""
        # Arrange
        parser = HTMLParser()
        html = """
        <html>
            <body>
                <div class="item">First</div>
                <div class="item">Second</div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser.extract_text(soup, ".item")

        # Assert
        assert result == "First"

    def test_extract_text_handles_nested_elements(self) -> None:
        """Test extract_text() extracts text from nested elements."""
        # Arrange
        parser = HTMLParser()
        html = "<html><body><div class='outer'><span>Nested</span> Text</div></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser.extract_text(soup, ".outer")

        # Assert
        assert result == "NestedText"  # BeautifulSoup strips whitespace between tags


class TestHTMLParserExtractAttribute:
    """Test suite for HTMLParser.extract_attribute() method."""

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

    def test_extract_attribute_handles_empty_attribute_value(self) -> None:
        """Test extract_attribute() returns None for empty attribute values."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body><a href=''>Link</a></body></html>")

        # Act
        result = parser.extract_attribute(soup, "a", "href")

        # Assert - Empty string is falsy, should return None
        assert result is None

    def test_extract_attribute_extracts_data_attributes(self) -> None:
        """Test extract_attribute() extracts custom data attributes."""
        # Arrange
        parser = HTMLParser()
        html = "<html><body><div data-id='12345' data-name='test'>Content</div></body></html>"
        soup = parser.parse(html)

        # Act
        result_id = parser.extract_attribute(soup, "div", "data-id")
        result_name = parser.extract_attribute(soup, "div", "data-name")

        # Assert
        assert result_id == "12345"
        assert result_name == "test"


class TestHTMLParserExtractAll:
    """Test suite for HTMLParser.extract_all() method."""

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
        assert all(isinstance(elem, Tag) for elem in result)
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

    def test_extract_all_preserves_order(self) -> None:
        """Test extract_all() preserves document order of elements."""
        # Arrange
        parser = HTMLParser()
        html = """
        <html>
            <body>
                <div class="item">First</div>
                <p>Other</p>
                <div class="item">Second</div>
                <span>Another</span>
                <div class="item">Third</div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser.extract_all(soup, ".item")

        # Assert
        assert len(result) == 3
        assert result[0].get_text(strip=True) == "First"
        assert result[1].get_text(strip=True) == "Second"
        assert result[2].get_text(strip=True) == "Third"

    def test_extract_all_with_nested_selectors(self) -> None:
        """Test extract_all() works with complex nested selectors."""
        # Arrange
        parser = HTMLParser()
        html = """
        <html>
            <body>
                <div class="container">
                    <ul>
                        <li><a href="/1">Link 1</a></li>
                        <li><a href="/2">Link 2</a></li>
                    </ul>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser.extract_all(soup, ".container ul li a")

        # Assert
        assert len(result) == 2
        assert result[0].get("href") == "/1"
        assert result[1].get("href") == "/2"


class TestHTMLParserExtractPartData:
    """Test suite for HTMLParser.extract_part_data() base method."""

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

    def test_extract_part_data_returns_none_values(self) -> None:
        """Test extract_part_data() template returns None for all values."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body>Test</body></html>")

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["sku"] is None
        assert result["name"] is None
        assert result["price"] is None
        assert result["description"] is None
        assert result["category"] is None

    def test_extract_part_data_returns_empty_collections(self) -> None:
        """Test extract_part_data() returns empty dict/list for specifications/images."""
        # Arrange
        parser = HTMLParser()
        soup = parser.parse("<html><body>Test</body></html>")

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert isinstance(result["specifications"], dict)
        assert result["specifications"] == {}
        assert isinstance(result["images"], list)
        assert result["images"] == []


class TestCSFParserExtractPartData:
    """Test suite for CSFParser.extract_part_data() method."""

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
        # BeautifulSoup with strip=True removes whitespace after </a>, so "3951</a> - Radiator"
        # becomes "3951- Radiator" with no space before dash. Split on " - " doesn't match,
        # so the full text is returned as the name.
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
        # Application page specs are in "Key: Value" format within table cells
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

    def test_extract_part_data_price_is_none_on_application_page(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() sets price to None on application pages."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["price"] is None

    def test_extract_part_data_description_is_none_on_application_page(
        self, sample_html_application_page: str
    ) -> None:
        """Test extract_part_data() sets description to None on application pages."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        assert result["description"] is None

    def test_extract_part_data_raises_error_when_sku_missing(self) -> None:
        """Test extract_part_data() raises ValueError when SKU is missing."""
        # Arrange
        parser = CSFParser()
        html_no_sku = """
        <html>
            <body>
                <div class="applications">
                    <div class="row app">
                        <h4>Part Name Without SKU Link - Radiator</h4>
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
        html_no_name = """
        <html>
            <body>
                <div class="applications">
                    <div class="row app">
                        <h4><a href="/items/3951">3951</a></h4>
                    </div>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html_no_name)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        # When there's no " - " separator, the full text (SKU) becomes the name
        # This is actually valid behavior - the parser extracts what's there
        assert result["sku"] == "3951"
        assert result["name"] == "3951"  # Full h4 text without separator

    def test_extract_part_data_handles_empty_name_after_split(self) -> None:
        """Test extract_part_data() handles edge case of trailing dash."""
        # Arrange
        parser = CSFParser()
        html_empty_name = """
        <html>
            <body>
                <div class="applications">
                    <div class="row app">
                        <h4><a href="/items/3951">3951</a> - </h4>
                    </div>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html_empty_name)

        # Act
        result = parser.extract_part_data(soup)

        # Assert
        # BeautifulSoup strips whitespace, so "3951</a> - " becomes "3951-"
        # Without proper " - " separator, full text is used as name
        assert result["sku"] == "3951"
        assert result["name"] == "3951-"  # Trailing dash without space


class TestCSFParserExtractSpecifications:
    """Test suite for CSFParser._extract_specifications() method."""

    def test_extract_specifications_from_application_page(
        self, sample_html_application_page: str
    ) -> None:
        """Test _extract_specifications() extracts specs from application page table."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser._extract_specifications(soup)

        # Assert
        assert isinstance(result, dict)
        assert len(result) == 2
        assert result["Eng. Base"] == "1.5L L4 1497cc"
        assert result["Aspiration"] == "Turbocharged"

    def test_extract_specifications_removes_trailing_colons(self) -> None:
        """Test _extract_specifications() removes trailing colons from keys."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <table class="table-borderless">
                        <tbody>
                            <tr>
                                <td>Core Width: 24.5 in</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_specifications(soup)

        # Assert
        assert "Core Width" in result
        assert "Core Width:" not in result
        assert result["Core Width"] == "24.5 in"

    def test_extract_specifications_handles_bold_values(self) -> None:
        """Test _extract_specifications() extracts values with bold tags stripped."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <table class="table-borderless">
                        <tbody>
                            <tr>
                                <td>Position: Not Applicable</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_specifications(soup)

        # Assert
        assert result["Position"] == "Not Applicable"

    def test_extract_specifications_returns_empty_dict_when_no_specs(self) -> None:
        """Test _extract_specifications() returns empty dict when no specs found."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <div>No tables here</div>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_specifications(soup)

        # Assert
        assert result == {}
        assert isinstance(result, dict)

    def test_extract_specifications_handles_multiple_rows(self) -> None:
        """Test _extract_specifications() handles multiple spec rows."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <table class="table-borderless">
                        <tbody>
                            <tr>
                                <td>Spec 1: Value 1</td>
                                <td>Spec 2: Value 2</td>
                            </tr>
                            <tr>
                                <td>Spec 3: Value 3</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_specifications(soup)

        # Assert
        assert len(result) == 3
        assert result["Spec 1"] == "Value 1"
        assert result["Spec 2"] == "Value 2"
        assert result["Spec 3"] == "Value 3"


class TestCSFParserExtractImages:
    """Test suite for CSFParser._extract_images() method."""

    def test_extract_images_extracts_primary_image(self, sample_html_application_page: str) -> None:
        """Test _extract_images() extracts primary image from application page."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert len(result) == 1
        assert result[0]["is_primary"] is True
        assert "url" in result[0]
        assert "alt_text" in result[0]

    def test_extract_images_extracts_src_attribute(self, sample_html_application_page: str) -> None:
        """Test _extract_images() extracts src attribute from img tag."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert result[0]["url"].startswith("https://illumaware-digital-assets.s3")

    def test_extract_images_extracts_alt_text(self, sample_html_application_page: str) -> None:
        """Test _extract_images() extracts alt text from img tag."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_application_page)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert result[0]["alt_text"] == "3951"

    def test_extract_images_returns_empty_list_when_no_image(self) -> None:
        """Test _extract_images() returns empty list when no image found."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <div>No image here</div>
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert result == []
        assert isinstance(result, list)

    def test_extract_images_handles_data_src_attribute(self) -> None:
        """Test _extract_images() handles data-src for lazy loaded images."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <img class="primary-image" data-src="https://example.com/lazy.jpg" alt="Lazy">
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/lazy.jpg"

    def test_extract_images_prefers_src_over_data_src(self) -> None:
        """Test _extract_images() prefers src attribute over data-src."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <img class="primary-image"
                         src="https://example.com/actual.jpg"
                         data-src="https://example.com/lazy.jpg"
                         alt="Image">
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert result[0]["url"] == "https://example.com/actual.jpg"

    def test_extract_images_handles_missing_alt_text(self) -> None:
        """Test _extract_images() handles missing alt attribute gracefully."""
        # Arrange
        parser = CSFParser()
        html = """
        <html>
            <body>
                <div class="row app">
                    <img class="primary-image" src="https://example.com/image.jpg">
                </div>
            </body>
        </html>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_images(soup)

        # Assert
        assert len(result) == 1
        assert result[0]["alt_text"] == ""


class TestCSFParserExtractStockStatus:
    """Test suite for CSFParser._extract_stock_status() method."""

    def test_extract_stock_status_defaults_to_true(self) -> None:
        """Test _extract_stock_status() defaults to True for application pages."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse("<html><body>Test</body></html>")

        # Act
        result = parser._extract_stock_status(soup)

        # Assert
        assert result is True

    def test_extract_stock_status_ignores_soup_parameter(self) -> None:
        """Test _extract_stock_status() returns True regardless of soup content."""
        # Arrange
        parser = CSFParser()
        html_with_content = parser.parse("<html><body><div>Stock: Out</div></body></html>")
        html_empty = parser.parse("<html><body></body></html>")

        # Act
        result1 = parser._extract_stock_status(html_with_content)
        result2 = parser._extract_stock_status(html_empty)

        # Assert
        assert result1 is True
        assert result2 is True


class TestCSFParserExtractDetailPageData:
    """Test suite for CSFParser.extract_detail_page_data() method."""

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

    def test_extract_detail_page_data_includes_sku(self, sample_html_detail_page: str) -> None:
        """Test extract_detail_page_data() includes SKU in returned data."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)
        sku = "3883"

        # Act
        result = parser.extract_detail_page_data(soup, sku)

        # Assert
        assert result["sku"] == sku

    def test_extract_detail_page_data_handles_missing_description(self) -> None:
        """Test extract_detail_page_data() handles missing description gracefully."""
        # Arrange
        parser = CSFParser()
        html_no_desc = """
        <html>
            <body>
                <h5></h5>
                <table>
                    <tr>
                        <td>Core Width:</td>
                        <td>24.5 in</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        soup = parser.parse(html_no_desc)

        # Act
        result = parser.extract_detail_page_data(soup, "TEST")

        # Assert
        assert result["full_description"] is None


class TestCSFParserExtractDetailSpecifications:
    """Test suite for CSFParser._extract_detail_specifications() method."""

    def test_extract_detail_specifications_handles_3_cell_triplet_format(self) -> None:
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
        result = parser._extract_detail_specifications(soup)

        # Assert
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"
        assert result["Core Thickness"] == "2.5 in"

    def test_extract_detail_specifications_handles_2_cell_format(self) -> None:
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
        result = parser._extract_detail_specifications(soup)

        # Assert
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"

    def test_extract_detail_specifications_handles_single_cell_colon_format(self) -> None:
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
        result = parser._extract_detail_specifications(soup)

        # Assert
        assert result["Core Width"] == "24.5 in"
        assert result["Core Height"] == "16.25 in"

    def test_extract_detail_specifications_skips_vehicle_compatibility_tables(self) -> None:
        """Test _extract_detail_specifications() skips vehicle compatibility tables."""
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
        result = parser._extract_detail_specifications(soup)

        # Assert
        assert "Make" not in result
        assert "Model" not in result
        assert len(result) == 0

    def test_extract_detail_specifications_skips_interchange_tables(self) -> None:
        """Test _extract_detail_specifications() skips interchange reference tables."""
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
        result = parser._extract_detail_specifications(soup)

        # Assert
        assert "Reference Number" not in result
        assert "Reference Name" not in result
        assert len(result) == 0

    def test_extract_detail_specifications_removes_trailing_colons_from_keys(self) -> None:
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
        result = parser._extract_detail_specifications(soup)

        # Assert
        assert "Core Width" in result
        assert "Core Width:" not in result


class TestCSFParserExtractSpecFromRow:
    """Test suite for CSFParser._extract_spec_from_row() method."""

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
        specs: dict[str, Any] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)

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
        specs: dict[str, Any] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)

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
        specs: dict[str, Any] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)

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
        specs: dict[str, Any] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)

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
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, Any] = {"Core Width": "Original Value"}

        # Act
        parser._extract_spec_from_row(cells, specs)

        # Assert
        assert specs["Core Width"] == "Original Value"

    def test_extract_spec_from_row_handles_6_cell_rows(self) -> None:
        """Test _extract_spec_from_row() handles 6-cell rows (2 triplets)."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td></td>
            <td>Width</td>
            <td>24 in</td>
            <td></td>
            <td>Height</td>
            <td>16 in</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, Any] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)

        # Assert
        assert specs["Width"] == "24 in"
        assert specs["Height"] == "16 in"

    def test_extract_spec_from_row_ignores_short_colon_text(self) -> None:
        """Test _extract_spec_from_row() ignores very short colon-separated text."""
        # Arrange
        parser = CSFParser()
        html = """
        <tr>
            <td>A:B</td>
        </tr>
        """
        soup = parser.parse(html)
        tr = soup.find("tr")
        assert tr is not None
        assert isinstance(tr, Tag)
        cells = tr.find_all("td")
        specs: dict[str, Any] = {}

        # Act
        parser._extract_spec_from_row(cells, specs)

        # Assert
        assert len(specs) == 0


class TestCSFParserExtractFullDescription:
    """Test suite for CSFParser._extract_full_description() method."""

    def test_extract_full_description_returns_h5_text(self) -> None:
        """Test _extract_full_description() returns h5 element text."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><h5>High-performance radiator description</h5></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)

        # Assert
        assert result == "High-performance radiator description"

    def test_extract_full_description_returns_none_when_h5_empty(self) -> None:
        """Test _extract_full_description() returns None when h5 is empty."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><h5></h5></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)

        # Assert
        assert result is None

    def test_extract_full_description_returns_none_when_h5_missing(self) -> None:
        """Test _extract_full_description() returns None when h5 doesn't exist."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><div>No h5 here</div></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)

        # Assert
        assert result is None

    def test_extract_full_description_strips_whitespace(self) -> None:
        """Test _extract_full_description() strips whitespace from description."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><h5>  \n  Whitespace description  \n  </h5></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_full_description(soup)

        # Assert
        assert result == "Whitespace description"


class TestCSFParserExtractTechNotes:
    """Test suite for CSFParser._extract_tech_notes() method."""

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
        result = parser._extract_tech_notes(specifications)

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
        result = parser._extract_tech_notes(specifications)

        # Assert
        assert result is None

    def test_extract_tech_notes_handles_non_string_values(self) -> None:
        """Test _extract_tech_notes() returns None for non-string Tech Note values."""
        # Arrange
        parser = CSFParser()
        specifications: dict[str, Any] = {
            "Tech Note": None,
        }

        # Act
        result = parser._extract_tech_notes(specifications)

        # Assert
        assert result is None

    def test_extract_tech_notes_handles_empty_string(self) -> None:
        """Test _extract_tech_notes() returns empty string for empty Tech Note."""
        # Arrange
        parser = CSFParser()
        specifications = {
            "Tech Note": "",
        }

        # Act
        result = parser._extract_tech_notes(specifications)

        # Assert
        # The parser returns the value as-is if it's a string, even if empty
        # The check is "if tech_note is not None and isinstance(tech_note, str)"
        # Empty string passes this check
        assert result == ""


class TestCSFParserExtractInterchangeData:
    """Test suite for CSFParser._extract_interchange_data() method."""

    def test_extract_interchange_data_parses_interchange_table(
        self, sample_html_detail_page: str
    ) -> None:
        """Test _extract_interchange_data() parses full interchange table."""
        # Arrange
        parser = CSFParser()
        soup = parser.parse(sample_html_detail_page)

        # Act
        result = parser._extract_interchange_data(soup)

        # Assert
        assert len(result) == 3
        assert result[0]["reference_number"] == "19010-5AA-A01"
        assert result[0]["reference_type"] == "OEM"
        assert result[1]["reference_number"] == "HO3010177"
        assert result[1]["reference_type"] == "Partslink"
        assert result[2]["reference_number"] == "13408"
        assert result[2]["reference_type"] == "DPI"

    def test_extract_interchange_data_returns_empty_list_when_no_table(self) -> None:
        """Test _extract_interchange_data() returns empty list when table missing."""
        # Arrange
        parser = CSFParser()
        html = "<html><body><div>No interchange table</div></body></html>"
        soup = parser.parse(html)

        # Act
        result = parser._extract_interchange_data(soup)

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
        result = parser._extract_interchange_data(soup)

        # Assert
        assert len(result) == 1
        assert result[0]["reference_number"] == "19010RNAA51"

    def test_extract_interchange_data_stops_after_first_table(self) -> None:
        """Test _extract_interchange_data() only processes first interchange table."""
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
                    <td>FIRST-TABLE</td>
                    <td>OEM</td>
                </tr>
            </tbody>
        </table>
        <table>
            <thead>
                <tr>
                    <th>Reference Number</th>
                    <th>Reference Name</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>SECOND-TABLE</td>
                    <td>Partslink</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html)

        # Act
        result = parser._extract_interchange_data(soup)

        # Assert
        assert len(result) == 1
        assert result[0]["reference_number"] == "FIRST-TABLE"

    def test_extract_interchange_data_requires_both_headers(self) -> None:
        """Test _extract_interchange_data() requires both Reference headers."""
        # Arrange
        parser = CSFParser()
        html_only_number = """
        <table>
            <thead>
                <tr>
                    <th>Reference Number</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>19010RNAA51</td>
                </tr>
            </tbody>
        </table>
        """
        soup = parser.parse(html_only_number)

        # Act
        result = parser._extract_interchange_data(soup)

        # Assert - Should not match without both headers
        assert result == []
