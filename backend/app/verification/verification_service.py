from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from datetime import datetime, timezone

class VerificationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class VerificationAction(str, Enum):
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    CANCEL_CALENDAR_EVENT = "cancel_calendar_event"
    GET_AVAILABLE_SLOTS = "get_available_slots"

@dataclass
class VerificationRequest:
    id: str
    action: VerificationAction
    description: str
    payload: dict
    status: VerificationStatus = VerificationStatus.PENDING
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: datetime | None = None


class VerificationService:

    def __init__(self):
        self.pending_requests: dict[str, VerificationRequest] = {}

    def create_request(
        self,
        action: VerificationAction,
        description: str,
        payload: dict
    ) -> VerificationRequest:

        request = VerificationRequest(
            id=str(uuid4()),
            action=action,
            description=description,
            payload=payload
        )

        self.pending_requests[request.id] = request

        return request

    def get_request(
        self,
        request_id: str
    ) -> VerificationRequest:

        request = self.pending_requests.get(request_id)

        if not request:
            raise ValueError("Verification request not found")

        return request

    def approve(
        self,
        request_id: str
    ) -> VerificationRequest:

        request = self.get_request(request_id)

        if request.status != VerificationStatus.PENDING:
            raise ValueError(
                "Verification request has already been resolved"
            )

        request.status = VerificationStatus.APPROVED
        request.resolved_at = datetime.now(timezone.utc)

        return request

    def reject(
        self,
        request_id: str
    ) -> VerificationRequest:

        request = self.get_request(request_id)

        if request.status != VerificationStatus.PENDING:
            raise ValueError(
                "Verification request has already been resolved"
            )

        request.status = VerificationStatus.REJECTED
        request.resolved_at = datetime.now(timezone.utc)

        return request