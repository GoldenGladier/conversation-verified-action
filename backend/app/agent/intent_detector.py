from datetime import datetime

from openai import OpenAI

from app.agent.action_intent import ActionIntent
from app.config import settings


class IntentDetector:

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openai_api_key
        )

    def detect(
        self,
        message: str,
        context: str | None = None
    ) -> ActionIntent:

        current_date = datetime.now().date().isoformat()

        user_content = message

        if context:
            user_content = (
                "Context from the previous conversation:\n"
                f"{context}\n\n"
                "New user message:\n"
                f"{message}"
            )

        response = self.client.responses.parse(
            model="gpt-5.6-luna",
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an administrative assistant "
                        "for a dental clinic.\n\n"

                        f"Today's date is {current_date}.\n\n"

                        "Analyze the user's message and determine "
                        "whether they want to schedule a dental "
                        "appointment or query available appointment "
                        "slots.\n\n"

                        "If they want to schedule an appointment, "
                        "extract the patient name, date, time and "
                        "duration.\n\n"

                        "If they want to query available slots, "
                        "extract the date.\n\n"

                        "Resolve relative dates such as "
                        "'today', 'tomorrow', 'next Monday', etc. "
                        "using today's date as the reference.\n\n"

                        "When previous conversation context is "
                        "provided, use it to interpret the new user "
                        "message. The new message may only provide "
                        "one missing piece of information, such as "
                        "a time, duration, patient name, or date.\n\n"

                        "If there is no actionable request, "
                        "return an intent with action=null."
                    )
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            text_format=ActionIntent
        )

        return response.output_parsed