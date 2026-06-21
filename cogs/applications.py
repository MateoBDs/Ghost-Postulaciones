import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio

from utils.config_manager import load_config, load_questions
from utils.logger import log_application, send_log_embed


# =========================
# 📩 DM HELPER
# =========================
async def try_dm(user, text):
    try:
        await user.send(text)
    except:
        pass


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
# 📦 COG
# =========================
class ApplicationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # message_id -> data completa
        self.reviews = {}

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

        # DM EN ESPERA
        await try_dm(member, "Bienvenido al sistema de postulaciones, te tendremos informado del estado de tu postulación por aquí. Responde las preguntas que te estare haciendo en el ticket. ¡Suerte!.")

        await channel.send(f"👋 Hola {member.mention}, responde las preguntas.")

        questions = load_questions()
        answers = {}

        for q in questions:

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

        # ✅ AQUÍ YA TERMINÓ EL FORMULARIO
        await try_dm(member, "📩 Tu postulación ha sido enviada. Estado: EN ESPERA.")

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
            view=ReviewView(self.bot, cog, member.id, answers, channel.id)
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

        self.add_item(TakeReviewButton(cog, applicant_id))


# =========================
# 🟡 TAKE REVIEW
# =========================
class TakeReviewButton(Button):
    def __init__(self, cog, applicant_id):
        super().__init__(
            label="Tomar revisión",
            style=discord.ButtonStyle.primary,
            emoji="🟡"
        )
        self.cog = cog
        self.applicant_id = applicant_id

    async def callback(self, interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    config = load_config()
    staff_role = config['roles'].get('staff')

    if not any(r.id == staff_role for r in interaction.user.roles) \
    and not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ Sin permisos", ephemeral=True)

    msg_id = interaction.message.id

    if msg_id in self.cog.reviews:
        return await interaction.followup.send("❌ Ya tomado", ephemeral=True)

    self.cog.reviews[msg_id] = interaction.user.id

    # 🔥 AQUÍ EL DM QUE TE FALTABA
    applicant = interaction.guild.get_member(self.applicant_id)

    if applicant:
        try:
            await applicant.send("🔍 Tu postulación está EN REVISIÓN.")
        except:
            pass

    embed = interaction.message.embeds[0]
    embed.add_field(
        name="📋 Estado",
        value=f"En revisión por {interaction.user.mention}",
        inline=False
    )

    await interaction.message.edit(embed=embed, view=ReviewDecisionView(self.cog))

    await interaction.followup.send("✔ Revisión tomada", ephemeral=True)

        # guardamos todo
        self.cog.reviews[msg_id] = {
            "reviewer": interaction.user.id,
            "applicant": None,
            "channel": None
        }

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

        applicant_id = interaction.view.applicant_id
        self.cog.reviews[msg_id]["applicant"] = applicant_id
        self.cog.reviews[msg_id]["channel"] = interaction.view.channel_id

        user = interaction.guild.get_member(applicant_id)

        await try_dm(user, "🔍 Tu postulación está EN REVISIÓN.")


# =========================
# 🔵 DECISIÓN
# =========================
class ReviewDecisionView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(RejectButton(cog))
        self.add_item(InterviewButton(cog))


# =========================
# ❌ RECHAZO
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
        data = self.cog.reviews.get(msg_id)

        if not data or data["reviewer"] != interaction.user.id:
            return await interaction.response.send_message("❌ No eres el revisor", ephemeral=True)

        guild = interaction.guild
        user = guild.get_member(data["applicant"])

        await try_dm(user, "❌ Tu postulación ha sido RECHAZADA.")

        channel = guild.get_channel(data["channel"])
        if channel:
            await channel.delete()

        await interaction.message.delete()
        self.cog.reviews.pop(msg_id, None)

        await interaction.response.send_message("❌ Rechazado", ephemeral=True)


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
        data = self.cog.reviews.get(msg_id)

        if not data or data["reviewer"] != interaction.user.id:
            return await interaction.response.send_message("❌ No eres el revisor", ephemeral=True)

        config = load_config()
        guild = interaction.guild
        user = guild.get_member(data["applicant"])

        role_id = config['roles'].get('applicant')
        role = guild.get_role(role_id)

        if role and user:
            await user.add_roles(role)

        await try_dm(user, "🎤 Has pasado a ENTREVISTA. Un staff te contactará.")

        await interaction.response.send_message("🎤 Entrevista enviada", ephemeral=True)


# =========================
# 🚀 SETUP
# =========================
async def setup(bot):
    await bot.add_cog(ApplicationCog(bot))
