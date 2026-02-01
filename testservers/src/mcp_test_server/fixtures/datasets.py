"""Predefined PII test datasets with hardcoded values."""

# Personal PII fixtures
PERSONAL_FIXTURES = [
    {
        "name": {
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
        },
        "email": {"email": "john.smith@example.com"},
        "phone": {"phone": "(555) 123-4567", "country_code": "+1"},
        "dob": {"dob": "1985-03-15", "age": 39},
        "address": {
            "street": "123 Main Street",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701",
            "country": "USA",
        },
    },
    {
        "name": {
            "first_name": "Jane",
            "last_name": "Doe",
            "full_name": "Jane Doe",
        },
        "email": {"email": "jane.doe@testmail.org"},
        "phone": {"phone": "(555) 987-6543", "country_code": "+1"},
        "dob": {"dob": "1990-07-22", "age": 34},
        "address": {
            "street": "456 Oak Avenue",
            "city": "Portland",
            "state": "OR",
            "zip_code": "97201",
            "country": "USA",
        },
    },
    {
        "name": {
            "first_name": "Robert",
            "last_name": "Johnson",
            "full_name": "Robert Johnson",
        },
        "email": {"email": "r.johnson@company.net"},
        "phone": {"phone": "(555) 456-7890", "country_code": "+1"},
        "dob": {"dob": "1978-11-08", "age": 46},
        "address": {
            "street": "789 Pine Road",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "country": "USA",
        },
    },
]

# Financial PII fixtures
FINANCIAL_FIXTURES = [
    {
        "credit_card": {
            "number": "4532 1234 5678 9012",
            "expiry": "12/27",
            "cvv": "123",
            "card_type": "visa",
        },
        "bank_account": {
            "account_number": "1234567890",
            "routing_number": "021000021",
            "bank_name": "Chase Bank",
            "account_type": "checking",
        },
        "tax_id": {
            "ein": "12-3456789",
            "business_name": "Acme Corporation",
        },
    },
    {
        "credit_card": {
            "number": "5412 7534 9821 0036",
            "expiry": "08/26",
            "cvv": "456",
            "card_type": "mastercard",
        },
        "bank_account": {
            "account_number": "9876543210",
            "routing_number": "071000013",
            "bank_name": "Bank of America",
            "account_type": "savings",
        },
        "tax_id": {
            "ein": "98-7654321",
            "business_name": "Global Tech Inc",
        },
    },
    {
        "credit_card": {
            "number": "3782 822463 10005",
            "expiry": "03/28",
            "cvv": "7890",
            "card_type": "amex",
        },
        "bank_account": {
            "account_number": "5555666677",
            "routing_number": "026009593",
            "bank_name": "Wells Fargo",
            "account_type": "checking",
        },
        "tax_id": {
            "ein": "45-6789012",
            "business_name": "Smith & Associates LLC",
        },
    },
]

# Identity PII fixtures
IDENTITY_FIXTURES = [
    {
        "ssn": {"ssn": "123-45-6789"},
        "drivers_license": {
            "number": "D123456789012",
            "state": "CA",
            "expiry_date": "2027-05-15",
        },
        "passport": {
            "number": "123456789",
            "country": "USA",
            "expiry_date": "2030-08-20",
        },
    },
    {
        "ssn": {"ssn": "987-65-4321"},
        "drivers_license": {
            "number": "NY987654321",
            "state": "NY",
            "expiry_date": "2026-11-30",
        },
        "passport": {
            "number": "987654321",
            "country": "USA",
            "expiry_date": "2029-03-10",
        },
    },
    {
        "ssn": {"ssn": "456-78-9012"},
        "drivers_license": {
            "number": "TX456789012",
            "state": "TX",
            "expiry_date": "2028-02-28",
        },
        "passport": {
            "number": "456789012",
            "country": "USA",
            "expiry_date": "2031-12-01",
        },
    },
]

# Mixed fixtures combining all types
MIXED_FIXTURES = [
    {
        "personal": PERSONAL_FIXTURES[0],
        "identity": IDENTITY_FIXTURES[0],
        "financial": FINANCIAL_FIXTURES[0],
    },
    {
        "personal": PERSONAL_FIXTURES[1],
        "identity": IDENTITY_FIXTURES[1],
        "financial": FINANCIAL_FIXTURES[1],
    },
    {
        "personal": PERSONAL_FIXTURES[2],
        "identity": IDENTITY_FIXTURES[2],
        "financial": FINANCIAL_FIXTURES[2],
    },
]
