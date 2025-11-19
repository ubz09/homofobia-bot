# -*- coding: utf-8 -*-
import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask
# ¡¡IMPORTANTE!! requests es necesario para el checker
import requests 

# --- Configuración Inicial ---
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
DISTRIBUTION_INTERVAL_MINUTES = 30.0

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
registered_emails = set()

# --- Funciones Auxiliares ---

def load_accounts():
    """Carga los datos de las cuentas desde el archivo JSON y actualiza el conjunto de emails registrados."""
    global accounts_data, registered_emails
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'available' in data and 'distributed' in data:
                accounts_data = data
                # Reconstruir el conjunto de emails registrados
                registered_emails.clear()
                # Recorrer ambas listas para cargar los emails
                for account in accounts_data['distributed']:
                    if 'gmail' in account:
                        registered_emails.add(account['gmail'].lower())
                for account in accounts_data['available']:
                    if 'gmail' in account:
                        registered_emails.add(account['gmail'].lower())
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

def remove_import_file(file_path):
    """Elimina el archivo de importación de cuentas."""
    try:
        os.remove(file_path)
        print(f"Archivo de importación eliminado: {file_path}")
    except Exception as e:
        print(f"Error al eliminar archivo {file_path}: {e}")

# --------------------------------------------------------------------------------------------------
## 🚀 Función Central de Chequeo y Extracción (Checker)
# --------------------------------------------------------------------------------------------------

def check_and_extract_ms_account(email: str, password: str):
    """
    Simula la autenticación de Microsoft para validar credenciales y extraer el perfil.
    
    ⚠️ IMPORTANTE: DEBES REEMPLAZAR EL CONTENIDO DE ESTA FUNCIÓN con la lógica de 
    peticiones HTTP de tu "codigochecker.txt".
    
    Retorna: (True, dict_info) si es válido, (False, str_error) si falla.
    """
    
    # ----------------------------------------------------------------------------------
    # !!! ZONA A COMPLETAR CON TU LÓGICA ESPECÍFICA DE PETICIONES DE AUTENTICACIÓN !!!
    # ----------------------------------------------------------------------------------
    
    session = requests.Session()
    
    try:
        # Aquí iría tu código de `codigochecker.txt` para autenticación de MS.
        
        # --- SIMULACIÓN DE RESULTADO ---
        # Por ahora, simulamos que siempre falla para que no se use sin implementar la lógica.
        
        # Si la lógica de tu checker confirma que la cuenta es válida:
        if False: # Cambiar esta línea a `if True:` o a la lógica de éxito real.
            extracted_info = {
                'username': email.split('@')[0], 
                'gmail': email,                  
                'password': password,            
                'status_check': 'Verified',      
                'extracted_gamertag': 'Gamertag-Extraído' 
            }
            return True, extracted_info 
        else:
            # Si el checker encuentra un error de credenciales o la simulación falla:
             return False, "Credenciales inválidas o la lógica de chequeo no ha sido implementada/falló."
            
    except requests.exceptions.RequestException as e:
        # Error de conexión, timeout, etc.
        return False, f"Error de conexión HTTP durante el chequeo: {e}"
    except Exception as e:
        # Error interno, ej. parseo de respuesta
        return False, f"Error interno en el checker: {e}"
        
    # ----------------------------------------------------------------------------------
    # FIN DE ZONA A COMPLETAR
    # ----------------------------------------------------------------------------------

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
    embed = discord.Embed(
        title=f"✨ Cuenta Disponible | Correo: {account_to_distribute['gmail']} ✨",
        description="¡Se ha liberado una cuenta! Reacciona para indicar su estado:",
        color=discord.Color.dark_green()
    )
    embed.add_field(name="📧 Correo (Microsoft)", value=f"`{account_to_distribute['gmail']}`", inline=False)
    embed.add_field(name="🔒 Contraseña", value=f"`{account_to_distribute['password']}`", inline=False)
    embed.set_footer(text=f"Reacciona: ✅ Usada | ❌ Error Credenciales | 🚨 Cuenta No Sirve/Bloqueada | {len(accounts_data['available'])} restantes.")

    try:
        # Enviar el mensaje y añadir las tres reacciones
        message = await channel.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await message.add_reaction("🚨")

        # Guardar la información de la distribución
        account_data_distributed = account_to_distribute.copy()
        account_data_distributed['distribution_date'] = datetime.now().isoformat()
        account_data_distributed['message_id'] = message.id
        account_data_distributed['reactions'] = {'✅':0,'❌':0,'🚨':0,'users':[]}
        accounts_data['distributed'].append(account_data_distributed)
        
        save_accounts()
        update_log(account_to_distribute, "DISTRIBUTED")
        
    except:
        # Si falla el envío, devolver la cuenta
        accounts_data['available'].insert(0, account_to_distribute)


@bot.event
async def on_reaction_
