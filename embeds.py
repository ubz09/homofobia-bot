import discord
from typing import Dict, Any

def create_account_embed(account: Dict[str, Any], color: int = 0xa832a8) -> discord.Embed:
    """Create an embed for displaying account information"""
    embed = discord.Embed(
        title="📋 Información de la Cuenta",
        color=color,
        description=f"**ID de Cuenta**: `{account['id']}`"
    )
    
    embed.add_field(name="👤 IGN", value=f"```{account['ign']}```", inline=True)
    embed.add_field(name="📧 Correo", value=f"```{account['email']}```", inline=True)
    embed.add_field(name="🔐 Contraseña", value=f"```{account['password']}```", inline=True)
    
    # Show status with emoji
    status = account.get('status', 'ADDED')
    status_emoji = {
        'ADDED': '➕',
        'DISTRIBUTED': '✅',
        'DUPLICATED': '📋',
        'BLOCKED': '🚫',
        'ACTIVE': '🟢'
    }.get(status, '❓')
    
    embed.add_field(name="📊 Estado", value=f"{status_emoji} `{status}`", inline=False)
    
    return embed


def create_success_embed(title: str, description: str, color: int = 0x00FF00) -> discord.Embed:
    """Create a success embed"""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=color
    )
    embed.set_footer(text="Operación completada exitosamente")
    return embed


def create_error_embed(title: str, description: str, color: int = 0xFF0000) -> discord.Embed:
    """Create an error embed"""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=color
    )
    embed.set_footer(text="Ocurrió un error")
    return embed


def create_info_embed(title: str, description: str, color: int = 0x0099FF) -> discord.Embed:
    """Create an info embed"""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=color
    )
    embed.set_footer(text="Información")
    return embed


def create_skin_info_embed(player_name: str, player_uuid: str) -> discord.Embed:
    """Create a skin info embed with player information"""
    embed = discord.Embed(
        title="🎀 Información del Jugador Minecraft",
        color=0xa832a8,
        description=f"**Usuario**: `{player_name}`\n**UUID**: `{player_uuid}`"
    )
    embed.set_author(
        name="Visor de Skin 🎀",
        icon_url=f"https://skins.mcstats.com/head/{player_uuid}"
    )
    embed.set_thumbnail(url=f"https://skins.mcstats.com/head/{player_uuid}")
    
    return embed


def create_skin_embed(player_uuid: str, view: str = "front") -> discord.Embed:
    """Create a skin view embed"""
    embed = discord.Embed(color=0xa832a8)
    embed.set_image(url=f"https://skins.mcstats.com/body/{view}/{player_uuid}")
    return embed
