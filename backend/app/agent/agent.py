from dataclasses import dataclass

from app.calendar.calendar_tool import CalendarTool
from app.verification.verification_service import (
    VerificationService,
    VerificationAction
)
from app.agent.action_executor import ActionExecutor
from app.agent.intent_detector import IntentDetector
from app.agent.intent_validator import IntentValidator
from app.agent.conversation_service import ConversationService


@dataclass
class AgentResponse:
    message: str
    requires_verification: bool = False
    verification_id: str | None = None


class Agent:

    def __init__(self):
        self.calendar = CalendarTool()
        self.verification = VerificationService()
        self.action_executor = ActionExecutor(self.calendar)
        self.intent_detector = IntentDetector()
        self.intent_validator = IntentValidator()
        self.conversations = ConversationService()

    def process_message(
        self,
        message: str,
        conversation_id: str
    ) -> AgentResponse:

        # 1. Check if there is an existing conversation
        current_state = self.conversations.get(
            conversation_id
        )

        # 2. Build context from previous conversation
        context = None

        if current_state:
            context = self._build_context(
                current_state.intent
            )

        # 3. Detect the new message
        intent = self.intent_detector.detect(
            message,
            context
        )

        # 4. If there is an existing conversation,
        #    handle the conversation transition
        if current_state:

            previous_intent = current_state.intent

            # If the previous conversation was about
            # available slots and the user selected a time,
            # we are now creating an appointment.
            if (
                previous_intent.action
                    == VerificationAction.GET_AVAILABLE_SLOTS
                and intent.start_time
            ):
                intent.action = (
                    VerificationAction.CREATE_CALENDAR_EVENT
                )

            # Merge the new information with
            # the previous conversation
            intent = self._merge_intents(
                previous_intent,
                intent
            )

        # 5. GET_AVAILABLE_SLOTS
        if intent.action == VerificationAction.GET_AVAILABLE_SLOTS:

            if not intent.date:
                return AgentResponse(
                    message=(
                        "¿Para qué fecha quieres "
                        "consultar disponibilidad?"
                    )
                )

            # Save the availability query so the next
            # message can use its context.
            self.conversations.update(
                conversation_id,
                intent
            )

            slots = self.calendar.get_available_slots(
                date=intent.date.isoformat()
            )

            if not slots:
                return AgentResponse(
                    message=(
                        f"No encontré horarios disponibles "
                        f"para el {intent.date}."
                    )
                )

            formatted_slots = "\n".join(
                f"• {slot}"
                for slot in slots
            )

            return AgentResponse(
                message=(
                    f"Estos son los horarios disponibles "
                    f"para el {intent.date}:\n\n"
                    f"{formatted_slots}\n\n"
                    "¿Cuál horario prefieres?"
                )
            )

        # 6. No actionable intent detected
        if intent is None or intent.action is None:
            return AgentResponse(
                message=f"Agent recibió: {message}"
            )

        # 7. Use 30 minutes as the default appointment duration
        if (
            intent.action == VerificationAction.CREATE_CALENDAR_EVENT
            and intent.duration_minutes is None
        ):
            intent.duration_minutes = 30

        # 8. Save the current state
        self.conversations.update(
            conversation_id,
            intent
        )

        # 9. Validate required information
        missing_fields = self.intent_validator.validate(
            intent
        )
        
        if missing_fields:

            missing_messages = {
                "patient_name": "el nombre del paciente",
                "date": "la fecha",
                "start_time": "la hora",
                "duration_minutes": "la duración de la cita",
            }

            missing = [
                missing_messages[field]
                for field in missing_fields
            ]

            return AgentResponse(
                message=(
                    "Para poder agendar la cita necesito "
                    "la siguiente información:\n\n"
                    + "\n".join(
                        f"• {field}"
                        for field in missing
                    )
                )
            )

        # 9. All information is available.
        #    Clear the conversation state.
        self.conversations.clear(
            conversation_id
        )

        # 10. Create verification request
        request = self.verification.create_request(
            action=intent.action,
            description=message,
            payload={
                "patient_name": intent.patient_name,
                "date": intent.date.isoformat(),
                "start_time": intent.start_time.isoformat(
                    timespec="minutes"
                ),
                "duration_minutes": intent.duration_minutes,
            }
        )

        # 11. Ask for approval
        return AgentResponse(
            message=(
                "Encontré una posible acción para realizar:\n\n"
                f"Paciente: {intent.patient_name}\n"
                f"Fecha: {intent.date}\n"
                f"Hora: {intent.start_time.strftime('%H:%M')}\n"
                f"Duración: {intent.duration_minutes} minutos\n\n"
                "Necesito tu confirmación antes de "
                "crear la cita."
            ),
            requires_verification=True,
            verification_id=request.id
        )

    def _merge_intents(
        self,
        previous,
        current
    ):

        if current.action is None:
            current.action = previous.action

        if current.patient_name is None:
            current.patient_name = previous.patient_name

        if current.date is None:
            current.date = previous.date

        if current.start_time is None:
            current.start_time = previous.start_time

        if current.duration_minutes is None:
            current.duration_minutes = previous.duration_minutes

        return current

    def approve_verification(
        self,
        verification_id: str
    ):

        request = self.verification.approve(
            verification_id
        )

        result = self.action_executor.execute(
            request
        )

        return request, result

    def reject_verification(
        self,
        verification_id: str
    ):

        return self.verification.reject(
            verification_id
        )

    def _build_context(self, intent) -> str:

        return (
            f"Action: {intent.action}\n"
            f"Patient: {intent.patient_name}\n"
            f"Date: {intent.date}\n"
            f"Start time: {intent.start_time}\n"
            f"Duration: {intent.duration_minutes}"
        )
