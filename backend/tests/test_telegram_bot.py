import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.agent.agent import Agent, AgentResponse
from app.verification.verification_service import VerificationAction


DOCTOR_USER_ID = 101
PATIENT_USER_ID = 202
VERIFICATION_ID = "verification-id"


class FakeCalendar:

    def get_available_slots(self, *args, **kwargs):
        return []

    def create_event(self, *args, **kwargs):
        raise AssertionError("CalendarTool should be mocked in these tests")


with patch("app.agent.agent.CalendarTool", FakeCalendar):
    from app.telegram import bot


class FailingApprovalAgent:

    def approve_verification(self, verification_id, actor_user_id, source):
        assert verification_id == VERIFICATION_ID
        assert actor_user_id == PATIENT_USER_ID
        assert source == "telegram_callback"
        raise ValueError("Only the assigned doctor can approve")


class SuccessfulApprovalAgent:

    def approve_verification(self, verification_id, actor_user_id, source):
        assert verification_id == VERIFICATION_ID
        assert actor_user_id == DOCTOR_USER_ID
        assert source == "telegram_callback"
        return AgentResponse(message="Cita autorizada por el doctor.")


def make_update(action: str, actor_user_id: int):
    query = SimpleNamespace(
        data=f"verify:{action}:{VERIFICATION_ID}",
        from_user=SimpleNamespace(id=actor_user_id),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    return SimpleNamespace(callback_query=query), query


def make_patient_confirmed_agent():
    callback_agent = Agent(
        doctor_user_id=DOCTOR_USER_ID,
        patient_user_id=PATIENT_USER_ID,
        calendar=FakeCalendar(),
    )
    request = callback_agent.verification.create_request(
        action=VerificationAction.CREATE_CALENDAR_EVENT,
        description="Create appointment",
        payload={},
        chat_id=303,
        doctor_user_id=DOCTOR_USER_ID,
        patient_user_id=PATIENT_USER_ID,
    )
    callback_agent.verification.record_patient_confirmation(
        request.id,
        PATIENT_USER_ID,
        "telegram_conversation",
    )
    return callback_agent, request


def test_unauthorized_patient_receives_alert_without_editing_message(
    monkeypatch,
):
    update, query = make_update("approve", PATIENT_USER_ID)
    monkeypatch.setattr(bot, "agent", FailingApprovalAgent())

    asyncio.run(bot.handle_verification(update, None))

    query.answer.assert_awaited_once_with(
        "No se pudo procesar la solicitud: "
        "Only the assigned doctor can approve",
        show_alert=True,
    )
    query.edit_message_text.assert_not_awaited()


def test_authorized_doctor_edits_message_and_removes_keyboard(monkeypatch):
    update, query = make_update("approve", DOCTOR_USER_ID)
    monkeypatch.setattr(bot, "agent", SuccessfulApprovalAgent())

    asyncio.run(bot.handle_verification(update, None))

    query.answer.assert_awaited_once_with()
    query.edit_message_text.assert_awaited_once_with(
        "Cita autorizada por el doctor.",
        reply_markup=None,
    )


def test_patient_cannot_cancel_patient_confirmed_request(monkeypatch):
    callback_agent, request = make_patient_confirmed_agent()
    update, query = make_update("reject", PATIENT_USER_ID)
    query.data = f"verify:reject:{request.id}"
    monkeypatch.setattr(bot, "agent", callback_agent)

    asyncio.run(bot.handle_verification(update, None))

    assert request.status.value == "patient_confirmed"
    query.answer.assert_awaited_once_with(
        "No se pudo procesar la solicitud: "
        "Only the assigned doctor can cancel after patient confirmation",
        show_alert=True,
    )
    query.edit_message_text.assert_not_awaited()


def test_doctor_can_cancel_patient_confirmed_request(monkeypatch):
    callback_agent, request = make_patient_confirmed_agent()
    update, query = make_update("reject", DOCTOR_USER_ID)
    query.data = f"verify:reject:{request.id}"
    monkeypatch.setattr(bot, "agent", callback_agent)

    asyncio.run(bot.handle_verification(update, None))

    assert request.status.value == "rejected"
    query.answer.assert_awaited_once_with()
    query.edit_message_text.assert_awaited_once_with(
        "Cita cancelada.",
        reply_markup=None,
    )
