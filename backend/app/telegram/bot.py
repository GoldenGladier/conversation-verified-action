from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from app.agent.agent import Agent
from app.config import settings

agent = Agent()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola 👋\n"
        "Soy Admin Agent Tomato 🍅.\n\n"
        "Estoy listo para ayudarte."
    )

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message.text

    conversation_id = str(update.effective_chat.id)

    response = agent.process_message(
        message,
        conversation_id
    )
    
    if response.requires_verification:

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Aprobar",
                    callback_data=f"verify:approve:{response.verification_id}"
                ),
                InlineKeyboardButton(
                    "❌ Rechazar",
                    callback_data=f"verify:reject:{response.verification_id}"
                ),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            response.message,
            reply_markup=reply_markup
        )

        return

    await update.message.reply_text(response.message)

async def handle_verification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    await query.answer()

    action, verification_id = query.data.split(":", 2)[1:]

    try:

        if action == "approve":
            request, result = agent.approve_verification(
                verification_id
            )

            await query.edit_message_text(
                result
            )

        elif action == "reject":
            request = agent.reject_verification(
                verification_id
            )

            await query.edit_message_text(
                "❌ Acción rechazada.\n\n"
                f"{request.description}"
            )

    except ValueError as error:

        await query.edit_message_text(
            f"⚠️ No se pudo procesar la solicitud:\n{error}"
        )

def create_bot() -> Application:
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.add_handler(
        CallbackQueryHandler(handle_verification)
    )

    return application