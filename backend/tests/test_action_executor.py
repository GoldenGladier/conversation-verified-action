from datetime import datetime
from types import SimpleNamespace

from app.agent.action_executor import ActionExecutor
from app.verification.verification_service import (
    VerificationAction,
    VerificationRequest,
)


def test_action_executor_propagates_calendar_html_link():
    created = []

    class FakeCalendar:

        def create_event(self, title, start, end):
            created.append((title, start, end))
            return SimpleNamespace(
                html_link="https://calendar.google.test/event",
            )

    request = VerificationRequest(
        id="request-id",
        action=VerificationAction.CREATE_CALENDAR_EVENT,
        description="Create appointment",
        payload={
            "patient_name": "Ana",
            "date": "2026-09-15",
            "start_time": "10:00",
            "duration_minutes": 30,
        },
    )

    result = ActionExecutor(FakeCalendar()).execute(request)

    assert created == [
        (
            "Cita - Ana",
            datetime(2026, 9, 15, 10, 0),
            datetime(2026, 9, 15, 10, 30),
        )
    ]
    assert "https://calendar.google.test/event" in result
