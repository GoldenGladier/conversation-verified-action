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
from app.agent.patient_confirmation_detector import (
    PatientConfirmationDetector,
)


@dataclass
class AgentResponse:
    message: str
    requires_verification: bool = False
    verification_id: str | None = None
    show_doctor_approval_controls: bool = False


class Agent:

    def __init__(
        self,
        doctor_user_id: int | None = None,
        patient_user_id: int | None = None,
    ):
        self.calendar = CalendarTool()
        self.verification = VerificationService()
        self.action_executor = ActionExecutor(self.calendar)
        self.intent_detector = IntentDetector()
        self.intent_validator = IntentValidator()
        self.conversations = ConversationService()
        self.patient_confirmation_detector = PatientConfirmationDetector()
        self.doctor_user_id = doctor_user_id
        self.patient_user_id = patient_user_id

    def process_message(
        self,
        message: str,
        conversation_id: str,
        *,
        chat_id: int | None = None,
        sender_user_id: int | None = None,
        sender_name: str | None = None,
    ) -> AgentResponse:

        if chat_id is not None and sender_user_id is not None:
            self.conversations.add_recent_message(
                conversation_id,
                sender_user_id,
                sender_name,
                message,
            )

            active_request = (
                self.verification.get_proposed_request_for_chat(chat_id)
            )

            if (
                active_request
                and sender_user_id == active_request.patient_user_id
            ):
                confirmation = self.patient_confirmation_detector.detect(
                    message,
                    active_request,
                    self.conversations.get_recent_messages(conversation_id),
                    sender_role="patient",
                )

                if confirmation.decision == "confirm":
                    request = self.verification.record_patient_confirmation(
                        active_request.id,
                        sender_user_id,
                        source="telegram_conversation",
                    )
                    self.conversations.clear_recent_messages(
                        conversation_id
                    )
                    return AgentResponse(
                        message=(
                            "El paciente confirmó la cita. Doctor, "
                            "¿quieres crearla?"
                        ),
                        verification_id=request.id,
                        show_doctor_approval_controls=True,
                    )

                if confirmation.decision == "reject":
                    self.verification.reject(
                        active_request.id,
                        sender_user_id,
                        source="telegram_conversation",
                    )
                    self.conversations.clear_recent_messages(
                        conversation_id
                    )
                    return AgentResponse(
                        message="El paciente rechazó la propuesta de cita."
                    )

                if confirmation.decision == "modify":
                    self.verification.reject(
                        active_request.id,
                        sender_user_id,
                        source="telegram_conversation",
                    )
                    self.conversations.clear_recent_messages(
                        conversation_id
                    )
                    return AgentResponse(
                        message=(
                            "El paciente rechazó los términos actuales. "
                            "El doctor debe crear una nueva propuesta."
                        )
                    )

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

        is_telegram_context = (
            chat_id is not None or sender_user_id is not None
        )

        if is_telegram_context:
            if (
                chat_id is None
                or sender_user_id is None
                or self.doctor_user_id is None
                or self.patient_user_id is None
            ):
                return AgentResponse(
                    message=(
                        "Telegram role configuration is missing. "
                        "Set DOCTOR_TELEGRAM_USER_ID and "
                        "PATIENT_TELEGRAM_USER_ID."
                    )
                )

            if sender_user_id != self.doctor_user_id:
                return AgentResponse(
                    message=(
                        "Only the configured doctor can propose "
                        "an appointment."
                    )
                )

            if self.verification.get_proposed_request_for_chat(chat_id):
                return AgentResponse(
                    message=(
                        "There is already an active appointment proposal "
                        "for this chat."
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
            },
            chat_id=chat_id,
            doctor_user_id=(
                self.doctor_user_id if is_telegram_context else None
            ),
            patient_user_id=(
                self.patient_user_id if is_telegram_context else None
            ),
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
        verification_id: str,
        actor_user_id: int,
        source: str = "telegram_callback",
    ) -> AgentResponse:
        request = self.verification.approve_by_doctor(
            verification_id,
            actor_user_id,
            source,
        )

        result = self.action_executor.execute(request)

        return AgentResponse(
            message=result,
            verification_id=request.id,
        )

    def reject_verification(
        self,
        verification_id: str,
        actor_user_id: int,
        source: str = "telegram_callback",
    ) -> AgentResponse:
        request = self.verification.reject(
            verification_id,
            actor_user_id,
            source,
        )

        return AgentResponse(
            message="Cita cancelada.",
            verification_id=request.id,
        )

    def _build_context(self, intent) -> str:

        return (
            f"Action: {intent.action}\n"
            f"Patient: {intent.patient_name}\n"
            f"Date: {intent.date}\n"
            f"Start time: {intent.start_time}\n"
            f"Duration: {intent.duration_minutes}"
        )
