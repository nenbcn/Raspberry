from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from topics import Topics


TELEGRAM_API_TOKEN = '6085775716:AAE1gytGt3-qsRedO8MWEy6mhcTym4wbp00'
TOPICS = Topics()
HOUSE = None
ROOM = None
DEVICE = None
ACTION = None


async def pub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the publication conversation."""
    houses = Topics.houses
    await update.message.reply_text(
        "Starting publication process.\n"
        "Send /cancel to cancel the action.\n"
        "Select the house:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=houses,
            one_time_keyboard=True,
        ),
    )
    return HOUSE


async def room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected house and asks for a room."""
    user = update.message.from_user
    house = update.message.text
    logger.info("Selected house by user %s: %s", user.first_name, update.message.text)
    rooms = Topics.get_house_rooms(house=house)
    await update.message.reply_text(
        "Select the room of the house:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=rooms,
            one_time_keyboard=True,
        ),
    )
    return ROOM


async def device(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected room and asks for a device."""
    user = update.message.from_user
    room = update.message.text
    logger.info("Selected room by user %s: %s", user.first_name, update.message.text)
    devices = Topics.get_room_devices(room=room)
    await update.message.reply_text(
        "Select the device of the room:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=devices,
            one_time_keyboard=True,
        ),
    )
    return ROOM


async def action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected device and asks for an action."""
    user = update.message.from_user
    device = update.message.text
    logger.info("Selected device by user %s: %s", user.first_name, update.message.text)
    actions = Topics.get_device_actions(device=device)
    await update.message.reply_text(
        "Select the action for the device:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=actions,
            one_time_keyboard=True,
        ),
    )
    action = update.message.text
    await update.message.reply_text(f"Performing action: {action}.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("TOKEN").build()

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HOUSE: [MessageHandler(filters.Regex("^(Boy|Girl|Other)$"), gender)],
            ROOM: [MessageHandler(filters.PHOTO, photo)],
            DEVICE: [MessageHandler(filters.LOCATION, location)],
            ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()