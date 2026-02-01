"""MCP Test Server for PII data generation using FastMCP."""

import json
from typing import Literal

from faker import Faker
from mcp.server.fastmcp import FastMCP

fake = Faker()

from .generators import generator_registry
# Import generators to trigger auto-registration
from .generators import PersonalGenerator, IdentityGenerator, FinancialGenerator  # noqa: F401
from .fixtures import PERSONAL_FIXTURES, FINANCIAL_FIXTURES, MIXED_FIXTURES
from .fixtures.datasets import IDENTITY_FIXTURES

# Create FastMCP server instance with SSE support
mcp = FastMCP("pii-test-server", host="0.0.0.0")

# Valid PII types
PII_TYPES = Literal[
    "name", "email", "phone", "dob", "address", "personal",
    "ssn", "drivers_license", "passport", "identity",
    "credit_card", "bank_account", "tax_id", "financial",
]


@mcp.tool()
def generate_pii(pii_type: PII_TYPES) -> str:
    """Generate random PII test data of a specific type.

    Args:
        pii_type: Type of PII to generate (name, email, phone, dob, address, personal,
                  ssn, drivers_license, passport, identity, credit_card, bank_account,
                  tax_id, financial)
    """
    data = generator_registry.generate(pii_type)
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def generate_bulk_pii(pii_type: PII_TYPES, count: int = 5) -> str:
    """Generate multiple random PII records of a specific type.

    Args:
        pii_type: Type of PII to generate
        count: Number of records to generate (1-100, default 5)
    """
    count = max(1, min(count, 100))
    generator = generator_registry.get_by_type(pii_type)
    if not generator:
        return json.dumps({"error": f"Unknown PII type: {pii_type}"})
    data = generator.generate_bulk(pii_type, count)
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def list_pii_types() -> str:
    """List all available PII types organized by category."""
    types = generator_registry.list_types()
    return json.dumps(types, indent=2)


@mcp.tool()
def generate_full_record() -> str:
    """Generate a complete PII record with personal, identity, and financial data."""
    full_record = {
        "personal": generator_registry.generate("personal"),
        "identity": generator_registry.generate("identity"),
        "financial": generator_registry.generate("financial"),
    }
    return json.dumps(full_record, indent=2, default=str)


@mcp.tool()
def generate_text_with_pii(pii_type: PII_TYPES) -> str:
    """Generate lorem ipsum text containing embedded PII of the specified type.

    Args:
        pii_type: Type of PII to embed in the text
    """
    pii_data = generator_registry.generate(pii_type)
    lorem = fake.paragraph(nb_sentences=3)

    # Format PII value for embedding based on type
    if pii_type == "name":
        pii_value = pii_data["full_name"]
        text = f"{lorem} My name is {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "email":
        pii_value = pii_data["email"]
        text = f"{lorem} You can reach me at {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "phone":
        pii_value = pii_data["phone"]
        text = f"{lorem} Call me at {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "dob":
        pii_value = pii_data["dob"]
        text = f"{lorem} I was born on {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "address":
        pii_value = f"{pii_data['street']}, {pii_data['city']}, {pii_data['state']} {pii_data['zip_code']}"
        text = f"{lorem} I live at {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "ssn":
        pii_value = pii_data["ssn"]
        text = f"{lorem} My SSN is {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "drivers_license":
        pii_value = pii_data["number"]
        text = f"{lorem} My driver's license number is {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "passport":
        pii_value = pii_data["number"]
        text = f"{lorem} My passport number is {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "credit_card":
        pii_value = pii_data["number"]
        text = f"{lorem} Please charge my card {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "bank_account":
        pii_value = f"{pii_data['account_number']} (routing: {pii_data['routing_number']})"
        text = f"{lorem} My bank account is {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "tax_id":
        pii_value = pii_data["ein"]
        text = f"{lorem} Our company EIN is {pii_value}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "personal":
        name = pii_data["name"]["full_name"]
        email = pii_data["email"]["email"]
        phone = pii_data["phone"]["phone"]
        text = f"{lorem} My name is {name}, email me at {email} or call {phone}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "identity":
        ssn = pii_data["ssn"]["ssn"]
        dl = pii_data["drivers_license"]["number"]
        text = f"{lorem} My SSN is {ssn} and driver's license is {dl}. {fake.paragraph(nb_sentences=2)}"
    elif pii_type == "financial":
        card = pii_data["credit_card"]["number"]
        account = pii_data["bank_account"]["account_number"]
        text = f"{lorem} Use card {card} or account {account}. {fake.paragraph(nb_sentences=2)}"
    else:
        text = f"{lorem} {json.dumps(pii_data, default=str)} {fake.paragraph(nb_sentences=2)}"

    return text


@mcp.resource("pii://fixtures/personal")
def get_personal_fixtures() -> str:
    """Predefined personal PII test data (names, emails, phones, addresses)."""
    return json.dumps(PERSONAL_FIXTURES, indent=2)


@mcp.resource("pii://fixtures/identity")
def get_identity_fixtures() -> str:
    """Predefined identity PII test data (SSN, driver's license, passport)."""
    return json.dumps(IDENTITY_FIXTURES, indent=2)


@mcp.resource("pii://fixtures/financial")
def get_financial_fixtures() -> str:
    """Predefined financial PII test data (credit cards, bank accounts, tax IDs)."""
    return json.dumps(FINANCIAL_FIXTURES, indent=2)


@mcp.resource("pii://fixtures/mixed")
def get_mixed_fixtures() -> str:
    """Complete PII records combining personal, identity, and financial data."""
    return json.dumps(MIXED_FIXTURES, indent=2)


def main():
    """Run the MCP HTTP server."""
    import os
    import uvicorn

    host = os.environ.get("MCP_HOST", mcp.settings.host)
    port = int(os.environ.get("MCP_PORT", mcp.settings.port))

    config = uvicorn.Config(
        mcp.streamable_http_app(),
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
