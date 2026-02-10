"""Personal PII data generator."""

from datetime import date
from typing import Any, ClassVar

from .base import BaseGenerator


class PersonalGenerator(BaseGenerator):
    """Generator for personal PII data (names, emails, phones, DOB, addresses)."""

    category: ClassVar[str] = "personal"
    supported_types: ClassVar[list[str]] = ["name", "email", "phone", "dob", "address", "personal"]

    def generate(self, pii_type: str) -> dict[str, Any]:
        """Generate personal PII data."""
        generators = {
            "name": self._generate_name,
            "email": self._generate_email,
            "phone": self._generate_phone,
            "dob": self._generate_dob,
            "address": self._generate_address,
            "personal": self._generate_full_personal,
        }

        if pii_type not in generators:
            raise ValueError(f"Unsupported PII type: {pii_type}")

        return generators[pii_type]()

    def _generate_name(self) -> dict[str, Any]:
        """Generate name data."""
        first = self.faker.first_name()
        last = self.faker.last_name()
        return {
            "first_name": first,
            "last_name": last,
            "full_name": f"{first} {last}",
        }

    def _generate_email(self) -> dict[str, Any]:
        """Generate email address."""
        return {"email": self.faker.email()}

    def _generate_phone(self) -> dict[str, Any]:
        """Generate phone number in valid NANP format: (NXX) NXX-XXXX.

        NANP rules require the first digit of area code and exchange to be
        2-9 (not 0 or 1).  Random ###-format can produce 0xx exchanges like
        029 which Presidio's phone recognizer scores below min_score 0.3.
        """
        area = f"{self.faker.random_int(2, 9)}{self.faker.numerify('##')}"
        exchange = f"{self.faker.random_int(2, 9)}{self.faker.numerify('##')}"
        subscriber = self.faker.numerify("####")
        phone = f"({area}) {exchange}-{subscriber}"
        return {
            "phone": phone,
            "country_code": "+1",
        }

    def _generate_dob(self) -> dict[str, Any]:
        """Generate date of birth."""
        dob = self.faker.date_of_birth(minimum_age=18, maximum_age=90)
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return {
            "dob": dob.isoformat(),
            "age": age,
        }

    def _generate_address(self) -> dict[str, Any]:
        """Generate physical address."""
        return {
            "street": self.faker.street_address(),
            "city": self.faker.city(),
            "state": self.faker.state_abbr(),
            "zip_code": self.faker.zipcode(),
            "country": "USA",
        }

    def _generate_full_personal(self) -> dict[str, Any]:
        """Generate complete personal PII record."""
        return {
            "name": self._generate_name(),
            "email": self._generate_email(),
            "phone": self._generate_phone(),
            "dob": self._generate_dob(),
            "address": self._generate_address(),
        }
