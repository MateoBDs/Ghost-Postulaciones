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

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: Button):

        config = load_config()
        staff_role = config['roles'].get('staff')

        if not any(r.id == staff_role for r in interaction.user.roles) \
        and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ No tienes permisos",
                ephemeral=True
            )

        await interaction.response.send_message("Cerrando en 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()


# =========================
# 📋 COG PRINCIPAL
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
# 🟢 BOTÓN PRINCIPAL APPLY
# =========================
class ApplicationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Postularse para Staff",
        style=discord.ButtonStyle.green
    )
    async def apply(self, interaction: discord.Interaction, button: Button):

        config = load_config()

        if not config['applications_open']:
            return await interaction.response.send_message(
                "❌ Postulaciones cerradas",
                ephemeral=True
            )

        guild = interaction.guild
        member = interaction.user

        channel = await guild.create_text_channel(
            f"postu-{member.name}"
        )

        await interaction.response.send_message(
            f"Canal creado: {channel.mention}",
            ephemeral=True
        )

        await channel.send(f"Hola {member.mention}, responde las preguntas...")

        questions = load_questions()
        answers = {}

        for q in questions:
            await channel.send(q)

            def check(m):
                return m.author == member and m.channel == channel

            msg = await interaction.client.wait_for("message", check=check)
            answers[q] = msg.content

        log_application(member.id, member.name, answers)

        embed = discord.Embed(
            title=f"Postulación de {member}",
            color=discord.Color.gold()
        )

        for q, a in answers.items():
            embed.add_field(name=q, value=a[:1024], inline=False)

        review_channel = interaction.guild.get_channel(
            config['channels']['review']
        )

        await review_channel.send(
            embed=embed,
            view=ReviewView(self.bot, self.cog_from(interaction), member.id, answers)
        )

    def cog_from(self, interaction):
        return interaction.client.get_cog("ApplicationCog")


# =========================
# 📋 VIEW DE REVISIÓN
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
# 🟡 TOMAR REVISIÓN
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
            return await interaction.followup.send(
                "❌ No tienes permisos",
                ephemeral=True
            )

        msg_id = interaction.message.id

        if msg_id in self.cog.reviews:
            return await interaction.followup.send(
                f"❌ Ya está siendo revisada por <@{self.cog.reviews[msg_id]}>",
                ephemeral=True
            )

        self.cog.reviews[msg_id] = interaction.user.id

        if not interaction.message.embeds:
            return await interaction.followup.send("❌ Sin embed", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.add_field(
            name="📋 Estado",
            value=f"En revisión por: {interaction.user.mention}",
            inline=False
        )

        await interaction.message.edit(
            embed=embed,
            view=ReviewDecisionView(self.cog)
        )

        await interaction.followup.send("✔ Revisión tomada", ephemeral=True)


# =========================
# 🔵 DECISIÓN STAFF
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
# 📦 SETUP
# =========================
async def setup(bot):
    await bot.add_cog(ApplicationCog(bot))
