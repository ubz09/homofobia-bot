# -*- coding: utf-8 -*-
import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask
import asyncio
import aiohttp
import re
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- Configuración Inicial ---
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0))
DISTRIBUTION_INTERVAL_MINUTES = 30.0

# Validar variables de entorno requeridas
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN no está configurado")
    exit(1)
if CHANNEL_ID == 0:
    print("❌ ERROR: CHANNEL_ID no está configurado")
    exit(1)

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
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({'available': [], 'distributed': []}, f, indent=4)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('--- Archivo de Registro de Cuentas ---\n')

# --- Definición del Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

class AccountBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        self.accounts_data = {'available': [], 'distributed': []}
        self.registered_emails = set()
        self.temp_verified_accounts = {}

bot = AccountBot()

# --- Funciones de Autenticación Microsoft Simplificadas ---

async def simple_microsoft_auth(email, password):
    """
    Autenticación simplificada y más robusta
    """
    try:
        # Configurar sesión
        timeout = aiohttp.ClientTimeout(total=20)
        connector = aiohttp.TCPConnector(verify_ssl=False)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        ) as session:
            
            # Paso 1: Obtener página de login
            auth_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
            
            async with session.get(auth_url) as response:
                text = await response.text()
                
                # Buscar el token PPFT de diferentes formas
                ppft = None
                ppft_patterns = [
                    r'name="PPFT" value="([^"]+)"',
                    r'value="([^"]+)" id="i0327"',
                    r'value="([^"]+)" name="PPFT"'
                ]
                
                for pattern in ppft_patterns:
                    match = re.search(pattern, text)
                    if match:
                        ppft = match.group(1)
                        break
                
                if not ppft:
                    return {"success": False, "error": "No se pudo obtener token PPFT"}
                
                # Buscar URL Post
                url_post_match = re.search(r'urlPost:\s*[\'"]([^\'"]+)[\'"]', text)
                if not url_post_match:
                    return {"success": False, "error": "No se pudo obtener URL Post"}
                
                url_post = url_post_match.group(1)

            # Paso 2: Enviar login
            login_data = {
                'login': email,
                'loginfmt': email,
                'passwd': password,
                'PPFT': ppft,
            }

            async with session.post(
                url_post,
                data=login_data,
                allow_redirects=True,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                
                # Verificar si hay redirección con token
                if 'access_token' in str(response.url):
                    parsed = urlparse(str(response.url))
                    fragment = parse_qs(parsed.fragment)
                    access_token = fragment.get('access_token', [None])[0]
                    if access_token:
                        return {"success": True, "access_token": access_token}
                
                # Leer respuesta para detectar errores específicos
                response_text = await response.text()
                
                if "password is incorrect" in response_text.lower():
                    return {"success": False, "error": "Contraseña incorrecta"}
                elif "account doesn't exist" in response_text.lower():
                    return {"success": False, "error": "La cuenta no existe"}
                elif "recover" in response_text.lower() or "two-step" in response_text.lower():
                    return {"success": False, "error": "Verificación en dos pasos requerida"}
                elif "signed in too many times" in response_text.lower():
                    return {"success": False, "error": "Demasiados intentos, cuenta temporalmente bloqueada"}
                else:
                    return {"success": False, "error": "Error de autenticación - Verifica las credenciales"}

    except asyncio.TimeoutError:
        return {"success": False, "error": "Tiempo de espera agotado"}
    except Exception as e:
        return {"success": False, "error": f"Error de conexión: {str(e)}"}

async def get_minecraft_info(access_token):
    """Obtiene información básica de Minecraft"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(verify_ssl=False)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Verificar perfil de Minecraft
            async with session.get('https://api.minecraftservices.com/minecraft/profile', headers=headers) as response:
                if response.status == 200:
                    profile_data = await response.json()
                    return {
                        "has_minecraft": True,
                        "username": profile_data.get('name', 'No disponible'),
                        "uuid": profile_data.get('id', 'No disponible')
                    }
                else:
                    return {"has_minecraft": False}
                    
    except:
        return {"has_minecraft": False}

async def verify_microsoft_account(email, password):
    """
    Verificación simplificada y más confiable
    """
    # Validación básica
    if "@" not in email or "." not in email:
        return {
            "success": False,
            "error": "Formato de email inválido"
        }
    
    if len(password) < 1:
        return {
            "success": False,
            "error": "La contraseña no puede estar vacía"
        }

    # Intentar autenticación
    auth_result = await simple_microsoft_auth(email, password)
    
    if not auth_result["success"]:
        return auth_result

    # Si la autenticación fue exitosa, verificar Minecraft
    minecraft_info = await get_minecraft_info(auth_result["access_token"])
    
    if minecraft_info["has_minecraft"]:
        return {
            "success": True,
            "email": email,
            "password": password,
            "has_minecraft": True,
            "message": "✅ Cuenta verificada - Con Minecraft",
            "details": {
                "username": minecraft_info["username"],
                "uuid": minecraft_info["uuid"],
                "account_type": "Microsoft Account"
            }
        }
    else:
        return {
            "success": True,
            "email": email,
            "password": password,
            "has_minecraft": False,
            "message": "✅ Cuenta Microsoft válida - Sin Minecraft"
        }

# --- Funciones Auxiliares del Bot ---

def load_accounts():
    """Carga los datos de las cuentas desde el archivo JSON."""
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'available' in data and 'distributed' in data:
                bot.accounts_data = data
                bot.registered_emails.clear()
                for account in bot.accounts_data['distributed']:
                    if 'gmail' in account:
                        bot.registered_emails.add(account['gmail'].lower())
                for account in bot.accounts_data['available']:
                    if 'gmail' in account:
                        bot.registered_emails.add(account['gmail'].lower())
                print(f"✅ Cuentas cargadas: {len(bot.accounts_data['available'])} disponibles")
                return True
    except Exception as e:
        print(f"❌ Error cargando cuentas: {e}")
    return False

def save_accounts():
    """Guarda los datos de las cuentas en el archivo JSON."""
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot.accounts_data, f, indent=4)
    except Exception as e:
        print(f"❌ Error guardando cuentas: {e}")

def update_log(account_info, status):
    """Añade una entrada al archivo de registro."""
    log_entry = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"STATUS: {status} | Email: {account_info['gmail']}\n"
    )
    try:
        with open(LOGS_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"❌ Error escribiendo log: {e}")

def remove_import_file(file_path):
    """Elimina el archivo de importación de cuentas."""
    try:
        os.remove(file_path)
        print(f"✅ Archivo de importación eliminado: {file_path}")
    except Exception as e:
        print(f"❌ Error al eliminar archivo {file_path}: {e}")

# --- Comandos Corregidos ---

@bot.command(name='verifyaccount')
@commands.has_permissions(administrator=True)
async def verify_account(ctx, email: str, password: str):
    """Verifica una cuenta de Microsoft."""
    
    processing_msg = await ctx.send("🔍 **Verificando cuenta...**")
    
    try:
        result = await verify_microsoft_account(email, password)
        await processing_msg.delete()
        
        if result["success"]:
            if result.get("has_minecraft", False):
                details = result["details"]
                
                embed = discord.Embed(
                    title="✅ **CUENTA VERIFICADA - CON MINECRAFT**",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="📧 **Credenciales**",
                    value=f"**Email:** `{email}`\n**Contraseña:** `{password}`",
                    inline=False
                )
                
                embed.add_field(
                    name="🎮 **Información Minecraft**",
                    value=f"**Usuario:** `{details['username']}`\n**UUID:** `{details['uuid']}`",
                    inline=False
                )
                
                embed.set_footer(text="Reacciona con ✅ para añadir al inventario o ❌ para cancelar")
                
            else:
                embed = discord.Embed(
                    title="✅ **CUENTA VERIFICADA - SIN MINECRAFT**",
                    color=0xffff00
                )
                
                embed.add_field(
                    name="📧 **Credenciales**",
                    value=f"**Email:** `{email}`\n**Contraseña:** `{password}`",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 **Estado**",
                    value="Cuenta Microsoft válida pero sin Minecraft",
                    inline=False
                )
                
                embed.set_footer(text="Reacciona con ✅ para añadir al inventario o ❌ para cancelar")
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            bot.temp_verified_accounts[message.id] = {
                "email": email,
                "password": password,
                **result
            }
            
        else:
            embed = discord.Embed(
                title="❌ **ERROR EN VERIFICACIÓN**",
                color=0xff0000
            )
            
            embed.add_field(
                name="📧 **Credenciales**",
                value=f"**Email:** `{email}`\n**Contraseña:** `{password}`",
                inline=False
            )
            
            embed.add_field(
                name="🚨 **Error**",
                value=result["error"],
                inline=False
            )
            
            await ctx.send(embed=embed)
            
    except Exception as e:
        await processing_msg.delete()
        embed = discord.Embed(
            title="💥 **ERROR**",
            description=f"Error inesperado: {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@bot.command(name='importaccounts')
@commands.has_permissions(administrator=True)
async def import_accounts(ctx):
    """Importa cuentas desde un archivo de texto."""
    file_path = "import_accounts.txt"
    
    if not os.path.exists(file_path):
        embed = discord.Embed(
            title="❌ **Archivo No Encontrado**",
            description=f"No se encontró el archivo `{file_path}`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    processing_msg = await ctx.send("📥 **Importando cuentas...**")
    
    try:
        success_count = 0
        fail_count = 0
        duplicate_count = 0
        remaining_lines = []

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            if stripped_line.count(":") != 1:
                remaining_lines.append(line)
                fail_count += 1
                continue

            try:
                email, password = stripped_line.split(":", 1)
                email_lower = email.lower().strip()

                if email_lower in bot.registered_emails:
                    duplicate_count += 1
                    continue
                
                new_account = {
                    'username': email,
                    'gmail': email,
                    'password': password,
                    'added_date': datetime.now().isoformat(),
                    'added_by': 'import'
                }
                
                bot.accounts_data['available'].append(new_account)
                bot.registered_emails.add(email_lower)
                success_count += 1

            except Exception as e:
                remaining_lines.append(line)
                fail_count += 1
                print(f"Error procesando línea: {line} - {e}")

        save_accounts()

        # Manejar archivo restante
        if remaining_lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(remaining_lines) + '\n')
        else:
            remove_import_file(file_path)

        # Mostrar resultados
        embed = discord.Embed(
            title="📊 **Resultados de Importación**",
            color=0x0099ff
        )
        embed.add_field(name="✅ Correctas", value=success_count, inline=True)
        embed.add_field(name="🔄 Duplicadas", value=duplicate_count, inline=True)
        embed.add_field(name="❌ Fallidas", value=fail_count, inline=True)
        embed.add_field(name="📦 Total Inventario", value=f"{len(bot.accounts_data['available'])}", inline=False)
        
        await ctx.send(embed=embed)
        
        # Actualizar presencia
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(bot.accounts_data['available'])} cuentas"
            )
        )

    except Exception as e:
        embed = discord.Embed(
            title="❌ **Error en Importación**",
            description=f"Error: {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    
    finally:
        await processing_msg.delete()

@bot.command(name='addaccount')
@commands.has_permissions(administrator=True)
async def add_account(ctx, email: str, password: str):
    """Añade una cuenta manualmente."""
    email_lower = email.lower()

    if email_lower in bot.registered_emails:
        embed = discord.Embed(
            title="❌ **Cuenta Duplicada**",
            description=f"La cuenta `{email}` ya existe.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    new_account = {
        'username': email,
        'gmail': email,
        'password': password,
        'added_date': datetime.now().isoformat(),
        'added_by': str(ctx.author)
    }
    
    bot.accounts_data['available'].append(new_account)
    bot.registered_emails.add(email_lower)
    save_accounts()

    embed = discord.Embed(
        title="✅ **Cuenta Añadida**",
        color=0x00ff00
    )
    embed.add_field(name="📧 Email", value=email, inline=True)
    embed.add_field(name="📊 Total", value=f"{len(bot.accounts_data['available'])}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='stats')
async def stats(ctx):
    """Muestra estadísticas del inventario."""
    embed = discord.Embed(title="📊 **Estadísticas**", color=0x0099ff)
    embed.add_field(name="📥 Disponibles", value=len(bot.accounts_data['available']), inline=True)
    embed.add_field(name="📤 Distribuidas", value=len(bot.accounts_data['distributed']), inline=True)
    await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx):
    """Muestra ayuda de comandos."""
    embed = discord.Embed(
        title="🤖 **Comandos Disponibles**",
        color=0x0099ff
    )
    
    commands_list = [
        ("!verifyaccount <email> <contraseña>", "Verifica una cuenta Microsoft"),
        ("!addaccount <email> <contraseña>", "Añade una cuenta manualmente"),
        ("!importaccounts", "Importa cuentas desde import_accounts.txt"),
        ("!stats", "Muestra estadísticas del inventario"),
        ("!help", "Muestra esta ayuda")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    await ctx.send(embed=embed)

# --- Manejo de Reacciones ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    # Manejar verificación de cuentas
    if reaction.message.id in bot.temp_verified_accounts:
        if str(reaction.emoji) == "✅" and user != bot.user:
            account_data = bot.temp_verified_accounts[reaction.message.id]
            email_lower = account_data["email"].lower()
            
            if email_lower not in bot.registered_emails:
                new_account = {
                    'username': account_data["email"],
                    'gmail': account_data["email"],
                    'password': account_data["password"],
                    'verified': True,
                    'added_date': datetime.now().isoformat(),
                    'added_by': str(user)
                }
                
                if account_data.get("has_minecraft") and "details" in account_data:
                    new_account.update(account_data["details"])
                
                bot.accounts_data['available'].append(new_account)
                bot.registered_emails.add(email_lower)
                save_accounts()
                
                await reaction.message.reply("✅ **Cuenta añadida al inventario!**")
                
                await bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"{len(bot.accounts_data['available'])} cuentas"
                    )
                )
            else:
                await reaction.message.reply("❌ **Esta cuenta ya existe en el inventario.**")
            
            del bot.temp_verified_accounts[reaction.message.id]
            await reaction.message.clear_reactions()
        
        elif str(reaction.emoji) == "❌" and user != bot.user:
            await reaction.message.reply("❌ **Cuenta descartada.**")
            del bot.temp_verified_accounts[reaction.message.id]
            await reaction.message.clear_reactions()

# --- Eventos del Bot ---
@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como {bot.user}')
    load_accounts()
    
    if not distribute_account.is_running():
        distribute_account.start()
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.accounts_data['available'])} cuentas"
        )
    )

@tasks.loop(minutes=DISTRIBUTION_INTERVAL_MINUTES)
async def distribute_account():
    """Distribuye cuentas automáticamente."""
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel and bot.accounts_data['available']:
            account = bot.accounts_data['available'].pop(0)
            
            embed = discord.Embed(
                title="🎁 **Cuenta Disponible**",
                color=0x0099ff
            )
            embed.add_field(name="📧 Email", value=f"`{account['gmail']}`", inline=False)
            embed.add_field(name="🔒 Contraseña", value=f"`{account['password']}`", inline=False)
            embed.set_footer(text="Reacciona: ✅ Usada | ❌ Error | 🚨 Bloqueada")
            
            message = await channel.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            await message.add_reaction("🚨")
            
            save_accounts()
            
    except Exception as e:
        print(f"Error en distribución: {e}")

# --- Keep Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot de Cuentas Microsoft - En línea"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# --- Ejecución ---
if __name__ == '__main__':
    keep_alive()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Error iniciando bot: {e}")
