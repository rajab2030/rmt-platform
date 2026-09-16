from datetime import date

from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator


class CurrencyModel(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency must be a three-letter ISO-4217 code")
        return value


class BootstrapInput(CurrencyModel):
    organization_name: str = Field(min_length=1, max_length=120)
    budget_name: str = Field(min_length=1, max_length=120)
    owner_type: str = "department"
    owner_name: str = ""
    period_start: date
    period_end: date
    allocation_minor: StrictInt = Field(gt=0)
    owner_principal: str = Field(min_length=1, max_length=120)
    requester_principal: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @model_validator(mode="after")
    def valid_period(self):
        if self.period_start > self.period_end:
            raise ValueError("period_start must not be after period_end")
        if self.owner_type not in {"department", "project"}:
            raise ValueError("owner_type must be department or project")
        return self


class PurchaseRequestInput(CurrencyModel):
    budget_id: str = Field(min_length=1)
    amount_minor: StrictInt = Field(gt=0)
    purpose: str = Field(min_length=1, max_length=1000)
    supporting_reference: str = Field(default="", max_length=1000)


class PurchaseRequestVersionInput(CurrencyModel):
    amount_minor: StrictInt = Field(gt=0)
    purpose: str = Field(min_length=1, max_length=1000)
    supporting_reference: str = Field(default="", max_length=1000)


class DecisionInput(BaseModel):
    decision: str
    reason: str = Field(default="", max_length=1000)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        return value


class IdempotencyInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)


class SettlementInput(IdempotencyInput):
    amount_minor: StrictInt = Field(gt=0)


class AdjustmentInput(IdempotencyInput, CurrencyModel):
    amount_minor: StrictInt
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("amount_minor")
    @classmethod
    def nonzero_amount(cls, value: int) -> int:
        if value == 0:
            raise ValueError("adjustment cannot be zero")
        return value


class CorrectionInput(AdjustmentInput):
    correction_of: str = Field(min_length=1)
