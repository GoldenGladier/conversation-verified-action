from datetime import datetime
import json

from openai import OpenAI

from app.agent.conversation_service import RecentMessage
from app.agent.patient_confirmation_intent import PatientProposalResponse
from app.config import settings
from app.verification.verification_service import VerificationRequest


class PatientConfirmationDetector:

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def detect(
        self,
        message: str,
        proposal: VerificationRequest,
        recent_messages: list[RecentMessage],
        sender_role: str | None = None,
    ) -> PatientProposalResponse:
        proposal_context = {
            "description": proposal.description,
            "payload": proposal.payload,
            "created_at": proposal.created_at.isoformat(),
        }
        recent_context = [
            {
                "sender_user_id": recent.sender_user_id,
                "sender_name": recent.sender_name,
                "message": recent.message,
                "timestamp": recent.timestamp.isoformat(),
            }
            for recent in recent_messages
        ]

        response = self.client.responses.parse(
            model="gpt-5.6-luna",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Classify whether a patient message responds to the "
                        "active appointment proposal. Return confirm only for "
                        "a clear, unqualified acceptance of the exact proposed "
                        "terms. Return reject for a clear refusal. Return modify "
                        "when the patient requests or implies any change to the "
                        "date, time, duration, or another relevant term. Return "
                        "unrelated when the message responds to another topic or "
                        "there is insufficient evidence. If uncertain, always "
                        "return unrelated, never confirm. You classify text only "
                        "and cannot approve, execute, or change any request.\n\n"
                        f"Current date and time: {datetime.now().isoformat()}\n"
                        f"Sender role supplied by the application: {sender_role}\n"
                        "Active proposal:\n"
                        f"{json.dumps(proposal_context, ensure_ascii=False)}\n"
                        "Recent chat messages:\n"
                        f"{json.dumps(recent_context, ensure_ascii=False)}"
                    ),
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            text_format=PatientProposalResponse,
        )

        return response.output_parsed
