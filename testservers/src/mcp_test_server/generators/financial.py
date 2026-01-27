"""Financial PII data generator."""

from typing import Any, ClassVar
import random

from .base import BaseGenerator


class FinancialGenerator(BaseGenerator):
    """Generator for financial PII data (credit cards, bank accounts, tax IDs)."""

    category: ClassVar[str] = "financial"
    supported_types: ClassVar[list[str]] = ["credit_card", "bank_account", "tax_id", "financial"]

    # Card type prefixes (simplified)
    CARD_PREFIXES = {
        "visa": ["4"],
        "mastercard": ["51", "52", "53", "54", "55"],
        "amex": ["34", "37"],
        "discover": ["6011", "65"],
    }

    # Sample bank names
    BANK_NAMES = [
        "First National Bank",
        "Citizens Bank",
        "Chase Bank",
        "Bank of America",
        "Wells Fargo",
        "US Bank",
        "Capital One",
        "PNC Bank",
    ]

    def generate(self, pii_type: str) -> dict[str, Any]:
        """Generate financial PII data."""
        generators = {
            "credit_card": self._generate_credit_card,
            "bank_account": self._generate_bank_account,
            "tax_id": self._generate_tax_id,
            "financial": self._generate_full_financial,
        }

        if pii_type not in generators:
            raise ValueError(f"Unsupported PII type: {pii_type}")

        return generators[pii_type]()

    def _generate_credit_card(self) -> dict[str, Any]:
        """Generate credit card data (fake, not valid)."""
        card_type = random.choice(list(self.CARD_PREFIXES.keys()))
        prefix = random.choice(self.CARD_PREFIXES[card_type])

        # Generate remaining digits
        remaining_length = 16 - len(prefix) if card_type != "amex" else 15 - len(prefix)
        remaining = "".join([str(random.randint(0, 9)) for _ in range(remaining_length)])
        number = prefix + remaining

        # Format with spaces
        if card_type == "amex":
            formatted = f"{number[:4]} {number[4:10]} {number[10:]}"
        else:
            formatted = " ".join([number[i : i + 4] for i in range(0, 16, 4)])

        # Expiry date (MM/YY)
        month = random.randint(1, 12)
        year = random.randint(25, 30)
        expiry = f"{month:02d}/{year:02d}"

        # CVV
        cvv_length = 4 if card_type == "amex" else 3
        cvv = "".join([str(random.randint(0, 9)) for _ in range(cvv_length)])

        return {
            "number": formatted,
            "expiry": expiry,
            "cvv": cvv,
            "card_type": card_type,
        }

    def _generate_bank_account(self) -> dict[str, Any]:
        """Generate bank account data."""
        # Account number (10-12 digits)
        account_length = random.randint(10, 12)
        account_number = "".join([str(random.randint(0, 9)) for _ in range(account_length)])

        # Routing number (9 digits, starts with valid prefix)
        routing_prefix = random.choice(["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
        routing_rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
        routing_number = routing_prefix + routing_rest

        return {
            "account_number": account_number,
            "routing_number": routing_number,
            "bank_name": random.choice(self.BANK_NAMES),
            "account_type": random.choice(["checking", "savings"]),
        }

    def _generate_tax_id(self) -> dict[str, Any]:
        """Generate tax ID (EIN) data."""
        # EIN format: XX-XXXXXXX
        prefix = random.randint(10, 99)
        suffix = random.randint(1000000, 9999999)
        return {
            "ein": f"{prefix:02d}-{suffix:07d}",
            "business_name": self.faker.company(),
        }

    def _generate_full_financial(self) -> dict[str, Any]:
        """Generate complete financial PII record."""
        return {
            "credit_card": self._generate_credit_card(),
            "bank_account": self._generate_bank_account(),
            "tax_id": self._generate_tax_id(),
        }
