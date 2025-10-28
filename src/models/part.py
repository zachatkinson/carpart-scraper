"""Part data models.

This module defines the Pydantic models for automotive parts data.
All models are immutable (frozen) to ensure data integrity.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PartImage(BaseModel):
    """Image associated with a part.

    Attributes:
        url: Full URL to the image
        alt_text: Alternative text for accessibility
        is_primary: Whether this is the primary product image
    """

    url: str = Field(..., min_length=1, description="Image URL")
    alt_text: str | None = Field(None, description="Alt text for image")
    is_primary: bool = Field(default=False, description="Primary product image flag")

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }


class Part(BaseModel):
    """Automotive part model.

    Represents a single automotive part with all relevant metadata.
    Enforces data integrity through validation.

    Attributes:
        sku: Part SKU (Stock Keeping Unit), must start with 'CSF-'
        name: Part name/title
        price: Part price in USD (optional - not displayed on all pages)
        description: Full product description
        category: Product category (e.g., 'Radiators', 'Condensers')
        specifications: Dict of technical specifications
        images: List of associated images
        manufacturer: Manufacturer name (default: 'CSF')
        in_stock: Stock availability status
        features: List of product features/highlights
        tech_notes: Technical notes or special instructions
        position: Part position/location (e.g., 'Front', 'Rear')
    """

    sku: str = Field(..., min_length=1, max_length=100, description="Part SKU")
    name: str = Field(..., min_length=1, max_length=500, description="Part name")
    price: Decimal | None = Field(None, gt=0, decimal_places=2, description="Price in USD")
    description: str | None = Field(None, description="Product description")
    category: str = Field(..., min_length=1, description="Product category")
    specifications: dict[str, Any] = Field(
        default_factory=dict, description="Technical specifications"
    )
    images: list[PartImage] = Field(default_factory=list, description="Product images")
    manufacturer: str = Field(default="CSF", description="Manufacturer name")
    in_stock: bool = Field(default=True, description="Stock availability")
    features: list[str] = Field(default_factory=list, description="Product features")
    tech_notes: str | None = Field(None, description="Technical notes")
    position: str | None = Field(None, description="Part position/location")
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when part data was scraped",
    )

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        """Validate SKU format.

        Args:
            v: SKU value to validate

        Returns:
            Uppercased SKU

        Raises:
            ValueError: If SKU doesn't start with 'CSF-'
        """
        v = v.upper().strip()
        if not v.startswith("CSF-"):
            msg = "SKU must start with 'CSF-'"
            raise ValueError(msg)
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal | None) -> Decimal | None:
        """Validate price is reasonable.

        Args:
            v: Price value (can be None)

        Returns:
            Validated price or None

        Raises:
            ValueError: If price is unreasonably high (>$50,000)
        """
        if v is None:
            return None
        if v > Decimal("50000.00"):
            msg = "Price seems unreasonably high, please verify"
            raise ValueError(msg)
        return v

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        """Normalize category name.

        Args:
            v: Category name

        Returns:
            Title-cased category
        """
        return v.strip().title()

    model_config = {
        "frozen": True,  # Immutable
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }

    def get_primary_image(self) -> PartImage | None:
        """Get the primary product image.

        Returns:
            Primary image if exists, otherwise first image, otherwise None
        """
        if not self.images:
            return None

        # Find primary image
        for img in self.images:
            if img.is_primary:
                return img

        # Return first image if no primary set
        return self.images[0]
