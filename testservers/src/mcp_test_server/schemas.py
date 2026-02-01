"""Pydantic models for PII data types."""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class PersonName(BaseModel):
    """Personal name data."""

    first_name: str
    last_name: str
    full_name: str


class EmailAddress(BaseModel):
    """Email address data."""

    email: str


class PhoneNumber(BaseModel):
    """Phone number data."""

    phone: str
    country_code: str = "+1"


class DateOfBirth(BaseModel):
    """Date of birth data."""

    dob: date
    age: int


class Address(BaseModel):
    """Physical address data."""

    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"


class SSN(BaseModel):
    """Social Security Number data."""

    ssn: str = Field(..., pattern=r"^\d{3}-\d{2}-\d{4}$")


class DriversLicense(BaseModel):
    """Driver's license data."""

    number: str
    state: str
    expiry_date: date


class Passport(BaseModel):
    """Passport data."""

    number: str
    country: str
    expiry_date: date


class CreditCard(BaseModel):
    """Credit card data."""

    number: str
    expiry: str
    cvv: str
    card_type: str


class BankAccount(BaseModel):
    """Bank account data."""

    account_number: str
    routing_number: str
    bank_name: str
    account_type: Literal["checking", "savings"]


class TaxID(BaseModel):
    """Tax ID (EIN) data."""

    ein: str = Field(..., pattern=r"^\d{2}-\d{7}$")
    business_name: str


class PersonalPII(BaseModel):
    """Combined personal PII record."""

    name: PersonName
    email: EmailAddress
    phone: PhoneNumber
    dob: DateOfBirth
    address: Address


class IdentityPII(BaseModel):
    """Combined identity PII record."""

    ssn: SSN
    drivers_license: DriversLicense
    passport: Passport


class FinancialPII(BaseModel):
    """Combined financial PII record."""

    credit_card: CreditCard
    bank_account: BankAccount
    tax_id: TaxID


class FullPIIRecord(BaseModel):
    """Complete PII record with all data types."""

    personal: PersonalPII
    identity: IdentityPII
    financial: FinancialPII


# Type mapping for generator lookup
PII_TYPE_MAP = {
    "name": PersonName,
    "email": EmailAddress,
    "phone": PhoneNumber,
    "dob": DateOfBirth,
    "address": Address,
    "ssn": SSN,
    "drivers_license": DriversLicense,
    "passport": Passport,
    "credit_card": CreditCard,
    "bank_account": BankAccount,
    "tax_id": TaxID,
    "personal": PersonalPII,
    "identity": IdentityPII,
    "financial": FinancialPII,
    "full": FullPIIRecord,
}

PII_CATEGORIES = {
    "personal": ["name", "email", "phone", "dob", "address"],
    "identity": ["ssn", "drivers_license", "passport"],
    "financial": ["credit_card", "bank_account", "tax_id"],
}
