"""Data validator using Pydantic models.

This module validates raw scraped data and constructs validated Pydantic models.
Follows Single Responsibility Principle - only concerned with validation.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from pydantic import ValidationError

from src.models.part import Part, PartImage
from src.models.vehicle import Vehicle, VehicleCompatibility

logger = structlog.get_logger()


class DataValidator:
    """Validator for scraped data using Pydantic models.

    Validates raw data dictionaries and constructs type-safe Pydantic models.
    Provides helpful error messages for validation failures.
    """

    def validate_part(self, data: dict[str, Any]) -> Part:
        """Validate and construct Part from raw data.

        Args:
            data: Raw part data dict

        Returns:
            Validated Part instance

        Raises:
            ValidationError: If data is invalid with detailed error message

        Example:
            >>> validator = DataValidator()
            >>> data = {
            ...     "sku": "CSF-12345",
            ...     "name": "Radiator",
            ...     "price": "299.99",
            ...     "category": "Radiators"
            ... }
            >>> part = validator.validate_part(data)
            >>> part.sku
            'CSF-12345'
        """
        try:
            # Pre-process data
            processed_data = self._preprocess_part_data(data)

            # Validate with Pydantic
            part = Part(**processed_data)

            logger.info("part_validated", sku=part.sku, name=part.name)

        except ValidationError as e:
            logger.exception(
                "part_validation_failed",
                errors=e.errors(),
                data_keys=list(data.keys()),
            )
            raise
        else:
            return part

    def validate_vehicle(self, data: dict[str, Any]) -> Vehicle:
        """Validate and construct Vehicle from raw data.

        Args:
            data: Raw vehicle data dict

        Returns:
            Validated Vehicle instance

        Raises:
            ValidationError: If data is invalid

        Example:
            >>> validator = DataValidator()
            >>> data = {"make": "Audi", "model": "A4", "year": 2020}
            >>> vehicle = validator.validate_vehicle(data)
            >>> str(vehicle)
            '2020 Audi A4'
        """
        try:
            vehicle = Vehicle(**data)
            logger.info("vehicle_validated", vehicle=str(vehicle))

        except ValidationError as e:
            logger.exception(
                "vehicle_validation_failed",
                errors=e.errors(),
                data=data,
            )
            raise
        else:
            return vehicle

    def validate_compatibility(self, data: dict[str, Any]) -> VehicleCompatibility:
        """Validate and construct VehicleCompatibility from raw data.

        Args:
            data: Raw compatibility data dict with part_sku, vehicles list

        Returns:
            Validated VehicleCompatibility instance

        Raises:
            ValidationError: If data is invalid

        Example:
            >>> validator = DataValidator()
            >>> data = {
            ...     "part_sku": "CSF-12345",
            ...     "vehicles": [
            ...         {"make": "Audi", "model": "A4", "year": 2020},
            ...         {"make": "Audi", "model": "A4", "year": 2021}
            ...     ]
            ... }
            >>> compat = validator.validate_compatibility(data)
            >>> compat.get_year_range()
            (2020, 2021)
        """
        try:
            compatibility = VehicleCompatibility(**data)
            logger.info(
                "compatibility_validated",
                part_sku=compatibility.part_sku,
                vehicle_count=len(compatibility.vehicles),
            )

        except ValidationError as e:
            logger.exception(
                "compatibility_validation_failed",
                errors=e.errors(),
                part_sku=data.get("part_sku"),
            )
            raise
        else:
            return compatibility

    def _preprocess_part_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Preprocess part data before validation.

        Handles type conversions and data cleaning.

        Args:
            data: Raw part data

        Returns:
            Preprocessed data ready for Pydantic validation
        """
        processed = data.copy()

        # Convert price to Decimal (skip if None)
        if "price" in processed and processed["price"] is not None:
            processed["price"] = self._parse_price(processed["price"])

        # Process images if present
        if "images" in processed and isinstance(processed["images"], list):
            processed["images"] = [self._process_image(img) for img in processed["images"]]

        # Ensure specifications is a dict
        if "specifications" not in processed or not isinstance(processed["specifications"], dict):
            processed["specifications"] = {}

        # Ensure features is a list
        if "features" not in processed or not isinstance(processed["features"], list):
            processed["features"] = []
        else:
            # Ensure all features are strings
            processed["features"] = [str(f) for f in processed["features"] if f]

        # Ensure tech_notes is a string or None
        if "tech_notes" in processed and processed["tech_notes"] is not None:
            processed["tech_notes"] = str(processed["tech_notes"]).strip()
            # Convert empty strings to None
            if not processed["tech_notes"]:
                processed["tech_notes"] = None

        # Ensure position is a string or None
        if "position" in processed and processed["position"] is not None:
            processed["position"] = str(processed["position"]).strip()
            # Convert empty strings to None
            if not processed["position"]:
                processed["position"] = None

        # Set default manufacturer if not present
        if "manufacturer" not in processed:
            processed["manufacturer"] = "CSF"

        # Set default stock status if not present
        if "in_stock" not in processed:
            processed["in_stock"] = True

        logger.debug("part_data_preprocessed", sku=processed.get("sku"))
        return processed

    def _parse_price(self, price: str | float | Decimal) -> Decimal:
        """Parse price from various formats into Decimal.

        Note: This method should not be called with None. The caller should
        check for None before calling this method.

        Args:
            price: Price value (string, float, or Decimal) - must not be None

        Returns:
            Decimal price

        Raises:
            ValueError: If price cannot be parsed

        Example:
            >>> validator = DataValidator()
            >>> validator._parse_price("$299.99")
            Decimal('299.99')
            >>> validator._parse_price("1,299.99")
            Decimal('1299.99')
        """
        if isinstance(price, Decimal):
            return price

        # Convert to string and clean
        price_str = str(price).strip()

        # Remove common price formatting
        price_str = price_str.replace("$", "")
        price_str = price_str.replace(",", "")
        price_str = price_str.replace(" ", "")

        # Handle empty or invalid strings
        if not price_str or price_str == "":
            msg = "Price string is empty"
            raise ValueError(msg)

        try:
            return Decimal(price_str)
        except (InvalidOperation, ValueError) as e:
            logger.exception("price_parse_error", price=price, error=str(e))
            msg = f"Cannot parse price '{price}': {e}"
            raise ValueError(msg) from e

    def _process_image(self, image_data: dict[str, Any] | PartImage) -> PartImage:
        """Process image data into PartImage instance.

        Args:
            image_data: Raw image data or PartImage instance

        Returns:
            PartImage instance

        Raises:
            ValidationError: If image data is invalid
        """
        if isinstance(image_data, PartImage):
            return image_data

        try:
            return PartImage(**image_data)
        except ValidationError as e:
            logger.exception("image_validation_failed", errors=e.errors())
            raise

    def validate_batch(self, parts_data: list[dict[str, Any]]) -> list[Part]:
        """Validate multiple parts in batch.

        Continues validation even if some parts fail, collecting all errors.

        Args:
            parts_data: List of raw part data dicts

        Returns:
            List of successfully validated Parts

        Example:
            >>> validator = DataValidator()
            >>> parts_data = [
            ...     {"sku": "CSF-1", "name": "Part 1", "price": "99.99", "category": "Cat1"},
            ...     {"sku": "CSF-2", "name": "Part 2", "price": "199.99", "category": "Cat2"},
            ... ]
            >>> parts = validator.validate_batch(parts_data)
            >>> len(parts)
            2
        """
        valid_parts: list[Part] = []
        errors: list[dict[str, Any]] = []

        for idx, data in enumerate(parts_data):
            try:
                part = self.validate_part(data)
                valid_parts.append(part)
            except ValidationError as e:
                errors.append(
                    {
                        "index": idx,
                        "sku": data.get("sku", "unknown"),
                        "errors": e.errors(),
                    }
                )
                logger.warning(
                    "part_validation_failed_in_batch",
                    index=idx,
                    sku=data.get("sku"),
                )

        logger.info(
            "batch_validation_complete",
            total=len(parts_data),
            valid=len(valid_parts),
            failed=len(errors),
        )

        if errors:
            logger.warning("validation_errors_summary", errors=errors)

        return valid_parts
