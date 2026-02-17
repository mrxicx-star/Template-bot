import discord
from discord.ext import commands
import datetime
import os
import re
import json

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
spam_users = {}
whitelist = set()
maintenance_mode = False
anti_link = True
badwords_filter = True

DATA_FILE = "settings.json"

# ----------------------------
# LOAD / SAVE SETTINGS
# ----------------------------
def load_settings():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_settings(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

settings = load_settings()

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
# WELCOME SYSTEM
# ----------------------------
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)

    if guild_id in settings and "greet_msg" in settings[guild_id]:
        greet_msg = settings[guild_id]["greet_msg"]
    else:
        greet_msg = "Welcome {user} to **{server}** ❤️"

    msg = greet_msg.replace("{user}", member.mention).replace("{server}", member.guild.name)

    embed = discord.Embed(
        title="🎉 New Member Joined!",
        description=msg,
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text="Enjoy your stay!")

    channel = member.guild.system_channel
    if channel:
        await channel.send(embed=embed)

# ----------------------------
# GREET SET COMMAND
# ----------------------------
@bot.command()
async def greetset(ctx, *, message):
    guild_id = str(ctx.guild.id)

    if guild_id not in settings:
        settings[guild_id] = {}

    settings[guild_id]["greet_msg"] = message
    save_settings(settings)

    await ctx.send(
        f"✅ Welcome message set!\n\nExample:\n`{message}`\n\nUse:\n`{{user}}` = mention\n`{{server}}` = server name"
    )

# ----------------------------
# HELP MENU BUTTON SYSTEM
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛡 Moderation", style=discord.ButtonStyle.danger)
    async def mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛡 Moderation Commands",
            description="""
`!kick @user` → Kick member  
`!ban @user` → Ban member  
`!mute @user 5m` → Timeout member  
`!unmute @user` → Remove timeout  
`!warn @user` → Warn member  
`!purge 10` → Delete messages  
`!setslowmode 5` → Slowmode  
""",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="ℹ Info", style=discord.ButtonStyle.primary)
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="ℹ Info Commands",
            description="""
`!si` → Server Info  
`!userinfo @user` → User Info  
`!avatarinfo @user` → Avatar Link  
""",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⚙ Setup", style=discord.ButtonStyle.success)
    async def setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙ Setup Commands",
            description="""
`!setupall` → Auto create server setup  

Creates:
✅ Categories  
✅ Channels  
✅ Roles  

⚠ Bot needs:
`Manage Channels`  
`Manage Roles`  
""",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="👋 Welcome", style=discord.ButtonStyle.secondary)
    async def welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👋 Welcome System",
            description="""
`!greetset <message>` → Set custom welcome  

Example:
`!greetset Welcome {user} to {server} ❤️`

Tags:
`{user}` = member mention  
`{server}` = server name  
""",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

# ----------------------------
# HELP COMMAND
# ----------------------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📌 Moderation Bot Help",
        description="Click buttons below to view commands",
        color=discord.Color.red()
    )
    embed.set_footer(text="Single Embed Help Menu ✅ No Duplicate")
    await ctx.send(embed=embed, view=HelpMenu())

# ----------------------------
# SERVER INFO COMMAND (!si)
# ----------------------------
@bot.command(name="si")
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title="📌 Server Info",
        description=f"**{guild.name}**",
        color=discord.Color.purple()
    )

    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=False)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💎 Boost Tier", value=guild.premium_tier, inline=True)
    embed.add_field(name="🆔 Server ID", value=guild.id, inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=f"Created at: {guild.created_at.strftime('%d %B %Y')}")

    await ctx.send(embed=embed)

# ----------------------------
# SETUPALL COMMAND
# ----------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setupall(ctx):
    guild = ctx.guild

    await ctx.send("⚙ Setting up server... Please wait!")

    # Categories
    main_cat = await guild.create_category("🔥 MAIN")
    staff_cat = await guild.create_category("🛡 STAFF")

    # Channels
    await guild.create_text_channel("welcome", category=main_cat)
    await guild.create_text_channel("general-chat", category=main_cat)
    await guild.create_voice_channel("General Voice", category=main_cat)

    await guild.create_text_channel("mod-logs", category=staff_cat)
    await guild.create_text_channel("admin-chat", category=staff_cat)

    # Roles
    await guild.create_role(name="👑 Admin", colour=discord.Color.red())
    await guild.create_role(name="🛡 Moderator", colour=discord.Color.blue told())
    await guild.create_role(name="✨ Member", colour=discord.Color.green())

    await ctx.send("✅ Setup Completed Successfully!")

# ----------------------------
# BASIC MOD COMMANDS
# ----------------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ Kicked {member.mention}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ Banned {member.mention}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, time: str):
    amount = int(time[:-1])
    until = datetime.datetime.utcnow() + datetime.timedelta(minutes=amount)
    await member.edit(timeout=until)
    await ctx.send(f"✅ Muted {member.mention} for {time}")

@bot.command()
async def unmute(ctx, member: discord.Member):
    await member.edit(timeout=None)
    await ctx.send(f"✅ Unmuted {member.mention}")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))