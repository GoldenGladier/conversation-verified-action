import pytest

from app.agent.action_executor import ActionExecutor
from app.verification.verification_service import (
    VerificationAction,
    VerificationService,
    VerificationStatus,
)


DOCTOR_USER_ID = 101
PATIENT_USER_ID = 202
CHAT_ID = 303


def create_request(service: VerificationService):
    return service.create_request(
        action=VerificationAction.CREATE_CALENDAR_EVENT,
        description="Create a calendar event",
        payload={},
        chat_id=CHAT_ID,
        doctor_user_id=DOCTOR_USER_ID,
        patient_user_id=PATIENT_USER_ID,
    )


def patient_confirmed_request(service: VerificationService):
    request = create_request(service)
    service.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_callback",
    )
    return request


def test_new_verification_starts_proposed():
    request = create_request(VerificationService())

    assert request.status == VerificationStatus.PROPOSED


def test_get_proposed_request_for_chat_returns_the_single_proposal():
    service = VerificationService()
    request = create_request(service)

    assert service.get_proposed_request_for_chat(CHAT_ID) is request


def test_get_proposed_request_for_chat_returns_none_when_absent():
    service = VerificationService()

    assert service.get_proposed_request_for_chat(CHAT_ID) is None


def test_get_proposed_request_for_chat_ignores_resolved_requests():
    service = VerificationService()
    request = create_request(service)
    service.reject(request.id, PATIENT_USER_ID, "telegram_conversation")

    assert service.get_proposed_request_for_chat(CHAT_ID) is None


def test_get_proposed_request_for_chat_rejects_ambiguous_proposals():
    service = VerificationService()
    create_request(service)
    create_request(service)

    with pytest.raises(ValueError, match="Multiple proposed"):
        service.get_proposed_request_for_chat(CHAT_ID)


def test_patient_confirmation_never_executes_an_action(monkeypatch):
    service = VerificationService()
    request = create_request(service)
    executed = False

    def record_execution(*args, **kwargs):
        nonlocal executed
        executed = True

    monkeypatch.setattr(ActionExecutor, "execute", record_execution)

    confirmed = service.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_callback",
    )

    assert confirmed.status == VerificationStatus.PATIENT_CONFIRMED
    assert confirmed.patient_confirmed_by == PATIENT_USER_ID
    assert confirmed.patient_confirmed_at is not None
    assert confirmed.patient_confirmation_source == "telegram_callback"
    assert not executed


def test_wrong_telegram_user_cannot_confirm():
    service = VerificationService()
    request = create_request(service)

    with pytest.raises(ValueError, match="assigned patient"):
        service.record_patient_confirmation(
            request.id,
            999,
            "telegram_callback",
        )

    assert request.status == VerificationStatus.PROPOSED


def test_duplicate_patient_confirmation_is_rejected():
    service = VerificationService()
    request = patient_confirmed_request(service)

    with pytest.raises(ValueError, match="proposed state"):
        service.record_patient_confirmation(
            request.id,
            PATIENT_USER_ID,
            "telegram_callback",
        )

    assert request.patient_confirmed_by == PATIENT_USER_ID


def test_doctor_cannot_approve_before_patient_confirmation():
    service = VerificationService()
    request = create_request(service)

    with pytest.raises(ValueError, match="patient confirmed"):
        service.approve_by_doctor(
            request.id,
            DOCTOR_USER_ID,
            "telegram_callback",
        )


def test_wrong_telegram_user_cannot_approve():
    service = VerificationService()
    request = patient_confirmed_request(service)

    with pytest.raises(ValueError, match="assigned doctor"):
        service.approve_by_doctor(
            request.id,
            999,
            "telegram_callback",
        )


def test_patient_cannot_approve_after_patient_confirmation():
    service = VerificationService()
    request = patient_confirmed_request(service)

    with pytest.raises(ValueError, match="assigned doctor"):
        service.approve_by_doctor(
            request.id,
            PATIENT_USER_ID,
            "telegram_callback",
        )


def test_correct_doctor_can_approve_after_patient_confirmation():
    service = VerificationService()
    request = patient_confirmed_request(service)

    approved = service.approve_by_doctor(
        request.id,
        DOCTOR_USER_ID,
        "telegram_callback",
    )

    assert approved.status == VerificationStatus.APPROVED
    assert approved.doctor_approved_by == DOCTOR_USER_ID
    assert approved.doctor_approved_at is not None
    assert approved.doctor_approval_source == "telegram_callback"


def test_rejection_transitions_to_rejected():
    service = VerificationService()
    request = patient_confirmed_request(service)

    rejected = service.reject(
        request.id,
        DOCTOR_USER_ID,
        "telegram_callback",
    )

    assert rejected.status == VerificationStatus.REJECTED
    assert rejected.rejected_by_user_id == DOCTOR_USER_ID
    assert rejected.rejection_source == "telegram_callback"


def test_patient_can_reject_after_patient_confirmation():
    service = VerificationService()
    request = patient_confirmed_request(service)

    rejected = service.reject(
        request.id,
        PATIENT_USER_ID,
        "telegram_callback",
    )

    assert rejected.status == VerificationStatus.REJECTED
    assert rejected.rejected_by_user_id == PATIENT_USER_ID


def test_unassigned_user_cannot_reject():
    service = VerificationService()
    request = create_request(service)

    with pytest.raises(ValueError, match="assigned doctor or patient"):
        service.reject(request.id, 999, "telegram_callback")

    assert request.status == VerificationStatus.PROPOSED


def test_unassigned_user_cannot_reject_after_patient_confirmation():
    service = VerificationService()
    request = patient_confirmed_request(service)

    with pytest.raises(ValueError, match="assigned doctor or patient"):
        service.reject(request.id, 999, "telegram_callback")

    assert request.status == VerificationStatus.PATIENT_CONFIRMED


def test_approved_request_cannot_be_approved_again():
    service = VerificationService()
    request = patient_confirmed_request(service)
    service.approve_by_doctor(
        request.id,
        DOCTOR_USER_ID,
        "telegram_callback",
    )

    with pytest.raises(ValueError, match="patient confirmed"):
        service.approve_by_doctor(
            request.id,
            DOCTOR_USER_ID,
            "telegram_callback",
        )


def test_rejected_request_cannot_be_confirmed_or_approved():
    service = VerificationService()
    request = create_request(service)
    service.reject(request.id, PATIENT_USER_ID, "telegram_callback")

    with pytest.raises(ValueError, match="proposed state"):
        service.record_patient_confirmation(
            request.id,
            PATIENT_USER_ID,
            "telegram_callback",
        )

    with pytest.raises(ValueError, match="patient confirmed"):
        service.approve_by_doctor(
            request.id,
            DOCTOR_USER_ID,
            "telegram_callback",
        )
