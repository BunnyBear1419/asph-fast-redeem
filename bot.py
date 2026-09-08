# ==============================================================================
# SECTION 1: SYSTEM APPLICATION IMPORTS & REQUIREMENT MANIFESTS
# ==============================================================================
import discord
from discord import app_commands
from discord.ext import tasks, commands
import os
import asyncio
import threading
import re
import aiohttp
from http.server import BaseHTTPRequestHandler, HTTPServer
from supabase import create_client, Client
# ==============================================================================
# SECTION 2: WEB INFRASTRUCTURE & UPTIME KEEP-ALIVE SERVER NODE
# ==============================================================================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot cluster infrastructure is running completely healthy!")
        
    def log_message(self, format, *args):
        return  # Suppresses internal endpoint traffic logging loops inside Discloud console terminals

def run_web_server():
    server = HTTPServer(("0.0.0.0", 10000), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# ==============================================================================
# SECTION 3: SYSTEM GLOBAL CONSTANTS, PROMO REGEX, & EXCLUSIONS
# ==============================================================================
# Regex extraction expression isolating alphanumeric promo code shapes (6-14 characters)
CODE_PATTERN = re.compile(r'\b[A-Z0-9]{6,14}\b')

# Structural blacklists discarding false-positive strings matching our regex pattern shapes
BLACKLISTED_WORDS = {"REDEEM", "TOKENS", "CREDITS", "ASPHALT", "UNITE", "REDDIT", "PLAYER", "NINTENDO", "XBOX", "PLAYSTATION"}

# Master Visual Assets Fallbacks
DEFAULT_BANNER = "https://imgur.com"
DEFAULT_THUMBNAIL = "https://imgur.com"
# ==============================================================================
# SECTION 4: DATABASE CONNECTION MANAGEMENT & SUPABASE IO ROUTINES
# ==============================================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Initializing global client hooks binding securely to your Supabase tables database
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# ==============================================================================
# SECTION 5: ENGINE WORKSPACE CONFIGURATION & GATEWAY CLIENT ON_READY
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Production Supabase node initialized safely: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands globally across active server links.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        
    # Ignite background automated tracking crawlers loops
    if not auto_code_scraper_loop.is_running():
        auto_code_scraper_loop.start()
        print("📡 Background Automated Multi-Source Scraper Engine task engaged!")
# ==============================================================================
# SECTION 6: INTERACTIVE UI INTERFACE SYSTEMS & EMBED SELECTION DROPDOWNS
# ==============================================================================
class HelpDropdown(discord.ui.Select):
    def __init__(self, show_admin_docs: bool):
        options = [
            discord.SelectOption(label="📖 Bot Overview", value="overview", description="What does this bot do?", emoji="🤖"),
            discord.SelectOption(label="🎮 Player Commands", value="player", description="Commands for everyday users", emoji="🕹️"),
        ]
        if show_admin_docs:
            options.append(discord.SelectOption(label="🛡️ Admin Utilities", value="admin", description="Setup and configuration tools", emoji="⚙️"))
            
        super().__init__(placeholder="Select a module category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        
        loop = asyncio.get_event_loop()
        cfg_res = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("banner_url, thumbnail_url").eq("guild_id", guild_id).execute())
        
        banner = DEFAULT_BANNER
        thumb = DEFAULT_THUMBNAIL
        if cfg_res.data and len(cfg_res.data) > 0:
            banner = cfg_res.data[0].get("banner_url", DEFAULT_BANNER)
            thumb = cfg_res.data[0].get("thumbnail_url", DEFAULT_THUMBNAIL)

        selected_value = self.values[0] if self.values else ""
        embed = discord.Embed(title="Error", description="Unknown option configuration tracking parameters parsed.")
        # Continuing HelpDropdown class callback matrix routing logic loops
        if selected_value == "overview":
            embed = discord.Embed(
                title="🤖 Asphalt Legends Fast Redeem Manual",
                description="Welcome! This system manages **Asphalt Legends Unite Redeem Codes** inside your server community completely on autopilot!",
                color=discord.Color.from_rgb(20, 24, 40)
            )
            embed.set_image(url=banner)
            embed.add_field(name="✨ Key Framework", value="• Register your player ID to receive automatic rewards roles.\n• Instantly maps pre-filled 1-click URL parameters to your DMs when drops occur!\n• Connected directly to cloud databases ensuring multi-server data safety.", inline=False)
            
        elif selected_value == "player":
            embed = discord.Embed(title="🕹️ Player Commands Matrix", color=discord.Color.from_rgb(24, 40, 20))
            embed.set_thumbnail(url=thumb)
            embed.add_field(name="`/set_id`", value="**Usage:** `/set_id player_id: <YOUR_ID>`\nRegisters your unique Asphalt game ID and assigns server drop alert roles.", inline=False)
            embed.add_field(name="`/toggle_dm`", value="Toggles direct message redeem link alerts ON or OFF.", inline=False)
            embed.add_field(name="`/delete_id`", value="Removes your data footprint completely and drops associated alert roles.", inline=False)
            embed.add_field(name="`/history`", value="Brings up an emergency backlog archive of the last 5 codes scraped.", inline=False)
            embed.add_field(name="`/help`", value="Spawns this exact interactive selection panel UI.", inline=False)
            
        elif selected_value == "admin":
            embed = discord.Embed(title="⚙️ Administrator Utilities Manual", color=discord.Color.from_rgb(45, 15, 15))
            embed.set_thumbnail(url=thumb)
            embed.add_field(name="`/setup`", value="**Usage:** `/setup announcement_channel: #ch admin_role: @role player_role: @role`\nConfigures public notification channels, delegated management authorization groups, and target notification ping tags.", inline=False)
            embed.add_field(name="`/redeem`", value="**Usage:** `/redeem code: <code>`\nBlasts interactive 1-click links out to user DMs and logs to the configurations layout channel manually.", inline=False)
            embed.add_field(name="`/listplayers`", value="Renders an overview metrics grid matrix of active server registrations.", inline=False)
            embed.add_field(name="`/diagnose`", value="Runs a comprehensive core connection real-time stability diagnostic check.", inline=False)
            embed.add_field(name="`/admin_restore`", value="🛡️ Restores your server's player database registrations instantly from the daily cloud backups archive table.", inline=False)
            embed.add_field(name="Visual Branding Tools", value="`/admin_set_name` | `/admin_set_avatar` | `/admin_set_media` | `/admin_reset_defaults`", inline=False)
            embed.add_field(name="`/clearhistory`", value="Wipes out database information fields strictly isolated to this guild.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, show_admin_docs: bool):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(show_admin_docs))
# ==============================================================================
# SECTION 7: AUTOMATED DUAL-PLATFORM BACKGROUND LOOP SCRAPER TASK
# ==============================================================================
@tasks.loop(minutes=15)
async def auto_code_scraper_loop():
    """Monitors multiple web platforms asynchronously for new Asphalt promo drops."""
    await bot.wait_until_ready()
    headers = {"User-Agent": "DiscloudPlatinumAsphaltBot/5.0 (by /u/ProductionDeveloper)"}
    
    async with aiohttp.ClientSession() as session:
        # CRAWLER PIPELINE SOURCE 1: REDDIT COMMUNITY DATA MIRRORS FEED
        try:
            reddit_url = "https://reddit.com"
            async with session.get(reddit_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = data.get("data", {}).get("children", [])
                    for post in posts:
                        post_data = post.get("data", {})
                        search_blob = f"{post_data.get('title', '')} {post_data.get('selftext', '')}".upper()
                        await process_text_and_blast(search_blob)
        except Exception as e:
            print(f"⚠️ Reddit scraper execution check anomaly: {e}")

        # CRAWLER PIPELINE SOURCE 2: OFFICIAL GAMELOFT CORE WEBSITE NEWS AGENT
        try:
            gameloft_url = "https://asphaltlegends.com"
            async with session.get(gameloft_url, headers=headers) as response:
                if response.status == 200:
                    news_data = await response.json()
                    for article in news_data.get("articles", []):
                        search_blob = f"{article.get('title', '')} {article.get('description', '')}".upper()
                        await process_text_and_blast(search_blob)
        except Exception:
            pass 

async def process_text_and_blast(search_blob: str):
    keywords = ["REDEEM CODE", "NEW CODE", "PROMO CODE", "FREE TOKENS", "REWARD CODE", "WORKING CODE", "UNITE CODE"]
    if any(kw in search_blob for kw in keywords):
        found_codes = CODE_PATTERN.findall(search_blob)
        for code in found_codes:
            code = code.upper()
            if code in BLACKLISTED_WORDS:
                continue
                
            loop = asyncio.get_event_loop()
            cache_check = await loop.run_in_executor(None, lambda: supabase.table("scraper_cache").select("code").eq("code", code).execute())
            if not cache_check.data:
                await loop.run_in_executor(None, lambda: supabase.table("scraper_cache").insert({"code": code}).execute())
                print(f"📡 Multi-Site Scraper Detected Fresh Code Matrix: {code}")
                await execute_global_automation_blast(code)
# ==============================================================================
# SECTION 8: GLOBAL AUTOMATION CODES BLASTING & DISTRIBUTION ENGINE
# ==============================================================================
async def execute_global_automation_blast(code: str):
    loop = asyncio.get_event_loop()
    configs_res = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("*").execute())
    profiles_res = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("*").eq("dm_enabled", True).execute())
    
    if not configs_res.data:
        return

    players_by_guild = {}
    for p in profiles_res.data:
        g_id = p["guild_id"]
        if g_id not in players_by_guild:
            players_by_guild[g_id] = []
        players_by_guild[g_id].append(p)

    for guild_cfg in configs_res.data:
        guild_id_str = guild_cfg["guild_id"]
        guild = bot.get_guild(int(guild_id_str))
        if not guild:
            continue
            
        target_channel = bot.get_channel(guild_cfg["notification_channel"])
        if not target_channel:
            continue
            
        player_role_id = guild_cfg["alert_role_id"]
        ping_string = f"<@&{player_role_id}>" if player_role_id else "@everyone"
        
        public_embed = discord.Embed(
            title="🏎️ Automated Asphalt Legends Redeem Code! 🏎️",
            description=f"🚨 **A new global redemption drop has been auto-detected!** 🚨\n\n**Redeem Code:** `{code.upper()}`",
            color=discord.Color.from_rgb(230, 160, 15)
        )
        public_embed.set_image(url=guild_cfg.get("banner_url", DEFAULT_BANNER))
        public_embed.add_field(name="__Claim Framework__", value="Registered profiles: Check your direct messages for your custom pre-filled 1-click links!\n\nManual users claim here: [Gameloft Portal](https://gameloft.com)", inline=False)
        
        try:
            await target_channel.send(content=ping_string, embed=public_embed)
        except Exception:
            pass
            
        # Distribute customized direct messages to all server users
        guild_players = players_by_guild.get(guild_id_str, [])
        for p_info in guild_players:
            member = guild.get_member(int(p_info["user_id"]))
            if member:
                prefilled_url = f"https://gameloft.com?playerId={p_info['player_id']}&code={code.upper()}"
                dm_embed = discord.Embed(
                    title="🏁 Auto-Filled Reward Pipeline 🏁",
                    description=f"**Code:** `{code.upper()}`\n\nClick below to access the claim portal with your player credentials pre-mapped!",
                    color=discord.Color.from_rgb(40, 180, 70)
                )
                dm_embed.add_field(name="__Dynamic Reward Portal__", value=f"[Click Here to Instantly Claim]({prefilled_url})")
                try:
                    await member.send(embed=dm_embed)
                    # RATE LIMIT PROTECTION: Critical suggestion throttle mapping safety
                    await asyncio.sleep(0.4) 
                except Exception:
                    pass
# ==============================================================================
# SECTION 9: BASE SECURITY CLEARANCE MIDDLEWARE COMPLIANCE & CHECK INTERCEPTS
# ==============================================================================
def is_admin_or_delegated():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        if interaction.user.guild_permissions.administrator:
            return True
        
        guild_id = str(interaction.guild.id)
        loop = asyncio.get_event_loop()
        cfg_check = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("bot_admin_role_id").eq("guild_id", guild_id).execute())
        
        if cfg_check.data and len(cfg_check.data) > 0:
            delegated_role_id = cfg_check.data[0].get("bot_admin_role_id")
            if delegated_role_id and discord.utils.get(interaction.user.roles, id=int(delegated_role_id)):
                return True
                
        raise app_commands.errors.MissingPermissions(["administrator (or delegated bot admin role)"])
    return app_commands.check(predicate)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("🚫 **Access Denied:** administrative clearances or delegated group assignments missing.", ephemeral=True)
        else:
            await interaction.followup.send("🚫 **Access Denied:** Administrative authorization validation checks failed.", ephemeral=True)
# ==============================================================================
# SECTION 10: END-USER UTILITIES & MASTER WORKBENCH (SLASH COMMANDS)
# ==============================================================================

# --- PLAYER UTILITIES ---
@bot.tree.command(name="help", description="Tells the admins or players about what this bot does & how to use it.")
async def help_slash(interaction: discord.Interaction):
    is_authorized = False
    if interaction.user.guild_permissions.administrator:
        is_authorized = True
    else:
        loop = asyncio.get_event_loop()
        cfg_check = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("bot_admin_role_id").eq("guild_id", str(interaction.guild_id)).execute())
        if cfg_check.data and len(cfg_check.data) > 0 and discord.utils.get(interaction.user.roles, id=int(cfg_check.data[0]["bot_admin_role_id"])):
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
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("dm_enabled").eq("guild_id", guild_id).eq("user_id", user_id).execute())
    current_dm_pref = prof_check.data[0]["dm_enabled"] if prof_check.data and len(prof_check.data) > 0 else True
    
    await loop.run_in_executor(None, lambda: supabase.table("player_profiles").upsert({
        "guild_id": guild_id, "user_id": user_id, "username": interaction.user.name, "player_id": player_id, "dm_enabled": current_dm_pref
    }).execute())
    
    cfg_check = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("alert_role_id").eq("guild_id", guild_id).execute())
    role_msg = ""
    if cfg_check.data and len(cfg_check.data) > 0 and cfg_check.data[0]["alert_role_id"]:
        role = interaction.guild.get_role(int(cfg_check.data[0]["alert_role_id"]))
        if role:
            try:
                await interaction.user.add_roles(role)
                role_msg = f" and assigned target tier role: {role.mention}"
            except discord.Forbidden:
                role_msg = " *(⚠️ Notice: System role configuration could not be bound due to permission hierarchy configuration caps)*"
                
    await interaction.response.send_message(f"✅ Linked Asphalt ID: **{player_id}** to {interaction.user.mention}{role_msg}\n🔔 DM Alerts: {'**ON**' if current_dm_pref else '**OFF**'}")
@bot.tree.command(name="delete_id", description="Removes your game registration metadata profile completely.")
async def delete_id_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("user_id").eq("guild_id", guild_id).eq("user_id", user_id).execute())
    if prof_check.data and len(prof_check.data) > 0:
        await loop.run_in_executor(None, lambda: supabase.table("player_profiles").delete().eq("guild_id", guild_id).eq("user_id", user_id).execute())
        cfg_check = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("alert_role_id").eq("guild_id", guild_id).execute())
        role_message = "."
        if cfg_check.data and len(cfg_check.data) > 0 and cfg_check.data[0]["alert_role_id"]:
            role = interaction.guild.get_role(int(cfg_check.data[0]["alert_role_id"]))
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
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("dm_enabled").eq("guild_id", guild_id).eq("user_id", user_id).execute())
    if not prof_check.data or len(prof_check.data) == 0:
        return await interaction.response.send_message("⚠️ Please register your identity via `/set_id` prior to executing adjustments.", ephemeral=True)
        
    new_pref = not prof_check.data[0]["dm_enabled"]
    await loop.run_in_executor(None, lambda: supabase.table("player_profiles").update({"dm_enabled": new_pref}).eq("guild_id", guild_id).eq("user_id", user_id).execute())
    await interaction.response.send_message(f"🔔 DM alerts changed to **{'ON' if new_pref else 'OFF'}** for {interaction.user.mention}.")

@bot.tree.command(name="history", description="Displays the last 5 active or recent auto-scraped redemption codes.")
async def history_slash(interaction: discord.Interaction):
    loop = asyncio.get_event_loop()
    cache_res = await loop.run_in_executor(None, lambda: supabase.table("scraper_cache").select("code, detected_at").order("detected_at", desc=True).limit(5).execute())
    if not cache_res.data:
        return await interaction.response.send_message("🗂️ **No recent code drops found in the cloud tracking cache database.**", ephemeral=True)
        
    embed = discord.Embed(title="🏁 Recent Redemption Drop History", description="Missed an automated alert stream? Here are the most recent promo parameters discovered by the tracking core:", color=discord.Color.from_rgb(30, 90, 160))
    
    for idx, row in enumerate(cache_res.data, 1):
        code = row["code"]
        manual_url = f"https://asphaltlegendsunite.com{code}"
        embed.add_field(name=f"{idx}. Code: `{code}`", value=f"🔗 [Manual Claim Portal Shortcut]({manual_url})", inline=False)
        
    await interaction.response.send_message(embed=embed, ephemeral=True)
# --- MASTER ADMINISTRATION WORKBENCH WORKSPACE ---
@bot.tree.command(name="setup", description="Configure the channel and specific target roles for administration and drops.")
@app_commands.describe(announcement_channel="The destination text channel for public code announcements.", admin_role="Exactly one management group role given permission to execute admin commands.", player_role="Exactly one role that will be pinged and assigned to players on registration.")
@is_admin_or_delegated()
async def setup_slash(interaction: discord.Interaction, announcement_channel: discord.TextChannel, admin_role: discord.Role, player_role: discord.Role):
    guild_id = str(interaction.guild_id)
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: supabase.table("guild_config").upsert({
        "guild_id": guild_id, "notification_channel": announcement_channel.id, "bot_admin_role_id": admin_role.id, "alert_role_id": player_role.id
    }).execute())
    
    embed = discord.Embed(title="⚙️ Configuration Setup Matrix Saved to Supabase Cloud!", color=discord.Color.from_rgb(200, 140, 10))
    embed.add_field(name="📢 Announcements Channel", value=announcement_channel.mention, inline=True)
    embed.add_field(name="🛡️ Master Admin Authority Role", value=admin_role.mention, inline=True)
    embed.add_field(name="🔔 Player Alert Role Mention", value=player_role.mention, inline=False)
    await interaction.response.send_message(embed=embed)
    
    try:
        await announcement_channel.send(content=f"{player_role.mention} System Pipeline Connected Successfully to Cloud Database Environment nodes.")
    except discord.Forbidden:
        await interaction.followup.send("⚠️ **Configuration saved to cloud instance**, but bot lacks structural permissions to type inside that announcement channel!")
@bot.tree.command(name="diagnose", description="🛡️ Admin Tool: Runs an interactive real-time system stability and diagnostic health check.")
@is_admin_or_delegated()
async def diagnose_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    
    latency = round(bot.latency * 1000)
    ping_status = "🟢 Excellent" if latency < 150 else "🟡 Slow" if latency < 300 else "🔴 High Delay"
    scraper_status = "🟢 Active & Scanning" if auto_code_scraper_loop.is_running() else "🔴 Stopped"
    
    loop = asyncio.get_event_loop()
    cfg_res = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("*").eq("guild_id", guild_id).execute())
    channel_status, perm_status = "🔴 Unconfigured", "🔴 N/A"
    
    if cfg_res.data and len(cfg_res.data) > 0:
        target_channel_id = cfg_res.data[0]["notification_channel"]
        channel = bot.get_channel(target_channel_id)
        if channel:
            channel_status = f"🟢 Linked ({channel.mention})"
            perms = channel.permissions_for(interaction.guild.me)
            perm_status = "🟢 Verified Full Perms" if perms.send_messages and perms.embed_links else "⚠️ Missing Send/Embed Permissions"
            
    prof_count = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("user_id", count="exact").eq("guild_id", guild_id).execute())
    db_status = f"🟢 Supabase Cloud Online ({prof_count.count if prof_count.count is not None else 0} Live Profiles Vaulted)"

    embed = discord.Embed(title="🛡️ System Diagnostics & Health Status Dashboard", color=discord.Color.from_rgb(30, 140, 200))
    embed.add_field(name="🛰️ Discord Gateway Latency", value=f"📡 Ping: `{latency}ms` | {ping_status}", inline=False)
    embed.add_field(name="📡 Automated Scraper Task Engine", value=scraper_status, inline=False)
    embed.add_field(name="📢 Announcement Channel Route", value=channel_status, inline=True)
    embed.add_field(name="🔐 Bot Permissions Check", value=perm_status, inline=True)
    embed.add_field(name="🗄️ Supabase DB Cloud Audit", value=db_status, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="listplayers", description="Displays a detailed manifest profile metrics matrix of registered members.")
@is_admin_or_delegated()
async def listplayers_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    server_res = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("*").eq("guild_id", guild_id).execute())
    
    if not server_res.data:
        return await interaction.response.send_message("🧹 **Server registration profile index database is currently blank inside cloud rows.**", ephemeral=True)
    
    total_users = len(server_res.data)
    dm_enabled_count = sum(1 for info in server_res.data if info.get("dm_enabled", True))
    dm_percent = round((dm_enabled_count / total_users) * 100) if total_users > 0 else 0
    
    embed = discord.Embed(title=f"📋 Registered Profiles Metrics: {interaction.guild.name}", color=discord.Color.from_rgb(30, 90, 160))
    embed.add_field(name="📊 Metrics Summary", value=f"👥 Total Enrollment: `{total_users} Players` | 🔔 Alert Coverage: `{dm_percent}% DMs Active`", inline=False)
    
    for info in server_res.data[:20]:
        pref = "✅ Active" if info.get("dm_enabled", True) else "❌ Blocked"
        embed.add_field(name=f"User: {info['username']}", value=f"🆔 Game ID: `{info['player_id']}` | 📥 DM alerts: {pref}", inline=False)
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="redeem", description="Broadcasts a redeem code drop publicly and updates verified target players via DM.")
@app_commands.describe(code="The code string to broadcast and distribute (e.g., SPEED2026)")
@is_admin_or_delegated()
async def redeem_slash(interaction: discord.Interaction, code: str):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    cfg_res = await loop.run_in_executor(None, lambda: supabase.table("guild_config").select("*").eq("guild_id", guild_id).execute())
    
    if not cfg_res.data or len(cfg_res.data) == 0 or not cfg_res.data[0]["notification_channel"]:
        return await interaction.response.send_message("⚠️ Announcement pipes are unconfigured. Please run `/setup` first to link structural nodes.", ephemeral=True)
    
    cfg = cfg_res.data[0]
    target_channel = bot.get_channel(cfg["notification_channel"])
    if not target_channel:
        return await interaction.response.send_message("⚠️ Targeted logging infrastructure channel could not be resolved.", ephemeral=True)
    
    ping_string = f"<@&{cfg['alert_role_id']}>" if cfg['alert_role_id'] else "@everyone"
    server_res = await loop.run_in_executor(None, lambda: supabase.table("player_profiles").select("*").eq("guild_id", guild_id).execute())
    
    public_embed = discord.Embed(title="🏎️ New Asphalt Legends Redeem Code! 🏎️", description=f"🚨 **A new redemption drop has broken!** 🚨\n\n**Redeem Code:** `{code.upper()}`", color=discord.Color.from_rgb(230, 160, 15))
    public_embed.set_image(url=cfg.get("banner_url", DEFAULT_BANNER))
    public_embed.add_field(name="__Claim Framework__", value="Registered profiles: Stand by for custom pre-filled 1-click links arriving inside your direct message systems!\n\nManual users claim here: [Gameloft Portal](https://gameloft.com)", inline=False)
    
    await interaction.response.defer(ephemeral=True)
    await target_channel.send(content=ping_string, embed=public_embed)
    
    success, opted_out, failed = 0, 0, 0
    for info in server_res.data:
        if not info.get("dm_enabled", True):
            opted_out += 1
            continue
            
        member = interaction.guild.get_member(int(info["user_id"]))
        if member:
            prefilled_url = f"https://gameloft.com?playerId={info['player_id']}&code={code.upper()}"
            dm_embed = discord.Embed(title="🏁 Auto-Filled Reward Pipeline 🏁", description=f"**Code:** `{code.upper()}`\n\nClick the element below to access the claim portal with your player credentials pre-mapped!", color=discord.Color.from_rgb(40, 180, 70))
            dm_embed.add_field(name="__Dynamic Reward Portal__", value=f"[Click Here to Instantly Claim]({prefilled_url})")
            try:
                await member.send(embed=dm_embed)
                success += 1
                await asyncio.sleep(0.4) 
            except discord.Forbidden:
                failed += 1
        else:
            failed += 1
    await interaction.followup.send(f"✅ Drop processed to {target_channel.mention}! Logs: Delivered: {success} | Skipped: {opted_out} | Failed: {failed}")

@bot.tree.command(name="admin_set_name", description="⚙️ Admin Tool: Update the globally exposed account username across Discord.")
@is_admin_or_delegated()
async def admin_set_name_slash(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    try:
        await bot.user.edit(username=name)
        await interaction.followup.send(f"🎯 **Success:** Bot application profile display identifier updated to: **{name}**")
    except Exception as e:
        await interaction.followup.send(f"❌ **Discord Refusal:** Cannot adjust name string: `{str(e)}`", ephemeral=True)

@bot.tree.command(name="admin_set_avatar", description="⚙️ Admin Tool: Instantly upload an image file to update the bot's application icon picture.")
@is_admin_or_delegated()
async def admin_set_avatar_slash(interaction: discord.Interaction, attachment: discord.Attachment):
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        return await interaction.response.send_message("⚠️ **Format Exception:** Uploaded asset file must be a standard format graphic (PNG/JPEG).", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try:
        image_bytes = await attachment.read()
        await bot.user.edit(avatar=image_bytes)
        await interaction.followup.send("🎯 **Success:** Bot application profile avatar asset updated successfully across all servers!")
    except Exception as e:
        await interaction.followup.send(f"❌ **API Rejection exception:** Avatar adjustment limits exceeded or layout rejected: `{str(e)}`", ephemeral=True)

@bot.tree.command(name="admin_set_media", description="⚙️ Admin Tool: Configure custom imagery links used within embeds inside this specific server.")
@app_commands.choices(element=[
    app_commands.Choice(name="Landscape Banner Artwork (Full Size)", value="banner"),
    app_commands.Choice(name="Square Thumbnail Badge (Small Size)", value="thumbnail")
])
@is_admin_or_delegated()
async def admin_set_media_slash(interaction: discord.Interaction, element: app_commands.Choice[str], image_url: str):
    if not image_url.startswith("http"):
        return await interaction.response.send_message("⚠️ **Format Exception:** Imagery location arguments must point to a valid web URL target string.", ephemeral=True)
        
    guild_id = str(interaction.guild_id)
    field = "banner_url" if element.value == "banner" else "thumbnail_url"
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: supabase.table("guild_config").upsert({"guild_id": guild_id, field: image_url}).execute())
    await interaction.response.send_message(f"🎯 **Success:** Dynamic theme mapping updated! This server's `{element.value}` asset updated successfully.")

@bot.tree.command(name="admin_reset_defaults", description="⚙️ Admin Tool: Purge visual overrides configurations and restore native game themes.")
@is_admin_or_delegated()
async def admin_reset_defaults_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: supabase.table("guild_config").update({"banner_url": DEFAULT_BANNER, "thumbnail_url": DEFAULT_THUMBNAIL}).eq("guild_id", guild_id).execute())
    await interaction.response.send_message("🧹 **Success:** Custom graphics metadata drops purged. Original *Asphalt Legends Unite* branding elements restored!")

class ConfirmClearHistoryView(discord.ui.View):
    def __init__(self, author: discord.Member, guild_id: str):
        super().__init__(timeout=60)
        self.author = author
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("🚫 This confirmation terminal is locked to the executing administrative actor.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🔴")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: supabase.table("player_profiles").delete().eq("guild_id", self.guild_id).execute())
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🧹 **Database Server Registry Cleared Successfully!** Isolate server cache purged safely.", view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.success, emoji="🟢")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Operation Cancelled safely.** Local server profile registries left untouched.", view=self)

@bot.tree.command(name="clearhistory", description="Wipes out the entire registration database for this guild.")
@is_admin_or_delegated()
async def clearhistory_slash(interaction: discord.Interaction):
    view = ConfirmClearHistoryView(interaction.user, str(interaction.guild_id))
    await interaction.response.send_message(content="⚠️ **CRITICAL WARNING:** You are about to wipe the player registration data profile for *only this server*. This operation cannot be reversed. Proceed?", view=view, ephemeral=True)

@bot.tree.command(name="admin_restore", description="🛡️ Emergency Recovery Tool: Restores server user registrations from historical archives.")
@is_admin_or_delegated()
async def admin_restore_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    
    loop = asyncio.get_event_loop()
    archive_res = await loop.run_in_executor(None, lambda: supabase.table("daily_backups_archive").select("*").eq("guild_id", guild_id).order("saved_at", desc=True).execute())
    
    if not archive_res.data:
        return await interaction.followup.send("⚠️ **Data Recovery Exception:** No historical snapshot backup sequences located matching this server ID.", ephemeral=True)
        
    restored_count = 0
    seen_users = set()
    
    for row in archive_res.data:
        u_id = row["user_id"]
        if u_id not in seen_users:
            seen_users.add(u_id)
            
            await loop.run_in_executor(None, lambda: supabase.table("player_profiles").upsert({
                "guild_id": guild_id,
                "user_id": u_id,
                "username": row["username"],
"player_id": row["player_id"],"dm_enabled": row["dm_enabled"]}).execute())restored_count += 1await interaction.followup.send(f"🟢 Database Recovery Complete: Successfully synced and restored {restored_count} active player profiles from cloud archives!", ephemeral=True)token = os.environ.get("DISCORD_BOT_TOKEN", "")if not token and os.path.exists("token.txt"):with open("token.txt", "r", encoding="utf-8") as tf:token = tf.read().strip()if not token or token == "YOUR_TOKEN_HERE":print("❌ ERROR: Missing target validation credentials token configurations inside cloud environments maps paths.")else:bot.run(token)
