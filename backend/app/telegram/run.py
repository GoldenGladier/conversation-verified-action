from app.telegram.bot import create_bot


def main():
    application = create_bot()

    print("Telegram bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()