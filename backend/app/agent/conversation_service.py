from app.agent.action_intent import ActionIntent
from app.agent.conversation_state import ConversationState


class ConversationService:

    def __init__(self):
        self.conversations: dict[str, ConversationState] = {}

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