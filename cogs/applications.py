import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from utils.config_manager import load_config, load_questions, update_config_value
from utils.logger import log_application, send_log_embed

class CloseTicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        staff_role_id = config['roles'].get('staff')
        
        is_staff = any(role.id == staff_role_id for role in interaction.user.roles)
        if not is_staff and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Solo el Staff puede cerrar este ticket.", ephemeral=True)
            return

        await interaction.response.send_message("Cerrando el ticket en 5 segundos...")
        
        await send_log_embed(self.bot, config, "Ticket Cerrado", f"El ticket {interaction.channel.name} fue cerrado por {interaction.user.mention}")
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

class ReviewView(View):
    def __init__(self, bot, applicant_id, answers):
        super().__init__(timeout=None)
        self.bot = bot
        self.applicant_id = applicant_id
        self.answers = answers

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, custom_id="approve_app")
    async def approve(self, interaction: discord.Interaction, button: Button):
        await self.handle_review(interaction, "Aprobado", discord.Color.green())

    @discord.ui.button(label="Rechazar", style=discord.ButtonStyle.red, custom_id="reject_app")
    async def reject(self, interaction: discord.Interaction, button: Button):
        await self.handle_review(interaction, "Rechazado", discord.Color.red())

    @discord.ui.button(label="Entrevista", style=discord.ButtonStyle.blurple, custom_id="interview_app")
    async def interview(self, interaction: discord.Interaction, button: Button):
        await self.handle_review(interaction, "Entrevista Solicitada", discord.Color.blue())

    async def handle_review(self, interaction, status, color):
        config = load_config()
        staff_role_id = config['roles'].get('staff')
        if not any(role.id == staff_role_id for role in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tienes permisos.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.title = f"{embed.title} - {status}"
        embed.color = color
        embed.add_field(name="Revisado por", value=interaction.user.mention)
        
        for child in self.children:
            child.disabled = True
            
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"Postulación marcada como: {status}", ephemeral=True)
        
        # Lógica adicional según el estado (ej. mover a canal de entrevistas)
        if status == "Entrevista Solicitada":
            await self.setup_interview(interaction, config)
            
        await send_log_embed(self.bot, config, f"Postulación {status}", f"La postulación de <@{self.applicant_id}> fue revisada por {interaction.user.mention}")

    async def setup_interview(self, interaction, config):
        guild = interaction.guild
        applicant = guild.get_member(self.applicant_id)
        if not applicant: return

        # Añadir rol de postulante si existe
        role_id = config['roles'].get('applicant')
        if role_id:
            role = guild.get_role(role_id)
            if role: await applicant.add_roles(role)

        # Crear canal de entrevista
        category_id = config['categories'].get('interviews')
        category = guild.get_channel(category_id) if category_id else None
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            applicant: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        interviewer_role_id = config['roles'].get('interviewer')
        if interviewer_role_id:
            i_role = guild.get_role(interviewer_role_id)
            if i_role: overwrites[i_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(f"entrevista-{applicant.name}", category=category, overwrites=overwrites)
        await channel.send(f"¡Hola {applicant.mention}! Has sido seleccionado para una entrevista. Un {f'<@&{interviewer_role_id}>' if interviewer_role_id else 'entrevistador'} se pondrá en contacto contigo pronto.", view=CloseTicketView(self.bot))

class ApplicationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Postularse para Staff", style=discord.ButtonStyle.green, custom_id="apply_button")
    async def apply_button_callback(self, interaction: discord.Interaction, button: Button):
        config = load_config()
        if not config['applications_open']:
            redirect_id = config['channels'].get('closed_redirect')
            mention = f"<#{redirect_id}>" if redirect_id else "el canal correspondiente"
            await interaction.response.send_message(f"Las postulaciones están cerradas. Consulta {mention}.", ephemeral=True)
            return

        guild = interaction.guild
        member = interaction.user

        channel_name = f'postu-{member.name.lower().replace(" ", "-")}'
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message("Ya tienes un canal de postulación abierto.", ephemeral=True)
            return

        category_id = config['categories'].get('tickets')
        category = guild.get_channel(category_id) if category_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        }
        
        staff_role_id = config['roles'].get('staff')
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await interaction.response.send_message(f"Canal creado: {ticket_channel.mention}", ephemeral=True)
        await send_log_embed(self.bot, config, "Nuevo Ticket", f"{member.mention} ha abierto un ticket de postulación: {ticket_channel.mention}")

        await ticket_channel.send(f"¡Hola {member.mention}! Responde a las siguientes preguntas para completar tu postulación.")

        questions = load_questions()
        answers = {}
        
        for i, question in enumerate(questions):
            # Barra de progreso visual
            progress = i / len(questions)
            bar_length = 15
            filled = int(progress * bar_length)
            bar = "🟩" * filled + "⬜" * (bar_length - filled)
            
            embed_q = discord.Embed(title=f"Pregunta {i+1} de {len(questions)}", description=question, color=config['embeds']['application_color'])
            embed_q.set_footer(text=f"Progreso: [{bar}] {int(progress*100)}%")
            
            await ticket_channel.send(embed=embed_q)
            
            def check(m):
                return m.author == member and m.channel == ticket_channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=600)
                answers[question] = msg.content
            except asyncio.TimeoutError:
                await ticket_channel.send("Tiempo agotado. El canal se cerrará.")
                await asyncio.sleep(5)
                await ticket_channel.delete()
                return

        # Registro en historial JSON
        log_application(member.id, member.name, answers)

        # Resumen final en el canal del ticket
        embed_res = discord.Embed(title=f"Resumen de Postulación: {member.display_name}", color=discord.Color.gold())
        for q, a in answers.items():
            val = (a[:1020] + "...") if len(a) > 1024 else a
            embed_res.add_field(name=q, value=val, inline=False)

        await ticket_channel.send(embed=embed_res)
        await ticket_channel.send("✅ **Postulación completada.** El Staff revisará tus respuestas. No cierres este canal.", view=CloseTicketView(self.bot))
        
        # Enviar al canal de revisión
        review_channel_id = config['channels'].get('review')
        if review_channel_id:
            review_channel = self.bot.get_channel(review_channel_id)
            if review_channel:
                await review_channel.send(embed=embed_res, view=ReviewView(self.bot, member.id, answers))

class ApplicationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ApplicationView(self.bot))
        self.bot.add_view(CloseTicketView(self.bot))
        # Nota: ReviewView no es persistente globalmente de la misma forma sin una BD compleja, 
        # pero para Railway y reinicios ocasionales, las vistas en mensajes antiguos pueden requerir manejo dinámico.
        # Aquí lo mantenemos simple.

async def setup(bot):
    await bot.add_cog(ApplicationCog(bot))
