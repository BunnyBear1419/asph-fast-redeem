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

# --- TINY WEB SERVER TO FOOL HEALTH CHECKS ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
        
    def log_message(self, format, *args):
        return # Quiet logs

def run_web_server():
    server = HTTPServer(("0.0.0.0", 10000), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# --------------------------------------------------------------

DB_FILE = "asphalt_bot_database.json"
CONFIG_FILE = "asphalt_bot_config.json"
SCRAPER_CACHE_FILE = "asphalt_scraper_cache.json"

# Alphanumeric codes filter pattern (typically matching 6-14 characters for Gameloft codes)
CODE_PATTERN = re.compile(r'\b[A-Z0-9]{6,14}\b')

# Universal regex false-positives to filter out immediately
BLACKLISTED_WORDS = {"REDEEM", "TOKENS", "CREDITS", "ASPHALT", "UNITE", "REDDIT", "PLAYER", "NINTENDO", "XBOX", "PLAYSTATION"}

# --- STORAGE DATABASE IO PROTOCOLS ---
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


# --- DISCORD APPLICATION CLIENT BASE ---
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Production node verified: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        
    # Launch Background Automated Scraper Loop
    if not auto_code_scraper_loop.is_running():
        auto_code_scraper_loop.start()
        print("📡 Background Automated Code Scraper Task Cycle engaged!")


# --- PERMISSIONS COMPLIANCE INTERCEPTS ---
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


# ==============================================================================
# DISCORD UI INTERACTION NODES (DROP-DOWNS)
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
        # Sleek Premium Palette System Styling
        dark_blue = discord.Color.from_rgb(20, 24, 40)
        dark_green = discord.Color.from_rgb(24, 40, 20)
        dark_red = discord.Color.from_rgb(45, 15, 15)

        # FIXED: self.values returns a list. We must check the first selected item using self.values[0]
        selected_value = self.values[0]
        embed = discord.Embed(title="Error", description="Unknown option selected.")

        if selected_value == "📖 Bot Overview":
            embed = discord.Embed(
                title="🤖 Asphalt Legends Fast Redeem Manual",
                description="Welcome! This system manages **Asphalt Legends Unite Redeem Codes** inside your server community!",
                color=dark_blue
            )
            embed.add_field(name="✨ Key Framework", value="• Register your player ID to receive automatic rewards roles.\n• Instantly maps pre-filled 1-click URL parameters to your DMs when drops occur!\n• Monitors community networks automatically to discover new codes 24/7.", inline=False)
            
        elif selected_value == "🎮 Player Commands":
            embed = discord.Embed(title="🕹️ Player Commands Matrix", color=dark_green)
            embed.add_field(name="`/set_id`", value="**Usage:** `/set_id player_id: <YOUR_ID>`\nRegisters your unique Asphalt game ID and assigns server drop alert roles.", inline=False)
            embed.add_field(name="`/toggle_dm`", value="Toggles direct message redeem link alerts ON or OFF.", inline=False)
            embed.add_field(name="`/delete_id`", value="Removes your data footprint completely and drops associated alert roles.", inline=False)
            embed.add_field(name="`/help` & `/commands`", value="Spawns this exact interactive selection panel UI.", inline=False)
            
        elif selected_value == "🛡️ Admin Utilities":
            embed = discord.Embed(title="⚙️ Administrator Utilities Manual", color=dark_red)
            embed.add_field(name="`/setup`", value="**Usage:** `/setup announcement_channel: #ch admin_role: @role player_role: @role`\nConfigures public notification channels, delegated management authorization groups, and target notification ping tags.", inline=False)
            embed.add_field(name="`/redeem`", value="**Usage:** `/redeem code: <code>`\nBlasts interactive 1-click links out to user DMs and logs to the configurations layout channel manually.", inline=False)
            embed.add_field(name="`/listplayers`", value="Renders an overview checklist matrix of active server registrations.", inline=False)
            embed.add_field(name="`/test_code`", value="Fires an isolated test payload embed to verification configurations.", inline=False)
            embed.add_field(name="`/clearhistory`", value="Wipes out database information fields strictly isolated to this guild.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, show_admin_docs: bool):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(show_admin_docs))


# ==============================================================================
# AUTOMATED ACTION LOOP SCRAPER (REDDIT API AGENT)
# ==============================================================================

@tasks.loop(minutes=15)
async def auto_code_scraper_loop():
    """Monitors the web space asynchronously for new Asphalt promo drops."""
    await bot.wait_until_ready()
    url = "https://www.reddit.com/r/Asphalt9/new.json?limit=12"
    headers = {"User-Agent": "DiscloudPlatinumAsphaltBot/3.0 (by /u/ProductionDeveloper)"}
    
    sent_cache = load_scraper_cache()
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return
                
                data = await response.json()
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "").upper()
                    selftext = post_data.get("selftext", "").upper()
                    
                    keywords = ["REDEEM CODE", "NEW CODE", "PROMO CODE", "FREE TOKENS", "REWARD CODE", "WORKING CODE", "UNITE CODE"]
                    
                    if any(kw in title for kw in keywords) or any(kw in selftext for kw in keywords):
                        search_blob = f"{title} {selftext}"
                        found_codes = CODE_PATTERN.findall(search_blob)
                        
                        for code in found_codes:
                            if code in BLACKLISTED_WORDS:
                                continue
                                
                            if code not in sent_cache:
                                print(f"📡 Scraper Detected Fresh Global Code Matrix: {code}")
                                sent_cache.add(code)
                                save_scraper_cache(sent_cache)
                                
                                # Global Deployment Dispatch Loop
                                await execute_global_automation_blast(code)
                                
        except Exception as e:
            print(f"⚠️ Scraper telemetry loop error event: {e}")

async def execute_global_automation_blast(code: str):
    """Iterates through database footprints to announce auto-scraped keys globally."""
    config = load_config()
    data = load_data()
    
    public_color = discord.Color.from_rgb(230, 160, 15) # Warm Gold Accent
    dm_color = discord.Color.from_rgb(40, 180, 70)      # High-Visibility Green
    
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
        public_embed.add_field(
            name="__Claim Framework__",
            value="Registered profiles: Check your direct messages for your custom pre-filled 1-click links!\n\nManual users claim here: [Gameloft Portal](https://www.gameloft.com/redeem/asphalt-legends-unite)",
            inline=False
        )
        public_embed.set_footer(text="Automated Delivery Network • Claim quickly before limits are reached!")
        
        try:
            await target_channel.send(content=ping_string, embed=public_embed)
        except Exception:
            continue
            
        # Process Individual Player DM Blasts for this specific guild
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
                    await asyncio.sleep(0.3) # Throttle rate limit overhead splits safely
                except Exception:
                    pass


# ==============================================================================
# CORE SYSTEM SLASH COMMANDS
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


@bot.tree.command(name="commands", description="Pop up all available commands with detailed usage for players and admins.")
async def commands_slash(interaction: discord.Interaction):
    config = load_config()
    is_authorized = False
    
    if interaction.user.guild_permissions.administrator:
        is_authorized = True
    else:
        delegated_id = config.get(str(interaction.guild_id), {}).get("bot_admin_role_id")
        if delegated_id and discord.utils.get(interaction.user.roles, id=int(delegated_id)):
            is_authorized = True

    embed = discord.Embed(
        title="🎮 Command Directory Manual",
        description="Select a module below to inspect arguments, usage parameters, and functional options.",
        color=discord.Color.from_rgb(40, 20, 45)
    )
    await interaction.response.send_message(embed=embed, view=HelpView(is_authorized), ephemeral=False)


@bot.tree.command(name="setup", description="Configure the channel and specific target roles for administration and drops.")
@app_commands.describe(
    announcement_channel="The destination text channel for public code announcements.",
    admin_role="Exactly one management group role given permission to execute admin commands.",
    player_role="Exactly one role that will be pinged and assigned to players on registration."
)
@is_admin_or_delegated()
async def setup_slash(
    interaction: discord.Interaction,
    announcement_channel: discord.TextChannel,
    admin_role: discord.Role,
    player_role: discord.Role
):
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
    
    # --- INTERACTIVE SETUP VALIDATION FEEDBACK LOOP ---
    mock_code = "UNITE2026"
    test_embed = discord.Embed(
        title="🏎️ Verification Stream: System Setup Live! 🏎️",
        description=f"🤖 This is a pipeline verification test broadcast message.\n\n**Active Test Code Framework:** `{mock_code}`",
        color=discord.Color.from_rgb(50, 120, 220)
    )
    test_embed.set_footer(text="Verification Loop Active • Connection Nodes Sync Operational.")
    try:
        await announcement_channel.send(content=f"{player_role.mention} System Online Verification Stream Checked Successfully.", embed=test_embed)
    except discord.Forbidden:
        await interaction.followup.send("⚠️ **Notice:** Configuration saved, but the bot lacks permission to type in that announcement channel!")


# --- CONVERTED PLAYER UTILITIES ---

@bot.tree.command(name="set_id", description="Registers your unique Asphalt Game ID and applies saved server roles.")
@app_commands.describe(player_id="Your authentic Asphalt game identity code (e.g., u-4a5b6c)")
async def set_id_slash(interaction: discord.Interaction, player_id: str):
    player_id = player_id.strip().lower()
    
    # Basic data structure normalization filter
    if not player_id.startswith("u-"):
        return await interaction.response.send_message("⚠️ **Format Exception:** Asphalt Game IDs must start with `u-` structure format syntax (e.g. `u-4a5b6c`). Check your profile card tab inside the app.", ephemeral=True)

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    
    data = load_data()
    config = load_config()
    
    if guild_id not in data:
        data[guild_id] = {}
        
    current_dm_pref = data[guild_id].get(user_id, {}).get("dm_enabled", True)
    
    data[guild_id][user_id] = {
        "username": interaction.user.name,
        "player_id": player_id,
        "dm_enabled": current_dm_pref
    }
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
                
    await interaction.response.send_message(
        f"✅ Linked Asphalt ID: **{player_id}** to {interaction.user.mention}{role_msg}\n"
        f"🔔 DM Alerts: {'**ON**' if current_dm_pref else '**OFF**'}"
    )

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


# --- CONVERTED MANUAL ADMIN UTILITIES ---

@bot.tree.command(name="clearhistory", description="Wipes out the entire registration database for this guild.")
@is_admin_or_delegated()
async def clearhistory_slash(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)
    
    if guild_id in data:
        del data[guild_id]
        save_data(data)
    await interaction.response.send_message("🧹 **Database Registry Cleared Successfully!**")


@bot.tree.command(name="listplayers", description="Displays a detailed manifest profile listing of registered members.")
@is_admin_or_delegated()
async def listplayers_slash(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)
    server_data = data.get(guild_id, {})
    
    if not server_data:
        return await interaction.response.send_message("🧹 **Guild registration profile index is currently blank.**", ephemeral=True)
    
    embed = discord.Embed(title=f"📋 Registered Profiles: {interaction.guild.name}", color=discord.Color.from_rgb(30, 90, 160))
    for disc_id, info in server_data.items():
        pref = "✅ Enabled" if info.get("dm_enabled", True) else "❌ Disabled"
        embed.add_field(name=f"User: {info['username']}", value=f"**Game ID:** `{info['player_id']}` | **DMs:** {pref}", inline=False)
        
    await interaction.response.send_message(embed=embed)


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
        await interaction.response.send_message("❌ **Error:** Cannot map connection routes to DM logs. Verify user setting frameworks.", ephemeral=True)


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
    
    public_embed = discord.Embed(
        title="🏎️ New Asphalt Legends Redeem Code! 🏎️",
        description=f"🚨 **A new global redemption drop has broken!** 🚨\n\n**Redeem Code:** `{code.upper()}`",
        color=discord.Color.from_rgb(230, 160, 15)
    )
    public_embed.add_field(
        name="__Claim Framework__",
        value="Registered profiles: Stand by for custom pre-filled 1-click links arriving inside your direct message systems!\n\nManual users claim here: [Gameloft Portal](https://www.gameloft.com/redeem/asphalt-legends-unite)",
        inline=False
    )
    public_embed.set_footer(text="Warning: Active redemption caps or timeline expirations apply!")
    
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
            dm_embed = discord.Embed(
                title="🏁 Auto-Filled Reward Pipeline 🏁",
                description=f"**Code:** `{code.upper()}`\n\nClick the element below to access the claim portal with your player credentials pre-mapped!",
                color=discord.Color.from_rgb(40, 180, 70)
            )
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


# --- GLOBAL APP ERROR INTERCEPT HANDLER ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("🚫 **Access Denied:** administrative clearances or delegated group assignments missing.", ephemeral=True)
        else:
            await interaction.followup.send("🚫 **Access Denied:** Administrative authorization validation checks failed.", ephemeral=True)


# --- APPLICATION INITIALIZATION BOOTLOADER ---
token = os.environ.get("DISCORD_BOT_TOKEN", "")
if not token and os.path.exists("token.txt"):
    with open("token.txt", "r", encoding="utf-8") as tf:
        token = tf.read().strip()

if not token or token == "YOUR_TOKEN_HERE":
    print("❌ ERROR: Missing target validation credentials token configurations inside system paths.")
else:
    bot.run(token)
