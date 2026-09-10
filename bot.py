import os
import re
import random
import asyncio
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import aiohttp

import discord
from discord import app_commands
from discord.ext import tasks, commands
import pymongo
from pymongo import MongoClient, DESCENDING
from bs4 import BeautifulSoup

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot connection nodes active!")
        
    def log_message(self, format, *args):
        return

class ResilientHTTPServer(HTTPServer):
    allow_reuse_address = True

def run_web_server():
    try:
        server = ResilientHTTPServer(("0.0.0.0", 10000), KeepAliveHandler)
        server.serve_forever()
    except OSError as e:
        print(f"⚠️ Web Infrastructure Note (Port 10000 busy): {e}. Proceeding smoothly.")

threading.Thread(target=run_web_server, daemon=True).start()

CODE_PATTERN = re.compile(r'\b[A-Za-z0-9_-]{6,16}\b')

BLACKLISTED_WORDS = {
    "REDEEM", "TOKENS", "CREDITS", "ASPHALT", "UNITE", 
    "REDDIT", "PLAYER", "NINTENDO", "XBOX", "PLAYSTATION",
    "WORKING", "PROMO", "REWARD", "CODES", "DISCORD", "SERVER"
}

# Safe fallbacks. If an admin inputs an invalid URL, the URL validator will strip it before sending to Discord.
DEFAULT_BANNER = None
DEFAULT_THUMBNAIL = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "myDiscordBot")

if not MONGO_URI:
    raise ValueError("❌ CRITICAL ERROR: The 'MONGO_URI' variable is missing from Discloud Environment Variables!")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]

guild_config_col = db["guild_config"]
player_profiles_col = db["player_profiles"]
scraper_cache_col = db["scraper_cache"]
backups_archive_col = db["daily_backups_archive"]

class AsphaltBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  
        intents.members = True          
        super().__init__(command_prefix="!", intents=intents)
        self.guild_cache = {}

    async def setup_hook(self):
        if not auto_code_scraper_loop.is_running():
            auto_code_scraper_loop.start()
        print("🟢 Background Scraping Engine successfully initialized.")

bot = AsphaltBot()

@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"✅ MongoDB cluster linked safely: {bot.user.name}")
    print(f"🤖 Bot application logged in as: {bot.user}")
    print(f"🛡️ Infrastructure systems running optimally.")
    print(f"==========================================")
    
    try:
        print("⚡ Synchronizing command trees to active servers...")
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print(f"🎯 Command matrices successfully bound locally across {len(bot.guilds)} servers.")
    except Exception as e:
        print(f"⚠️ Startup sync pipeline exception: {e}")

    try:
        loop = asyncio.get_event_loop()
        configs = await loop.run_in_executor(None, lambda: list(guild_config_col.find({})))
        for cfg in configs:
            g_id = cfg.get("guild_id")
            if g_id:
                bot.guild_cache[str(g_id)] = cfg
        print(f"📦 Preloaded configuration cache for {len(configs)} servers.")
    except Exception as e:
        print(f"⚠️ Non-blocking warning during startup cache preload: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.content == "!forcesyncguild":
        if not message.author.guild_permissions.administrator:
            try:
                await message.channel.send("❌ **Access Denied:** Only administrators can run this emergency force sync layout override.")
            except discord.Forbidden:
                pass
            return
            
        try:
            bot.tree.copy_global_to(guild=message.guild)
            synced = await bot.tree.sync(guild=message.guild)
            await message.channel.send(f"⚡ **Emergency Cache Breaker Active:** Successfully synchronized `{len(synced)}` commands straight to this server scope matrix! Please type `CTRL + R` or `CMD + R` to drop client UI lag tables.")
        except Exception as sync_err:
            await message.channel.send(f"⚠️ **Sync Pipeline Exception Encountered:** {sync_err}")
        return

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

def is_valid_image_url(url: str) -> bool:
    """Ensures URLs actually point directly to an image asset context to prevent Discord payload API silent rejections."""
    if not url or not isinstance(url, str):
        return False
    if url.startswith("https://imgur.com") and not (url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg") or url.endswith(".gif")):
        return False
    return url.startswith(("http://", "https://"))

class HelpDropdown(discord.ui.Select):
    def __init__(self, show_admin_docs: bool):
        options = [
            discord.SelectOption(label="ℹ️ Information Directory", value="information", description="What this bot does & core architecture overview."),
            discord.SelectOption(label="🎮 Player Utilities", value="player", description="Commands manifest and usage profiles for members."),
        ]
        if show_admin_docs:
            options.append(discord.SelectOption(label="🛡️ Admin Console", value="admin", description="Master system overrides and workspace tools."))
            
        super().__init__(placeholder="Select system segment...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            guild_id = str(interaction.guild_id)
            
            cfg_res = bot.guild_cache.get(guild_id)
            if not cfg_res:
                loop = asyncio.get_event_loop()
                cfg_res = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id})) or {}
                
            banner = cfg_res.get("banner_url", DEFAULT_BANNER)
            thumb = cfg_res.get("thumbnail_url", DEFAULT_THUMBNAIL)
            
            selected_value = self.values[0] if self.values else ""
            embed = None
            
            if selected_value == "information":
                embed = discord.Embed(
                    title="ℹ️ System Architecture & Operations Overview",
                    description=(
                        "This integration provides an advanced, automated notification network designed to solve "
                        "reward voucher lookup bottlenecks across the community infrastructure.\n\n"
                        "**Core Engine Blueprint:**\n"
                        "🔹 **Background Automated Scraper:** Wakeful task loops run quietly **every 5 minutes** executing non-blocking scrape routines across multi-site target vectors.\n"
                        "🔹 **Target Constraints Narrowing:** Filters analyze content blocks exclusively targeting **Asphalt Legends Unite** rewards metrics layout patterns.\n"
                        "🔹 **Smart Deduplication Pipeline:** Discovered strings match against database indexes to completely discard duplicate elements before alert delivery.\n"
                        "🔹 **Instant Direct Delivery Mapping:** Links prefill user credentials, sending registered players straight to Gameloft active portals with zero manual typing requirements."
                    ),
                    color=discord.Color.from_rgb(14, 21, 46)
                )
                if is_valid_image_url(banner):
                    embed.set_image(url=banner)
            elif selected_value == "player":
                embed = discord.Embed(
                    title="🕹️ Player Utilities & Manifest Commands Index",
                    description=(
                        "Universal commands available to all community members:\n\n"
                        "📝 `/help` - Launches this comprehensive interactive dropdown options navigation system map.\n"
                        "🔑 `/set_id [player_id]` - Links your custom Asphalt Player ID structure to your account data. **Requires format `u-` to register properly.** Enrolls you in premium priority DM notifications layers.\n"
                        "🔔 `/toggle_dm` - Dynamically toggles your private direct message rewards delivery pipeline channel **ON** or **OFF** instantly.\n"
                        "🗑️ `/delete_id` - Completely scrubs your personal registration metadata profile card from the global storage vaults."
                    ),
                    color=discord.Color.from_rgb(14, 21, 46)
                )
                if is_valid_image_url(thumb):
                    embed.set_thumbnail(url=thumb)
            elif selected_value == "admin":
                embed = discord.Embed(
                    title="⚙️ Master Administration Workspace & Controls Console",
                    description=(
                        "Management systems overrides restricted to designated server roles parameters:\n\n"
                        "🛠️ `/setup [channel] [admin_role] [player_role]` - Maps target reward notification drop streams, sets your base alert role ping configurations, and authorizes access keys.\n"
                        "📢 `/redeem [code]` - Forces a manual, priority reward notification layout broadcast across the configured server channel lanes and fires instant matching pre-filled player DMs.\n"
                        "📋 `/listplayers` - Generates a secure roster snapshot display showing up to 20 registered members and their active profiles matching this guild partition matrix.\n"
                        "🧹 `/clearhistory` - Opens an interactive verification interface to cleanly wipe all current player profiles registrations data streams out of this guild context records rows.\n"
                        "🖼️ `/admin_embed_builder [type] [attachment]` - Modifies graphic visuals layouts dynamically using live drag-and-drop file configuration options.\n"
                        "🩺 `/diagnose` - Triggers an infrastructure system stability check monitoring exact latency delays, environment variables states, and live cloud numbers.\n"
                        "🔄 `/sync` - Forces a complete command tree refresh sync operation updating structural slash mappings across Discord API servers instantly."
                    ),
                    color=discord.Color.from_rgb(14, 21, 46)
                )
                if is_valid_image_url(thumb):
                    embed.set_thumbnail(url=thumb)
            
            if embed is None:
                return

            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self.view)
        except Exception as e:
            print(f"❌ Exception captured inside HelpDropdown callback operations framework: {e}")

class HelpView(discord.ui.View):
    def __init__(self, show_admin_docs: bool):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(show_admin_docs))

class ConfirmClearHistoryView(discord.ui.View):
    def __init__(self, author: discord.Member, guild_id: str):
        super().__init__(timeout=60)
        self.author = author
        self.guild_id = guild_id
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="🟢")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: player_profiles_col.delete_many({"guild_id": self.guild_id}))
            self.stop()
            await interaction.response.edit_message(content="🧹 Wiped registration logs from server caches successfully!", view=None)
        except pymongo.errors.PyMongoError:
            await interaction.response.edit_message(content=f"⚠️ Database Operation Failure: Safe Mask Check Error, check environment profiles.", view=None)
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="🔴")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="🛑 Operation Aborted.", view=None)

@tasks.loop(minutes=5)
async def auto_code_scraper_loop():
    await bot.wait_until_ready()
    async with aiohttp.ClientSession() as session:
        rss_targets = [
            "https://old.reddit.com/r/AsphaltLegendsUnite/new/.rss",
            "https://old.reddit.com/r/Asphalt9/new/.rss"
        ]
        
        for url in rss_targets:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
            }
            try:
                async with session.get(url, headers=headers, timeout=12) as response:
                    if response.status == 200:
                        xml_data = await response.text()
                        
                        soup = BeautifulSoup(xml_data, features="xml")
                        for entry in soup.find_all('entry'):
                            title = entry.find('title')
                            content = entry.find('content')
                            
                            title_text = title.get_text() if title else ""
                            content_text = content.get_text() if content else ""
                            
                            search_blob = f"{title_text} {content_text}".upper()
                            await process_text_and_blast(search_blob)
            except Exception as e:
                print(f"⚠️ RSS Scraper Vector Matrix Delay Note on URL ({url}): {e}")
            await asyncio.sleep(3)

async def process_text_and_blast(search_blob: str):
    keywords = [
        "REDEEM CODE", "NEW CODE", "PROMO CODE", "FREE TOKENS", 
        "REWARD CODE", "WORKING CODE", "UNITE CODE", "GIFT CODE",
        "SEASON CODE", "CLAIM CODE", "FREEBIE", "PROMOCODE", "REDEEMCODE",
        "NEW REDEEM", "ASPHALTLEGOBMW", "LIMITED TIME", "PORTAL ACTIVE"
    ]
    if any(kw in search_blob for kw in keywords):
        for code in CODE_PATTERN.findall(search_blob):
            code = code.upper().replace("-", "")
            if code in BLACKLISTED_WORDS or len(code) < 6:
                continue
                
            loop = asyncio.get_event_loop()
            cache_check = await loop.run_in_executor(None, lambda: scraper_cache_col.find_one({"code": code}))
            if not cache_check:
                try:
                    await loop.run_in_executor(None, lambda: scraper_cache_col.insert_one({"code": code, "detected_at": datetime.now(timezone.utc)}))
                    print(f"📡 Multi-Site Scraper Engine Pipeline: Discovered Fresh Voucher Code Matrix -> {code}")
                    await execute_global_automation_blast(code)
                except Exception as db_err:
                    print(f"⚠️ Database Error archiving newly scraped code element context: {db_err}")

async def broadcast_code_to_dms(code: str, target_guild_id_str: str = None):
    loop = asyncio.get_event_loop()
    
    query_filter = {"dm_enabled": True}
    if target_guild_id_str:
        query_filter["guild_id"] = target_guild_id_str
        
    profiles_res = await loop.run_in_executor(None, lambda: list(player_profiles_col.find(query_filter)))
    if not profiles_res:
        return

    players_by_guild = {}
    for p in profiles_res:
        g_id = p["guild_id"]
        if g_id not in players_by_guild:
            players_by_guild[g_id] = []
        players_by_guild[g_id].append(p)

    for guild_id_str, players in players_by_guild.items():
        guild = bot.get_guild(int(guild_id_str))
        if not guild:
            continue
            
        for p_info in players:
            member = guild.get_member(int(p_info["user_id"]))
            if not member:
                try:
                    member = await guild.fetch_member(int(p_info["user_id"]))
                except Exception:
                    continue
                    
            if member:
                prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends?playerId={p_info['player_id']}&code={code.upper()}"
                dm_embed = discord.Embed(
                    title="🏁 Reward Pipeline Notification: Link Online", 
                    description=f"A fresh voucher code has matched your player registry matrix. Click the button mapping below to process immediate claiming actions.", 
                    color=discord.Color.from_rgb(14, 21, 46)
                )
                dm_embed.add_field(name="🔑 Target Code", value=f"`{code.upper()}`", inline=True)
                dm_embed.add_field(name="🆔 Linked Account ID", value=f"`{p_info['player_id']}`", inline=True)
                
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="🚀 Speed-Redeem Link", url=prefilled_url, style=discord.ButtonStyle.link))
                try:
                    await member.send(embed=dm_embed, view=view)
                    await asyncio.sleep(0.2)
                except discord.Forbidden:
                    print(f"🚫 Direct message delivery block encountered for player user UID {p_info['user_id']}. Privacy restrictions active.")
                except Exception as dm_err:
                    print(f"⚠️ DM transmission channel failure on user interface lines mapping loop: {dm_err}")

async def execute_global_automation_blast(code: str):
    loop = asyncio.get_event_loop()
    configs_res = await loop.run_in_executor(None, lambda: list(guild_config_col.find({})))
    
    if not configs_res:
        return

    for guild_cfg in configs_res:
        guild_id_str = guild_cfg["guild_id"]
        guild = bot.get_guild(int(guild_id_str))
        if not guild:
            continue
            
        channel_id = guild_cfg.get("notification_channel")
        if not channel_id:
            continue
            
        target_channel = bot.get_channel(int(channel_id))
        if not target_channel:
            try:
                target_channel = await bot.fetch_channel(int(channel_id))
            except Exception:
                continue
                
        if not target_channel:
            continue
            
        prev_msg_id = guild_cfg.get("last_notification_message_id")
        if prev_msg_id:
            try:
                old_msg = await target_channel.fetch_message(int(prev_msg_id))
                await old_msg.delete()
            except Exception:
                pass

        player_role_id = guild_cfg.get("alert_role_id")
        ping_string = f"<@&{player_role_id}>" if player_role_id else "@everyone"
        public_embed = discord.Embed(
            title="🏁 OFFICIAL ASPHALT LEGENDS UNITE REDEEM CODE 🏁",
            description=f"A new universal rewards voucher has been deployed across global tracking arrays!\n\n**PROMO CODE:**\n```📬 {code.upper()} ```\n\n[Launch Official Redeem Portal](https://www.gameloft.com/redeem/asphalt-legends)",
            color=discord.Color.from_rgb(14, 21, 46)
        )
        
        banner_url = guild_cfg.get("banner_url")
        if is_valid_image_url(banner_url):
            public_embed.set_image(url=banner_url)
        
        try:
            sent_msg = await target_channel.send(content=ping_string, embed=public_embed)
            await loop.run_in_executor(None, lambda: guild_config_col.update_one(
                {"guild_id": guild_id_str},
                {"$set": {"last_notification_message_id": sent_msg.id}}
            ))
        except Exception as msg_err:
            print(f"⚠️ Failed broadcasting layout message to public channel in server {guild_id_str}: {msg_err}")

    await broadcast_code_to_dms(code)

def is_admin_or_delegated():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        if interaction.user.guild_permissions.administrator:
            return True
        
        guild_id = str(interaction.guild.id)
        cfg_check = bot.guild_cache.get(guild_id)
        
        if not cfg_check:
            loop = asyncio.get_event_loop()
            cfg_check = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
            if cfg_check:
                bot.guild_cache[guild_id] = cfg_check
        
        if cfg_check:
            delegated_role_id = cfg_check.get("bot_admin_role_id")
            if delegated_role_id and discord.utils.get(interaction.user.roles, id=int(delegated_role_id)):
                return True
                
        raise app_commands.errors.MissingPermissions(["administrator"])
    return app_commands.check(predicate)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("🚫 **Access Denied:** administrative clearances validation parameters verification error.", ephemeral=True)

@bot.tree.command(name="help", description="📖 Comprehensive interactive navigation documentation matrix console manual.")
async def help_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    is_authorized = False
    
    if interaction.user.guild_permissions.administrator:
        is_authorized = True
    else:
        cfg_check = bot.guild_cache.get(guild_id)
        if not cfg_check:
            loop = asyncio.get_event_loop()
            cfg_check = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
            if cfg_check:
                bot.guild_cache[guild_id] = cfg_check
                
        if cfg_check and cfg_check.get("bot_admin_role_id") and discord.utils.get(interaction.user.roles, id=int(cfg_check["bot_admin_role_id"])):
            is_authorized = True

    embed = discord.Embed(
        title="🗂️ Help Documentation & Information Command Center", 
        description="Welcome to the system navigation interface launcher panel. Please select an operational directory partition from the dropdown choice box component below to view specific metrics layout guidelines.", 
        color=discord.Color.from_rgb(14, 21, 46)
    )
    await interaction.response.send_message(embed=embed, view=HelpView(is_authorized), ephemeral=True)

@bot.tree.command(name="set_id", description="🎮 Link your private unique Asphalt Player Identification hash tracker sequence.")
async def set_id_slash(interaction: discord.Interaction, player_id: str):
    player_id = player_id.strip().lower()
    if not player_id.startswith("u-"):
        return await interaction.response.send_message("⚠️ Format Exception: Account ID parameters must begin explicitly with `u-` identifier structures mapping chains.", ephemeral=True)

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: player_profiles_col.find_one({"guild_id": guild_id, "user_id": user_id})) or {}
    current_dm_pref = prof_check.get("dm_enabled", True)
    
    await loop.run_in_executor(None, lambda: player_profiles_col.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": {"username": interaction.user.name, "player_id": player_id, "dm_enabled": current_dm_pref}},
        upsert=True
    ))
    
    cfg_check = bot.guild_cache.get(guild_id)
    if not cfg_check:
        cfg_check = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
        if cfg_check:
            bot.guild_cache[guild_id] = cfg_check
            
    if cfg_check and cfg_check.get("alert_role_id"):
        role = interaction.guild.get_role(int(cfg_check["alert_role_id"]))
        if role:
            try: 
                await interaction.user.add_roles(role)
            except discord.Forbidden: 
                pass
                
    dm_status_str = "ON" if current_dm_pref else "OFF"
    await interaction.response.send_message(f"✅ Linked Asphalt ID: **{player_id}**\n🔔 Private DM Alerts Status: **{dm_status_str}**")

@bot.tree.command(name="delete_id", description="🗑️ Public Tool: Unlink and scrub your profile data completely from cluster ledgers.")
async def delete_id_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: player_profiles_col.find_one({"guild_id": guild_id, "user_id": user_id}))
    if prof_check:
        await loop.run_in_executor(None, lambda: player_profiles_col.delete_one({"guild_id": guild_id, "user_id": user_id}))
        await interaction.response.send_message("❌ Account profiling data matrix scrubbed cleanly out of structural registers tables lanes.")
    else:
        await interaction.response.send_message("⚠️ Context signature lookups failure: No registration data located matching your profile ID.", ephemeral=True)

@bot.tree.command(name="toggle_dm", description="🔔 Public Tool: Instantly switches your private direct message rewards delivery on or off.")
async def toggle_dm_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: player_profiles_col.find_one({"guild_id": guild_id, "user_id": user_id}))
    if not prof_check:
        return await interaction.response.send_message("⚠️ Setup Exception: You must register a structural account ID sequence via `/set_id` before toggling channels.", ephemeral=True)
    new_pref = not prof_check.get("dm_enabled", True)
    await loop.run_in_executor(None, lambda: player_profiles_col.update_one({"guild_id": guild_id, "user_id": user_id}, {"$set": {"dm_enabled": new_pref}}))
    await interaction.response.send_message(f"🔔 DM notification delivery preferences altered: Alerts turned **{'ON' if new_pref else 'OFF'}**.")

@bot.tree.command(name="setup", description="🛠️ Admin Tool: Configure notification target channels, manager clearings, and player pings.")
@is_admin_or_delegated()
async def setup_slash(interaction: discord.Interaction, announcement_channel: discord.TextChannel, admin_role: discord.Role, player_role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    
    updated_config = {
        "guild_id": guild_id,
        "notification_channel": announcement_channel.id, 
        "bot_admin_role_id": admin_role.id, 
        "alert_role_id": player_role.id,
        "banner_url": None,
        "thumbnail_url": None
    }
    
    await loop.run_in_executor(None, lambda: guild_config_col.update_one(
        {"guild_id": guild_id}, 
        {"$set": updated_config}, 
        upsert=True
    ))
    bot.guild_cache[guild_id] = updated_config
    await interaction.followup.send("⚙️ Setup matrix configuration nodes saved directly to cloud tables rows checked successfully!", ephemeral=True)

@bot.tree.command(name="redeem", description="📢 Admin Tool: Dispatches an administrative custom priority voucher alert.")
@is_admin_or_delegated()
async def redeem_slash(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    code = code.strip().upper()
    
    try:
        cfg_res = bot.guild_cache.get(guild_id)
        if not cfg_res:
            loop = asyncio.get_event_loop()
            cfg_res = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
            if cfg_res:
                bot.guild_cache[guild_id] = cfg_res
                
        if not cfg_res or not cfg_res.get("notification_channel"):
            return await interaction.followup.send("⚠️ Configuration Missing or Broken: Please re-run the `/setup` command to rebuild your database rows.", ephemeral=True)
            
        channel_id = int(cfg_res["notification_channel"])
        target_channel = bot.get_channel(channel_id)
        
        if not target_channel:
            try:
                target_channel = await bot.fetch_channel(channel_id)
            except Exception:
                target_channel = None

        if not target_channel:
            return await interaction.followup.send("⚠️ Setup Error: The target announcement channel could not be found or access is forbidden. Please re-run `/setup`.", ephemeral=True)
        
        public_embed = discord.Embed(
            title="🏁 MANUAL REWARDS REDEEM CODE ALERT 🏁", 
            description=f"An administrative reward drop has occurred!\n\n**PROMO CODE:**\n```📬 {code} ```\n\n[Launch Official Redeem Portal](https://www.gameloft.com/redeem/asphalt-legends)", 
            color=discord.Color.from_rgb(14, 21, 46)
        )
        
        banner_url = cfg_res.get("banner_url")
        if is_valid_image_url(banner_url):
            public_embed.set_image(url=banner_url)
        
        await target_channel.send(embed=public_embed)
        await interaction.followup.send("✅ Public drop notifications dispatched successfully across connected channels.", ephemeral=True)

        await broadcast_code_to_dms(code, target_guild_id_str=guild_id)

    except Exception as cmd_error:
        print(f"❌ Critical Error inside /redeem command routine: {cmd_error}")
        try:
            await interaction.followup.send(f"⚠️ Internal System Error: `{cmd_error}`. Check your Discloud server console logs for details.", ephemeral=True)
        except Exception:
            pass

@bot.tree.command(name="listplayers", description="📋 Admin Tool: Displays active membership profiling registration lists.")
@is_admin_or_delegated()
async def listplayers_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    server_res = await loop.run_in_executor(None, lambda: list(player_profiles_col.find({"guild_id": guild_id}).limit(20)))
    if not server_res:
        return await interaction.followup.send("🧹 Enrollment checklists index metrics are currently blank.", ephemeral=True)
        
    embed = discord.Embed(title="📋 Registered Manifest Checklist", color=discord.Color.from_rgb(14, 21, 46))
    for info in server_res:
        embed.add_field(name=f"User Display Profile: {info['username']}", value=f"🆔 Game Account ID: `{info['player_id']}`", inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="clearhistory", description="🧹 Admin Tool: Purges the player configuration registry table dataset for this guild.")
@is_admin_or_delegated()
async def clearhistory_slash(interaction: discord.Interaction):
    view = ConfirmClearHistoryView(interaction.user, str(interaction.guild_id))
    await interaction.response.send_message(content="⚠️ Proceed with purging profiles for this guild context partition line logs?", view=view, ephemeral=True)

@bot.tree.command(name="admin_restore", description="🔄 Admin Tool: Restores registration records snapshots from system backup storage matrices.")
@is_admin_or_delegated()
async def admin_restore_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    try:
        archive_res = await loop.run_in_executor(None, lambda: list(backups_archive_col.find({"guild_id": guild_id}).sort("saved_at", DESCENDING)))
        if not archive_res: 
            return await interaction.followup.send("⚠️ Snapshot Restore Note: No historical backup file configurations found inside this partition tracker.", ephemeral=True)
        
        restored_count = 0
        seen_users = set()
        for row in archive_res:
            u_id = row["user_id"]
            if u_id not in seen_users:
                seen_users.add(u_id)
                await loop.run_in_executor(None, lambda: player_profiles_col.update_one(
                    {"guild_id": guild_id, "user_id": u_id},
                    {"$set": {"username": row["username"], "player_id": row["player_id"], "dm_enabled": row["dm_enabled"]}},
                    upsert=True
                ))
                restored_count += 1
        await interaction.followup.send(f"🟢 Sync checked! Restored `{restored_count}` player profile entry cards successfully!", ephemeral=True)
    except pymongo.errors.PyMongoError:
        await interaction.followup.send(f"⚠️ Snapshot Restore Failure: An internal ledger reading error occurred.", ephemeral=True)

@bot.tree.command(name="admin_embed_builder", description="🖼️ Admin Tool: Direct image upload tool mapping server branding banners/thumbnails configurations.")
@app_commands.choices(element=[app_commands.Choice(name="Banner Layout Image", value="banner"), app_commands.Choice(name="Thumbnail Layout Image", value="thumbnail")])
@is_admin_or_delegated()
async def admin_embed_builder_slash(interaction: discord.Interaction, element: app_commands.Choice[str], image_file: discord.Attachment):
    if not image_file.content_type or not image_file.content_type.startswith("image/"):
        return await interaction.response.send_message("⚠️ Attachment Error: Target file structure must evaluate cleanly to standard graphic format types.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    saved_url = image_file.url
    guild_id = str(interaction.guild_id)
    field = "banner_url" if element.value == "banner" else "thumbnail_url"
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: guild_config_col.update_one({"guild_id": guild_id}, {"$set": {field: saved_url}}, upsert=True))
    
    if guild_id not in bot.guild_cache:
        bot.guild_cache[guild_id] = {}
    bot.guild_cache[guild_id][field] = saved_url
    
    await interaction.followup.send(f"🎯 Brand Visual Success: The custom {element.name} asset has been cached and loaded into automated drop templates.", ephemeral=True)

@bot.tree.command(name="identity", description="👤 Owner Tool: Dynamically rebrand the bot name and avatar via a single interactive interface option.")
@app_commands.describe(new_name="The updated display name for the bot application.", avatar_file="The graphic file asset to register as the bot's new profile picture.")
@commands.is_owner()
async def identity_slash(interaction: discord.Interaction, new_name: str, avatar_file: discord.Attachment):
    if not avatar_file.content_type or not avatar_file.content_type.startswith("image/"):
        return await interaction.response.send_message("⚠️ Attachment Error: Target file structure must evaluate cleanly to standard graphic format types.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    try:
        # Fetch the attachment bytes from the Discord CDN
        avatar_bytes = await avatar_file.read()
        
        # Modify the global application client state profile fields
        await bot.user.edit(username=new_name, avatar=avatar_bytes)
        
        await interaction.followup.send(f"🤖 **Identity Rebrand Matrix Executed:** Main application signature updated cleanly to **{new_name}** across structural platforms.", ephemeral=True)
    except discord.HTTPException as http_err:
        print(f"❌ Application state editing payload error: {http_err}")
        await interaction.followup.send(f"⚠️ **Discord API Pipeline Boundary Exceeded:** Identity updates are rate-limited globally by Discord (typically 2 changes per hour). Please review console records: `{http_err}`", ephemeral=True)
    except Exception as general_err:
        print(f"❌ Unexpected application fault inside identity controller: {general_err}")
        await interaction.followup.send(f"⚠️ **Internal Processing Fault Encountered:** `{general_err}`", ephemeral=True)

@bot.tree.command(name="diagnose", description="🩺 Admin Tool: Runs an interactive system diagnostic stability health check.")
@is_admin_or_delegated()
async def diagnose_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    latency = round(bot.latency * 1000) if bot.latency and not str(bot.latency).isalpha() else 0
    loop = asyncio.get_event_loop()
    
    raw_env_uri = os.environ.get("MONGO_URI", "NOT_FOUND")
    masked_uri = "System Environment Protected" if raw_env_uri != "NOT_FOUND" else "Missing Secure Key Parameters"

    mongo_status = "🟢 Connected"
    try:
        await loop.run_in_executor(None, lambda: db.command("ping"))
        prof_count = await loop.run_in_executor(None, lambda: player_profiles_col.count_documents({"guild_id": guild_id}))
    except Exception:
        mongo_status = "🔴 Connection Failed"
        prof_count = "N/A"

    embed = discord.Embed(title="🛡️ Infrastructure Diagnostics Snapshot Report", color=discord.Color.from_rgb(14, 21, 46))
    embed.add_field(name="📡 Satellite Network Latency", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="🗄️ Database Connection Status", value=f"`{mongo_status}`", inline=True)
    embed.add_field(name="🔒 active URI string Mask", value=f"`{masked_uri}`", inline=False)
    embed.add_field(name="📊 Guild Active Profiles Registry Count", value=f"`{prof_count} Live Entries`", inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="sync", description="🔄 Forces a direct refresh sync tree mapping parameters across Discord structures.")
@app_commands.choices(scope=[
    app_commands.Choice(name="Global (Update Everywhere - Takes time)", value="global"),
    app_commands.Choice(name="This Server Only (Instant Wipe & Update)", value="guild"),
    app_commands.Choice(name="Purge/Clear This Server's Cache", value="clear_guild")
])
@commands.is_owner()
async def sync_slash(interaction: discord.Interaction, scope: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    try:
        if scope.value == "global":
            synced = await bot.tree.sync()
            await interaction.followup.send(f"🎯 **Global Sync Dispatched:** Synced `{len(synced)}` commands across standard endpoints. (Discord may take up to an hour to populate).", ephemeral=True)
            
        elif scope.value == "guild":
            bot.tree.copy_global_to(guild=interaction.guild)
            synced = await bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"⚡ **Instant Server Sync Complete:** Pushed `{len(synced)}` commands directly to this server layout.", ephemeral=True)
            
        elif scope.value == "clear_guild":
            bot.tree.clear_commands(guild=interaction.guild)
            await bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("🧹 **Server Purge Successful:** Completely scrubbed local guild overlays. Try reloading Discord now.", ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"❌ **Sync Exception Encountered:** {e}", ephemeral=True)

if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ CRITICAL BOOT BLOCK: The 'DISCORD_BOT_TOKEN' environment key array registry is empty. Execution killed.")
    else:
        bot.run(token)
