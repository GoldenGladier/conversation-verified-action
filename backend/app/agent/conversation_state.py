from dataclasses import dataclass

from app.agent.action_intent import ActionIntent


@dataclass
class ConversationState:
    intent: ActionIntent