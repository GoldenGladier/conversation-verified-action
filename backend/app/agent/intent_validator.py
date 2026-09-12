from app.agent.action_intent import ActionIntent
from app.verification.verification_service import (
    VerificationAction,
)


class IntentValidator:

    def validate(
        self,
        intent: ActionIntent
    ) -> list[str]:

        missing_fields = []

        if intent.action == VerificationAction.CREATE_CALENDAR_EVENT:

            if not intent.patient_name:
                missing_fields.append("patient_name")

            if not intent.date:
                missing_fields.append("date")

            if not intent.start_time:
                missing_fields.append("start_time")

            # if not intent.duration_minutes:
            #     missing_fields.append("duration_minutes")

        return missing_fields