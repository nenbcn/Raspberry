import logging
logging.basicConfig(
    format="%(asctime)s -- %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
import paho.mqtt.client as mqtt
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler
from topics import Topics
from typing import List




TELEGRAM_API_TOKEN = '6085775716:AAE1gytGt3-qsRedO8MWEy6mhcTym4wbp00'
MQTT_SERVER = '192.168.1.52'
MQTT_USER = 'nenbcn'
MQTT_PASSWORD = 'rikic0'
TOPICS = Topics()
MAX_RETRIES = 5  # Número máximo de intentos de conexión
# Stages
SELECT_HOUSE, SELECT_ROOM, SELECT_DEVICE, SELECT_ACTION = range(4)
# topics instance
topics = Topics()


# conecdtarse a mqtt
def setup_mqtt_client() -> mqtt.Client:
    """
    Crea y configura un cliente MQTT.

    :return: Cliente MQTT configurado.
    """
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
      
    for i in range(MAX_RETRIES):
        try:
            mqtt_client.connect(MQTT_SERVER)
            print(f"Conexión MQTT establecida en el intento {i+1}.")
            return mqtt_client
        except ConnectionRefusedError:
            if i < MAX_RETRIES - 1:  # no es el último intento
                time.sleep(5)  # espera antes de intentarlo de nuevo
            else:  # último intento
                print(f"No se pudo establecer la conexión MQTT después de {MAX_RETRIES} intentos.")
                return None

async def public_topic(mqtt_client, topic, payload):
    mqtt_client.publish(topic, payload)
    logger.info("Publish mqtt", topic, payload)

async def subscribe_to_topic(mqtt_client, topic):
    mqtt_client.subscribe(topic)
    logger.info("subscribe mqtt", topic)


async def handle_recon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /recon.

    :param update: Objeto de actualización de Telegram.
    :param context: Objeto de contexto de Telegram.
    """
    global mqtt_client  # Accedemos a la variable global mqtt_client
    mqtt_client = setup_mqtt_client()  # Intentamos establecer la conexión MQTT
    if mqtt_client is None:
        await update.message.reply_text("No se pudo reconectar al servidor MQTT.")
    else:
        await update.message.reply_text("Conexión MQTT reestablecida exitosamente.")
        logger.info("conexion mqtt ok")


# Define a few command handlers. These take the two arguments update and context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Envia un mensaje cuando se emite el comando /start.

    :param update: Objeto de actualización de Telegram.
    :param context: Objeto de contexto de Telegram.
    """
    user = update.effective_user
    print(user)
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        #reply_markup=ForceReply(selective=True),
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send a list of commands and their functions when the command /help is issued.

    :param update: Object representing an incoming update for your Telegram bot
    :param context: Object that contains the context of the callback being processed
    """
    help_text = """
    Aquí tienes algunos comandos que puedes usar:
    /start - Inicia la interacción con el bot
    /help - Muestra este mensaje de ayuda
    /pub - Inicia una secuencia de encuestas para seleccionar un tema para publicar
    /sub - Inicia una secuencia de encuestas para seleccionar un tema al que suscribirse
    /recon - Intenta reconectar al broker mqtt
    /cancel - Cancela el comando
    """
    await update.message.reply_text(help_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Echo del mensaje del usuario.
    :param update: Objeto de actualización de Telegram.
    :param context: Objeto de contexto de Telegram.
    """
    await update.message.reply_text(update.message.text)


# Command /sub to start the bot
async def sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    """
    context.user_data.clear()  # Limpia los datos del usuario al inicio
    
    user = update.message.from_user
    logger.info("User %s started the conversation sub.", user.first_name)
    context.user_data['current_conversation'] = 'sub'
    current_conversation = context.user_data.get('current_conversation')
    if current_conversation == 'pub':
        houses = topics.publication_houses
    elif current_conversation == 'sub':
        houses = topics.subscription_houses
    else:   
        raise ValueError("No estoy en una conversación conocida")

    #crea una lista keyboard con una boton para cada casa
    keyboard = [[InlineKeyboardButton(house, callback_data=house)] for house in houses]
    # crea un teclado con todos los botones de las casa
    reply_markup = InlineKeyboardMarkup(keyboard)
    # enviar el teclado al chat en reply_markup se carga el teclado que hemos construido antes
    await update.message.reply_text("Selecciona una casa", reply_markup=reply_markup)
    return SELECT_HOUSE

async def pub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    """
    context.user_data.clear()  # Limpia los datos del usuario al inicio
    context.user_data['current_conversation'] = 'pub'
    user = update.message.from_user
    logger.info("User %s started the conversation pub.", user.first_name)
    context.user_data['current_conversation'] = 'pub'
    current_conversation = context.user_data.get('current_conversation')
    if current_conversation == 'pub':
        houses = topics.publication_houses
    elif current_conversation == 'sub':
        houses = topics.subscription_houses
    else:   
        raise ValueError("No estoy en una conversación conocida")
    keyboard = [[InlineKeyboardButton(house, callback_data=house)] for house in houses]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una casa", reply_markup=reply_markup)
    return SELECT_HOUSE


async def select_house(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    guarda la casa y pide habitaciones
    en esta funcion solo se entra cuando el usuario a pulsado un boton "callbackqueryHandler
    
    """
    logger.info("User started selec_house")
    # recupera el valor del boton pulsado y lo carga en query
    query = update.callback_query
    # confirma al chat que ha leido el boton pulsado, es imporatnte hacerlo porque sino hay problems
    await query.answer()
    # guarda la casa en el context
    selected_house = query.data
    context.user_data['house'] = selected_house
    # carga en rooms la lista de habitaciones de la casa seleccionada
    current_conversation = context.user_data['current_conversation']
    if current_conversation == 'pub':
        rooms = topics.publication_rooms
    elif current_conversation == 'sub':
        rooms = topics.subscription_rooms
    else:   
        raise ValueError("No estoy en una conversación conocida")
    # crea un teclado con la lista de habitaciones -> reply_markup
    rooms = [room[1] for room in rooms if room[0] == selected_house]
    keyboard = [[InlineKeyboardButton(room, callback_data=room)] for room in rooms]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # edita el mensaje en el chat y lo cambia por el keyboard para sleccionar habitaciones
    await query.edit_message_text(text=f"Seleccionaste {selected_house}. Ahora selecciona una habitación", reply_markup=reply_markup)
    return SELECT_ROOM


async def select_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    guarda la habitacion en context y pide el device
    """
    logger.info("User started selec_room")
    # recupera el boton pulsado
    query = update.callback_query
    # confirma que la leido el boton pulsado
    await query.answer()
    selected_room = query.data
    context.user_data['room'] = selected_room
    current_conversation = context.user_data['current_conversation']
    if current_conversation == 'pub':
        devices = topics.publication_devices
    elif current_conversation == 'sub':
        devices = topics.subscription_devices
    else:   
        raise ValueError("No estoy en una conversación conocida")
    # crea un teclado con la lista de devices validos
    devices = [device[2] for device in devices if device[0] == context.user_data['house'] and device[1] == selected_room]
    keyboard = [[InlineKeyboardButton(device, callback_data=device)] for device in devices]
    reply_markup = InlineKeyboardMarkup(keyboard)
    #edita el mensaje del chat y lo cambio por el teclado con los devices validos
    await query.edit_message_text(text=f"Seleccionaste {selected_room}. Ahora selecciona un dispositivo", reply_markup=reply_markup)
    return SELECT_DEVICE

async def select_device(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    guarda el device en context y pide la accion
    """
    logger.info("User started selec_device")
    # lee el boton pulsado y luego confirma que lo ha leido
    query = update.callback_query
    await query.answer()
    selected_device = query.data
    context.user_data['device'] = selected_device
    current_conversation = context.user_data['current_conversation']
    if current_conversation == 'pub':
        actions = topics.publication_actions
    elif current_conversation == 'sub':
        actions = topics.subscription_actions
    else:   
        raise ValueError("No estoy en una conversación conocida")
    # crea el teclado con la lista de acciones
    actions = [action[3] for action in actions if action[0] == context.user_data['house'] and action[1] == context.user_data['room'] and action[2] == selected_device]
    keyboard = [[InlineKeyboardButton(action, callback_data=action)] for action in actions]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # edita el mensaje del chat y lo cambia por el teclado con las lista de acciones
    await query.edit_message_text(text=f"Seleccionaste {selected_device}. Ahora selecciona una acción", reply_markup=reply_markup)
    return SELECT_ACTION

async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    guarda la accion en context y pasa a end
        si esta en conversacion sub parara a end_sub
        si este en conversacion pub pasara a end_pub
    """
    logger.info("User started selec_action")
    # lee el boton pulsado y confirma que lo ha leido
    query = update.callback_query
    await query.answer()
    selected_action = query.data
    context.user_data['action'] = selected_action
    # edita el mensaje del chat para indicar que ha seleccionado una accion
    await query.edit_message_text(text=f"Seleccionaste {selected_action}")
    
    current_conversation = context.user_data['current_conversation']
    if current_conversation == 'pub':
        return await end_pub(update, context)
    elif current_conversation == 'sub':
        return await end_sub(update, context)
    else:   
        return ConversationHandler.END
        
        
    


async def end_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    monta el topic y se subscribe por mqtt
    """
    logger.info("User started end_sub")
    #query = update.callback_query
    #await query.answer()

    # Realiza la suscripción al topic específico
    house = context.user_data['house']
    room = context.user_data['room']
    device = context.user_data['device']
    action = context.user_data['action']
    topic = f"casa/{house}/{room}/{device}/{action}"
    await subscribe_to_topic(mqtt_client, topic)
    mensaje =f"Subscrito a {topic}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=mensaje)

    #await query.edit_message_text(text=f"subscrito a {topic}") 

    context.user_data.clear()  # Limpia los datos del usuario al final
    return ConversationHandler.END


async def end_pub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    monta el topic
    lee el json con la definicion de los parametros {nombre: nombre , tipo:int,float, str}
    pide valor de los paramtros
    monta el payload con un json con el nombre y valor de parametros
    publica el topic por mqtt
    """
    logger.info("User started end_pub")        
    #query = update.callback_query
    #await query.answer()

    # Obtener la lista de parámetros asociados al topic
    house = context.user_data['house']
    room = context.user_data['room']
    device = context.user_data['device']
    action = context.user_data['action']
    topic = f"casa/{house}/{room}/{device}/{action}"
    parametros = topics.parameters.get((house, room, device, action), [])
    
    # Crear un diccionario para almacenar los valores de los parámetros ingresados por el usuario
    valores_parametros = {}
    
    # Solicitar los valores de los parámetros al usuario
    for parametro in parametros:
        nombre_parametro = parametro['nombre']
        tipo_parametro = parametro['tipo']
        
        # Solicitar el valor del parámetro al usuario
        await query.edit_message_text(text=f"Ingresa el valor para el parámetro '{nombre_parametro}':")
        
        while True:
            logger.info("User started while validate parameter")
            # Esperar la respuesta del usuario
            response = await update.message.reply_to_message()
            valor_ingresado = response.text.strip()
            
            # Validar el tipo del valor ingresado
            if tipo_parametro == 'int':
                try:
                    valor_parametro = int(valor_ingresado)
                    valores_parametros[nombre_parametro] = valor_parametro
                    break  # Valor correcto, salir del bucle while
                except ValueError:
                    await update.message.reply_text(f"Error: el valor para el parámetro '{nombre_parametro}' debe ser un entero.")
            elif tipo_parametro == 'float':
                try:
                    valor_parametro = float(valor_ingresado)
                    valores_parametros[nombre_parametro] = valor_parametro
                    break  # Valor correcto, salir del bucle while
                except ValueError:
                    await update.message.reply_text(f"Error: el valor para el parámetro '{nombre_parametro}' debe ser un número decimal.")
            else:
                # Tipo de parámetro no reconocido
                await update.message.reply_text(f"Error: el tipo de parámetro '{tipo_parametro}' no es válido.")
                break  # Salir del bucle while sin guardar el valor, volver a solicitar el mismo parámetro
        
    # Verificar si todos los parámetros se ingresaron correctamente
    logger.info("User finish while parameters")
    if len(valores_parametros) == len(parametros):
        # Realizar la publicación del topic con los valores de los parámetros
        payload = json.dumps(valores_parametros)
        public_topic(mqtt_client, topic, payload)
        logger.info("mqtt public topic")
        await query.edit_message_text(text=f"Publicado topic = {topic} Payload = {payload}")
        context.user_data.clear()  # Limpia los datos del usuario al final
        return ConversationHandler.END
    else:
        # Al menos un parámetro no se ingresó correctamente, volver a solicitar el mismo parámetro
        return ENVIO

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Finaliza la conversación y manda un mensaje al usuario.
    """
    logger.info("User call /cancel")
    context.user_data.clear()  # Limpia los datos del usuario
    await update.message.reply_text('Deteniendo la conversación.')
    return ConversationHandler.END


 #       subscribe_to_topic(mqtt_client, topic)

def main() -> None:
    """Start the bot."""
    # mqtt setup
    global mqtt_client  # Declaramos mqtt_client como variable global
    mqtt_client = setup_mqtt_client()
    
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_API_TOKEN).build()
    
    conversation_handler_pub = ConversationHandler(
        entry_points=[CommandHandler('pub', pub)],
        states={
            SELECT_HOUSE    : [CallbackQueryHandler(select_house),CommandHandler('cancel',cancel )],
            SELECT_ROOM     : [CallbackQueryHandler(select_room),CommandHandler('cancel',cancel )],
            SELECT_DEVICE   : [CallbackQueryHandler(select_device),CommandHandler('cancel',cancel )],
            SELECT_ACTION   : [CallbackQueryHandler(select_action),CommandHandler('cancel',cancel )],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    conversation_handler_sub = ConversationHandler(
        entry_points=[CommandHandler('sub', sub),],
        states={
            SELECT_HOUSE    : [CallbackQueryHandler(select_house),CommandHandler('cancel', cancel)],
            SELECT_ROOM     : [CallbackQueryHandler(select_room),CommandHandler('cancel', cancel)],
            SELECT_DEVICE   : [CallbackQueryHandler(select_device),CommandHandler('cancel', cancel)],
            SELECT_ACTION   : [CallbackQueryHandler(select_action),CommandHandler('cancel',cancel )],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    application.add_handler(conversation_handler_pub)
    application.add_handler(conversation_handler_sub)
    #application.add_handler(CommandHandler("sub", sub))
    #application.add_handler(CommandHandler("pub", pub))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("recon", handle_recon_command))
    application.run_polling()
    # Run the bot until the user presses Ctrl-C

if __name__ == "__main__":
    main()
