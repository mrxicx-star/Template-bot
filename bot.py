#!/usr/bin/env python3
import os
import json
import asyncio
import requests
from pathlib import Path
import datetime
from typing import Optional
import discord
from discord.ext import commands
from discord import Permissions

# -----------------------------
# Load tokens from environment
# -----------------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# -----------------------------
# Intents & bot setup
# -----------------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # remove default help

# -----------------------------
# Config & templates
# -----------------------------
CONFIG_DIR = Path("configs")
CONFIG_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)
AUTOROLE_FILE = CONFIG_DIR / "autoroles.json"

def _load_autoroles():
    if AUTOROLE_FILE.exists():
        try:
            return json.loads(AUTOROLE_FILE.read_text())
        except Exception:
            return {}
    return {}

def _save_autoroles(data):
    AUTOROLE_FILE.write_text(json.dumps(data, indent=2))

def is_guild_admin(ctx):
    return ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.administrator

# -----------------------------
# Multi-page help embed
# -----------------------------
help_pages = [
    {"title": "Moderation Commands", "description": "**Kick/Ban:** `!kick @user`, `!ban @user [reason]`\n**Mute/Unmute:** `!mute @user`, `!unmute @user`\n**Timeout:** `!tempban @user 10m/h/d`, `!softban @user`\n**Warnings:** `!warn @user [reason]`, `!warns @user`, `!clearwarns @user`\n**Purge messages:** `!purge 10` deletes 10 messages\n**Slowmode:** `!slowmode 5s/10s/1m`"},
    {"title": "Reaction Roles & Tags", "description": "**Reaction Roles:** `!rr make`, `!rr add`, `!rr remove`, `!rr unique`, `!rr clear`, `!rr edit`\n**Tags:** `!tag add`, `!tag edit`, `!tag remove`, `!tags`, `!tag info`"},
    {"title": "Server Settings / Logging", "description": "**Prefix:** `!prefix set !`\n**Logging:** `!log channel #channel`, `!log ignore @role`\n**Starboard:** `!starboard`\n**Auto-post / Levels:** `!autopost`, `!levels`, `!rank`\n**Giveaways & Polls:** `!giveaway`, `!poll`"},
    {"title": "Role Management", "description": "**Add/Remove Roles:** `!role add @user Role`, `!role remove @user Role`\n**Role Color:** `!role color Role #hex`\n**Role List:** `!role list`\n**Ignore / Enable:** `!ignore`, `!unignore`, `!disable`, `!enable`"},
    {"title": "General / Info", "description": "**Help:** `!help` (this page)\n**Info:** `!info`\n**Ping:** `!ping`\n**Server Info:** `!serverinfo`\n**User Info:** `!userinfo @user`\n**Avatar:** `!avatar @user`"},
    {"title": "Extra Moderator Tools", "description": "**Mod Logs:** `!modlogs @user`\n**Clear warnings:** `!clearwarns @user`\n**Mass Kick/Ban:** `!masskick @role`, `!massban @role`\n**Event / Announcement:** `!announce message`, `!event create`\n**Audit:** `!audit logs`\n**Server Maintenance:** `!lockdown`, `!unlock`"},
]

class HelpView(discord.ui.View):
    def __init__(self, pages):
        super().__init__(timeout=180)
        self.pages = pages
        self.current = 0
        self.message = None

    async def update_embed(self):
        page = self.pages[self.current]
        embed = discord.Embed(title=page["title"], description=page["description"], color=discord.Color.blue())
        embed.set_footer(text=f"Page {self.current+1}/{len(self.pages)}")
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await self.update_embed()
        await interaction.response.defer()

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await self.update_embed()
        await interaction.response.defer()

@bot.command(name="help")
async def custom_help(ctx):
    view = HelpView(help_pages)
    embed = discord.Embed(title=help_pages[0]["title"], description=help_pages[0]["description"], color=discord.Color.blue())
    embed.set_footer(text=f"Page 1/{len(help_pages)}")
    view.message = await ctx.send(embed=embed, view=view)

# -----------------------------
# Bot Events
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ Missing permission: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ Bot missing permission: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument")
    else:
        print(f"Command error: {error}")

# -----------------------------
# Moderation / Roles commands
# -----------------------------
def _parse_duration_to_seconds(s: str) -> Optional[int]:
    s = s.strip().lower()
    try:
        if s.endswith("s"): return int(s[:-1])
        if s.endswith("m"): return int(s[:-1])*60
        if s.endswith("h"): return int(s[:-1])*3600
        if s.endswith("d"): return int(s[:-1])*86400
        return int(s)*60
    except: return None

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ Kicked {member} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not kick: {e}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Banned {member} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not ban: {e}")

@bot.command(name="mute")
async def mute(ctx, member: discord.Member, *, reason: str=None):
    try:
        until = datetime.datetime.utcnow() + datetime.timedelta(days=28)
        await member.edit(communication_disabled_until=until, reason=reason)
        await ctx.send(f"✅ Muted {member.mention} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not mute: {e}")

@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member, *, reason: str=None):
    try:
        await member.edit(communication_disabled_until=None, reason=reason)
        await ctx.send(f"✅ Unmuted {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ Could not unmute: {e}")

# -----------------------------
# Autorole commands
# -----------------------------
@bot.command(name="setautorole")
@commands.check(lambda ctx: is_guild_admin(ctx))
async def set_autorole(ctx, *, role_name: str):
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
    if role is None:
        await ctx.send("❌ Role not found.")
        return
    data = _load_autoroles()
    data[str(guild.id)] = role.id
    _save_autoroles(data)
    await ctx.send(f"✅ Autorole set to {role.name}")

@bot.command(name="removeautorole")
@commands.check(lambda ctx: is_guild_admin(ctx))
async def remove_autorole(ctx):
    guild = ctx.guild
    data = _load_autoroles()
    if str(guild.id) in data:
        del data[str(guild.id)]
        _save_autoroles(data)
        await ctx.send("✅ Autorole removed.")
    else:
        await ctx.send("❌ No autorole set for this server.")

@bot.event
async def on_member_join(member: discord.Member):
    data = _load_autoroles()
    rid = data.get(str(member.guild.id))
    if rid:
        role = discord.utils.get(member.guild.roles, id=rid)
        if role:
            try: await member.add_roles(role)
            except: pass

# -----------------------------
# Run the bot
# -----------------------------
bot.run(DISCORD_BOT_TOKEN)

        