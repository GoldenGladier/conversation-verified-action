from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.agent.action_intent import ActionIntent
from app.agent.conversation_state import ConversationState


@dataclass
class RecentMessage:
    sender_user_id: int | None
    sender_name: str | None
    message: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ConversationService:

    def __init__(self, recent_message_limit: int = 5):
        self.conversations: dict[str, ConversationState] = {}
        self.recent_messages: dict[str, list[RecentMessage]] = {}
        self.recent_message_limit = recent_message_limit

    def get(
        self,
        conversation_id: str
    ) -> ConversationState | None:

        return self.conversations.get(conversation_id)

    def create(
        self,
        conversation_id: str,
        intent: ActionIntent
    ) -> ConversationState:

        state = ConversationState(
            intent=intent
        )

        self.conversations[conversation_id] = state

        return state

    def update(
        self,
        conversation_id: str,
        intent: ActionIntent
    ) -> ConversationState:

        state = ConversationState(
            intent=intent
        )

        self.conversations[conversation_id] = state

        return state

    def clear(
        self,
        conversation_id: str
    ):

        self.conversations.pop(
            conversation_id,
            None
        )

    def add_recent_message(
        self,
        conversation_id: str,
        sender_user_id: int | None,
        sender_name: str | None,
        message: str,
    ) -> None:
        messages = self.recent_messages.setdefault(conversation_id, [])
        messages.append(
            RecentMessage(
                sender_user_id=sender_user_id,
                sender_name=sender_name,
                message=message,
            )
        )

        if len(messages) > self.recent_message_limit:
            del messages[:-self.recent_message_limit]

    def get_recent_messages(
        self,
        conversation_id: str,
    ) -> list[RecentMessage]:
        return list(self.recent_messages.get(conversation_id, []))

    def clear_recent_messages(
        self,
        conversation_id: str,
    ) -> None:
        self.recent_messages.pop(conversation_id, None)
