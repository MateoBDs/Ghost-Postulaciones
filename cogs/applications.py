import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio

from utils.config_manager import load_config, load_questions
from utils.logger import log_application, send_log_embed


# =========================
# 🔒 CLOSE TICKET VIEW
# =========================
class CloseTicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: Button):

        config = load_config()
        staff_role = config['roles'].get('staff')

        is_staff = any(r.id == staff_role for r in interaction.user.roles)

        if not is_staff and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Solo el staff puede cerrar esto",
                ephemeral=True
            )

        await interaction.response.send_message("⏳ Cerrando ticket en 5 segundos...")
        await asyncio.sleep(5)

        await send_log_embed(
            self.bot,
            config,
            "Ticket cerrado",
            f"{interaction.channel.name} cerrado por {interaction.user.mention}"
        )

        await interaction.channel.delete()


# =========================
# 📦 COG PRINCIPAL
# =========================
class ApplicationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reviews = {}  # message_id -> reviewer_id

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ApplicationView(self.bot))
        self.bot.add_view(CloseTicketView(self.bot))


# =========================
# 🟢 APPLY VIEW
# =========================
class ApplicationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Postularse para Staff", style=discord.ButtonStyle.green, custom_id="apply_button")
    async def apply(self, interaction: discord.Interaction, button: Button):

        config = load_config()

        if not config['applications_open']:
            return await interaction.response.send_message(
                "❌ Las postulaciones están cerradas",
                ephemeral=True
            )

        guild = interaction.guild
        member = interaction.user

        channel_name = f"postu-{member.name}".lower().replace(" ", "-")

        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            return await interaction.response.send_message(
                "❌ Ya tienes una postulación abierta",
                ephemeral=True
            )

        category = guild.get_channel(config['categories']['tickets'])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        staff_role = config['roles'].get('staff')
        if staff_role:
            role = guild.get_role(staff_role)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(
            f"📩 Canal creado: {channel.mention}",
            ephemeral=True
        )

        await send_log_embed(
            self.bot,
            config,
            "Nueva postulación",
            f"{member.mention} creó {channel.mention}"
        )

        await channel.send(f"👋 Hola {member.mention}, responde las preguntas.")

        questions = load_questions()
        answers = {}

        for i, q in enumerate(questions):

            await channel.send(f"❓ {q}")

            def check(m):
                return m.author == member and m.channel == channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=600)
                answers[q] = msg.content
            except asyncio.TimeoutError:
                await channel.send("⛔ Tiempo agotado")
                await asyncio.sleep(5)
                await channel.delete()
                return

        log_application(member.id, member.name, answers)

        embed = discord.Embed(
            title=f"📋 Postulación de {member}",
            color=discord.Color.gold()
        )

        for q, a in answers.items():
            embed.add_field(name=q, value=a[:1024], inline=False)

        review_channel = guild.get_channel(config['channels']['review'])

        cog = interaction.client.get_cog("ApplicationCog")

        await review_channel.send(
            embed=embed,
            view=ReviewView(self.bot, cog, member.id, answers)
        )


# =========================
# 📋 REVIEW VIEW
# =========================
class ReviewView(View):
    def __init__(self, bot, cog, applicant_id, answers):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
        self.applicant_id = applicant_id
        self.answers = answers

        self.add_item(TakeReviewButton(cog))


# =========================
# 🟡 TAKE REVIEW
# =========================
class TakeReviewButton(Button):
    def __init__(self, cog):
        super().__init__(
            label="Tomar revisión",
            style=discord.ButtonStyle.primary,
            emoji="🟡"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        config = load_config()
        staff_role = config['roles'].get('staff')

        if not any(r.id == staff_role for r in interaction.user.roles) \
        and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Sin permisos", ephemeral=True)

        msg_id = interaction.message.id

        if msg_id in self.cog.reviews:
            return await interaction.followup.send(
                f"❌ Ya tomado por <@{self.cog.reviews[msg_id]}>",
                ephemeral=True
            )

        self.cog.reviews[msg_id] = interaction.user.id

        if not interaction.message.embeds:
            return await interaction.followup.send("❌ Sin embed", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.add_field(
            name="📋 Estado",
            value=f"En revisión por {interaction.user.mention}",
            inline=False
        )

        await interaction.message.edit(
            embed=embed,
            view=ReviewDecisionView(self.cog)
        )

        await interaction.followup.send("✔ Revisión tomada", ephemeral=True)


# =========================
# 🔵 DECISION VIEW
# =========================
class ReviewDecisionView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(RejectButton(cog))
        self.add_item(InterviewButton(cog))


# =========================
# ❌ RECHAZAR
# =========================
class RejectButton(Button):
    def __init__(self, cog):
        super().__init__(
            label="Rechazar",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):

        msg_id = interaction.message.id

        if self.cog.reviews.get(msg_id) != interaction.user.id:
            return await interaction.response.send_message(
                "❌ No eres el revisor",
                ephemeral=True
            )

        await interaction.response.send_message(
            "❌ Postulación rechazada",
            ephemeral=True
        )


# =========================
# 🎤 ENTREVISTA
# =========================
class InterviewButton(Button):
    def __init__(self, cog):
        super().__init__(
            label="Entrevista",
            style=discord.ButtonStyle.success,
            emoji="🎤"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):

        msg_id = interaction.message.id

        if self.cog.reviews.get(msg_id) != interaction.user.id:
            return await interaction.response.send_message(
                "❌ No eres el revisor",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🎤 Entrevista solicitada",
            ephemeral=True
        )


# =========================
# 🚀 SETUP
# =========================
async def setup(bot):
    await bot.add_cog(ApplicationCog(bot))
