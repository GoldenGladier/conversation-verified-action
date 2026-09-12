from dataclasses import dataclass
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SLOT_MINUTES = 30


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    html_link: str | None = None


class CalendarTool:

    def __init__(
        self,
        credentials_path: str | None = None,
        calendar_id: str | None = None,
        timezone: str | None = None,
    ):
        if credentials_path is None or calendar_id is None or timezone is None:
            from app.config import settings
            credentials_path = (
                credentials_path
                or settings.google_calendar_credentials_path
            )
            calendar_id = calendar_id or settings.google_calendar_id
            timezone = timezone or settings.google_calendar_timezone

        self.credentials_path = credentials_path
        self.calendar_id = calendar_id
        self.timezone_name = timezone or "America/Mexico_City"
        self.timezone = ZoneInfo(self.timezone_name)

        if not self.calendar_id:
            raise ValueError(
                "GOOGLE_CALENDAR_ID is empty. "
                "Set it to your calendar ID (usually your Gmail), "
                "not 'primary'."
            )

        creds_file = self._resolve_credentials_path(
            self.credentials_path
        )
        credentials = service_account.Credentials.from_service_account_file(
            str(creds_file),
            scopes=SCOPES,
        )
        self.service = build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def get_available_slots(
        self,
        date: str,
        start_time: str = "09:00",
        end_time: str = "18:00",
    ) -> list[str]:
        day = datetime.fromisoformat(date).date()
        window_start = datetime.combine(
            day,
            time.fromisoformat(start_time),
            tzinfo=self.timezone,
        )
        window_end = datetime.combine(
            day,
            time.fromisoformat(end_time),
            tzinfo=self.timezone,
        )
        busy = self._list_busy(window_start, window_end)

        slots: list[str] = []
        slot_start = window_start
        duration = timedelta(minutes=SLOT_MINUTES)

        while slot_start + duration <= window_end:
            if self._is_free(slot_start, duration, busy):
                slots.append(slot_start.strftime("%H:%M"))
            slot_start += duration

        return slots

    def is_available(
        self,
        start: datetime,
        duration_minutes: int,
    ) -> bool:
        start = self._localize(start)
        duration = timedelta(minutes=duration_minutes)
        end = start + duration
        busy = self._list_busy(start, end)
        return self._is_free(start, duration, busy)

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
    ) -> CalendarEvent:
        start = self._localize(start)
        end = self._localize(end)
        duration_minutes = int((end - start).total_seconds() / 60)

        if duration_minutes <= 0:
            raise ValueError("Event end time must be after start time")

        if not self.is_available(start, duration_minutes):
            raise ValueError(
                "Appointment overlaps with an existing event"
            )

        body = {
            "summary": title,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": self.timezone_name,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": self.timezone_name,
            },
        }

        try:
            created = (
                self.service.events()
                .insert(calendarId=self.calendar_id, body=body)
                .execute()
            )
        except HttpError as error:
            raise ValueError(
                f"Could not create calendar event: {error}"
            ) from error

        return CalendarEvent(
            title=title,
            start=start,
            end=end,
            html_link=created.get("htmlLink"),
        )

    def _resolve_credentials_path(self, credentials_path: str) -> Path:
        path = Path(credentials_path)
        if not path.is_absolute():
            backend_root = Path(__file__).resolve().parents[2]
            candidates = [
                Path.cwd() / credentials_path,
                backend_root / credentials_path,
            ]
            path = next(
                (candidate for candidate in candidates if candidate.is_file()),
                candidates[0],
            )

        if not path.is_file():
            raise FileNotFoundError(
                f"Google Calendar credentials not found at {path}. "
                "Download the service account JSON and save it as "
                "backend/credentials.json."
            )

        return path

    def _localize(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self.timezone)
        return value.astimezone(self.timezone)

    def _parse_google_datetime(self, payload: dict) -> datetime:
        if "dateTime" in payload:
            parsed = datetime.fromisoformat(
                payload["dateTime"].replace("Z", "+00:00")
            )
            return parsed.astimezone(self.timezone)

        day = datetime.fromisoformat(payload["date"]).date()
        return datetime.combine(day, time.min, tzinfo=self.timezone)

    def _list_busy(
        self,
        start: datetime,
        end: datetime,
    ) -> list[tuple[datetime, datetime]]:
        try:
            result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except HttpError as error:
            raise ValueError(
                f"Could not read calendar events: {error}"
            ) from error

        busy: list[tuple[datetime, datetime]] = []
        for item in result.get("items", []):
            if item.get("status") == "cancelled":
                continue
            busy.append((
                self._parse_google_datetime(item["start"]),
                self._parse_google_datetime(item["end"]),
            ))
        return busy

    def _is_free(
        self,
        start: datetime,
        duration: timedelta,
        busy: list[tuple[datetime, datetime]],
    ) -> bool:
        end = start + duration
        return not any(
            start < busy_end and end > busy_start
            for busy_start, busy_end in busy
        )
