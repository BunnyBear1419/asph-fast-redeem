import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- TINY WEB SERVER TO FOOL RENDER FREE TIER ---
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
# -----------------------------------------------

DB_FILE = "asphalt_bot_database.json"
CONFIG_FILE = "asphalt_bot_config.json"

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


# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
bot = commands.Bot(command_prefix="!", intents=intents) # Prefix kept as fallback

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")


# --- CUSTOM PERMISSION CHECK ---
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
# ADVANCED INTERACTIVE UI: SELECT MENU / DROP-DOWNS
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
        if self.values == "📖 Bot Overview":
            embed = discord.Embed(
                title="🤖 Asphalt Legends Fast Redeem Manual",
                description="Welcome! This bot automates the processing of **Asphalt Legends Redeem Codes** directly inside your server community!",
                color=discord.Color.blue()
            )
            embed.add_field(name="✨ Key Framework", value="• Register your player ID to receive automatic rewards roles.\n• Instantly maps pre-filled 1-click URL parameters to your DMs when drops occur!", inline=False)
            
        elif self.values == "🎮 Player Commands":
            embed = discord.Embed(title="🕹️ Player Commands Matrix", color=discord.Color.green())
            embed.add_field(name="`/set_id`", value="**Usage:** `/set_id player_id: <YOUR_ID>`\nRegisters your unique Asphalt game ID and assigns server drop alert roles.", inline=False)
            embed.add_field(name="`/toggle_dm`", value="Toggles direct message redeem link alerts ON or OFF.", inline=False)
            embed.add_field(name="`/delete_id`", value="Removes your data footprint completely and drops associated alert roles.", inline=False)
            embed.add_field(name="`/help` & `/commands`", value="Spawns this exact interactive selection panel UI.", inline=False)
            
        elif self.values == "🛡️ Admin Utilities":
            embed = discord.Embed(title="⚙️ Administrator Utilities Manual", color=discord.Color.red())
            embed.add_field(name="`/setup`", value="**Usage:** `/setup announcement_channel: #ch register_roles: @r1, @r2 admin_role: @r`\nConfigures notification pipes, management authorities, and assigns multiple automated player reward roles.", inline=False)
            embed.add_field(name="`/redeem`", value="**Usage:** `/redeem code: <code>`\nBlasts interactive 1-click links out to user DMs and logs to the configurations layout channel.", inline=False)
            embed.add_field(name="`/listplayers`", value="Renders an overview checklist matrix of active server registrations.", inline=False)
            embed.add_field(name="`/test_code`", value="Fires an isolated test payload embed to verification configurations.", inline=False)
            embed.add_field(name="`/clearhistory`", value="Wipes out database information fields strictly isolated to this guild.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, show_admin_docs: bool):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(show_admin_docs))


# ==============================================================================
# MODERN SLASH COMMAND DECLARATIONS
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
        color=discord.Color.blue()
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
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, view=HelpView(is_authorized), ephemeral=False)


@bot.tree.command(name="setup", description="Configure channels, administrators, and save up to 3 automatic player registration roles.")
@app_commands.describe(
    announcement_channel="The destination text channel for public code announcements.",
    admin_role="Sets a fallback role allowed to execute administrative bot commands.",
    register_role_1="Primary role a user gets awarded when registering their game id.",
    register_role_2="Second optional automated role awarded to verified players.",
    register_role_3="Third optional automated role awarded to verified players."
)
@is_admin_or_delegated()
async def setup_slash(
    interaction: discord.Interaction,
    announcement_channel: discord.TextChannel,
    admin_role: discord.Role,
    register_role_1: discord.Role,
    register_role_2: discord.Role = None,
    register_role_3: discord.Role = None
):
    guild_id = str(interaction.guild_id)
    config = load_config()
    
    if guild_id not in config:
        config[guild_id] = {}
        
    # Build list of active tier IDs
    role_ids = [register_role_1.id]
    role_mentions = [register_role_1.mention]
    
    if register_role_2:
        role_ids.append(register_role_2.id)
        role_mentions.append(register_role_2.mention)
    if register_role_3:
        role_ids.append(register_role_3.id)
        role_mentions.append(register_role_3.mention)
        
    config[guild_id]["notification_channel"] = announcement_channel.id
    config[guild_id]["bot_admin_role_id"] = admin_role.id
    config[guild_id]["alert_role_ids"] = role_ids  # Saved as a list array inside configuration files
    
    save_config(config)
    
    embed = discord.Embed(title="⚙️ Configuration Setup Matrix Saved!", color=discord.Color.gold())
    embed.add_field(name="📢 Announcements Channel", value=announcement_channel.mention, inline=True)
    embed.add_field(name="🛡️ Delegated Admin Authority", value=admin_role.mention, inline=True)
    embed.add_field(name="🎭 Saved Registration Multi-Roles", value=", ".join(role_mentions), inline=False)
    
    await interaction.response.send_message(embed=embed)


# --- CONVERTED PLAYER UTILITIES ---

@bot.tree.command(name="set_id", description="Registers your unique Asphalt Game ID and applies saved server roles.")
@app_commands.describe(player_id="Your authentic Asphalt game identity code (e.g., u-4a5b6c)")
async def set_id_slash(interaction: discord.Interaction, player_id: str):
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
    
    # Process multi-role adjustments
    saved_role_ids = config.get(guild_id, {}).get("alert_role_ids", [])
    assigned_mentions = []
    failed_flag = False
    
    if saved_role_ids:
        for r_id in saved_role_ids:
            role = interaction.guild.get_role(int(r_id))
            if role:
                try:
                    await interaction.user.add_roles(role)
                    assigned_mentions.append(role.mention)
                except discord.Forbidden:
                    failed_flag = True
    
    role_msg = f" & assigned roles: {', '.join(assigned_mentions)}" if assigned_mentions else ""
    if failed_flag:
        role_msg += " *(⚠️ Notice: Some roles could not be assigned due to hierarchy settings)*"
        
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
        
        # Loop through saved configurations array to strip roles away
        saved_role_ids = config.get(guild_id, {}).get("alert_role_ids", [])
        removed_names = []
        
        if saved_role_ids:
            for r_id in saved_role_ids:
                role = interaction.guild.get_role(int(r_id))
                if role and role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role)
                        removed_names.append(role.name)
                    except Exception:
                        pass
                        
        role_message = f" and cleared permissions for: **{', '.join(removed_names)}**." if removed_names else "."
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


# --- CONVERTED ADMIN UTILITIES ---

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
    
    embed = discord.Embed(title=f"📋 Registered Profiles: {interaction.guild.name}", color=discord.Color.blue())
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
    prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends?playerId={info['player_id']}&code=TEST12345"
    
    embed = discord.Embed(title="🧪 Isolated Delivery Telemetry Test", description="Testing dynamic string injection interfaces.\n\n**Code:** `TEST12345`", color=discord.Color.orange())
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
    saved_role_ids = config.get(guild_id, {}).get("alert_role_ids", [])
    
    if not target_channel_id:
        return await interaction.response.send_message("⚠️ Announcement pipes are unconfigured. Please run `/setup` first to link structural nodes.", ephemeral=True)
    
    target_channel = bot.get_channel(target_channel_id)
    if not target_channel:
        return await interaction.response.send_message("⚠️ Targeted logging infrastructure channel could not be resolved.", ephemeral=True)
    
    # Generate multi-role notification pings if applicable
    ping_string = " ".join([f"<@&{r_id}>" for r_id in saved_role_ids]) if saved_role_ids else "@everyone"
    
    data = load_data()
    server_data = data.get(guild_id, {})
    
    public_embed = discord.Embed(
        title="🏎️ New Asphalt Legends Redeem Code! 🏎️",
        description=f"🚨 **A new global redemption drop has broken!** 🚨\n\n**Redeem Code:** `{code.upper()}`",
        color=discord.Color.gold()
    )
    public_embed.add_field(
        name="__Claim Framework__",
        value="Registered profiles: Stand by for custom pre-filled 1-click links arriving inside your direct message systems!\n\nManual users claim here: [Gameloft Portal](https://www.gameloft.com/redeem/asphalt-legends)",
        inline=False
    )
    public_embed.set_footer(text="Warning: Active redemption caps or timeline expirations apply!")
    
    # Defer immediate response to manage delivery processing overhead loops safely
    await interaction.response.defer(ephemeral=True)
    await target_channel.send(content=ping_string, embed=public_embed)
    
    success, opted_out, failed = 0, 0, 0
    for u_id, info in server_data.items():
        if not info.get("dm_enabled", True):
            opted_out += 1
            continue
            
        member = interaction.guild.get_member(int(u_id))
        if member:
            prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends?playerId={info['player_id']}&code={code.upper()}"
            dm_embed = discord.Embed(
                title="🏁 Auto-Filled Reward Pipeline 🏁",
                description=f"**Code:** `{code.upper()}`\n\nClick the element below to access the claim portal with your player credentials pre-mapped!",
                color=discord.Color.green()
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