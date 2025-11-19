# -*- coding: utf-8 -*-
import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
from threading import Thread # Necesario para Keep Alive
from flask import Flask

# Eliminamos la librería 'requests' ya que no haremos validación externa
# Eliminamos 'time' ya que no se necesitan los reintentos

# --- Configuración Inicial ---
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
DISTRIBUTION_INTERVAL_MINUTES = 10.0

# --- Rutas de Archivos ---
DATA_DIR = 'data'
ACCOUNTS_FILE = os.path.join(DATA_DIR, 'accounts.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.txt')

# Asegurarse de que las carpetas y archivos existan
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

for file_path in [ACCOUNTS_FILE, LOGS_FILE]:
    if not os.path.exists(file_path):
        if file_path.endswith('.json'):
            # Inicializar el archivo JSON con las estructuras necesarias
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({'available': [], 'distributed': []}, f, indent=4)
        else:
            # Inicializar el archivo de logs
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('--- Archivo de Registro de Cuentas ---\n')

# --- Definición del Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Cargar los datos de las cuentas al iniciar
accounts_data = {'available': [], 'distributed': []}

# --- Funciones Auxiliares ---

def load_accounts():
    """Carga los datos de las cuentas desde el archivo JSON."""
    global accounts_data
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'available' in data and 'distributed' in data:
                accounts_data = data
                return True
            else:
                return False
    except:
        return False

def save_accounts():
    """Guarda los datos de las cuentas en el archivo JSON."""
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts_data, f, indent=4)
    except Exception as e:
        print(f"Error guardando cuentas: {e}")

def update_log(account_info, status):
    """Añade una entrada al archivo de registro (log)."""
    # Usamos el 'gmail' (ahora cualquier email) como identificador principal en el log
    log_entry = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"STATUS: {status} | Email: {account_info['gmail']} | Pass: {account_info['password']}\n"
    )
    try:
        with open(LOGS_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error escribiendo log: {e}")

# --- Tasks y Eventos ---

@bot.event
async def on_ready():
    """Evento que se ejecuta cuando el bot está listo."""
    print(f'🤖 Bot conectado como {bot.user}!')
    load_accounts()
    # Iniciar el bucle de distribución
    distribute_account.start()

@tasks.loop(minutes=DISTRIBUTION_INTERVAL_MINUTES)
async def distribute_account():
    """Tarea de bucle para distribuir cuentas en el canal configurado."""
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    if not channel or not accounts_data['available']:
        return

    # Sacar la primera cuenta disponible
    account_to_distribute = accounts_data['available'].pop(0)

    required_keys = ['gmail', 'password']
    # Comprobamos solo el correo y la contraseña
    if not all(key in account_to_distribute for key in required_keys):
        accounts_data['available'].insert(0, account_to_distribute)
        return

    # Crear el Embed para la distribución
    # *** CAMBIO: El título usa el correo como identificador principal ***
    embed = discord.Embed(
        title=f"✨ Cuenta Disponible | Correo: {account_to_distribute['gmail']} ✨",
        description="¡Se ha liberado una cuenta! Reacciona para indicar su estado:",
        color=discord.Color.dark_green()
    )
    # *** CAMBIO: Se eliminó el campo del Nickname ***
    embed.add_field(name="📧 Correo (Microsoft)", value=f"`{account_to_distribute['gmail']}`", inline=False)
    embed.add_field(name="🔒 Contraseña", value=f"`{account_to_distribute['password']}`", inline=False)
    # *** CAMBIO: Se añadió la nueva reacción al texto de pie de página ***
    embed.set_footer(text=f"Reacciona: ✅ Usada | ❌ Error Credenciales | 🚨 Cuenta No Sirve/Bloqueada | {len(accounts_data['available'])} restantes.")

    try:
        # Enviar el mensaje y añadir las tres reacciones
        message = await channel.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await message.add_reaction("🚨") # Nueva reacción

        # Guardar la información de la distribución
        account_data_distributed = account_to_distribute.copy()
        account_data_distributed['distribution_date'] = datetime.now().isoformat()
        account_data_distributed['message_id'] = message.id
        # *** CAMBIO: Inicializar la nueva reacción en los datos ***
        account_data_distributed['reactions'] = {'✅':0,'❌':0,'🚨':0,'users':[]}
        accounts_data['distributed'].append(account_data_distributed)

        save_accounts()
        update_log(account_to_distribute, "DISTRIBUTED")
    except:
        # Si falla el envío (ej. el bot no tiene permisos), devolver la cuenta
        accounts_data['available'].insert(0, account_to_distribute)

@bot.event
async def on_reaction_add(reaction, user):
    """Maneja las reacciones a los mensajes de distribución."""
    if user.bot:
        return

    # *** CAMBIO: Añadida la nueva reacción 🚨 ***
    valid_emojis = ["✅","❌", "🚨"]

    # Comprobar si la reacción está en el canal correcto y es un emoji válido
    if reaction.message.channel.id != CHANNEL_ID or str(reaction.emoji) not in valid_emojis:
        return

    message_id = reaction.message.id
    reacted_emoji = str(reaction.emoji)
    user_id = user.id

    # Buscar la cuenta distribuida correspondiente
    for account in accounts_data['distributed']:
        if account.get('message_id') == message_id:
            # Comprobar si el usuario ya reaccionó
            if user_id in account['reactions']['users']:
                await reaction.remove(user)
                return

            # Registrar la nueva reacción
            account['reactions']['users'].append(user_id)
            account['reactions'][reacted_emoji] += 1
            save_accounts()
            return

# --- Comandos ---

@bot.command(name='addaccount', help='Añade una cuenta de Microsoft (Email y Password). Formato: !addaccount <correo> <contraseña>')
@commands.has_permissions(administrator=True)
async def add_account(ctx, email: str, password: str):
    """
    Añade una cuenta al inventario, usando el email como identificador principal.
    """

    await ctx.send("✅ Recibida la información.")

    # El campo 'username' se utiliza internamente para mantener la estructura,
    # pero ahora guarda el email.
    new_account = {'username':email,'gmail':email,'password':password}
    accounts_data['available'].append(new_account)
    save_accounts()
    update_log(new_account,"ADDED")

    # Enviar confirmación con Embed
    embed = discord.Embed(
        title="✅ Cuenta Añadida",
        description="La cuenta ha sido añadida al inventario y está lista para ser distribuida.",
        color=discord.Color.blue()
    )
    embed.add_field(name="📧 Correo (Microsoft)", value=email)
    embed.add_field(name="🔒 Contraseña", value=password)
    embed.add_field(name="Inventario Total", value=f"{len(accounts_data['available'])} disponibles")
    await ctx.send(embed=embed)

@bot.command(name='importaccounts', help='Importa varias cuentas desde archivo import_accounts.txt con formato: correo:contraseña')
@commands.has_permissions(administrator=True)
async def import_accounts(ctx):
    """Importa cuentas desde un archivo de texto con formato email:contraseña."""
    file_path = "import_accounts.txt"
    if not os.path.exists(file_path):
        await ctx.send(f"❌ No se encontró el archivo {file_path}. Asegúrate de crearlo con formato `correo:contraseña` por línea.")
        return

    await ctx.send("⏳ Importando cuentas...")
    success_count = 0
    fail_count = 0

    with open(file_path,'r',encoding='utf-8') as f:
        lines = f.read().splitlines()
        for line in lines:
            if line.count(":") != 1: continue # Debe haber exactamente un ':' (email:pass)

            try:
                # Separar los dos valores
                email, password = line.strip().split(":", 1)

                # Usamos el email como 'username' para el seguimiento interno
                new_account = {'username':email,'gmail':email,'password':password}
                accounts_data['available'].append(new_account)
                update_log(new_account,"ADDED")
                success_count += 1
            except Exception as e:
                print(f"Error procesando línea en import: {line}. Error: {e}")
                fail_count += 1

    save_accounts()
    await ctx.send(f"✅ Importadas **{success_count}** cuentas correctamente.\n❌ Fallidas (formato incorrecto): **{fail_count}**")

@add_account.error
async def add_account_error(ctx,error):
    """Maneja errores específicos del comando addaccount."""
    if isinstance(error, commands.MissingRequiredArgument):
        # Ahora solo se requieren 2 argumentos
        await ctx.send("❌ Uso incorrecto: `!addaccount <correo_completo> <contraseña>`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Permiso denegado. Solo administradores pueden usar este comando.")
    else:
        print(f"Error inesperado en add_account: {error}")
        await ctx.send("❌ Error al añadir la cuenta. Revisa la consola para más detalles.")

# --- Keep Alive para Replit ---

app = Flask('')
@app.route('/')
def home():
    """Ruta simple para mantener el bot activo en entornos como Replit."""
    return "Bot is running and ready!"

def run():
    """Ejecuta la aplicación Flask."""
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Inicia el thread para mantener la aplicación web activa."""
    t = Thread(target=run)
    t.start()

# --- Ejecución Final ---
if __name__ == '__main__':
    keep_alive()
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("*** ERROR: Token de Discord inválido ***")
    except Exception as e:
        print(f"*** ERROR FATAL: {e} ***")
