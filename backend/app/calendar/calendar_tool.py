from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime


class CalendarTool:

    def __init__(self):
        self.events: list[CalendarEvent] = []

    def get_available_slots(
        self, 
        date: str,        
        start_time: str = "09:00",
        end_time: str = "18:00"
    ) -> list[str]:
        """
        Returns available appointment slots.
        This is currently a mock implementation.
        """

        slots = [
            "10:00",
            "11:30",
            "13:00",
            "16:00",
            "17:30",
        ]

        return [
            slot
            for slot in slots
            if self.is_available(
                start=datetime.fromisoformat(f"{date}T{slot}"),
                duration_minutes=30
            )
        ]

    def is_available(
        self,
        start: datetime,
        duration_minutes: int
    ) -> bool:
        end = start + timedelta(minutes=duration_minutes)

        return not any(
            start < event.end and end > event.start
            for event in self.events
        )

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime
    ) -> CalendarEvent:
        """
        Creates and retains a mock calendar event.
        """

        if not self.is_available(
            start=start,
            duration_minutes=int((end - start).total_seconds() / 60)
        ):
            raise ValueError("Appointment overlaps with an existing event")

        event = CalendarEvent(
            title=title,
            start=start,
            end=end
        )

        self.events.append(event)

        return event
