import discord
from discord.ext import commands
from utils.config_manager import load_config, update_config_value, save_config

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        config = load_config()
        await ctx.message.delete()

        embed = discord.Embed(
            title=config['embeds']['setup_title'],
            description=config['embeds']['setup_description'],
            color=config['embeds']['setup_color']
        )

        status_text = "Abiertas" if config['applications_open'] else "Cerradas"
        embed.set_footer(text=f"BD Postulaciones • Sistema automático de Staff • Estado: {status_text}")

        # La vista se manejará en el cog de aplicaciones para persistencia
        from cogs.applications import ApplicationView
        view = ApplicationView(self.bot)
        
        if not config['applications_open']:
            view.children[0].disabled = True
            view.children[0].label = "Cerradas"

        msg = await ctx.send(embed=embed, view=view)
        update_config_value('setup_message_id', msg.id)
        update_config_value('channels', {**config['channels'], 'applications': ctx.channel.id})

    @commands.command(name="abrir-p")
    @commands.has_permissions(administrator=True)
    async def abrir(self, ctx):
        config = load_config()
        config['applications_open'] = True
        save_config(config)
        
        await ctx.send("Postulaciones abiertas.", delete_after=5)
        await self.update_setup_message(config)

    @commands.command(name="cerrar-p")
    @commands.has_permissions(administrator=True)
    async def cerrar(self, ctx):
        config = load_config()
        config['applications_open'] = False
        save_config(config)
        
        await ctx.send("Postulaciones cerradas.", delete_after=5)
        await self.update_setup_message(config)

    async def update_setup_message(self, config):
        setup_id = config.get('setup_message_id')
        channel_id = config['channels'].get('applications')
        
        if setup_id and channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(setup_id)
                    embed = msg.embeds[0]
                    status_text = "Abiertas" if config['applications_open'] else "Cerradas"
                    embed.set_footer(text=f"BD Postulaciones • Sistema automático de Staff • Estado: {status_text}")
                    
                    from cogs.applications import ApplicationView
                    view = ApplicationView(self.bot)
                    if not config['applications_open']:
                        view.children[0].disabled = True
                        view.children[0].label = "Cerradas"
                    
                    await msg.edit(embed=embed, view=view)
                except Exception as e:
                    print(f"Error actualizando mensaje de setup: {e}")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
