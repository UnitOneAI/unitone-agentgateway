"""Identity PII data generator."""

from datetime import date, timedelta
from typing import Any, ClassVar
import random

from .base import BaseGenerator


class IdentityGenerator(BaseGenerator):
    """Generator for identity PII data (SSN, driver's license, passport)."""

    category: ClassVar[str] = "identity"
    supported_types: ClassVar[list[str]] = ["ssn", "drivers_license", "passport", "identity"]

    # US state abbreviations for driver's license
    US_STATES = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    ]

    def generate(self, pii_type: str) -> dict[str, Any]:
        """Generate identity PII data."""
        generators = {
            "ssn": self._generate_ssn,
            "drivers_license": self._generate_drivers_license,
            "passport": self._generate_passport,
            "identity": self._generate_full_identity,
        }

        if pii_type not in generators:
            raise ValueError(f"Unsupported PII type: {pii_type}")

        return generators[pii_type]()

    def _generate_ssn(self) -> dict[str, Any]:
        """Generate SSN (fake, not valid)."""
        # Generate fake SSN pattern (never starts with 9, 666, or 000)
        area = random.randint(1, 899)
        if area == 666:
            area = 667
        group = random.randint(1, 99)
        serial = random.randint(1, 9999)
        return {"ssn": f"{area:03d}-{group:02d}-{serial:04d}"}

    def _generate_drivers_license(self) -> dict[str, Any]:
        """Generate driver's license data."""
        state = random.choice(self.US_STATES)
        # Generate state-style license number
        number = f"{state}{random.randint(100000000, 999999999)}"
        expiry = date.today() + timedelta(days=random.randint(365, 365 * 5))
        return {
            "number": number,
            "state": state,
            "expiry_date": expiry.isoformat(),
        }

    def _generate_passport(self) -> dict[str, Any]:
        """Generate passport data."""
        # US passport numbers are 9 digits
        number = f"{random.randint(100000000, 999999999)}"
        expiry = date.today() + timedelta(days=random.randint(365, 365 * 10))
        return {
            "number": number,
            "country": "USA",
            "expiry_date": expiry.isoformat(),
        }

    def _generate_full_identity(self) -> dict[str, Any]:
        """Generate complete identity PII record."""
        return {
            "ssn": self._generate_ssn(),
            "drivers_license": self._generate_drivers_license(),
            "passport": self._generate_passport(),
        }
