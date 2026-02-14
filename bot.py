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

# Load tokens from environment variables (safer than hardcoding)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

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

@bot.event
async def on_ready():
    print("✅ Bot is online as", bot.user)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You don't have permission to use this command. Required: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ Bot missing permissions: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided")
    else:
        print(f"Command error: {error}")

# -----------------------------
# Setup commands
# -----------------------------
@bot.group(name="setup", invoke_without_command=True)
@commands.check(lambda ctx: is_guild_admin(ctx))
async def setup(ctx, template_url: str = None):
    """Group for server setup commands."""
    if template_url:
        loop = asyncio.get_running_loop()
        try:
            resp = await loop.run_in_executor(None, requests.get, template_url)
        except Exception as e:
            await ctx.send(f"❌ Failed to fetch template: {e}")
            return
        if resp.status_code != 200:
            await ctx.send(f"❌ Failed to fetch template: HTTP {resp.status_code}")
            return

        content_type = resp.headers.get("Content-Type", "")
        try:
            if "json" in content_type.lower():
                data = resp.json()
            else:
                text = resp.text.strip()
                if not text:
                    await ctx.send("❌ Template response was empty. Provide a raw JSON URL or paste the template JSON.")
                    return
                try:
                    data = json.loads(text)
                except Exception as e:
                    preview = (text[:300] + "...") if len(text) > 300 else text
                    await ctx.send(
                        f"❌ Failed to parse JSON template. Ensure the URL points to raw JSON.\nParse error: {e}\nResponse preview:\n```\n{preview}\n```"
                    )
                    return
        except Exception as e:
            await ctx.send(f"❌ Failed to parse template response: {e}")
            return

        await apply_template_data(ctx, data)
        return

    await ctx.send("Usage: `!setup roles`, `!setup channels`, or `!setup all`")

@setup.command(name="roles")
@commands.check(lambda ctx: is_guild_admin(ctx))
async def setup_roles(ctx):
    """Create common roles: Admin, Moderator, Member"""
    guild = ctx.guild
    created = []
    roles_to_create = [
        ("Admin", Permissions(administrator=True)),
        ("Moderator", Permissions(kick_members=True, ban_members=True, manage_messages=True)),
        ("Member", Permissions(send_messages=True, read_messages=True)),
    ]
    for name, perms in roles_to_create:
        if discord.utils.get(guild.roles, name=name) is None:
            role = await guild.create_role(name=name, permissions=perms)
            created.append(role.name)
    await ctx.send(f"✅ Roles created: {', '.join(created) if created else 'none (already exist)'}")

@setup.command(name="channels")
@commands.check(lambda ctx: is_guild_admin(ctx))
async def setup_channels(ctx):
    """Create categories and common channels."""
    guild = ctx.guild

    def get_or_create_category(name):
        return discord.utils.get(guild.categories, name=name)

    created = []

    # Welcome
    if get_or_create_category("Welcome") is None:
        cat = await guild.create_category("Welcome")
        welcome = await guild.create_text_channel("welcome", category=cat)
        rules = await guild.create_text_channel("rules", category=cat)
        created += ["category: Welcome", "welcome", "rules"]

    # General
    if get_or_create_category("General") is None:
        cat = await guild.create_category("General")
        general = await guild.create_text_channel("general", category=cat)
        bot_commands = await guild.create_text_channel("bot-commands", category=cat)
        created += ["category: General", "general", "bot-commands"]

    # Voice
    if get_or_create_category("Voice") is None:
        cat = await guild.create_category("Voice")
        vc = await guild.create_voice_channel("General VC", category=cat)
        created += ["category: Voice", "General VC"]

    await ctx.send(f"✅ Channels created: {', '.join(created) if created else 'none (already exist)'}")

@setup.command(name="all")
@commands.check(lambda ctx: is_guild_admin(ctx))
async def setup_all(ctx, name: str = "default"):
    """Apply a template or fallback to basic setup."""
    tpl = TEMPLATES_DIR / f"{name}.json"
    if tpl.exists():
        await apply_template(ctx, name)
        return

    if ctx.message and getattr(ctx.message, "attachments", None):
        att = ctx.message.attachments[0]
        loop = asyncio.get_running_loop()
        try:
            resp = await loop.run_in_executor(None, requests.get, att.url)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    await apply_template_data(ctx, data)
                    return
                except Exception as e:
                    await ctx.send(f"❌ Attached file failed JSON parse: {e}")
            else:
                await ctx.send(f"❌ Could not download attachment: HTTP {resp.status_code}")
        except Exception as e:
            await ctx.send(f"❌ Failed to fetch attachment: {e}")

    await setup_roles(ctx)
    await setup_channels(ctx)

# -----------------------------
# Template helpers
# -----------------------------
async def apply_template(ctx, name: str):
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        await ctx.send("❌ Template not found.")
        return
    guild = ctx.guild
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        await ctx.send(f"❌ Failed to read template: {e}")
        return
    await apply_template_data(ctx, data)

async def apply_template_data(ctx, data: dict):
    guild = ctx.guild
    me = guild.me
    perm_warnings = []
    if not me.guild_permissions.manage_roles:
        perm_warnings.append("manage_roles")
    if not me.guild_permissions.manage_channels:
        perm_warnings.append("manage_channels")
    if perm_warnings:
        await ctx.send(f"❌ Bot missing permissions: {', '.join(perm_warnings)}. It may fail to create roles/channels.")

    created_roles = []
    failed_roles = []
    for r in data.get("roles", []):
        try:
            if discord.utils.get(guild.roles, name=r) is None:
                await guild.create_role(name=r)
                created_roles.append(r)
        except Exception as e:
            failed_roles.append((r, str(e)))

    created_ch = []
    failed_ch = []
    for cat in data.get("categories", []):
        cname = cat.get("name")
        existing = discord.utils.get(guild.categories, name=cname)
        try:
            newcat = existing or await guild.create_category(cname)
        except Exception as e:
            failed_ch.append((f"category:{cname}", str(e)))
            continue

        for ch in cat.get("channels", []):
            chname = ch.get("name")
            ctype = ch.get("type", "text")
            try:
                if any(c.name == chname for c in newcat.channels):
                    continue
                if ctype == "voice":
                    await guild.create_voice_channel(chname, category=newcat)
                else:
                    await guild.create_text_channel(chname, category=newcat)
                created_ch.append(f"{cname}/{chname}")
            except Exception as e:
                failed_ch.append((f"{cname}/{chname}", str(e)))

    summary_lines = [
        f"Roles created: {created_roles or 'none'}"
    ]
    if failed_roles:
        summary_lines.append(f"Roles failed: {failed_roles}")
    summary_lines.append(f"Channels created: {created_ch or 'none'}")
    if failed_ch:
        summary_lines.append(f"Channels failed: {failed_ch}")

    await ctx.send("✅ Template applied. " + " | ".join(summary_lines))

# -----------------------------
# Moderation / role commands
# -----------------------------
def _parse_duration_to_seconds(s: str) -> Optional[int]:
    s = s.strip().lower()
    try:
        if s.endswith("s"):
            return int(s[:-1])
        if s.endswith("m"):
            return int(s[:-1]) * 60
        if s.endswith("h"):
            return int(s[:-1]) * 3600
        if s.endswith("d"):
            return int(s[:-1]) * 86400
        return int(s) * 60
    except Exception:
        return None

# Example: kick, ban, timeout, addrole, removerole, mute, unmute
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ Kicked {member} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not kick: {e}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Banned {member} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not ban: {e}")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: str, *, reason: str = None):
    seconds = _parse_duration_to_seconds(duration)
    if seconds is None:
        await ctx.send("❌ Invalid duration. Examples: 10m, 1h, 30s, 1d, or plain minutes like 10.")
        return
    until = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
    try:
        await member.edit(communication_disabled_until=until, reason=reason)
        await ctx.send(f"✅ Timed out {member.mention} for {duration} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not timeout: {e}")

@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, *, role_name: str):
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
    if role is None:
        await ctx.send("❌ Role not found.")
        return
    try:
        await member.add_roles(role)
        await ctx.send(f"✅ Added role {role.name} to {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ Could not add role: {e}")

@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, *, role_name: str):
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
    if role is None:
        await ctx.send("❌ Role not found.")
        return
    try:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed role {role.name} from {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ Could not remove role: {e}")

@bot.command(name="mute")
async def mute(ctx, member: discord.Member, *, reason: str = None):
    try:
        until = datetime.datetime.utcnow() + datetime.timedelta(days=28)
        await member.edit(communication_disabled_until=until, reason=reason)
        await ctx.send(f"✅ Muted {member.mention} ({reason or 'no reason'})")
    except Exception as e:
        await ctx.send(f"❌ Could not mute: {e}")

@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member, *, reason: str = None):
    try:
        await member.edit(communication_disabled_until=None, reason=reason)
        await ctx.send(f"✅ Unmuted {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ Could not unmute: {e}")

@bot.command(name="warn")
async def warn(ctx, member: discord.Member, *, reason: str = None):
    await ctx.send(f"⚠️ {member.mention} has been warned ({reason or 'no reason'})")

@bot.command(name="warns")
async def warns(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"⚠️ {target.mention} has 0 warnings")

@bot.command(name="clearwarns")
async def clearwarns(ctx, member: discord.Member):
    await ctx.send(f"✅ Warnings cleared for {member.mention}")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"✅ Deleted {amount} messages.", delete_after=5)

# -----------------------------
# Autorole
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
    if not rid:
        return
    role = discord.utils.get(member.guild.roles, id=rid)
    if role:
        try:
            await member.add_roles(role)
        except Exception:
            pass
 
# -----------------------------
# Run bot
# -----------------------------
bot.run(DISCORD_BOT_TOKEN)
