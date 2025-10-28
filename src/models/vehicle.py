"""Vehicle and compatibility data models.

This module defines models for vehicles and part compatibility mappings.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class Vehicle(BaseModel):
    """Vehicle model.

    Represents a specific vehicle make/model/year combination.

    Attributes:
        make: Vehicle manufacturer (e.g., 'Audi', 'BMW')
        model: Vehicle model (e.g., 'A4', '3 Series')
        year: Model year
        submodel: Optional submodel/trim (e.g., 'Quattro', 'M-Sport')
        engine: Engine specification (e.g., '2.0L L4', '3.0L V6')
        fuel_type: Fuel type (e.g., 'Gasoline', 'Diesel', 'Electric', 'Hybrid')
        aspiration: Engine aspiration (e.g., 'Turbocharged', 'Naturally Aspirated')
    """

    make: str = Field(..., min_length=1, max_length=100, description="Vehicle make")
    model: str = Field(..., min_length=1, max_length=100, description="Vehicle model")
    year: int = Field(..., ge=1900, le=2030, description="Model year")
    submodel: str | None = Field(None, max_length=100, description="Submodel/trim")
    engine: str | None = Field(None, max_length=100, description="Engine specification")
    fuel_type: str | None = Field(None, max_length=50, description="Fuel type")
    aspiration: str | None = Field(None, max_length=50, description="Engine aspiration")

    @field_validator("make", "model")
    @classmethod
    def normalize_text(cls, v: str) -> str:
        """Normalize make/model text.

        Args:
            v: Text to normalize

        Returns:
            Title-cased text
        """
        return v.strip().title()

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate year is reasonable.

        Args:
            v: Year value

        Returns:
            Validated year

        Raises:
            ValueError: If year is before 1950 or more than 2 years in future
        """
        min_year = 1950
        current_year = datetime.now(UTC).year
        if v < min_year:
            msg = "Year must be 1950 or later"
            raise ValueError(msg)
        if v > current_year + 2:
            msg = f"Year cannot be more than 2 years in the future ({current_year + 2})"
            raise ValueError(msg)
        return v

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }

    def __str__(self) -> str:
        """String representation.

        Returns:
            Human-readable vehicle description
        """
        base = f"{self.year} {self.make} {self.model}"
        if self.submodel:
            return f"{base} {self.submodel}"
        return base


class VehicleCompatibility(BaseModel):
    """Part-to-vehicle compatibility mapping.

    Links a part SKU to compatible vehicles.

    Attributes:
        part_sku: Part SKU this compatibility applies to
        vehicles: List of compatible vehicles
        notes: Optional compatibility notes (e.g., 'Requires adapter kit')
    """

    part_sku: str = Field(..., min_length=1, description="Part SKU")
    vehicles: list[Vehicle] = Field(..., min_length=1, description="Compatible vehicles")
    notes: str | None = Field(None, description="Compatibility notes")
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when compatibility data was scraped",
    )

    @field_validator("part_sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        """Validate SKU format.

        Args:
            v: SKU value

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

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }

    def get_year_range(self) -> tuple[int, int] | None:
        """Get the year range of compatible vehicles.

        Returns:
            Tuple of (min_year, max_year) or None if no vehicles
        """
        if not self.vehicles:
            return None

        years = [v.year for v in self.vehicles]
        return min(years), max(years)

    def is_compatible_with(self, vehicle: Vehicle) -> bool:
        """Check if a vehicle is in the compatibility list.

        Args:
            vehicle: Vehicle to check

        Returns:
            True if vehicle is compatible
        """
        return vehicle in self.vehicles
