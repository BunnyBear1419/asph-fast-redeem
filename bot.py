# ==============================================================================
# SECTION 1: CORE APPLICATION LIBRARIES & BASE MANIFESTS
# ==============================================================================
import discord
from discord import app_commands
from discord.ext import tasks, commands
import os
import asyncio
import threading
import re
import aiohttp
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient, DESCENDING
# ==============================================================================
# SECTION 2: WEB INFRASTRUCTURE BACKGROUND RECEPTACLE
# ==============================================================================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot connection nodes active!")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    server = HTTPServer(("0.0.0.0", 10000), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# ==============================================================================
# SECTION 3: SYSTEM SEARCH INTERFACES & EXCLUSIONS
# ==============================================================================
CODE_PATTERN = re.compile(r'\b[A-Z0-9]{6,14}\b')

BLACKLISTED_WORDS = {
    "REDEEM", "TOKENS", "CREDITS", "ASPHALT", "UNITE", 
    "REDDIT", "PLAYER", "NINTENDO", "XBOX", "PLAYSTATION"
}

DEFAULT_BANNER = "https://imgur.com"
DEFAULT_THUMBNAIL = "https://imgur.com"
# ==============================================================================
# SECTION 4: MONGODB CONNECTIONS UTILITIES
# ==============================================================================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "asphalt_bot_db")

# Initialize MongoDB Client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]

# Collections Mapping
guild_config_col = db["guild_config"]
player_profiles_col = db["player_profiles"]
scraper_cache_col = db["scraper_cache"]
backups_archive_col = db["daily_backups_archive"]
# ==============================================================================
# SECTION 5: APPLICATION BOOT SYSTEM
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ MongoDB cluster linked: {bot.user.name}")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"❌ Sync failure: {e}")
        
    if not auto_code_scraper_loop.is_running():
        auto_code_scraper_loop.start()
# ==============================================================================
# SECTION 6: INTERACTIVE DROPDOWN INTERACTION CHANNELS
# ==============================================================================
class HelpDropdown(discord.ui.Select):
    def __init__(self, show_admin_docs: bool):
        options = [
            discord.SelectOption(label="📖 Bot Overview", value="overview", description="Overview instructions"),
            discord.SelectOption(label="🎮 Player Commands", value="player", description="User utility metrics"),
        ]
        if show_admin_docs:
            options.append(discord.SelectOption(label="🛡️ Admin Utilities", value="admin", description="Admin workbench mapping"))
            
        super().__init__(placeholder="Select system segment...", min_values=1, max_values=1, options=options)
        
    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        
        loop = asyncio.get_event_loop()
        cfg_res = await loop.run_in_executor(
            None, lambda: guild_config_col.find_one({"guild_id": guild_id})
        )
        
        banner = DEFAULT_BANNER
        thumb = DEFAULT_THUMBNAIL
        if cfg_res:
            banner = cfg_res.get("banner_url", DEFAULT_BANNER)
            thumb = cfg_res.get("thumbnail_url", DEFAULT_THUMBNAIL)

        selected_value = self.values if self.values else ""
        embed = discord.Embed(title="Error", description="Unknown partition route selection parameters.")
        if selected_value == "overview":
            embed = discord.Embed(title="🤖 Asphalt Legends Fast Redeem Manual", description="Automated drops processing layout matrix.", color=discord.Color.from_rgb(20, 24, 40))
            embed.set_image(url=banner)
            embed.add_field(name="✨ Key Framework", value="• Register your player ID via `/set_id` to get custom links inside your DMs automatically!", inline=False)
            
        elif selected_value == "player":
            embed = discord.Embed(title="🕹️ Player Commands Matrix", color=discord.Color.from_rgb(24, 40, 20))
            embed.set_thumbnail(url=thumb)
            embed.add_field(name="`/set_id` | `/toggle_dm` | `/delete_id` | `/history`", value="Standard player infrastructure tools map utilities.", inline=False)
            
        elif selected_value == "admin":
            embed = discord.Embed(title="⚙️ Administrator Utilities Manual", color=discord.Color.from_rgb(45, 15, 15))
            embed.set_thumbnail(url=thumb)
            embed.add_field(name="`/setup` | `/redeem` | `/listplayers` | `/diagnose` | `/admin_restore`", value="Master administration commands module workspace console tools.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, show_admin_docs: bool):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(show_admin_docs))
# ==============================================================================
# SECTION 7: DUAL-PLATFORM BACKGROUND AUTOMATION SCRAPER
# ==============================================================================
@tasks.loop(minutes=15)
async def auto_code_scraper_loop():
    await bot.wait_until_ready()
    headers = {"User-Agent": "DiscloudPlatinumAsphaltBot/5.0"}
    
    async with aiohttp.ClientSession() as session:
        try:
            reddit_url = "https://reddit.com"
            async with session.get(reddit_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for post in data.get("data", {}).get("children", []):
                        p_data = post.get("data", {})
                        search_blob = f"{p_data.get('title', '')} {p_data.get('selftext', '')}".upper()
                        await process_text_and_blast(search_blob)
        except Exception as e:
            print(f"⚠️ Reddit tracking delay event exception: {e}")
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
        for code in CODE_PATTERN.findall(search_blob):
            code = code.upper()
            if code in BLACKLISTED_WORDS:
                continue
                
            loop = asyncio.get_event_loop()
            cache_check = await loop.run_in_executor(None, lambda: scraper_cache_col.find_one({"code": code}))
            if not cache_check:
                await loop.run_in_executor(None, lambda: scraper_cache_col.insert_one({"code": code, "detected_at": datetime.now(timezone.utc)}))
                print(f"📡 Multi-Site Scraper Detected Fresh Code Matrix: {code}")
                await execute_global_automation_blast(code)
# ==============================================================================
# SECTION 8: CODES DISTRIBUTION HYPER-DRIVE LOOP
# ==============================================================================
async def execute_global_automation_blast(code: str):
    loop = asyncio.get_event_loop()
    configs_res = await loop.run_in_executor(None, lambda: list(guild_config_col.find({})))
    profiles_res = await loop.run_in_executor(None, lambda: list(player_profiles_col.find({"dm_enabled": True})))
    
    if not configs_res:
        return

    players_by_guild = {}
    for p in profiles_res:
        g_id = p["guild_id"]
        if g_id not in players_by_guild:
            players_by_guild[g_id] = []
        players_by_guild[g_id].append(p)
        
    for guild_cfg in configs_res:
        guild_id_str = guild_cfg["guild_id"]
        guild = bot.get_guild(int(guild_id_str))
        if not guild:
            continue
            
        target_channel = bot.get_channel(guild_cfg["notification_channel"])
        if not target_channel:
            continue
            
        player_role_id = guild_cfg.get("alert_role_id")
        ping_string = f"<@&{player_role_id}>" if player_role_id else "@everyone"
        
        public_embed = discord.Embed(title="🏎️ Automated Asphalt Legends Redeem Code! 🏎️", description=f"🚨 Code: `{code.upper()}`", color=discord.Color.from_rgb(230, 160, 15))
        public_embed.set_image(url=guild_cfg.get("banner_url", DEFAULT_BANNER))
        try:
            await target_channel.send(content=ping_string, embed=public_embed)
        except Exception:
            pass
            
        for p_info in players_by_guild.get(guild_id_str, []):
            member = guild.get_member(int(p_info["user_id"]))
            if member:
                prefilled_url = f"https://gameloft.com{p_info['player_id']}&code={code.upper()}"
                dm_embed = discord.Embed(title="🏁 Reward Pipeline Link Online", description=f"Code: `{code.upper()}`", color=discord.Color.from_rgb(40, 180, 70))
                dm_embed.add_field(name="Link", value=f"[Claim Reward Instantly]({prefilled_url})")
                try:
                    await member.send(embed=dm_embed)
                    await asyncio.sleep(0.4)
                except Exception:
                    pass
# ==============================================================================
# SECTION 9: SECURE POLICY COMPLIANCE EXCEPTION HANDLERS
# ==============================================================================
def is_admin_or_delegated():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        if interaction.user.guild_permissions.administrator:
            return True
        
        guild_id = str(interaction.guild.id)
        loop = asyncio.get_event_loop()
        cfg_check = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
        
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
            await interaction.response.send_message("🚫 **Access Denied:** administrative clearances validation error.", ephemeral=True)
# ==============================================================================
# SECTION 10: USER FRONTEND SLASHPANEL TERMINAL NODES
# ==============================================================================
@bot.tree.command(name="help", description="Tells the admins or players about what this bot does & how to use it.")
async def help_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    is_authorized = False
    if interaction.user.guild_permissions.administrator:
        is_authorized = True
    else:
        loop = asyncio.get_event_loop()
        cfg_check = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
        if cfg_check and cfg_check.get("bot_admin_role_id") and discord.utils.get(interaction.user.roles, id=int(cfg_check["bot_admin_role_id"])):
            is_authorized = True

    embed = discord.Embed(title="🗂️ Help Documentation Center", description="Select choice parameters matrix:", color=discord.Color.from_rgb(20, 24, 40))
    await interaction.response.send_message(embed=embed, view=HelpView(is_authorized), ephemeral=True)

@bot.tree.command(name="set_id", description="Registers your unique Asphalt Game ID.")
async def set_id_slash(interaction: discord.Interaction, player_id: str):
    player_id = player_id.strip().lower()
    if not player_id.startswith("u-"):
        return await interaction.response.send_message("⚠️ Format Exception: Must begin with `u-` keys structure layout data panels.", ephemeral=True)

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: player_profiles_col.find_one({"guild_id": guild_id, "user_id": user_id}))
    current_dm_pref = prof_check.get("dm_enabled", True) if prof_check else True
    
    await loop.run_in_executor(None, lambda: player_profiles_col.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": {"username": interaction.user.name, "player_id": player_id, "dm_enabled": current_dm_pref}},
        upsert=True
    ))
    
    cfg_check = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
    if cfg_check and cfg_check.get("alert_role_id"):
        role = interaction.guild.get_role(int(cfg_check["alert_role_id"]))
        if role:
            try: await interaction.user.add_roles(role)
            except discord.Forbidden: pass
                
    dm_status_str = "ON" if current_dm_pref else "OFF"
    await interaction.response.send_message(f"✅ Linked Asphalt ID: **{player_id}**
🔔 DM Alerts: **{dm_status_str}**")

@bot.tree.command(name="delete_id", description="Removes your game registration metadata profile completely.")
async def delete_id_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: player_profiles_col.find_one({"guild_id": guild_id, "user_id": user_id}))
    if prof_check:
        await loop.run_in_executor(None, lambda: player_profiles_col.delete_one({"guild_id": guild_id, "user_id": user_id}))
        await interaction.response.send_message("❌ Player database asset unlinked safely configuration parameters drops.")
    else:
        await interaction.response.send_message("⚠️ Context profiling signature matching failure.", ephemeral=True)

@bot.tree.command(name="toggle_dm", description="Toggle direct message notifications.")
async def toggle_dm_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    loop = asyncio.get_event_loop()
    prof_check = await loop.run_in_executor(None, lambda: player_profiles_col.find_one({"guild_id": guild_id, "user_id": user_id}))
    if not prof_check:
        return await interaction.response.send_message("⚠️ Register structural ID via `/set_id` first.", ephemeral=True)
        
    new_pref = not prof_check.get("dm_enabled", True)
    await loop.run_in_executor(None, lambda: player_profiles_col.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": {"dm_enabled": new_pref}}
    ))
    await interaction.response.send_message(f"🔔 DM alerts turned **{'ON' if new_pref else 'OFF'}**.")

@bot.tree.command(name="history", description="Displays the last 5 auto-scraped redemption codes.")
async def history_slash(interaction: discord.Interaction):
    loop = asyncio.get_event_loop()
    cache_res = await loop.run_in_executor(None, lambda: list(scraper_cache_col.find({}).sort("detected_at", DESCENDING).limit(5)))
    if not cache_res:
        return await interaction.response.send_message("🗂️ No backlog metrics logs recorded.", ephemeral=True)
        
    embed = discord.Embed(title="🏁 Recent Redemption Drop History", color=discord.Color.from_rgb(30, 90, 160))
    for idx, row in enumerate(cache_res, 1):
        code = row["code"]
        manual_url = f"https://asphaltlegendsunite.com{code}"
        embed.add_field(name=f"{idx}. Code: `{code}`", value=f"🔗 [Claim Shortcut Link]({manual_url})", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup", description="Configure the channel and specific target roles.")
@is_admin_or_delegated()
async def setup_slash(interaction: discord.Interaction, announcement_channel: discord.TextChannel, admin_role: discord.Role, player_role: discord.Role):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: guild_config_col.update_one(
        {"guild_id": guild_id},
        {"$set": {
            "notification_channel": announcement_channel.id, 
            "bot_admin_role_id": admin_role.id, 
            "alert_role_id": player_role.id
        }},
        upsert=True
    ))
    await interaction.response.send_message("⚙️ Setup matrix configuration nodes saved directly to cloud tables rows checked successfully!")

@bot.tree.command(name="diagnose", description="🛡️ Admin Tool: Runs an interactive system diagnostic stability health check.")
@is_admin_or_delegated()
async def diagnose_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    
    latency = round(bot.latency * 1000)
    loop = asyncio.get_event_loop()
    
    mongo_status = "🟢 Connected"
    try:
        await loop.run_in_executor(None, lambda: db.command("ping"))
        prof_count = await loop.run_in_executor(None, lambda: player_profiles_col.count_documents({"guild_id": guild_id}))
    except Exception as e:
        mongo_status = f"🔴 Connection Failed: {str(e)[:50]}"
        prof_count = "N/A"

    embed = discord.Embed(title="🛡️ System Diagnostics Status", color=discord.Color.from_rgb(30, 140, 200))
    embed.add_field(name="Satellite Delay Latency", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="MongoDB Connection Status", value=f"`{mongo_status}`", inline=True)
    embed.add_field(name="MongoDB Cloud Online Vaults", value=f"`{prof_count} Live Entries`", inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="listplayers", description="Displays membership profiling matrix manifest lists.")
@is_admin_or_delegated()
async def listplayers_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    server_res = await loop.run_in_executor(None, lambda: list(player_profiles_col.find({"guild_id": guild_id}).limit(20)))
    if not server_res:
        return await interaction.response.send_message("🧹 Enrollment checklists index metrics are currently blank.", ephemeral=True)
        
    embed = discord.Embed(title="📋 Registered Manifest checklist", color=discord.Color.from_rgb(30, 90, 160))
    for info in server_res:
        embed.add_field(name=f"User: {info['username']}", value=f"🆔 Game ID: `{info['player_id']}`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="redeem", description="Manual broadcast blast distribution channels operations logs.")
@is_admin_or_delegated()
async def redeem_slash(interaction: discord.Interaction, code: str):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    cfg_res = await loop.run_in_executor(None, lambda: guild_config_col.find_one({"guild_id": guild_id}))
    if not cfg_res:
        return await interaction.response.send_message("⚠️ Run `/setup` configurations matrix routing fields nodes first.", ephemeral=True)
        
    target_channel = bot.get_channel(cfg_res["notification_channel"])
    await interaction.response.defer(ephemeral=True)
    
    public_embed = discord.Embed(title="🏎️ New Asphalt Legends Redeem Code! 🏎️", description=f"Code: `{code.upper()}`", color=discord.Color.from_rgb(230, 160, 15))
    public_embed.set_image(url=cfg_res.get("banner_url", DEFAULT_BANNER))
    await target_channel.send(embed=public_embed)
    await interaction.followup.send("✅ Public drop notifications dispatched successfully across connected servers loops nodes links channels.")

@bot.tree.command(name="admin_set_name", description="⚙️ Admin Tool: Adjust user name identifiers mapping loops variables.")
@is_admin_or_delegated()
async def admin_set_name_slash(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    try:
        await bot.user.edit(username=name)
        await interaction.followup.send(f"🎯 Name string adjusted to: **{name}**")
    except Exception as e: await interaction.followup.send(f"❌ Limits bound constraint blocking logic error exception: {e}")

@bot.tree.command(name="admin_set_avatar", description="⚙️ Admin Tool: Adjust bot application graphic profile interface icons templates.")
@is_admin_or_delegated()
async def admin_set_avatar_slash(interaction: discord.Interaction, attachment: discord.Attachment):
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        return await interaction.response.send_message("⚠️ Exception constraints requirements: Target file container structure must be an image type format description asset block maps.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try:
        image_bytes = await attachment.read()
        await bot.user.edit(avatar=image_bytes)
        await interaction.followup.send("🎯 Success avatar assets configured completely globally checks checked!")
    except Exception as e: await interaction.followup.send(f"❌ Rejection handling trigger: {e}")

@bot.tree.command(name="admin_set_media", description="⚙️ Admin Tool: Custom graphics links.")
@app_commands.choices(element=[app_commands.Choice(name="Banner", value="banner"), app_commands.Choice(name="Thumbnail", value="thumbnail")])
@is_admin_or_delegated()
async def admin_set_media_slash(interaction: discord.Interaction, element: app_commands.Choice[str], image_url: str):
    if not image_url.startswith("http"): return await interaction.response.send_message("⚠️ Must be valid web URL protocol string.", ephemeral=True)
    guild_id = str(interaction.guild_id)
    field = "banner_url" if element.value == "banner" else "thumbnail_url"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: guild_config_col.update_one(
        {"guild_id": guild_id},
        {"$set": {field: image_url}},
        upsert=True
    ))
    await interaction.response.send_message("🎯 Success theme matrix asset overrides saved to cloud instance lines checked.")

@bot.tree.command(name="admin_reset_defaults", description="⚙️ Admin Tool: Clear configurations visual branding parameters overrides.")
@is_admin_or_delegated()
async def admin_reset_defaults_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: guild_config_col.update_one(
        {"guild_id": guild_id},
        {"$set": {"banner_url": DEFAULT_BANNER, "thumbnail_url": DEFAULT_THUMBNAIL}}
    ))
    await interaction.response.send_message("🧹 Overrides dropped. Original themes parameters re-enabled successfully traces checks logged!")

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
        await loop.run_in_executor(None, lambda: player_profiles_col.delete_many({"guild_id": self.guild_id}))
        self.stop()
        await interaction.response.edit_message(content="🧹 Wiped registration logs from server caches successfully!", view=None)
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="🔴")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="🛑 Operation Aborted.", view=None)

@bot.tree.command(name="clearhistory", description="Wipes out the entire registration database for this guild.")
@is_admin_or_delegated()
async def clearhistory_slash(interaction: discord.Interaction):
    view = ConfirmClearHistoryView(interaction.user, str(interaction.guild_id))
    await interaction.response.send_message(content="⚠️ Proceed with purging profiles for this guild context partition line logs?", view=view, ephemeral=True)

@bot.tree.command(name="admin_restore", description="🛡️ Restores registration snapshots records rows directly from backup arrays indexes.")
@is_admin_or_delegated()
async def admin_restore_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    loop = asyncio.get_event_loop()
    archive_res = await loop.run_in_executor(None, lambda: list(backups_archive_col.find({"guild_id": guild_id}).sort("saved_at", DESCENDING)))
    if not archive_res: return await interaction.followup.send("⚠️ No snapshot archive files located.", ephemeral=True)
    
    restored_count = 0
    seen_users = set()
    for row in archive_res:
        u_id = row["user_id"]
        if u_id not in seen_users:
            seen_users.add(u_id)
            await loop.run_in_executor(None, lambda: player_profiles_col.update_one(
                {"guild_id": guild_id, "user_id": u_id},
                {"$set": {
                    "username": row["username"], 
                    "player_id": row["player_id"], 
                    "dm_enabled": row["dm_enabled"]
                }},
                upsert=True
            ))
            restored_count += 1
            
    await interaction.followup.send(f"🟢 Sync checked! Restored `{restored_count}` player profile entry cards successfully!", ephemeral=True)

token = os.environ.get("DISCORD_BOT_TOKEN", "")
if not token and os.path.exists("token.txt"):
    with open("token.txt", "r", encoding="utf-8") as tf: token = tf.read().strip()

if not token or token == "YOUR_TOKEN_HERE": print("❌ ERROR: Missing credential keys mapping token configurations variables.")
else: bot.run(token)
