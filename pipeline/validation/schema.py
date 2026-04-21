from typing import Dict, Any
from pydantic import BaseModel, ValidationError


class InvoiceSchema(BaseModel):
    invoice_number: str | None = None
    vendor_name: str | None = None
    total_amount: str | None = None
    issue_date: str | None = None
    due_date: str | None = None

    class Config:
        extra = "allow"


class SchemaValidator:
    def validate(self, data: Dict[str, Any], schema_cls=InvoiceSchema) -> tuple[bool, Dict[str, Any]]:
        """Validate extracted data against schema."""
        try:
            validated = schema_cls(**data)
            return True, validated.model_dump()
        except ValidationError as e:
            return False, {"errors": e.errors()}
