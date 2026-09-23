from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime
from app.models.alert import AlertType, AlertSeverity


class AlertResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    related_amount: Decimal | None
    related_date: date | None
    is_read: bool
    is_dismissed: bool
    is_resolved: bool
    commitment_id: uuid.UUID | None
    receivable_id: uuid.UUID | None
    fired_at: datetime

    model_config = {"from_attributes": True}
