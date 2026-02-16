import discord
from discord.ext import commands
import datetime
import os
import re

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

OWNER_ID = None
log_channel_id = None
spam_users = {}
whitelist = set()
maintenance_mode = False
anti_link = True
badwords_filter = True

# ----------------------------
# BOT READY
# ----------------------------
@bot.event
async def on_ready():
    global OWNER_ID
    app_info = await bot.application_info()
    OWNER_ID = app_info.owner.id
    print(f"✅ Bot Online: {bot.user}")
    print(f"👑 Owner Loaded: {OWNER_ID}")

# ----------------------------
# PAGINATED HELP MENU (ONE EMBED)
# ----------------------------
class HelpPages(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.sections = [
            {
                "title": "Moderation Commands",
                "description": (
                    "> Use `/help <command>` to get more information\n\n"
                    "> `/caseupdate`\n"
                    "> `/caseclose`\n"
                    "> `/mute`\n"
                    "> `/namewarn`\n"
                    "> `/purge`\n"
                    "> `/setslowmode`\n"
                    "> `/unmute`\n"
                    "> `/unwarn`\n"
                    "> `/warn`\n"
                    "> `/warns`"
                )
            },
            {
                "title": "Info & Utility Commands",
                "description": (
                    "> Use `/help <command>` to get more information\n\n"
                    "> `/help`\n"
                    "> `/info`\n"
                    "> `/list`\n"
                    "> `/avatarinfo`\n"
                    "> `/bannerinfo`\n"
                    "> `/guildbannerinfo`\n"
                    "> `/guildiconinfo`\n"
                    "> `/guildmembercount`\n"
                    "> `/guildsplashinfo`\n"
                    "> `/stickerpackinfo`\n"
                    "> `/userinfo`\n"
                    "> `/casedelete`\n"
                    "> `/caseinfo`\n"
                    "> `/caselist`\n"
                    "> `/casesplit`"
                )
            }
        ]
        self.page = 0  # start with first section

    async def update_embed(self, interaction):
        section = self.sections[self.page]
        embed = discord.Embed(
            title="Moderation Bot Help Menu",
            description=section["description"],
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.sections)}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.primary)
    async def previous(self, interaction, button):
        self.page = (self.page - 1) % len(self.sections)
        await self.update_embed(interaction)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        self.page = (self.page + 1) % len(self.sections)
        await self.update_embed(interaction)

@bot.command()
async def help(ctx):
    """Shows the help menu with Next/Previous buttons."""
    view = HelpPages()
    section = view.sections[0]
    embed = discord.Embed(
        title="Moderation Bot Help Menu",
        description=section["description"],
        color=discord.Color.blue()
    )
    embed.set_footer(text="Page 1/2")
    await ctx.send(embed=embed, view=view)

# ----------------------------
# Rest of your bot commands go here...
# Keep all moderation, info, and owner commands as in your original code
# ----------------------------

bot.run(os.getenv("DISCORD_BOT_TOKEN"))