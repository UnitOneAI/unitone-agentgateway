"""Web/networking PII data generator (Canadian SIN, URLs)."""

import random
from typing import Any, ClassVar

from .base import BaseGenerator


class WebGenerator(BaseGenerator):
    """Generator for web/networking PII data (Canadian SIN, URLs)."""

    category: ClassVar[str] = "web"
    supported_types: ClassVar[list[str]] = ["ca_sin", "url"]

    DOMAINS = [
        "example.com", "test-corp.org", "acme-inc.net", "globaltech.io",
        "mydomain.co.uk", "company.de", "startup.app", "enterprise.cloud",
    ]

    PATHS = [
        "/api/v1/users", "/dashboard", "/settings/profile", "/docs/guide",
        "/products/12345", "/account/billing", "/reports/2024/q3",
    ]

    def generate(self, pii_type: str) -> dict[str, Any]:
        """Generate web/networking PII data."""
        generators = {
            "ca_sin": self._generate_ca_sin,
            "url": self._generate_url,
        }

        if pii_type not in generators:
            raise ValueError(f"Unsupported PII type: {pii_type}")

        return generators[pii_type]()

    def _generate_ca_sin(self) -> dict[str, Any]:
        """Generate Canadian Social Insurance Number (SIN).

        Format: XXX-XXX-XXX (9 digits, first digit 1-9).
        """
        first = random.randint(1, 9)
        remaining = random.randint(10000000, 99999999)
        digits = f"{first}{remaining:08d}"
        formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:9]}"
        return {"sin": formatted}

    def _generate_url(self) -> dict[str, Any]:
        """Generate HTTP/HTTPS URL."""
        scheme = random.choice(["http", "https"])
        domain = random.choice(self.DOMAINS)
        path = random.choice(self.PATHS)
        has_query = random.choice([True, False])
        url = f"{scheme}://{domain}{path}"
        if has_query:
            url += f"?id={random.randint(1, 9999)}"
        return {"url": url}
