import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from utils.config_manager import load_config

# Cargar variables de entorno
load_dotenv()

class PostuBot(commands.Bot):
    def __init__(self):
        config = load_config()
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=config['bot_prefix'], intents=intents)

    async def setup_hook(self):
        # Importar aquí para evitar importaciones circulares si fuera necesario
        from cogs.applications import ApplicationCog
        from cogs.admin import AdminCog
        
        await self.add_cog(ApplicationCog(self))
        await self.add_cog(AdminCog(self))
        print("Cogs cargados exitosamente.")

    async def on_ready(self):
        print(f'Bot conectado como {self.user} (ID: {self.user.id})')
        print('------')

if __name__ == "__main__":
    bot = PostuBot()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: No se encontró el DISCORD_TOKEN en el archivo .env")
    else:
        bot.run(token)
