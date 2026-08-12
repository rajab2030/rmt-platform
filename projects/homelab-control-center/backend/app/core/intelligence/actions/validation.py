from pydantic import BaseModel


class ValidationResult(BaseModel):

    execution_id: str

    valid: bool

    expected_state: str

    observed_state: str

    message: str = ""
