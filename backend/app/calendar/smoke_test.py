import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from app.calendar.calendar_tool import CalendarTool


def main() -> None:
    load_dotenv()
    calendar = CalendarTool(
        credentials_path=os.getenv(
            "GOOGLE_CALENDAR_CREDENTIALS_PATH",
            "credentials.json",
        ),
        calendar_id=os.getenv("GOOGLE_CALENDAR_ID", ""),
        timezone=os.getenv(
            "GOOGLE_CALENDAR_TIMEZONE",
            "America/Mexico_City",
        ),
    )
    start = None
    for offset in range(0, 7):
        day = (datetime.now() + timedelta(days=offset)).date().isoformat()
        slots = calendar.get_available_slots(day)
        if slots:
            start = datetime.fromisoformat(f"{day}T{slots[0]}")
            break

    if start is None:
        raise ValueError("No free slots found in the next 7 days")

    end = start + timedelta(minutes=30)
    event = calendar.create_event(
        "Hackathon test",
        start,
        end,
    )
    print(event)
    if event.html_link:
        print(event.html_link)


if __name__ == "__main__":
    main()
