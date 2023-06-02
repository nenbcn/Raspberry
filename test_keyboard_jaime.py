import logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler
from topics import Topics

TELEGRAM_API_TOKEN = '6085775716:AAE1gytGt3-qsRedO8MWEy6mhcTym4wbp00'

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stages
SELECT_HOUSE, SELECT_ROOM, SELECT_DEVICE, SELECT_ACTION, END = range(5)
# topics instance
topics = Topics()

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje cuando se emite el comando /help."""
    logger.info("User call /help 1")
    help_message = (
        "ver 5 \n"
        "/sub - Inicia la selección de casa, habitación, dispositivo y acción.\n"
        "/pub - Inicia la selección de casa, habitación, dispositivo y acción.\n"
        "/cancel - Detiene la conversación actual.\n"
        "/help - Muestra este mensaje de ayuda."
    )
    await update.message.reply_text(help_message)

# Command /sub to start the bot
async def sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()  # Limpia los datos del usuario al inicio
    user = update.message.from_user
    logger.info("User %s started the conversation sub.", user.first_name)
    keyboard = [[InlineKeyboardButton(house, callback_data=house)] for house in topics.houses]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una casa", reply_markup=reply_markup)
    return SELECT_HOUSE

async def pub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()  # Limpia los datos del usuario al inicio
    user = update.message.from_user
    logger.info("User %s started the conversation pub.", user.first_name)
    keyboard = [[InlineKeyboardButton(house, callback_data=house)] for house in topics.houses]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una casa", reply_markup=reply_markup)
    return SELECT_HOUSE


async def select_house(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_house = query.data
    context.user_data['house'] = selected_house
    rooms = [room[1] for room in topics.rooms if room[0] == selected_house]
    keyboard = [[InlineKeyboardButton(room, callback_data=room)] for room in rooms]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Seleccionaste {selected_house}. Ahora selecciona una habitación", reply_markup=reply_markup)
    return SELECT_ROOM

async def select_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_room = query.data
    context.user_data['room'] = selected_room
    devices = [device[2] for device in topics.devices if device[0] == context.user_data['house'] and device[1] == selected_room]
    keyboard = [[InlineKeyboardButton(device, callback_data=device)] for device in devices]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Seleccionaste {selected_room}. Ahora selecciona un dispositivo", reply_markup=reply_markup)
    return SELECT_DEVICE

async def select_device(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_device = query.data
    context.user_data['device'] = selected_device
    actions = [action[3] for action in topics.actions if action[0] == context.user_data['house'] and action[1] == context.user_data['room'] and action[2] == selected_device]
    keyboard = [[InlineKeyboardButton(action, callback_data=action)] for action in actions]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Seleccionaste {selected_device}. Ahora selecciona una acción", reply_markup=reply_markup)
    return SELECT_ACTION

async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_action = query.data
    context.user_data['action'] = selected_action
    await query.edit_message_text(text=f"Seleccionaste {selected_action}. Configuración completa: {context.user_data['house']} / {context.user_data['room']} / {context.user_data['device']} / {context.user_data['action']}")
    return END

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("end")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="¡Hasta la próxima vez!")
    context.user_data.clear()  # Limpia los datos del usuario al final
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finaliza la conversación y manda un mensaje al usuario."""
    logger.info("User call /cancel")
    context.user_data.clear()  # Limpia los datos del usuario
    await update.message.reply_text('Deteniendo la conversación.')
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_TOKEN).build()
    


    conv_handler_sub = ConversationHandler(
        entry_points=[CommandHandler('sub', sub),],
        states={
            SELECT_HOUSE: [
                CallbackQueryHandler(select_house), 
                CommandHandler('cancel', cancel)
            ],
            SELECT_ROOM: [
                CallbackQueryHandler(select_room),
                CommandHandler('cancel', cancel)
            ],
            SELECT_DEVICE: [
                CallbackQueryHandler(select_device),
                CommandHandler('cancel', cancel)
            ],
            SELECT_ACTION: [
                CallbackQueryHandler(select_action),
                CommandHandler('cancel',cancel )
            ],
            END: [
                CallbackQueryHandler(end),
                CommandHandler('cancel', cancel)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

 # Añade el handler para el comando /help
  
    application.add_handler(conv_handler_sub)
 #   application.add_handler(CommandHandler("sub", sub))
    application.add_handler(CommandHandler("pub", pub))
    application.add_handler(CommandHandler("help", help))
    application.run_polling()



if __name__ == "__main__":
    main()

