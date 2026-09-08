# ==============================================================================
# SECTION 1: SYSTEM IMPORTS & HOOK INITIALIZATION MANIFEST
# ==============================================================================
import discord
from discord import app_commands
from discord.ext import tasks, commands
import json
import os
import asyncio
import threading
import re
import aiohttp
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==============================================================================
# SECTION 2: WEB SERVICE INFRASTRUCTURE & DISCLOUD UPTIME HEALTH CHECK
# ==============================================================================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot infrastructure is healthy and active!")
        
    def log_message(self, format, *args):
        return  # Suppresses internal connection telemetry logs inside Discloud dashboard

def run_web_server():
    server = HTTPServer(("0.0.0.0", 10000), KeepAliveHandler)
    server.serve_forever()

# Fire keep-alive network port binding immediately in background thread memory space
threading.Thread(target=run_web_server, daemon=True).start()

# ==============================================================================
# SECTION 3: SYSTEM GLOBAL CONSTANTS, REGEX REGISTRY, & FILTER DICTIONARIES
# ==============================================================================
DB_FILE = "asphalt_bot_database.json"
CONFIG_FILE = "asphalt_bot_config.json"
SCRAPER_CACHE_FILE = "asphalt_scraper_cache.json"

# RegEx expression to accurately isolate promo code alphanumeric arrays (6-14 characters)
CODE_PATTERN = re.compile(r'\b[A-Z0-9]{6,14}\b')

# Universal false-positive matches to drop instantly during extraction parsing loops
BLACKLISTED_WORDS = {"REDEEM", "TOKENS", "CREDITS", "ASPHALT", "UNITE", "REDDIT", "PLAYER", "NINTENDO", "XBOX", "PLAYSTATION"}

# ==============================================================================
# SECTION 4: HARD STORAGE IO MANAGEMENT & SECURE PARSING PROTOCOLS
# ==============================================================================
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def load_scraper_cache():
    if os.path.exists(SCRAPER_CACHE_FILE):
        try:
            with open(SCRAPER_CACHE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_scraper_cache(cache_set):
    with open(SCRAPER_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(cache_set), f, indent=4)

# ==============================================================================
# SECTION 5: SYSTEM APPLICATION BOT CLIENT CONTEXT & INTERACTION SYNC ENGINE
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Production node verified online: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        
    # Launch background automated network platform scrapers safely
    if not auto_code_scraper_loop.is_running():
        auto_code_scraper_loop.start()
        print("📡 Background Automated Code Scraper Task Cycle engaged!")

# ==============================================================================
# SECTION 6: INTERACTIVE UI DRIVEN INTERFACE ENGINE (HELP SELECT DROP-DOWNS)
# ==============================================================================
class HelpDropdown(discord.ui.Select):
    def __init__(self, show_admin_docs: bool):
        options = [
            discord.SelectOption(label="📖 Bot Overview", description="What does this bot do?", emoji="🤖"),
            discord.SelectOption(label="🎮 Player Commands", description="Commands for everyday users", emoji="🕹️"),
        ]
        if show_admin_docs:
            options.append(discord.SelectOption(label="🛡️ Admin Utilities", description="Setup and configuration tools", emoji="⚙️"))
            
        super().__init__(placeholder="Select a module category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        dark_blue = discord.Color.from_rgb(20, 24, 40)
        dark_green = discord.Color.from_rgb(24, 40, 20)
        dark_red = discord.Color.from_rgb(45, 15, 15)

        selected_value = self.values[0]
        embed = discord.Embed(title="Error", description="Unknown option selected.")

        if selected_value == "📖 Bot Overview":
            embed = discord.Embed(
                title="🤖 Asphalt Legends Fast Redeem Manual",
                description="Welcome! This system manages **Asphalt Legends Unite Redeem Codes** inside your server community!",
                color=dark_blue
            )
            embed.set_image(url="https://i.imgur.com/wVf7YwV.jpg")
            embed.add_field(name="✨ Key Framework", value="• Register your player ID to receive automatic rewards roles.\n• Instantly maps pre-filled 1-click URL parameters to your DMs when drops occur!\n• Monitors community networks automatically to discover new codes 24/7.", inline=False)
            
        elif selected_value == "🎮 Player Commands":
            embed = discord.Embed(title="🕹️ Player Commands Matrix", color=dark_green)
            embed.add_field(name="`/set_id`", value="**Usage:** `/set_id player_id: <YOUR_ID>`\nRegisters your unique Asphalt game ID and assigns server drop alert roles.", inline=False)
            embed.add_field(name="`/toggle_dm`", value="Toggles direct message redeem link alerts ON or OFF.", inline=False)
            embed.add_field(name="`/delete_id`", value="Removes your data footprint completely and drops associated alert roles.", inline=False)
            embed.add_field(name="`/history`", value="Brings up an emergency backlog archive of the last 5 codes scraped.", inline=False)
            embed.add_field(name="`/help`", value="Spawns this exact interactive selection panel UI.", inline=False)
            
        elif selected_value == "🛡️ Admin Utilities":
            embed = discord.Embed(title="⚙️ Administrator Utilities Manual", color=dark_red)
            embed.add_field(name="`/setup`", value="**Usage:** `/setup announcement_channel: #ch admin_role: @role player_role: @role`\nConfigures public notification channels, delegated management authorization groups, and target notification ping tags.", inline=False)
            embed.add_field(name="`/redeem`", value="**Usage:** `/redeem code: <code>`\nBlasts interactive 1-click links out to user DMs and logs to the configurations layout channel manually.", inline=False)
            embed.add_field(name="`/listplayers`", value="Renders an overview metrics grid matrix of active server registrations.", inline=False)
            embed.add_field(name="`/diagnose`", value="Runs a comprehensive core connection real-time stability diagnostic check.", inline=False)
            embed.add_field(name="`/test_code`", value="Fires an isolated test payload embed to validation configurations.", inline=False)
            embed.add_field(name="`/clearhistory`", value="Wipes out database information fields strictly isolated to this guild.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, show_admin_docs: bool):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(show_admin_docs))

# ==============================================================================
# SECTION 7: AUTOMATED BACKGROUND MULTI-SITE CODE ACQUISITION CRAWLER
# ==============================================================================
@tasks.loop(minutes=15)
async def auto_code_scraper_loop():
    """Monitors multiple web platforms asynchronously for new Asphalt promo drops."""
    await bot.wait_until_ready()
    sent_cache = load_scraper_cache()
    headers = {"User-Agent": "DiscloudPlatinumAsphaltBot/4.0 (by /u/ProductionDeveloper)"}
    
    async with aiohttp.ClientSession() as session:
        # PLATFORM TARGET 1: THE REDDIT COMMUNITY MIRROR CHANNELS
        try:
            reddit_url = "https://www.reddit.com/r/Asphalt9/new.json?limit=12"
            async with session.get(reddit_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = data.get("data", {}).get("children", [])
                    for post in posts:
                        post_data = post.get("data", {})
                        search_blob = f"{post_data.get('title', '')} {post_data.get('selftext', '')}".upper()
                        await process_text_and_blast(search_blob, sent_cache)
        except Exception as e:
            print(f"⚠️ Reddit scraper interface delay context: {e}")

        # PLATFORM TARGET 2: OFFICIAL GAMELOFT UNITE SITE INDEX FEED
        try:
            gameloft_url = "https://asphaltlegends.com/api/news?limit=5"
            async with session.get(gameloft_url, headers=headers) as response:
                if response.status == 200:
                    news_data = await response.json()
                    for article in news_data.get("articles", []):
                        search_blob = f"{article.get('title', '')} {article.get('description', '')}".upper()
                        await process_text_and_blast(search_blob, sent_cache)
        except Exception:
            pass

async def process_text_and_blast(search_blob: str, sent_cache: set):
    keywords = ["REDEEM CODE", "NEW CODE", "PROMO CODE", "FREE TOKENS", "REWARD CODE", "WORKING CODE", "UNITE CODE"]
    if any(kw in search_blob for kw in keywords):
        found_codes = CODE_PATTERN.findall(search_blob)
        for code in found_codes:
            if code in BLACKLISTED_WORDS:
                continue
            if code not in sent_cache:
                print(f"📡 Multi-Site Scraper Detected Fresh Code Matrix: {code}")
                sent_cache.add(code)
                save_scraper_cache(sent_cache)
                await execute_global_automation_blast(code)

# ==============================================================================
# SECTION 8: GLOBAL SERVER PAYLOAD ROUTING & PLAYER PASSENGER DM DELIVERY
# ==============================================================================
async def execute_global_automation_blast(code: str):
    config = load_config()
    data = load_data()
    
    public_color = discord.Color.from_rgb(230, 160, 15)
    dm_color = discord.Color.from_rgb(40, 180, 70)
    
    for guild_id_str, guild_cfg in config.items():
        guild = bot.get_guild(int(guild_id_str))
        if not guild:
            continue
            
        target_channel_id = guild_cfg.get("notification_channel")
        player_role_id = guild_cfg.get("alert_role_id")
        
        if not target_channel_id:
            continue
        target_channel = bot.get_channel(target_channel_id)
        if not target_channel:
            continue
            
        ping_string = f"<@&{player_role_id}>" if player_role_id else "@everyone"
        
        public_embed = discord.Embed(
            title="🏎️ Automated Asphalt Legends Redeem Code! 🏎️",
            description=f"🚨 **A new global redemption drop has been auto-detected!** 🚨\n\n**Redeem Code:** `{code.upper()}`",
            color=public_color
        )
        public_embed.set_image(url="https://i.imgur.com/wVf7YwV.jpg")
        public_embed.add_field(name="__Claim Framework__", value="Registered profiles: Check your direct messages for your custom pre-filled 1-click links!\n\nManual users claim here: [Gameloft Portal](https://www.gameloft.com/redeem/asphalt-legends-unite)", inline=False)
        
        try:
            await target_channel.send(content=ping_string, embed=public_embed)
        except Exception:
            continue
            
        server_data = data.get(guild_id_str, {})
        for u_id, info in server_data.items():
            if not info.get("dm_enabled", True):
                continue
                
            member = guild.get_member(int(u_id))
            if member:
                prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends-unite?playerId={info['player_id']}&code={code.upper()}"
                dm_embed = discord.Embed(
                    title="🏁 Auto-Filled Reward Pipeline 🏁",
                    description=f"**Code:** `{code.upper()}`\n\nClick below to access the claim portal with your player credentials pre-mapped!",
                    color=dm_color
                )
                dm_embed.add_field(name="__Dynamic Reward Portal__", value=f"[Click Here to Instantly Claim]({prefilled_url})")
                try:
                    await member.send(embed=dm_embed)
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

# ==============================================================================
# SECTION 9: ACCESS SECURITY COMPLIANCE MIDDLEWARE & PERMISSION ERROR WRAPPERS
# ==============================================================================
def is_admin_or_delegated():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        if interaction.user.guild_permissions.administrator:
            return True
        
        config = load_config()
        guild_id = str(interaction.guild.id)
        delegated_role_id = config.get(guild_id, {}).get("bot_admin_role_id")
        
        if delegated_role_id:
            if discord.utils.get(interaction.user.roles, id=int(delegated_role_id)):
                return True
                
        raise app_commands.errors.MissingPermissions(["administrator (or delegated bot admin role)"])
    return app_commands.check(predicate)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("🚫 **Access Denied:** Administrative clearances or delegated group assignments missing.", ephemeral=True)
        else:
            await interaction.followup.send("🚫 **Access Denied:** Administrative authorization checks failed.", ephemeral=True)

# ==============================================================================
# SECTION 10: USER OPERATIONS & ADMIN CONTROL WORKBENCH (SLASH SYSTEM REGISTER)
# ==============================================================================
@bot.tree.command(name="help", description="Tells the admins or players about what this bot does & how to use it.")
async def help_slash(interaction: discord.Interaction):
    config = load_config()
    is_authorized = False
    
    if interaction.user.guild_permissions.administrator:
        is_authorized = True
    else:
        delegated_id = config.get(str(interaction.guild_id), {}).get("bot_admin_role_id")
        if delegated_id and discord.utils.get(interaction.user.roles, id=int(delegated_id)):
            is_authorized = True

    embed = discord.Embed(
        title="🗂️ Help & System Documentation Center",
        description="Please select a documentation segment from the drop-down menu panel below to learn how to operate this engine module.",
        color=discord.Color.from_rgb(20, 24, 40)
    )
    await interaction.response.send_message(embed=embed, view=HelpView(is_authorized), ephemeral=True)

@bot.tree.command(name="set_id", description="Registers your unique Asphalt Game ID and applies saved server roles.")
@app_commands.describe(player_id="Your authentic Asphalt game identity code (e.g., u-4a5b6c)")
async def set_id_slash(interaction: discord.Interaction, player_id: str):
    player_id = player_id.strip().lower()
    
    if not player_id.startswith("u-"):
        return await interaction.response.send_message("⚠️ **Format Exception:** Asphalt Game IDs must start with a clean `u-` syntax configuration (e.g. `u-4a5b6c`). Check your profile tab inside the app.", ephemeral=True)

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    data = load_data()
    config = load_config()
    
    if guild_id not in data:
        data[guild_id] = {}
        
    current_dm_pref = data[guild_id].get(user_id, {}).get("dm_enabled", True)
    data[guild_id][user_id] = {"username": interaction.user.name, "player_id": player_id, "dm_enabled": current_dm_pref}
    save_data(data)
    
    saved_role_id = config.get(guild_id, {}).get("alert_role_id")
    role_msg = ""
    
    if saved_role_id:
        role = interaction.guild.get_role(int(saved_role_id))
        if role:
            try:
                await interaction.user.add_roles(role)
                role_msg = f" and assigned target tier role: {role.mention}"
            except discord.Forbidden:
                role_msg = " *(⚠️ Notice: System role configuration could not be bound due to permission hierarchy setting configurations)*"
                
    await interaction.response.send_message(f"✅ Linked Asphalt ID: **{player_id}** to {interaction.user.mention}{role_msg}\n🔔 DM Alerts: {'**ON**' if current_dm_pref else '**OFF**'}")

@bot.tree.command(name="delete_id", description="Removes your game registration metadata profile completely.")
async def delete_id_slash(interaction: discord.Interaction):
    data = load_data()
    config = load_config()
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    if guild_id in data and user_id in data[guild_id]:
        del data[guild_id][user_id]
        if not data[guild_id]:
            del data[guild_id]
        save_data(data)
        
        saved_role_id = config.get(guild_id, {}).get("alert_role_id")
        role_message = "."
        
        if saved_role_id:
            role = interaction.guild.get_role(int(saved_role_id))
            if role and role in interaction.user.roles:
                try:
                    await interaction.user.remove_roles(role)
                    role_message = f" and cleared your server role group **{role.name}**."
                except Exception:
                    pass
                        
        await interaction.response.send_message(f"❌ {interaction.user.mention}, your player database profiling asset was dropped{role_message}")
    else:
        await interaction.response.send_message("⚠️ No player entry footprint located matching your account signature.", ephemeral=True)

@bot.tree.command(name="toggle_dm", description="Toggle direct message notifications for code alerts.")
async def toggle_dm_slash(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    if guild_id not in data or user_id not in data[guild_id]:
        return await interaction.response.send_message("⚠️ Please register your identity via `/set_id` prior to executing config configurations.", ephemeral=True)
    
    current_setting = data[guild_id][user_id].get("dm_enabled", True)
    data[guild_id][user_id]["dm_enabled"] = not current_setting
    save_data(data)
    
    status = "ON" if data[guild_id][user_id]["dm_enabled"] else "OFF"
    await interaction.response.send_message(f"🔔 DM alerts changed to **{status}** for {interaction.user.mention}.")

@bot.tree.command(name="history", description="Displays the last 5 active or recent auto-scraped redemption codes.")
async def history_slash(interaction: discord.Interaction):
    sent_cache = load_scraper_cache()
    if not sent_cache:
        return await interaction.response.send_message("🗂️ **No recent code drops found in the local tracking cache.**", ephemeral=True)
        
    recent_codes = list(sent_cache)[-5:]
    recent_codes.reverse()
    
    embed = discord.Embed(title="🏁 Recent Redemption Drop History", description="Missed an automated alert stream? Here are the most recent promo parameters discovered by the tracking core:", color=discord.Color.from_rgb(30, 90, 160))
    embed.set_thumbnail(url="https://i.imgur.com/vHInC4G.png")
    
    for idx, code in enumerate(recent_codes, 1):
        manual_url = f"https://www.asphaltlegendsunite.com/redeem?code={code}"
        embed.add_field(name=f"{idx}. Code: `{code}`", value=f"🔗 [Manual Claim Portal Shortcut]({manual_url})", inline=False)
        
    embed.set_footer(text="Tip: For personalized 1-click auto-filled delivery links, run /set_id!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup", description="Configure the channel and specific target roles for administration and drops.")
@app_commands.describe(announcement_channel="The destination text channel for public code announcements.", admin_role="Exactly one management group role given permission to execute admin commands.", player_role="Exactly one role that will be pinged and assigned to players on registration.")
@is_admin_or_delegated()
async def setup_slash(interaction: discord.Interaction, announcement_channel: discord.TextChannel, admin_role: discord.Role, player_role: discord.Role):
    guild_id = str(interaction.guild_id)
    config = load_config()
    
    if guild_id not in config:
        config[guild_id] = {}
        
    config[guild_id]["notification_channel"] = announcement_channel.id
    config[guild_id]["bot_admin_role_id"] = admin_role.id
    config[guild_id]["alert_role_id"] = player_role.id
    save_config(config)
    
    embed = discord.Embed(title="⚙️ Configuration Setup Matrix Saved!", color=discord.Color.from_rgb(200, 140, 10))
    embed.add_field(name="📢 Announcements Channel", value=announcement_channel.mention, inline=True)
    embed.add_field(name="🛡️ Master Admin Authority Role", value=admin_role.mention, inline=True)
    embed.add_field(name="🔔 Player Alert Role Mention", value=player_role.mention, inline=False)
    await interaction.response.send_message(embed=embed)
    
    mock_code = "UNITE2026"
    test_embed = discord.Embed(title="🏎️ Verification Stream: System Setup Live! 🏎️", description=f"🤖 This is an automated setup confirmation trace verification.\n\n**Active Validation Frame Code:** `{mock_code}`", color=discord.Color.from_rgb(50, 120, 220))
    try:
        await announcement_channel.send(content=f"{player_role.mention} System Pipeline Connected Successfully.", embed=test_embed)
    except discord.Forbidden:
        await interaction.followup.send("⚠️ **Configuration saved**, but the bot lacks structural text permissions to type inside that announcement channel!")

@bot.tree.command(name="diagnose", description="🛡️ Admin Tool: Runs an interactive real-time system stability and diagnostic health check.")
@is_admin_or_delegated()
async def diagnose_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    config = load_config()
    guild_id = str(interaction.guild_id)
    guild_cfg = config.get(guild_id, {})
    
    latency = round(bot.latency * 1000)
    ping_status = "🟢 Excellent" if latency < 150 else "🟡 Slow" if latency < 300 else "🔴 High Delay"
    scraper_status = "🟢 Active & Scanning" if auto_code_scraper_loop.is_running() else "🔴 Stopped"
    
    target_channel_id = guild_cfg.get("notification_channel")
    channel_status, perm_status = "🔴 Unconfigured", "🔴 N/A"
    
    if target_channel_id:
        channel = bot.get_channel(target_channel_id)
        if channel:
            channel_status = f"🟢 Linked ({channel.mention})"
            perms = channel.permissions_for(interaction.guild.me)
            perm_status = "🟢 Verified Full Perms" if perms.send_messages and perms.embed_links else "⚠️ Missing Send/Embed Permissions"
        else:
            channel_status = "🔴 Configured but Channel Hidden/Wiped"
            
    try:
        data = load_data()
        server_players = len(data.get(guild_id, {}))
        db_status = f"🟢 Healthy ({server_players} Profiles Vaulted)"
    except Exception as e:
        db_status = f"🔴 Storage IO Exception: {str(e)}"

    embed = discord.Embed(title="🛡️ System Diagnostics & Health Status Dashboard", color=discord.Color.from_rgb(30, 140, 200))
    embed.add_field(name="🛰️ Discord Gateway Latency", value=f"📡 Ping: `{latency}ms` | {ping_status}", inline=False)
    embed.add_field(name="📡 Automated Scraper Task Engine", value=scraper_status, inline=False)
    embed.add_field(name="📢 Announcement Channel Route", value=channel_status, inline=True)
    embed.add_field(name="🔐 Bot Permissions Check", value=perm_status, inline=True)
    embed.add_field(name="🗄️ Database Integrity Audit", value=db_status, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="listplayers", description="Displays a detailed manifest profile metrics matrix of registered members.")
@is_admin_or_delegated()
async def listplayers_slash(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)
    server_data = data.get(guild_id, {})
    
    if not server_data:
        return await interaction.response.send_message("🧹 **Server registration profile index database is currently blank.**", ephemeral=True)
    
    total_users = len(server_data)
    dm_enabled_count = sum(1 for info in server_data.values() if info.get("dm_enabled", True))
    dm_percent = round((dm_enabled_count / total_users) * 100) if total_users > 0 else 0
    
    embed = discord.Embed(title=f"📋 Registered Profiles Metrics: {interaction.guild.name}", color=discord.Color.from_rgb(30, 90, 160))
    embed.add_field(name="📊 Metrics Summary", value=f"👥 Total Enrollment: `{total_users} Players` | 🔔 Alert Coverage: `{dm_percent}% DMs Active`", inline=False)
    
    for disc_id, info in list(server_data.items())[:20]:
        pref = "✅ Active" if info.get("dm_enabled", True) else "❌ Blocked"
        embed.add_field(name=f"User: {info['username']}", value=f"🆔 Game ID: `{info['player_id']}` | 📥 DM alerts: {pref}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="redeem", description="Broadcasts a redeem code drop publicly and updates verified target players via DM.")
@app_commands.describe(code="The code string to broadcast and distribute (e.g., SPEED2026)")
@is_admin_or_delegated()
async def redeem_slash(interaction: discord.Interaction, code: str):
    config = load_config()
    guild_id = str(interaction.guild_id)
    target_channel_id = config.get(guild_id, {}).get("notification_channel")
    player_role_id = config.get(guild_id, {}).get("alert_role_id")
    
    if not target_channel_id:
        return await interaction.response.send_message("⚠️ Announcement pipes are unconfigured. Please run `/setup` first to link structural nodes.", ephemeral=True)
    
    target_channel = bot.get_channel(target_channel_id)
    if not target_channel:
        return await interaction.response.send_message("⚠️ Targeted logging infrastructure channel could not be resolved.", ephemeral=True)
    
    ping_string = f"<@&{player_role_id}>" if player_role_id else "@everyone"
    data = load_data()
    server_data = data.get(guild_id, {})
    
    public_embed = discord.Embed(title="🏎️ New Asphalt Legends Redeem Code! 🏎️", description=f"🚨 **A new global redemption drop has broken!** 🚨\n\n**Redeem Code:** `{code.upper()}`", color=discord.Color.from_rgb(230, 160, 15))
    public_embed.set_image(url="https://i.imgur.com/wVf7YwV.jpg")
    public_embed.add_field(name="__Claim Framework__", value="Registered profiles: Stand by for custom pre-filled 1-click links arriving inside your direct message systems!\n\nManual users claim here: [Gameloft Portal](https://www.gameloft.com/redeem/asphalt-legends-unite)", inline=False)
    
    await interaction.response.defer(ephemeral=True)
    await target_channel.send(content=ping_string, embed=public_embed)
    
    success, opted_out, failed = 0, 0, 0
    for u_id, info in server_data.items():
        if not info.get("dm_enabled", True):
            opted_out += 1
            continue
            
        member = interaction.guild.get_member(int(u_id))
        if member:
            prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends-unite?playerId={info['player_id']}&code={code.upper()}"
            dm_embed = discord.Embed(title="🏁 Auto-Filled Reward Pipeline 🏁", description=f"**Code:** `{code.upper()}`\n\nClick the element below to access the claim portal with your player credentials pre-mapped!", color=discord.Color.from_rgb(40, 180, 70))
            dm_embed.add_field(name="__Dynamic Reward Portal__", value=f"[Click Here to Instantly Claim]({prefilled_url})")
            try:
                await member.send(embed=dm_embed)
                success += 1
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                failed += 1
        else:
            failed += 1
    await interaction.followup.send(f"✅ Drop processed to {target_channel.mention}! Logs: Delivered: {success} | Skipped: {opted_out} | Failed: {failed}")

@bot.tree.command(name="test_code", description="Fires an isolated format structural verification frame directly to your DMs.")
@is_admin_or_delegated()
async def test_code_slash(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    if guild_id not in data or user_id not in data[guild_id]:
        return await interaction.response.send_message("⚠️ Link your game profile through `/set_id` inside this server environment first before running telemetry metrics.", ephemeral=True)
    
    info = data[guild_id][user_id]
    prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends-unite?playerId={info['player_id']}&code=TEST12345"
    
    embed = discord.Embed(title="🧪 Isolated Delivery Telemetry Test", description="Testing dynamic string injection interfaces.\n\n**Code:** `TEST12345`", color=discord.Color.from_rgb(220, 100, 20))
    embed.add_field(name="__Pre-filled Claim URL__", value=f"[Open Gameloft Web Portal]({prefilled_url})")
    try:
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("📥 **Success!** Verification package dispatched to user DMs.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ **Error:** Cannot map connection routes to DM logs. Verify user privacy profiles.", ephemeral=True)

@bot.tree.command(name="clearhistory", description="Wipes out the entire registration database for this guild.")
@is_admin_or_delegated()
async def clearhistory_slash(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)
    
    if guild_id in data:
        del data[guild_id]
        save_data(data)
    await interaction.response.send_message("🧹 **Database Server Registry Cleared Successfully!**")

# FETCH EXECUTION LOGIC TARGET NODE ENVIRONMENT VARIABLE
token = os.environ.get("DISCORD_BOT_TOKEN", "")
if not token and os.path.exists("token.txt"):
    with open("token.txt", "r", encoding="utf-8") as tf:
        token = tf.read().strip()

if not token or token == "YOUR_TOKEN_HERE":
    print("❌ ERROR: Missing target validation credentials token configurations inside system paths.")
else:
    bot.run(token)
