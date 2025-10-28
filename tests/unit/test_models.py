"""Unit tests for Pydantic models.

Tests all models in src.models package following AAA pattern.
Covers validation, data integrity, and edge cases.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from src.models.part import Part, PartImage
from src.models.vehicle import Vehicle, VehicleCompatibility


class TestPartImage:
    """Tests for PartImage model."""

    def test_valid_image_creation(self) -> None:
        """Test creating a valid PartImage instance."""
        # Arrange
        url = "https://example.com/image.jpg"
        alt_text = "Product image"
        is_primary = True

        # Act
        image = PartImage(url=url, alt_text=alt_text, is_primary=is_primary)

        # Assert
        assert image.url == url
        assert image.alt_text == alt_text
        assert image.is_primary is True

    def test_image_with_minimal_fields(self) -> None:
        """Test creating image with only required field."""
        # Arrange
        url = "https://example.com/image.jpg"

        # Act
        image = PartImage(url=url)

        # Assert
        assert image.url == url
        assert image.alt_text is None
        assert image.is_primary is False

    def test_image_url_required(self) -> None:
        """Test that URL is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PartImage()  # type: ignore[call-arg]

        assert "url" in str(exc_info.value)

    def test_image_url_cannot_be_empty(self) -> None:
        """Test that URL cannot be empty string."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            PartImage(url="")

        assert "url" in str(exc_info.value)

    def test_image_whitespace_stripped(self) -> None:
        """Test that whitespace is stripped from strings."""
        # Arrange
        url = "  https://example.com/image.jpg  "
        alt_text = "  Alt text  "

        # Act
        image = PartImage(url=url, alt_text=alt_text)

        # Assert
        assert image.url == url.strip()
        assert image.alt_text == alt_text.strip()

    def test_image_is_immutable(self) -> None:
        """Test that PartImage is frozen (immutable)."""
        # Arrange
        image = PartImage(url="https://example.com/image.jpg")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            image.url = "https://example.com/new.jpg"  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()


class TestPart:
    """Tests for Part model."""

    def test_valid_part_creation(self) -> None:
        """Test creating a valid Part instance."""
        # Arrange
        sku = "CSF-12345"
        name = "High Performance Radiator"
        price = Decimal("299.99")
        category = "Radiators"

        # Act
        part = Part(sku=sku, name=name, price=price, category=category)

        # Assert
        assert part.sku == sku
        assert part.name == name
        assert part.price == price
        assert part.category == category
        assert part.manufacturer == "CSF"
        assert part.in_stock is True
        assert part.features == []
        assert part.specifications == {}
        assert part.images == []

    def test_part_with_all_fields(self) -> None:
        """Test creating part with all optional fields."""
        # Arrange
        sku = "CSF-99999"
        name = "Premium Condenser"
        price = Decimal("399.99")
        description = "High quality condenser"
        category = "Condensers"
        specifications = {"width": "24 inches", "height": "18 inches"}
        features = ["Lightweight", "Corrosion resistant"]
        tech_notes = "Requires special installation"
        position = "Front"
        images = [PartImage(url="https://example.com/img1.jpg", is_primary=True)]

        # Act
        part = Part(
            sku=sku,
            name=name,
            price=price,
            description=description,
            category=category,
            specifications=specifications,
            features=features,
            tech_notes=tech_notes,
            position=position,
            images=images,
        )

        # Assert
        assert part.sku == sku
        assert part.name == name
        assert part.price == price
        assert part.description == description
        assert part.category == "Condensers"
        assert part.specifications == specifications
        assert part.features == features
        assert part.tech_notes == tech_notes
        assert part.position == position
        assert len(part.images) == 1

    def test_part_sku_required(self) -> None:
        """Test that SKU is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(name="Test Part", category="Test")  # type: ignore[call-arg]

        assert "sku" in str(exc_info.value)

    def test_part_sku_cannot_be_empty(self) -> None:
        """Test that SKU cannot be empty."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="", name="Test Part", category="Test")

        assert "sku" in str(exc_info.value)

    def test_part_sku_must_start_with_csf(self) -> None:
        """Test that SKU must start with 'CSF-'."""
        # Arrange
        invalid_sku = "ABC-12345"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku=invalid_sku, name="Test Part", category="Test")

        error_message = str(exc_info.value).lower()
        assert "csf" in error_message

    def test_part_sku_normalized_to_uppercase(self) -> None:
        """Test that SKU is normalized to uppercase."""
        # Arrange
        lowercase_sku = "csf-12345"

        # Act
        part = Part(sku=lowercase_sku, name="Test Part", category="Test")

        # Assert
        assert part.sku == "CSF-12345"

    def test_part_price_optional(self) -> None:
        """Test that price is optional."""
        # Arrange
        sku = "CSF-12345"
        name = "Test Part"
        category = "Test"

        # Act
        part = Part(sku=sku, name=name, category=category, price=None)

        # Assert
        assert part.price is None

    def test_part_price_must_be_positive(self) -> None:
        """Test that price must be positive when provided."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name="Test", category="Test", price=Decimal("-10.00"))

        assert "price" in str(exc_info.value).lower()

    def test_part_price_cannot_be_zero(self) -> None:
        """Test that price cannot be zero."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name="Test", category="Test", price=Decimal("0.00"))

        assert "price" in str(exc_info.value).lower()

    def test_part_price_has_decimal_precision(self) -> None:
        """Test that price uses Decimal for precision."""
        # Arrange
        price = Decimal("299.99")

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", price=price)

        # Assert
        assert isinstance(part.price, Decimal)
        assert part.price == price

    def test_part_price_rejects_unreasonably_high_values(self) -> None:
        """Test that price validation rejects unreasonably high values."""
        # Arrange
        excessive_price = Decimal("75000.00")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name="Test", category="Test", price=excessive_price)

        error_message = str(exc_info.value).lower()
        assert "price" in error_message

    def test_part_features_list_validation(self) -> None:
        """Test that features list is properly validated."""
        # Arrange
        features = ["Feature 1", "Feature 2", "Feature 3"]

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", features=features)

        # Assert
        assert part.features == features
        assert isinstance(part.features, list)

    def test_part_features_defaults_to_empty_list(self) -> None:
        """Test that features defaults to empty list."""
        # Arrange & Act
        part = Part(sku="CSF-12345", name="Test", category="Test")

        # Assert
        assert part.features == []
        assert isinstance(part.features, list)

    def test_part_tech_notes_optional(self) -> None:
        """Test that tech_notes is optional."""
        # Arrange & Act
        part = Part(sku="CSF-12345", name="Test", category="Test")

        # Assert
        assert part.tech_notes is None

    def test_part_tech_notes_accepts_string(self) -> None:
        """Test that tech_notes accepts string values."""
        # Arrange
        notes = "Special installation required"

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", tech_notes=notes)

        # Assert
        assert part.tech_notes == notes

    def test_part_specifications_dict_validation(self) -> None:
        """Test that specifications dict is properly validated."""
        # Arrange
        specs = {
            "width": "24 inches",
            "height": "18 inches",
            "weight": "5 lbs",
            "material": "Aluminum",
        }

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", specifications=specs)

        # Assert
        assert part.specifications == specs
        assert isinstance(part.specifications, dict)

    def test_part_specifications_defaults_to_empty_dict(self) -> None:
        """Test that specifications defaults to empty dict."""
        # Arrange & Act
        part = Part(sku="CSF-12345", name="Test", category="Test")

        # Assert
        assert part.specifications == {}
        assert isinstance(part.specifications, dict)

    def test_part_category_required(self) -> None:
        """Test that category is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name="Test Part")  # type: ignore[call-arg]

        assert "category" in str(exc_info.value)

    def test_part_category_normalized_to_title_case(self) -> None:
        """Test that category is normalized to title case."""
        # Arrange
        lowercase_category = "radiators"

        # Act
        part = Part(sku="CSF-12345", name="Test", category=lowercase_category)

        # Assert
        assert part.category == "Radiators"

    def test_part_name_required(self) -> None:
        """Test that name is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", category="Test")  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_part_name_cannot_be_empty(self) -> None:
        """Test that name cannot be empty."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name="", category="Test")

        assert "name" in str(exc_info.value)

    def test_part_is_immutable(self) -> None:
        """Test that Part is frozen (immutable)."""
        # Arrange
        part = Part(sku="CSF-12345", name="Test", category="Test")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            part.sku = "CSF-99999"  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_part_get_primary_image_returns_primary(self) -> None:
        """Test get_primary_image returns the primary image."""
        # Arrange
        images = [
            PartImage(url="https://example.com/img1.jpg", is_primary=False),
            PartImage(url="https://example.com/img2.jpg", is_primary=True),
            PartImage(url="https://example.com/img3.jpg", is_primary=False),
        ]
        part = Part(sku="CSF-12345", name="Test", category="Test", images=images)

        # Act
        primary = part.get_primary_image()

        # Assert
        assert primary is not None
        assert primary.url == "https://example.com/img2.jpg"
        assert primary.is_primary is True

    def test_part_get_primary_image_returns_first_when_no_primary(self) -> None:
        """Test get_primary_image returns first image when no primary set."""
        # Arrange
        images = [
            PartImage(url="https://example.com/img1.jpg", is_primary=False),
            PartImage(url="https://example.com/img2.jpg", is_primary=False),
        ]
        part = Part(sku="CSF-12345", name="Test", category="Test", images=images)

        # Act
        primary = part.get_primary_image()

        # Assert
        assert primary is not None
        assert primary.url == "https://example.com/img1.jpg"

    def test_part_get_primary_image_returns_none_when_no_images(self) -> None:
        """Test get_primary_image returns None when no images."""
        # Arrange
        part = Part(sku="CSF-12345", name="Test", category="Test", images=[])

        # Act
        primary = part.get_primary_image()

        # Assert
        assert primary is None

    def test_part_rejects_invalid_data(self) -> None:
        """Test that Part rejects completely invalid data."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            Part(
                sku="",  # Empty SKU
                name="",  # Empty name
                price=Decimal("-100"),  # Negative price
                category="",  # Empty category
            )


class TestVehicle:
    """Tests for Vehicle model."""

    def test_valid_vehicle_creation(self) -> None:
        """Test creating a valid Vehicle instance."""
        # Arrange
        make = "Honda"
        model = "Accord"
        year = 2020

        # Act
        vehicle = Vehicle(make=make, model=model, year=year)

        # Assert
        assert vehicle.make == make
        assert vehicle.model == model
        assert vehicle.year == year
        assert vehicle.submodel is None
        assert vehicle.engine is None
        assert vehicle.fuel_type is None
        assert vehicle.aspiration is None

    def test_vehicle_with_all_fields(self) -> None:
        """Test creating vehicle with all optional fields."""
        # Arrange
        make = "Audi"
        model = "A4"
        year = 2021
        submodel = "Quattro"
        engine = "2.0L L4"
        fuel_type = "Gasoline"
        aspiration = "Turbocharged"

        # Act
        vehicle = Vehicle(
            make=make,
            model=model,
            year=year,
            submodel=submodel,
            engine=engine,
            fuel_type=fuel_type,
            aspiration=aspiration,
        )

        # Assert
        assert vehicle.make == make
        assert vehicle.model == model
        assert vehicle.year == year
        assert vehicle.submodel == submodel
        assert vehicle.engine == engine
        assert vehicle.fuel_type == fuel_type
        assert vehicle.aspiration == aspiration

    def test_vehicle_year_minimum_1950(self) -> None:
        """Test that year must be 1950 or later."""
        # Arrange
        invalid_year = 1949

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(make="Ford", model="Model T", year=invalid_year)

        error_message = str(exc_info.value).lower()
        assert "1950" in error_message

    def test_vehicle_year_maximum_validation(self) -> None:
        """Test that year cannot be more than 2 years in future."""
        # Arrange
        current_year = datetime.now(UTC).year
        future_year = current_year + 3  # 3 years in future

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(make="Tesla", model="Cybertruck", year=future_year)

        error_message = str(exc_info.value).lower()
        assert "future" in error_message

    def test_vehicle_year_accepts_current_year(self) -> None:
        """Test that current year is accepted."""
        # Arrange
        current_year = datetime.now(UTC).year

        # Act
        vehicle = Vehicle(make="Ford", model="F-150", year=current_year)

        # Assert
        assert vehicle.year == current_year

    def test_vehicle_year_accepts_next_year(self) -> None:
        """Test that next year is accepted (for upcoming models)."""
        # Arrange
        next_year = datetime.now(UTC).year + 1

        # Act
        vehicle = Vehicle(make="Chevrolet", model="Silverado", year=next_year)

        # Assert
        assert vehicle.year == next_year

    def test_vehicle_make_required(self) -> None:
        """Test that make is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(model="Accord", year=2020)  # type: ignore[call-arg]

        assert "make" in str(exc_info.value)

    def test_vehicle_model_required(self) -> None:
        """Test that model is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(make="Honda", year=2020)  # type: ignore[call-arg]

        assert "model" in str(exc_info.value)

    def test_vehicle_year_required(self) -> None:
        """Test that year is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(make="Honda", model="Accord")  # type: ignore[call-arg]

        assert "year" in str(exc_info.value)

    def test_vehicle_make_normalized_to_title_case(self) -> None:
        """Test that make is normalized to title case."""
        # Arrange
        lowercase_make = "honda"

        # Act
        vehicle = Vehicle(make=lowercase_make, model="Accord", year=2020)

        # Assert
        assert vehicle.make == "Honda"

    def test_vehicle_model_normalized_to_title_case(self) -> None:
        """Test that model is normalized to title case."""
        # Arrange
        lowercase_model = "accord"

        # Act
        vehicle = Vehicle(make="Honda", model=lowercase_model, year=2020)

        # Assert
        assert vehicle.model == "Accord"

    def test_vehicle_engine_optional(self) -> None:
        """Test that engine is optional."""
        # Arrange & Act
        vehicle = Vehicle(make="Honda", model="Accord", year=2020)

        # Assert
        assert vehicle.engine is None

    def test_vehicle_fuel_type_optional(self) -> None:
        """Test that fuel_type is optional."""
        # Arrange & Act
        vehicle = Vehicle(make="Honda", model="Accord", year=2020)

        # Assert
        assert vehicle.fuel_type is None

    def test_vehicle_aspiration_optional(self) -> None:
        """Test that aspiration is optional."""
        # Arrange & Act
        vehicle = Vehicle(make="Honda", model="Accord", year=2020)

        # Assert
        assert vehicle.aspiration is None

    def test_vehicle_is_immutable(self) -> None:
        """Test that Vehicle is frozen (immutable)."""
        # Arrange
        vehicle = Vehicle(make="Honda", model="Accord", year=2020)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            vehicle.year = 2021  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_vehicle_str_without_submodel(self) -> None:
        """Test __str__ method without submodel."""
        # Arrange
        vehicle = Vehicle(make="Honda", model="Accord", year=2020)

        # Act
        result = str(vehicle)

        # Assert
        assert result == "2020 Honda Accord"

    def test_vehicle_str_with_submodel(self) -> None:
        """Test __str__ method with submodel."""
        # Arrange
        vehicle = Vehicle(make="Audi", model="A4", year=2021, submodel="Quattro")

        # Act
        result = str(vehicle)

        # Assert
        assert result == "2021 Audi A4 Quattro"

    def test_vehicle_rejects_invalid_data(self) -> None:
        """Test that Vehicle rejects completely invalid data."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            Vehicle(
                make="",  # Empty make
                model="",  # Empty model
                year=1800,  # Invalid year
            )


class TestVehicleCompatibility:
    """Tests for VehicleCompatibility model."""

    def test_valid_compatibility_creation(self) -> None:
        """Test creating a valid VehicleCompatibility instance."""
        # Arrange
        part_sku = "CSF-12345"
        vehicles = [
            Vehicle(make="Honda", model="Accord", year=2020),
            Vehicle(make="Honda", model="Accord", year=2021),
        ]

        # Act
        compatibility = VehicleCompatibility(part_sku=part_sku, vehicles=vehicles)

        # Assert
        assert compatibility.part_sku == part_sku
        assert len(compatibility.vehicles) == 2
        assert compatibility.notes is None

    def test_compatibility_with_notes(self) -> None:
        """Test creating compatibility with notes."""
        # Arrange
        part_sku = "CSF-12345"
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]
        notes = "Requires adapter kit for installation"

        # Act
        compatibility = VehicleCompatibility(part_sku=part_sku, vehicles=vehicles, notes=notes)

        # Assert
        assert compatibility.notes == notes

    def test_compatibility_part_sku_required(self) -> None:
        """Test that part_sku is required."""
        # Arrange
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VehicleCompatibility(vehicles=vehicles)  # type: ignore[call-arg]

        assert "part_sku" in str(exc_info.value)

    def test_compatibility_part_sku_cannot_be_empty(self) -> None:
        """Test that part_sku cannot be empty."""
        # Arrange
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VehicleCompatibility(part_sku="", vehicles=vehicles)

        assert "part_sku" in str(exc_info.value)

    def test_compatibility_part_sku_must_start_with_csf(self) -> None:
        """Test that part_sku must start with 'CSF-'."""
        # Arrange
        invalid_sku = "ABC-12345"
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VehicleCompatibility(part_sku=invalid_sku, vehicles=vehicles)

        error_message = str(exc_info.value).lower()
        assert "csf" in error_message

    def test_compatibility_part_sku_normalized_to_uppercase(self) -> None:
        """Test that part_sku is normalized to uppercase."""
        # Arrange
        lowercase_sku = "csf-12345"
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]

        # Act
        compatibility = VehicleCompatibility(part_sku=lowercase_sku, vehicles=vehicles)

        # Assert
        assert compatibility.part_sku == "CSF-12345"

    def test_compatibility_vehicles_required(self) -> None:
        """Test that vehicles list is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VehicleCompatibility(part_sku="CSF-12345")  # type: ignore[call-arg]

        assert "vehicles" in str(exc_info.value)

    def test_compatibility_vehicles_minimum_one(self) -> None:
        """Test that vehicles list must have at least one vehicle."""
        # Arrange
        empty_vehicles: list[Vehicle] = []

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VehicleCompatibility(part_sku="CSF-12345", vehicles=empty_vehicles)

        error_message = str(exc_info.value).lower()
        assert "vehicles" in error_message

    def test_compatibility_is_immutable(self) -> None:
        """Test that VehicleCompatibility is frozen (immutable)."""
        # Arrange
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            compatibility.part_sku = "CSF-99999"  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_compatibility_get_year_range_single_vehicle(self) -> None:
        """Test get_year_range with single vehicle."""
        # Arrange
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Act
        year_range = compatibility.get_year_range()

        # Assert
        assert year_range is not None
        assert year_range == (2020, 2020)

    def test_compatibility_get_year_range_multiple_vehicles(self) -> None:
        """Test get_year_range with multiple vehicles."""
        # Arrange
        vehicles = [
            Vehicle(make="Honda", model="Accord", year=2018),
            Vehicle(make="Honda", model="Accord", year=2020),
            Vehicle(make="Honda", model="Accord", year=2019),
            Vehicle(make="Honda", model="Accord", year=2021),
        ]
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Act
        year_range = compatibility.get_year_range()

        # Assert
        assert year_range is not None
        assert year_range == (2018, 2021)

    def test_compatibility_get_year_range_empty_vehicles(self) -> None:
        """Test get_year_range returns None when no vehicles.

        Note: This tests the internal method logic. In practice, the model validation
        prevents creating a VehicleCompatibility with an empty vehicles list.
        """
        # Arrange
        # Manually test the edge case by checking the method behavior
        # This tests the method's internal logic for empty list handling
        empty_compat = VehicleCompatibility.__new__(VehicleCompatibility)
        object.__setattr__(empty_compat, "vehicles", [])

        # Act
        year_range = empty_compat.get_year_range()

        # Assert
        assert year_range is None

    def test_compatibility_is_compatible_with_returns_true(self) -> None:
        """Test is_compatible_with returns True for compatible vehicle."""
        # Arrange
        vehicle1 = Vehicle(make="Honda", model="Accord", year=2020)
        vehicle2 = Vehicle(make="Honda", model="Civic", year=2020)
        vehicles = [vehicle1, vehicle2]
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Act
        result = compatibility.is_compatible_with(vehicle1)

        # Assert
        assert result is True

    def test_compatibility_is_compatible_with_returns_false(self) -> None:
        """Test is_compatible_with returns False for incompatible vehicle."""
        # Arrange
        vehicle1 = Vehicle(make="Honda", model="Accord", year=2020)
        vehicle2 = Vehicle(make="Honda", model="Civic", year=2020)
        vehicles = [vehicle1]
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Act
        result = compatibility.is_compatible_with(vehicle2)

        # Assert
        assert result is False

    def test_compatibility_rejects_invalid_data(self) -> None:
        """Test that VehicleCompatibility rejects completely invalid data."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            VehicleCompatibility(
                part_sku="",  # Empty SKU
                vehicles=[],  # Empty vehicles list
            )


# ============================================================================
# Serialization and Deserialization Tests
# ============================================================================


class TestPartImageSerialization:
    """Tests for PartImage serialization/deserialization."""

    def test_part_image_model_dump(self) -> None:
        """Test PartImage.model_dump() serialization."""
        # Arrange
        image = PartImage(
            url="https://example.com/image.jpg",
            alt_text="Test image",
            is_primary=True,
        )

        # Act
        data = image.model_dump()

        # Assert
        assert data["url"] == "https://example.com/image.jpg"
        assert data["alt_text"] == "Test image"
        assert data["is_primary"] is True
        assert isinstance(data, dict)

    def test_part_image_model_dump_json_mode(self) -> None:
        """Test PartImage.model_dump() with JSON mode."""
        # Arrange
        image = PartImage(url="https://example.com/image.jpg", alt_text="Test")

        # Act
        data = image.model_dump(mode="json")

        # Assert
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com/image.jpg"
        assert data["alt_text"] == "Test"

    def test_part_image_model_dump_json(self) -> None:
        """Test PartImage.model_dump_json() serialization."""
        # Arrange
        image = PartImage(url="https://example.com/image.jpg", is_primary=True)

        # Act
        json_str = image.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        assert "https://example.com/image.jpg" in json_str
        assert '"is_primary":true' in json_str or '"is_primary": true' in json_str

    def test_part_image_deserialization_from_dict(self) -> None:
        """Test creating PartImage from dictionary."""
        # Arrange
        data: dict[str, Any] = {
            "url": "https://example.com/test.jpg",
            "alt_text": "Test Alt",
            "is_primary": False,
        }

        # Act
        image = PartImage(**data)

        # Assert
        assert image.url == "https://example.com/test.jpg"
        assert image.alt_text == "Test Alt"
        assert image.is_primary is False

    def test_part_image_model_validate(self) -> None:
        """Test PartImage.model_validate() class method."""
        # Arrange
        data = {"url": "https://example.com/img.jpg", "is_primary": True}

        # Act
        image = PartImage.model_validate(data)

        # Assert
        assert isinstance(image, PartImage)
        assert image.url == "https://example.com/img.jpg"
        assert image.is_primary is True


class TestPartSerialization:
    """Tests for Part serialization/deserialization."""

    def test_part_model_dump(self) -> None:
        """Test Part.model_dump() serialization."""
        # Arrange
        part = Part(
            sku="CSF-12345",
            name="Test Part",
            price=Decimal("99.99"),
            category="Radiators",
            description="Test description",
        )

        # Act
        data = part.model_dump()

        # Assert
        assert data["sku"] == "CSF-12345"
        assert data["name"] == "Test Part"
        assert data["price"] == Decimal("99.99")
        assert data["category"] == "Radiators"
        assert data["description"] == "Test description"
        assert isinstance(data, dict)

    def test_part_model_dump_json_mode(self) -> None:
        """Test Part.model_dump() with JSON mode converts Decimal to string."""
        # Arrange
        part = Part(
            sku="CSF-99999",
            name="Test Part",
            price=Decimal("299.99"),
            category="Condensers",
        )

        # Act
        data = part.model_dump(mode="json")

        # Assert
        assert isinstance(data, dict)
        assert data["price"] == "299.99"  # Decimal serialized as string in JSON mode
        assert isinstance(data["price"], str)

    def test_part_model_dump_json(self) -> None:
        """Test Part.model_dump_json() serialization."""
        # Arrange
        part = Part(
            sku="CSF-12345",
            name="Test Part",
            price=Decimal("99.99"),
            category="Radiators",
        )

        # Act
        json_str = part.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        assert "CSF-12345" in json_str
        assert "Test Part" in json_str
        assert "99.99" in json_str

    def test_part_deserialization_from_dict(self) -> None:
        """Test creating Part from dictionary."""
        # Arrange
        data: dict[str, Any] = {
            "sku": "csf-88888",
            "name": "Radiator",
            "price": "199.99",
            "category": "radiators",
            "specifications": {"width": "24in"},
        }

        # Act
        part = Part(**data)

        # Assert
        assert part.sku == "CSF-88888"  # Normalized to uppercase
        assert part.name == "Radiator"
        assert part.price == Decimal("199.99")  # Converted to Decimal
        assert part.category == "Radiators"  # Normalized to title case
        assert part.specifications == {"width": "24in"}

    def test_part_model_validate(self) -> None:
        """Test Part.model_validate() class method."""
        # Arrange
        data = {
            "sku": "CSF-77777",
            "name": "Test",
            "category": "Test Category",
            "price": 50.00,
        }

        # Act
        part = Part.model_validate(data)

        # Assert
        assert isinstance(part, Part)
        assert part.sku == "CSF-77777"
        assert part.price == Decimal("50.00")

    def test_part_with_nested_images_serialization(self) -> None:
        """Test Part serialization with nested PartImage objects."""
        # Arrange
        images = [
            PartImage(url="https://example.com/img1.jpg", is_primary=True),
            PartImage(url="https://example.com/img2.jpg", is_primary=False),
        ]
        part = Part(
            sku="CSF-12345",
            name="Test",
            category="Test",
            images=images,
        )

        # Act
        data = part.model_dump()

        # Assert
        assert len(data["images"]) == 2
        assert data["images"][0]["url"] == "https://example.com/img1.jpg"
        assert data["images"][0]["is_primary"] is True
        assert data["images"][1]["url"] == "https://example.com/img2.jpg"

    def test_part_deserialization_with_nested_images(self) -> None:
        """Test Part deserialization with nested image dictionaries."""
        # Arrange
        data: dict[str, Any] = {
            "sku": "CSF-12345",
            "name": "Test",
            "category": "Test",
            "images": [
                {"url": "https://example.com/img1.jpg", "is_primary": True},
                {"url": "https://example.com/img2.jpg", "is_primary": False},
            ],
        }

        # Act
        part = Part(**data)

        # Assert
        assert len(part.images) == 2
        assert isinstance(part.images[0], PartImage)
        assert part.images[0].url == "https://example.com/img1.jpg"
        assert part.images[0].is_primary is True

    def test_part_serialization_with_none_values(self) -> None:
        """Test Part serialization with None values for optional fields."""
        # Arrange
        part = Part(
            sku="CSF-12345",
            name="Test",
            category="Test",
            price=None,
            description=None,
            tech_notes=None,
            position=None,
        )

        # Act
        data = part.model_dump()

        # Assert
        assert data["price"] is None
        assert data["description"] is None
        assert data["tech_notes"] is None
        assert data["position"] is None


class TestVehicleSerialization:
    """Tests for Vehicle serialization/deserialization."""

    def test_vehicle_model_dump(self) -> None:
        """Test Vehicle.model_dump() serialization."""
        # Arrange
        vehicle = Vehicle(
            make="Honda",
            model="Accord",
            year=2020,
            engine="2.0L L4",
        )

        # Act
        data = vehicle.model_dump()

        # Assert
        assert data["make"] == "Honda"
        assert data["model"] == "Accord"
        assert data["year"] == 2020
        assert data["engine"] == "2.0L L4"
        assert isinstance(data, dict)

    def test_vehicle_model_dump_json(self) -> None:
        """Test Vehicle.model_dump_json() serialization."""
        # Arrange
        vehicle = Vehicle(make="Toyota", model="Camry", year=2021)

        # Act
        json_str = vehicle.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        assert "Toyota" in json_str
        assert "Camry" in json_str
        assert "2021" in json_str

    def test_vehicle_deserialization_from_dict(self) -> None:
        """Test creating Vehicle from dictionary."""
        # Arrange
        data: dict[str, Any] = {
            "make": "audi",
            "model": "a4",
            "year": 2022,
            "submodel": "quattro",
        }

        # Act
        vehicle = Vehicle(**data)

        # Assert
        assert vehicle.make == "Audi"  # Normalized to title case
        assert vehicle.model == "A4"  # Normalized to title case
        assert vehicle.year == 2022
        assert vehicle.submodel == "quattro"

    def test_vehicle_model_validate(self) -> None:
        """Test Vehicle.model_validate() class method."""
        # Arrange
        data = {"make": "BMW", "model": "3 Series", "year": 2023}

        # Act
        vehicle = Vehicle.model_validate(data)

        # Assert
        assert isinstance(vehicle, Vehicle)
        assert vehicle.make == "Bmw"  # Title cased
        assert vehicle.model == "3 Series"
        assert vehicle.year == 2023

    def test_vehicle_serialization_with_all_optional_fields(self) -> None:
        """Test Vehicle serialization with all optional fields populated."""
        # Arrange
        vehicle = Vehicle(
            make="Mercedes",
            model="C-Class",
            year=2024,
            submodel="AMG",
            engine="3.0L V6",
            fuel_type="Gasoline",
            aspiration="Turbocharged",
        )

        # Act
        data = vehicle.model_dump()

        # Assert
        assert data["submodel"] == "AMG"
        assert data["engine"] == "3.0L V6"
        assert data["fuel_type"] == "Gasoline"
        assert data["aspiration"] == "Turbocharged"


class TestVehicleCompatibilitySerialization:
    """Tests for VehicleCompatibility serialization/deserialization."""

    def test_compatibility_model_dump(self) -> None:
        """Test VehicleCompatibility.model_dump() serialization."""
        # Arrange
        vehicles = [
            Vehicle(make="Honda", model="Accord", year=2020),
            Vehicle(make="Honda", model="Accord", year=2021),
        ]
        compatibility = VehicleCompatibility(
            part_sku="CSF-12345",
            vehicles=vehicles,
            notes="Direct fit",
        )

        # Act
        data = compatibility.model_dump()

        # Assert
        assert data["part_sku"] == "CSF-12345"
        assert len(data["vehicles"]) == 2
        assert data["notes"] == "Direct fit"
        assert isinstance(data, dict)

    def test_compatibility_model_dump_json(self) -> None:
        """Test VehicleCompatibility.model_dump_json() serialization."""
        # Arrange
        vehicles = [Vehicle(make="Toyota", model="Camry", year=2022)]
        compatibility = VehicleCompatibility(part_sku="CSF-99999", vehicles=vehicles)

        # Act
        json_str = compatibility.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        assert "CSF-99999" in json_str
        assert "Toyota" in json_str
        assert "Camry" in json_str
        assert "2022" in json_str

    def test_compatibility_deserialization_from_dict(self) -> None:
        """Test creating VehicleCompatibility from dictionary."""
        # Arrange
        data: dict[str, Any] = {
            "part_sku": "csf-88888",
            "vehicles": [
                {"make": "ford", "model": "f-150", "year": 2020},
                {"make": "ford", "model": "f-150", "year": 2021},
            ],
            "notes": "Requires adapter",
        }

        # Act
        compatibility = VehicleCompatibility(**data)

        # Assert
        assert compatibility.part_sku == "CSF-88888"  # Normalized to uppercase
        assert len(compatibility.vehicles) == 2
        assert compatibility.vehicles[0].make == "Ford"  # Normalized
        assert compatibility.notes == "Requires adapter"

    def test_compatibility_model_validate(self) -> None:
        """Test VehicleCompatibility.model_validate() class method."""
        # Arrange
        data = {
            "part_sku": "CSF-77777",
            "vehicles": [{"make": "Chevrolet", "model": "Silverado", "year": 2023}],
        }

        # Act
        compatibility = VehicleCompatibility.model_validate(data)

        # Assert
        assert isinstance(compatibility, VehicleCompatibility)
        assert compatibility.part_sku == "CSF-77777"
        assert len(compatibility.vehicles) == 1

    def test_compatibility_with_nested_vehicles_serialization(self) -> None:
        """Test VehicleCompatibility serialization with nested Vehicle objects."""
        # Arrange
        vehicles = [
            Vehicle(make="Dodge", model="Ram", year=2020, engine="5.7L V8"),
            Vehicle(make="Dodge", model="Ram", year=2021, engine="5.7L V8"),
            Vehicle(make="Dodge", model="Ram", year=2022, engine="5.7L V8"),
        ]
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Act
        data = compatibility.model_dump()

        # Assert
        assert len(data["vehicles"]) == 3
        assert all(isinstance(v, dict) for v in data["vehicles"])
        assert data["vehicles"][0]["make"] == "Dodge"
        assert data["vehicles"][0]["engine"] == "5.7L V8"


# ============================================================================
# Edge Case and Boundary Tests
# ============================================================================


class TestPartEdgeCases:
    """Edge case tests for Part model."""

    def test_part_sku_with_whitespace_trimmed(self) -> None:
        """Test that SKU whitespace is trimmed before validation."""
        # Arrange
        sku_with_spaces = "  CSF-12345  "

        # Act
        part = Part(sku=sku_with_spaces, name="Test", category="Test")

        # Assert
        assert part.sku == "CSF-12345"

    def test_part_sku_lowercase_converted_to_uppercase(self) -> None:
        """Test lowercase SKU is converted to uppercase."""
        # Arrange
        lowercase_sku = "csf-99999"

        # Act
        part = Part(sku=lowercase_sku, name="Test", category="Test")

        # Assert
        assert part.sku == "CSF-99999"

    def test_part_sku_mixed_case_normalized(self) -> None:
        """Test mixed case SKU is normalized to uppercase."""
        # Arrange
        mixed_case_sku = "CsF-99999"

        # Act
        part = Part(sku=mixed_case_sku, name="Test", category="Test")

        # Assert
        assert part.sku == "CSF-99999"

    def test_part_price_boundary_max_valid(self) -> None:
        """Test Part accepts maximum valid price (50000.00)."""
        # Arrange
        max_price = Decimal("50000.00")

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", price=max_price)

        # Assert
        assert part.price == max_price

    def test_part_price_boundary_just_over_max(self) -> None:
        """Test Part rejects price just over maximum (50000.01)."""
        # Arrange
        over_max_price = Decimal("50000.01")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name="Test", category="Test", price=over_max_price)

        assert "price" in str(exc_info.value).lower()

    def test_part_price_min_valid(self) -> None:
        """Test Part accepts minimum valid price (0.01)."""
        # Arrange
        min_price = Decimal("0.01")

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", price=min_price)

        # Assert
        assert part.price == min_price

    def test_part_name_max_length(self) -> None:
        """Test Part name respects max_length constraint."""
        # Arrange
        long_name = "A" * 500  # Exactly at max length

        # Act
        part = Part(sku="CSF-12345", name=long_name, category="Test")

        # Assert
        assert len(part.name) == 500

    def test_part_name_over_max_length(self) -> None:
        """Test Part name over max_length is rejected."""
        # Arrange
        too_long_name = "A" * 501  # Over max length

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku="CSF-12345", name=too_long_name, category="Test")

        assert "name" in str(exc_info.value).lower()

    def test_part_sku_max_length(self) -> None:
        """Test Part SKU respects max_length constraint."""
        # Arrange
        sku = "CSF-" + "9" * 96  # Total 100 characters

        # Act
        part = Part(sku=sku, name="Test", category="Test")

        # Assert
        assert len(part.sku) == 100

    def test_part_sku_over_max_length(self) -> None:
        """Test Part SKU over max_length is rejected."""
        # Arrange
        too_long_sku = "CSF-" + "9" * 97  # Total 101 characters

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Part(sku=too_long_sku, name="Test", category="Test")

        assert "sku" in str(exc_info.value).lower()

    def test_part_category_whitespace_stripped_and_title_cased(self) -> None:
        """Test category whitespace stripped and title cased."""
        # Arrange
        category_with_spaces = "  radiators  "

        # Act
        part = Part(sku="CSF-12345", name="Test", category=category_with_spaces)

        # Assert
        assert part.category == "Radiators"

    def test_part_empty_specifications_dict(self) -> None:
        """Test Part with explicitly empty specifications dict."""
        # Arrange
        empty_specs: dict[str, str] = {}

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", specifications=empty_specs)

        # Assert
        assert part.specifications == {}
        assert isinstance(part.specifications, dict)

    def test_part_empty_features_list(self) -> None:
        """Test Part with explicitly empty features list."""
        # Arrange
        empty_features: list[str] = []

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", features=empty_features)

        # Assert
        assert part.features == []
        assert isinstance(part.features, list)

    def test_part_empty_images_list(self) -> None:
        """Test Part with explicitly empty images list."""
        # Arrange
        empty_images: list[PartImage] = []

        # Act
        part = Part(sku="CSF-12345", name="Test", category="Test", images=empty_images)

        # Assert
        assert part.images == []
        assert isinstance(part.images, list)


class TestVehicleEdgeCases:
    """Edge case tests for Vehicle model."""

    def test_vehicle_year_boundary_1950(self) -> None:
        """Test Vehicle accepts year exactly at minimum (1950)."""
        # Arrange
        min_year = 1950

        # Act
        vehicle = Vehicle(make="Ford", model="Model T", year=min_year)

        # Assert
        assert vehicle.year == 1950

    def test_vehicle_year_boundary_1949(self) -> None:
        """Test Vehicle rejects year below minimum (1949)."""
        # Arrange
        below_min_year = 1949

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(make="Ford", model="Model T", year=below_min_year)

        assert "1950" in str(exc_info.value).lower()

    def test_vehicle_year_boundary_current_plus_two(self) -> None:
        """Test Vehicle accepts year exactly 2 years in future."""
        # Arrange
        current_year = datetime.now(UTC).year
        max_year = current_year + 2

        # Act
        vehicle = Vehicle(make="Tesla", model="Cybertruck", year=max_year)

        # Assert
        assert vehicle.year == max_year

    def test_vehicle_make_whitespace_trimmed(self) -> None:
        """Test Vehicle make whitespace is trimmed."""
        # Arrange
        make_with_spaces = "  Honda  "

        # Act
        vehicle = Vehicle(make=make_with_spaces, model="Accord", year=2020)

        # Assert
        assert vehicle.make == "Honda"

    def test_vehicle_model_whitespace_trimmed(self) -> None:
        """Test Vehicle model whitespace is trimmed."""
        # Arrange
        model_with_spaces = "  Accord  "

        # Act
        vehicle = Vehicle(make="Honda", model=model_with_spaces, year=2020)

        # Assert
        assert vehicle.model == "Accord"

    def test_vehicle_make_uppercase(self) -> None:
        """Test Vehicle make with uppercase letters title cased."""
        # Arrange
        uppercase_make = "HONDA"

        # Act
        vehicle = Vehicle(make=uppercase_make, model="Accord", year=2020)

        # Assert
        assert vehicle.make == "Honda"

    def test_vehicle_model_max_length(self) -> None:
        """Test Vehicle model respects max_length constraint."""
        # Arrange
        long_model = "A" * 100  # Exactly at max length

        # Act
        vehicle = Vehicle(make="Test", model=long_model, year=2020)

        # Assert
        assert len(vehicle.model) == 100

    def test_vehicle_model_over_max_length(self) -> None:
        """Test Vehicle model over max_length is rejected."""
        # Arrange
        too_long_model = "A" * 101  # Over max length

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Vehicle(make="Test", model=too_long_model, year=2020)

        assert "model" in str(exc_info.value).lower()


class TestVehicleCompatibilityEdgeCases:
    """Edge case tests for VehicleCompatibility model."""

    def test_compatibility_sku_whitespace_trimmed(self) -> None:
        """Test VehicleCompatibility SKU whitespace is trimmed."""
        # Arrange
        sku_with_spaces = "  CSF-12345  "
        vehicles = [Vehicle(make="Honda", model="Accord", year=2020)]

        # Act
        compatibility = VehicleCompatibility(part_sku=sku_with_spaces, vehicles=vehicles)

        # Assert
        assert compatibility.part_sku == "CSF-12345"

    def test_compatibility_large_vehicle_list(self) -> None:
        """Test VehicleCompatibility with large list of vehicles."""
        # Arrange
        vehicles = [
            Vehicle(make="Honda", model="Accord", year=year)
            for year in range(2000, 2025)  # 25 vehicles
        ]

        # Act
        compatibility = VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

        # Assert
        assert len(compatibility.vehicles) == 25
        year_range = compatibility.get_year_range()
        assert year_range == (2000, 2024)
