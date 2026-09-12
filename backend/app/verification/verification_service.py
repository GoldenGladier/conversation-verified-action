from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class VerificationStatus(Enum):
    PROPOSED = "proposed"
    PATIENT_CONFIRMED = "patient_confirmed"
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
    chat_id: int | None = None
    doctor_user_id: int | None = None
    patient_user_id: int | None = None
    status: VerificationStatus = VerificationStatus.PROPOSED
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: datetime | None = None
    patient_confirmed_by: int | None = None
    patient_confirmed_at: datetime | None = None
    patient_confirmation_source: str | None = None
    doctor_approved_by: int | None = None
    doctor_approved_at: datetime | None = None
    doctor_approval_source: str | None = None
    rejected_by_user_id: int | None = None
    rejection_source: str | None = None


class VerificationService:

    def __init__(self):
        self.pending_requests: dict[str, VerificationRequest] = {}

    def create_request(
        self,
        action: VerificationAction,
        description: str,
        payload: dict,
        chat_id: int | None = None,
        doctor_user_id: int | None = None,
        patient_user_id: int | None = None,
    ) -> VerificationRequest:
        request = VerificationRequest(
            id=str(uuid4()),
            action=action,
            description=description,
            payload=payload,
            chat_id=chat_id,
            doctor_user_id=doctor_user_id,
            patient_user_id=patient_user_id,
        )

        self.pending_requests[request.id] = request

        return request

    def get_request(
        self,
        request_id: str,
    ) -> VerificationRequest:
        request = self.pending_requests.get(request_id)

        if not request:
            raise ValueError("Verification request not found")

        return request

    def get_proposed_request_for_chat(
        self,
        chat_id: int,
    ) -> VerificationRequest | None:
        requests = [
            request
            for request in self.pending_requests.values()
            if (
                request.chat_id == chat_id
                and request.status == VerificationStatus.PROPOSED
            )
        ]

        if len(requests) > 1:
            raise ValueError(
                "Multiple proposed verification requests exist for this chat"
            )

        return requests[0] if requests else None

    def record_patient_confirmation(
        self,
        request_id: str,
        patient_user_id: int,
        source: str,
    ) -> VerificationRequest:
        request = self.get_request(request_id)

        if request.status != VerificationStatus.PROPOSED:
            raise ValueError(
                "Verification request must be in proposed state"
            )

        if patient_user_id != request.patient_user_id:
            raise ValueError("Only the assigned patient can confirm")

        request.patient_confirmed_by = patient_user_id
        request.patient_confirmed_at = datetime.now(timezone.utc)
        request.patient_confirmation_source = source
        request.status = VerificationStatus.PATIENT_CONFIRMED

        return request

    def approve_by_doctor(
        self,
        request_id: str,
        doctor_user_id: int,
        source: str,
    ) -> VerificationRequest:
        request = self.get_request(request_id)

        if request.status != VerificationStatus.PATIENT_CONFIRMED:
            raise ValueError(
                "Verification request must be patient confirmed before approval"
            )

        if doctor_user_id != request.doctor_user_id:
            raise ValueError("Only the assigned doctor can approve")

        request.doctor_approved_by = doctor_user_id
        request.doctor_approved_at = datetime.now(timezone.utc)
        request.doctor_approval_source = source
        request.status = VerificationStatus.APPROVED
        request.resolved_at = request.doctor_approved_at

        return request

    def reject(
        self,
        request_id: str,
        user_id: int,
        source: str,
    ) -> VerificationRequest:
        request = self.get_request(request_id)

        if request.status in {
            VerificationStatus.APPROVED,
            VerificationStatus.REJECTED,
        }:
            raise ValueError(
                "Approved or rejected verification requests cannot be rejected"
            )

        if user_id not in {
            request.doctor_user_id,
            request.patient_user_id,
        }:
            raise ValueError("Only the assigned doctor or patient can reject")

        request.status = VerificationStatus.REJECTED
        request.rejected_by_user_id = user_id
        request.rejection_source = source
        request.resolved_at = datetime.now(timezone.utc)

        return request
