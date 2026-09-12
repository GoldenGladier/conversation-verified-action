from datetime import date, time

import pytest

from app.agent.action_intent import ActionIntent
from app.agent.agent import Agent
from app.agent.patient_confirmation_intent import PatientProposalResponse
from app.verification.verification_service import VerificationAction


DOCTOR_USER_ID = 101
PATIENT_USER_ID = 202
CHAT_ID = 303


class FakeIntentDetector:

    def detect(self, message: str, context: str | None = None) -> ActionIntent:
        return ActionIntent(
            action=VerificationAction.CREATE_CALENDAR_EVENT,
            patient_name="Ana",
            date=date(2026, 9, 15),
            start_time=time(10, 0),
            duration_minutes=30,
        )


class FakeCalendar:

    def get_available_slots(self, *args, **kwargs):
        return []

    def create_event(self, *args, **kwargs):
        raise AssertionError("CalendarTool should be mocked in these tests")


class FakePatientConfirmationDetector:

    def __init__(self, decision: str = "confirm"):
        self.decision = decision
        self.calls = []

    def detect(
        self,
        message,
        proposal,
        recent_messages,
        sender_role=None,
    ):
        self.calls.append(
            (message, proposal, recent_messages, sender_role)
        )
        return PatientProposalResponse(decision=self.decision)


def make_agent(
    doctor_user_id: int | None = None,
    patient_user_id: int | None = None,
) -> Agent:
    agent = Agent(
        doctor_user_id=doctor_user_id,
        patient_user_id=patient_user_id,
        calendar=FakeCalendar(),
    )
    agent.intent_detector = FakeIntentDetector()
    return agent


def create_telegram_proposal(agent: Agent):
    response = agent.process_message(
        "Agenda una cita",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=DOCTOR_USER_ID,
        sender_name="Doctor Example",
    )
    return agent.verification.get_request(response.verification_id)


def test_legacy_process_message_still_creates_a_request():
    agent = make_agent()

    response = agent.process_message("Agenda una cita", "legacy")

    request = agent.verification.get_request(response.verification_id)
    assert response.requires_verification
    assert request.chat_id is None
    assert request.doctor_user_id is None
    assert request.patient_user_id is None


def test_configured_doctor_can_create_role_aware_proposal():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)

    response = agent.process_message(
        "Agenda una cita",
        "telegram-doctor",
        chat_id=CHAT_ID,
        sender_user_id=DOCTOR_USER_ID,
        sender_name="Dr. Example",
    )

    request = agent.verification.get_request(response.verification_id)
    assert response.requires_verification
    assert request.chat_id == CHAT_ID
    assert request.doctor_user_id == DOCTOR_USER_ID
    assert request.patient_user_id == PATIENT_USER_ID


def test_configured_patient_cannot_create_proposal_as_doctor():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)

    response = agent.process_message(
        "Agenda una cita",
        "telegram-patient",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
        sender_name="Patient Example",
    )

    assert not response.requires_verification
    assert "configured doctor" in response.message
    assert not agent.verification.pending_requests


def test_sender_name_does_not_change_authorization():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)

    response = agent.process_message(
        "Agenda una cita",
        "telegram-name",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
        sender_name="Dr. Example",
    )

    assert not response.requires_verification
    assert not agent.verification.pending_requests


def test_telegram_context_without_role_configuration_does_not_create_request():
    agent = make_agent()

    response = agent.process_message(
        "Agenda una cita",
        "telegram-unconfigured",
        chat_id=CHAT_ID,
        sender_user_id=DOCTOR_USER_ID,
    )

    assert not response.requires_verification
    assert "role configuration is missing" in response.message
    assert not agent.verification.pending_requests


def test_patient_confirmation_updates_request_without_executing_action(
    monkeypatch,
):
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector("confirm")
    agent.patient_confirmation_detector = detector
    request = create_telegram_proposal(agent)
    executed = False

    def record_execution(*args, **kwargs):
        nonlocal executed
        executed = True

    monkeypatch.setattr(agent.action_executor, "execute", record_execution)

    response = agent.process_message(
        "Sí, me queda bien",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
        sender_name="Patient Example",
    )

    assert request.patient_confirmed_by == PATIENT_USER_ID
    assert request.patient_confirmation_source == "telegram_conversation"
    assert response.show_doctor_approval_controls
    assert not executed
    assert len(detector.calls) == 1


def test_no_active_proposal_does_not_call_confirmation_detector():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector()
    agent.patient_confirmation_detector = detector

    agent.process_message(
        "Sí",
        "no-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )

    assert not detector.calls


def test_proposal_in_another_chat_does_not_confirm():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector()
    agent.patient_confirmation_detector = detector
    request = create_telegram_proposal(agent)

    agent.process_message(
        "Sí",
        "other-chat",
        chat_id=CHAT_ID + 1,
        sender_user_id=PATIENT_USER_ID,
    )

    assert not detector.calls
    assert request.status.value == "proposed"


def test_doctor_or_third_party_cannot_confirm_patient_proposal():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector()
    agent.patient_confirmation_detector = detector
    request = create_telegram_proposal(agent)

    agent.process_message(
        "Sí",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=DOCTOR_USER_ID,
    )
    agent.process_message(
        "Sí",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=999,
    )

    assert not detector.calls
    assert request.status.value == "proposed"


def test_unrelated_patient_message_keeps_proposal_active():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector("unrelated")
    agent.patient_confirmation_detector = detector
    request = create_telegram_proposal(agent)

    response = agent.process_message(
        "Sí, también revisamos el expediente",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )

    assert request.status.value == "proposed"
    assert not response.show_doctor_approval_controls


def test_patient_rejection_and_modification_reject_proposal():
    for decision in ("reject", "modify"):
        agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
        agent.patient_confirmation_detector = (
            FakePatientConfirmationDetector(decision)
        )
        request = create_telegram_proposal(agent)

        agent.process_message(
            "No puedo" if decision == "reject" else "Sí, pero a las 5",
            "telegram-proposal",
            chat_id=CHAT_ID,
            sender_user_id=PATIENT_USER_ID,
        )

        assert request.status.value == "rejected"


def test_resolved_proposal_cannot_be_confirmed_again():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector("confirm")
    agent.patient_confirmation_detector = detector
    request = create_telegram_proposal(agent)

    agent.process_message(
        "Sí",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )
    agent.process_message(
        "Sí otra vez",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )

    assert request.status.value == "patient_confirmed"
    assert len(detector.calls) == 1


def test_rejected_proposal_cannot_be_confirmed():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector("reject")
    agent.patient_confirmation_detector = detector
    request = create_telegram_proposal(agent)

    agent.process_message(
        "No puedo",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )
    agent.process_message(
        "Sí, ahora sí",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )

    assert request.status.value == "rejected"
    assert len(detector.calls) == 1


def test_confirmation_detector_receives_limited_recent_messages():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    detector = FakePatientConfirmationDetector("confirm")
    agent.patient_confirmation_detector = detector
    create_telegram_proposal(agent)

    for number in range(6):
        agent.conversations.add_recent_message(
            "telegram-proposal",
            999,
            None,
            f"message {number}",
        )

    agent.process_message(
        "Sí",
        "telegram-proposal",
        chat_id=CHAT_ID,
        sender_user_id=PATIENT_USER_ID,
    )

    recent_messages = detector.calls[0][2]
    assert len(recent_messages) == 5
    assert recent_messages[-1].message == "Sí"


def test_agent_approves_with_telegram_actor_and_executes_action(
    monkeypatch,
):
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    request = create_telegram_proposal(agent)
    agent.verification.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_conversation",
    )

    executed_requests = []

    def record_execution(executed_request):
        executed_requests.append(executed_request)
        return "Cita creada. Abrir en Calendar: https://calendar.test/event"

    monkeypatch.setattr(agent.action_executor, "execute", record_execution)

    response = agent.approve_verification(request.id, DOCTOR_USER_ID)

    assert request.status.value == "approved"
    assert request.doctor_approved_by == DOCTOR_USER_ID
    assert request.doctor_approval_source == "telegram_callback"
    assert response.verification_id == request.id
    assert response.message == (
        "Cita creada. Abrir en Calendar: https://calendar.test/event"
    )
    assert executed_requests == [request]


def test_patient_cannot_approve_or_execute_action(monkeypatch):
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    request = create_telegram_proposal(agent)
    agent.verification.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_conversation",
    )
    executed = False

    def record_execution(*args, **kwargs):
        nonlocal executed
        executed = True

    monkeypatch.setattr(agent.action_executor, "execute", record_execution)

    with pytest.raises(ValueError, match="assigned doctor"):
        agent.approve_verification(request.id, PATIENT_USER_ID)

    assert request.status.value == "patient_confirmed"
    assert not executed


def test_approval_before_patient_confirmation_does_not_execute_action(
    monkeypatch,
):
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    request = create_telegram_proposal(agent)
    executed = False

    def record_execution(*args, **kwargs):
        nonlocal executed
        executed = True

    monkeypatch.setattr(agent.action_executor, "execute", record_execution)

    with pytest.raises(ValueError, match="patient confirmed"):
        agent.approve_verification(request.id, DOCTOR_USER_ID)

    assert request.status.value == "proposed"
    assert not executed


def test_calendar_failure_does_not_return_a_success_response(monkeypatch):
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    request = create_telegram_proposal(agent)
    agent.verification.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_conversation",
    )

    def fail_execution(*args, **kwargs):
        raise ValueError("Could not create calendar event")

    monkeypatch.setattr(agent.action_executor, "execute", fail_execution)

    with pytest.raises(ValueError, match="Could not create calendar event"):
        agent.approve_verification(request.id, DOCTOR_USER_ID)

    assert request.status.value == "approved"


def test_duplicate_approval_executes_action_only_once(monkeypatch):
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    request = create_telegram_proposal(agent)
    agent.verification.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_conversation",
    )
    executions = 0

    def record_execution(*args, **kwargs):
        nonlocal executions
        executions += 1
        return "Cita creada"

    monkeypatch.setattr(agent.action_executor, "execute", record_execution)

    agent.approve_verification(request.id, DOCTOR_USER_ID)

    with pytest.raises(ValueError, match="patient confirmed"):
        agent.approve_verification(request.id, DOCTOR_USER_ID)

    assert executions == 1


def test_agent_doctor_rejects_with_telegram_actor_and_default_source():
    agent = make_agent(DOCTOR_USER_ID, PATIENT_USER_ID)
    request = create_telegram_proposal(agent)
    agent.verification.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_conversation",
    )

    response = agent.reject_verification(request.id, DOCTOR_USER_ID)

    assert request.status.value == "rejected"
    assert request.rejected_by_user_id == DOCTOR_USER_ID
    assert request.rejection_source == "telegram_callback"
    assert response.verification_id == request.id
