import logging
logging.basicConfig(
    format="%(asctime)s -- %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
import paho.mqtt.client as mqtt
import time
import json
import paramiko
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler,MessageHandler, filters
from topics import Topics
from typing import List




TELEGRAM_API_TOKEN = '6085775716:AAE1gytGt3-qsRedO8MWEy6mhcTym4wbp00'
SERVER = '192.168.1.52'
USER = 'nenbcn'
PASSWORD = 'rikic0'
TOPICS = Topics()
MAX_RETRIES = 5  # Número máximo de intentos de conexión
# Stages
SELECT_HOUSE, SELECT_ROOM, SELECT_DEVICE, SELECT_ACTION, ENTER_PARAMETERS = range(5)
# topics instance
topics = Topics()

# conecdtarse a mqtt
async def setup_mqtt_client() -> mqtt.Client:
    """
    Crea y configura un cliente MQTT.

    :return: Cliente MQTT configurado.
    """
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(USER, PASSWORD)
    for i in range(MAX_RETRIES):
        try:
            mqtt_client.connect(SERVER)
            mqtt_client.loop_start()  # Iniciar el bucle de eventos
            print(f"Conexión MQTT establecida en el intento {i+1}.")
            return mqtt_client
        except ConnectionRefusedError:
            if i < MAX_RETRIES - 1:  # no es el último intento
                time.sleep(5)  # espera antes de intentarlo de nuevo
            else:  # último intento
                print(f"No se pudo establecer la conexión MQTT después de {MAX_RETRIES} intentos.")
                return None

async def handle_recon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /recon.

    :param update: Objeto de actualización de Telegram.
    :param context: Objeto de contexto de Telegram.
    """
    mqtt_client = context.chat_data.get("mqtt_client")
    if mqtt_client is not None and mqtt_client.is_connected():
        await context.bot.send_message(chat_id=update.effective_chat.id, text="La conexion ya esta activa")
    else:
        new_mqtt_client = await setup_mqtt_client()  # Intentamos establecer la conexión MQTT
        if new_mqtt_client is None:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No se pudo reconectar al servidor MQTT.")
        else:
            context.chat_data["mqtt_client"] = new_mqtt_client  # Guardar el nuevo cliente MQTT en el contexto
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Conexión MQTT reestablecida exitosamente.")
            logger.info("Conexión MQTT restablecida correctamente.")


async def public_topic(update: Update, context : ContextTypes.DEFAULT_TYPE, topic, payload) -> None:
    """
    Publica un mensaje en un tema MQTT.

    :param update: Objeto de actualización de Telegram.
    :param context: Objeto de contexto de Telegram.
    :param topic: Tema MQTT en el que se publicará el mensaje.
    :param payload: Mensaje a publicar.
    """
    mqtt_client = context.chat_data.get("mqtt_client")
    if mqtt_client is not None and mqtt_client.is_connected():
        mqtt_client.publish(topic, payload)
        logger.info(f"Publish mqtt, {topic}, {payload}")
    else:
        # La conexión MQTT no está activa, intentar reconectar
        await handle_recon_command(update, context)
        mqtt_client = context.chat_data.get("mqtt_client")
        if mqtt_client is not None and mqtt_client.is_connected():
            mqtt_client.publish(topic, payload)
            logger.info(f"Publish mqtt {topic}, {payload}")
        else:
            logger.error("La conexión MQTT no está activa. No se pudo publicar el mensaje.")
    
async def subscribe_to_topic(update: Update, context : ContextTypes.DEFAULT_TYPE, topic) -> None:
    """
    """
    mqtt_client = context.chat_data.get("mqtt_client")
    if mqtt_client is not None and mqtt_client.is_connected():
        mqtt_client.subscribe(topic)
        logger.info(f"subscribe mqtt {topic}")
    else:
         # La conexión MQTT no está activa, intentar reconectar
        await handle_recon_command(update, context)
        mqtt_client = context.chat_data.get("mqtt_client")
        if mqtt_client is not None and mqtt_client.is_connected():
            mqtt_client.subscribe(topic)
            logger.info(f"subscribe mqtt {topic}")
        else:
            logger.error("La conexión MQTT no está activa. No se pudo suscribir al tema.")


async def mqtt_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja el comando /mqtt_status.
    Devuelve el estado de la conexión MQTT y el broker al que está conectado.
    """
    mqtt_client = context.chat_data.get("mqtt_client")
    # Verificar si el cliente MQTT está conectado
    if mqtt_client is not None and mqtt_client.is_connected():
        # Obtener el broker al que está conectado el cliente MQTT
        broker = mqtt_client._host
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Estado de la conexión MQTT: Conectado\nBroker: {broker}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Estado de la conexión MQTT: Desconectado")


async def check_service_status():
    """
    verifica staus de los servicios de la raspberry
    """
    # Establecer conexión SSH con la Raspberry Pi
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(SERVER, username=USER, password=PASSWORD)

    # Ejecutar comandos para verificar el estado de los servicios
    commands = [
        "systemctl is-active mosquitto.service",
        "systemctl is-active nodered.service",
        "systemctl is-active grafana-server",
        "systemctl is-active influxdb.service"
    ]
    status = {}
    for command in commands:
        _, stdout, _ = ssh_client.exec_command(command)
        output = stdout.read().decode().strip()
        service_name = command.split()[-1]
        status[service_name] = (output == "active")
    # Cerrar conexión SSH
    ssh_client.close()
    return status

async def check_raspberry_services(update: Update, context):
    """
    """
    try:
        status = await check_service_status()
        response = "Estado de los servicios en la Raspberry Pi:\n"
        for service, is_active in status.items():
            if is_active:
                response += f"{service} está activo\n"
            else:
                response += f"{service} NO está activo!!!\n"

        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    except paramiko.SSHException as e:
        error_message = "Se produjo un error al establecer la conexión SSH con la Raspberry Pi. Verifica la configuración y los datos de conexión."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)



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
     
    # inicializar mqtt
    mqtt_client = context.chat_data.get("mqtt_client")
    if mqtt_client is None or not mqtt_client.is_connected():
        mqtt_client = await setup_mqtt_client()  # Establecer la conexión MQTT
        if mqtt_client is None:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No se pudo establecer la conexión MQTT.")
        else:
            context.chat_data["mqtt_client"] = mqtt_client  # Guardar el cliente MQTT en el contexto
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Conexión MQTT establecida.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Conexión MQTT ya está establecida.")

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
    /mqtt_status  - verifica conexion mqtt
    /raspberry  - verifica status servicios raspberry
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
        # Obtener la lista de parámetros asociados al topic
        house = context.user_data['house']
        room = context.user_data['room']
        device = context.user_data['device']
        action = context.user_data['action']
        topic = f"casa/{house}/{room}/{device}/{action}"
        context.user_data['topic'] =topic
        context.user_data['parametros'] = {}
        parametros = topics.parameters.get((house, room, device, action), [])
        context.user_data['parametros'] = parametros # lo pongo en context para que lo use end_sub

        if parametros:
            # Si hay parámetros, solicitar el valor del siguiente parámetro
            nombre_parametro = parametros[0]['nombre']
            await query.edit_message_text(text=f"Ingresa el valor para el parámetro '{nombre_parametro}':")
            context.user_data['valores_parametros'] = {}
            return ENTER_PARAMETERS  #con la respuesta se llamara a end_pub
        else:
            # Si no hay parámetros, llamar directamente a 'end_pub'
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
    
    topic = context.user_data ['topic']
    await subscribe_to_topic(update, context, topic)
    mensaje =f"Subscrito a {topic}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=mensaje)

    #await query.edit_message_text(text=f"subscrito a {topic}") 

    context.user_data.clear()  # Limpia los datos del usuario al final
    return ConversationHandler.END


async def end_pub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    1.  La función end_pub es llamada desde el ConversationHandler cuando está en el estado ENTER_PARAMETERS.
    2.  En cada llamada a la función, se obtiene el valor ingresado por el usuario desde el mensaje actual.
    3. Se verifica si aún quedan parámetros por procesar en la lista de parámetros parametros dentro del contexto del usuario.
    4. Si hay parámetros restantes:
        4.1. Se obtiene el próximo parámetro de la lista de parámetros mediante el método pop(0). Esto elimina el parámetro de la lista.
        4.2. Se valida el tipo del valor ingresado por el usuario según el tipo del parámetro.
        4.3. Si el tipo del valor no coincide con el tipo del parámetro o la conversión del valor falla, se envía un mensaje de error al usuario indicando el tipo de valor requerido.
        4.4. Si el tipo del valor coincide con el tipo del parámetro, se guarda el valor en el diccionario valores_parametros dentro del contexto del usuario.
        4.5. Se obtiene el nombre del siguiente parámetro y se envía un mensaje al usuario solicitando el valor del parámetro.
        4.6. Se retorna el estado ENTER_PARAMETERS para esperar la respuesta del usuario y continuar solicitando los valores de los parámetros restantes.
    5. Si no hay parámetros restantes:
        5.1. Se obtiene el tema (topic) y el diccionario de valores de parámetros (valores_parametros) del contexto del usuario.
        5.2. Se convierte el diccionario valores_parametros a una cadena JSON utilizando la función json.dumps().
        5.3. Se realiza la publicación del mensaje MQTT utilizando el cliente MQTT, el tema (topic) y el payload (valores_parametros en formato JSON).
        5.4. Se envía un mensaje al usuario confirmando la publicación del mensaje MQTT.
        5.5. Se limpian los datos del usuario en el contexto.
        5.6. Se finaliza la conversación.
"""

    if update.message:
        valor_ingresado = update.message.text.strip()
    else:
        valor_ingresado = ""


    if context.user_data.get('parametros'):
        parametro = context.user_data['parametros'].pop(0)
        nombre_parametro = parametro['nombre']
        tipo_parametro = parametro['tipo']

        if tipo_parametro == 'int':
            try:
                valor_parametro = int(valor_ingresado)
                context.user_data['valores_parametros'][nombre_parametro] = valor_parametro # solo si int es ok
                if context.user_data['parametros']:
                    siguiente_parametro = context.user_data['parametros'][0]['nombre']
                    await update.message.reply_text(f"Ingrese el valor para el parámetro '{siguiente_parametro}':")
                    return ENTER_PARAMETERS
            except ValueError:
                await update.message.reply_text(f"Error: el valor para el parámetro '{nombre_parametro}' debe ser un entero.")
                context.user_data['parametros'].insert(0, parametro)
                return ENTER_PARAMETERS
        elif tipo_parametro == 'float':
            try:
                valor_parametro = float(valor_ingresado)
                context.user_data['valores_parametros'][nombre_parametro] = valor_parametro
                if context.user_data['parametros']:
                    siguiente_parametro = context.user_data['parametros'][0]['nombre']
                    await update.message.reply_text(f"Ingrese el valor para el parámetro '{siguiente_parametro}':")
                    return ENTER_PARAMETERS
            except ValueError:
                await update.message.reply_text(f"Error: el valor para el parámetro '{nombre_parametro}' debe ser un número decimal.")
                context.user_data['parametros'].insert(0, parametro)
                return ENTER_PARAMETERS
        else:
            context.user_data['valores_parametros'][nombre_parametro] = valor_ingresado
            if context.user_data['parametros']:
                    siguiente_parametro = context.user_data['parametros'][0]['nombre']
                    await update.message.reply_text(f"Ingrese el valor para el parámetro '{siguiente_parametro}':")
                    return ENTER_PARAMETERS

    # Verificar si no quedan más parámetros en la lista si no quedan envia el mensaje
    if not context.user_data['parametros']:
        topic = context.user_data['topic']
        if context.user_data.get('valores_parametros'):
            payload = json.dumps(context.user_data['valores_parametros'])
        else:
            payload = ""
        await public_topic(update, context, topic, payload)
        if 'reply_to_message_id' in context.user_data:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Publicado topic = {topic} Payload = {payload}", reply_to_message_id=context.user_data['reply_to_message_id'])
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Publicado topic = {topic} Payload = {payload}")
        context.user_data.clear()
        return ConversationHandler.END

    return ENTER_PARAMETERS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Finaliza la conversación y manda un mensaje al usuario.
    """
    logger.info("User call /cancel")
    context.user_data.clear()  # Limpia los datos del usuario
    await update.message.reply_text('Deteniendo la conversación.')
    return ConversationHandler.END


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
            ENTER_PARAMETERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_pub)]
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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("recon", handle_recon_command))
    application.add_handler(CommandHandler("mqtt_status", mqtt_status))
    application.add_handler(CommandHandler("raspberry", check_raspberry_services))
    

    application.run_polling()
    # Run the bot until the user presses Ctrl-C

if __name__ == "__main__":
    main()
