import discord
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

# Start the web server in a separate background thread
threading.Thread(target=run_web_server, daemon=True).start()
# -----------------------------------------------

# MULTI-SERVER PATH RESTRUCTURE
# Changed from LOCALAPPDATA to standard project directories for seamless cross-platform cloud hosting compatibility.
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

# Dynamic prefix helper function grouped by Server Guild ID
def get_prefix(bot, message):
    if not message.guild:
        return "!"
    config = load_config()
    guild_id = str(message.guild.id)
    return config.get(guild_id, {}).get("prefix", "!")

# Set up intents and dynamically hook prefix getter
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          
bot = commands.Bot(command_prefix=get_prefix, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} | Active Multi-Server Dynamic Prefix Mode enabled.")


# --- GENERAL HELP COMMAND ---

@bot.command(name="commands")
async def show_commands(ctx):
    """Displays all available bot commands and their usage."""
    config = load_config()
    guild_id = str(ctx.guild.id) if ctx.guild else None
    p = config.get(guild_id, {}).get("prefix", "!") if guild_id else "!"
    
    embed = discord.Embed(
        title="🎮 Asphalt Legends Fast Redeem - Bot Commands 🎮",
        description=f"Use the following text commands with the prefix `{p}` to interact with the bot structure:",
        color=discord.Color.purple()
    )
    
    # Player Section
    embed.add_field(
        name="👤 Player Commands 👤",
        value=(
            f"`{p}set_id <your_id>` - Registers your unique Asphalt game ID.\n"
            f"`{p}toggle_dm` - Turn direct message redeem code notifications ON/OFF.\n"
            f"`{p}delete_id` - Completely removes your Asphalt game ID from the bot so you will get no more notifications or DMs.\n"
            f"`{p}commands` - Displays this help box with list of all commands for users & admins."
        ),
        inline=False
    )
    
    # Admin Section
    if ctx.guild and ctx.author.guild_permissions.administrator:
        embed.add_field(
            name="🛠️ Administrator Tools 🛠️",
            value=(
                f"`{p}setprefix <new_prefix>` - Changes the command prefix to whatever you want.\n"
                f"`{p}addchannel` - Sets the current channel for all redeem code announcements.\n"
                f"`{p}addrole <role_id>` - Links a specific role ID to be pinged during redeem drops.\n"
                f"`{p}redeem <code>` - Sends the alert to the designated channel & DMs active players.\n"
                f"`{p}listplayers` - Displays a list of all players who added their Asphalt game ID.\n"
                f"`{p}test_code` - Dispatches a mockup test portal URL to your own DMs.\n"
                f"`{p}clearhistory` - Instantly wipes out the entire user registration database."
            ),
            inline=False
        )
    
    embed.set_footer(text="🎮 Asphalt Legends Fast Redeem 🎮")
    await ctx.send(embed=embed)


# --- PLAYER COMMANDS ---

@bot.command(name="set_id")
async def set_id(ctx, player_id: str = None):
    """Link your Asphalt Player ID. Usage: !set_id YOUR_ID"""
    if not ctx.guild:
        return await ctx.send("⚠️ This command can only be used in a server.")
        
    config = load_config()
    guild_id = str(ctx.guild.id)
    p = config.get(guild_id, {}).get("prefix", "!")
    
    if not player_id:
        return await ctx.send(f"⚠️ Please provide your Asphalt game ID for example:  `{p}set_id u-4a5b6c`")
    
    data = load_data()
    user_id = str(ctx.author.id)
    current_dm_pref = data.get(user_id, {}).get("dm_enabled", True)
    
    data[user_id] = {
        "username": ctx.author.name,
        "player_id": player_id,
        "dm_enabled": current_dm_pref
    }
    save_data(data)
    
    # --- AUTOMATIC ROLE ASSIGNMENT ---
    role_id = config.get(guild_id, {}).get("alert_role_id")
    role_message = ""
    
    if role_id:
        role = ctx.guild.get_role(int(role_id))
        if role:
            try:
                await ctx.author.add_roles(role)
                role_message = f" & assigned the {role.mention} role!"
            except discord.Forbidden:
                role_message = f" (⚠️ Failed to assign role:  Bot lacks permissions or role is above the bot)."
            except Exception as e:
                role_message = f" (⚠️ Failed to assign role: {e})."
        else:
            role_message = " (⚠️ Configured alert role no longer exists in this server)."
    # ---------------------------------
    
    await ctx.send(f"✅ Linked Asphalt game ID: **{player_id}** to {ctx.author.mention}{role_message}\n"
f"🔔 DM Alerts:  {'**ON**' if current_dm_pref else '**OFF**'}")

@bot.command(name="delete_id")
async def delete_id(ctx):
    """Delete your ID from the system and remove the alert role."""
    if not ctx.guild:
        return await ctx.send("⚠️ This command can only be used in a server.")
        
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id in data:
        del data[user_id]
        save_data(data)
        
        # --- AUTOMATIC ROLE REMOVAL ---
        config = load_config()
        guild_id = str(ctx.guild.id)
        role_id = config.get(guild_id, {}).get("alert_role_id")
        role_message = ""
        
        if role_id:
            role = ctx.guild.get_role(int(role_id))
            if role and role in ctx.author.roles:
                try:
                    await ctx.author.remove_roles(role)
                    role_message = f" & your **{role.name}** role has been removed."
                except discord.Forbidden:
                    role_message = " (⚠️ Bot lacks permissions to remove your server role)."
                except Exception:
                    pass
        # ------------------------------
        
        await ctx.send(f"❌ {ctx.author.mention}, your Asphalt game ID has been completely removed{role_message} You will no longer receive notifications or DMs.")
    else:
        await ctx.send("⚠️ You don't have an Asphalt game ID registered.")

@bot.command(name="toggle_dm")
async def toggle_dm(ctx):
    """Toggle code alerts in your DMs."""
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id not in data:
        config = load_config()
        guild_id = str(ctx.guild.id) if ctx.guild else "default"
        p = config.get(guild_id, {}).get("prefix", "!") if ctx.guild else "!"
        return await ctx.send(f"⚠️ Register your ID first using `{p}set_id YOUR_ID` before changing settings.")
    
    current_setting = data[user_id].get("dm_enabled", True)
    data[user_id]["dm_enabled"] = not current_setting
    save_data(data)
    
    status = "ON" if data[user_id]["dm_enabled"] else "OFF"
    await ctx.send(f"🔔 DM code alerts are now **{status}** for {ctx.author.mention}.")


# --- ADMIN COMMANDS ---

@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def set_prefix(ctx, new_prefix: str = None):
    """[Admin] Dynamically alter the script command prefix."""
    if not new_prefix:
        return await ctx.send("⚠️ Please specify a prefix character for example:  `!setprefix ?`")
        
    if len(new_prefix) > 4:
        return await ctx.send("⚠️ The custom prefix cannot be longer than 4 characters.")
        
    config = load_config()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in config:
        config[guild_id] = {}
        
    config[guild_id]["prefix"] = new_prefix
    save_config(config)
    
    await ctx.send(f"⚙️ **Prefix Changed Successfully!**  From now on, use `{new_prefix}` before all commands in this server.")

@bot.command(name="addchannel")
@commands.has_permissions(administrator=True)
async def add_channel(ctx):
    """[Admin] Set this channel as the designated bot notification channel."""
    config = load_config()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in config:
        config[guild_id] = {}
        
    config[guild_id]["notification_channel"] = ctx.channel.id
    save_config(config)
    await ctx.send(f"📢 **Notification Channel Set!**  All public redeem codes announcements will now be sent to {ctx.channel.mention}.")

@bot.command(name="addrole")
@commands.has_permissions(administrator=True)
async def add_role(ctx, role_id: str = None):
    """[Admin] Configure a specific Role ID to be pinged on code drops."""
    config = load_config()
    guild_id = str(ctx.guild.id)
    p = config.get(guild_id, {}).get("prefix", "!")
    
    if not role_id or not role_id.isdigit():
        return await ctx.send(f"⚠️ Please provide a valid numeric Discord Role ID for example:  `{p}addrole 112233445566`")
    
    role = ctx.guild.get_role(int(role_id))
    if not role:
        return await ctx.send("❌ Error: Could not find that Role ID in this server.")
    
    if guild_id not in config:
        config[guild_id] = {}
        
    config[guild_id]["alert_role_id"] = int(role_id)
    save_config(config)
    await ctx.send(f"🔔 **Alert Role Configured!**  The bot will now ping {role.mention} on every public redeem code drop.")

@bot.command(name="clearhistory")
@commands.has_permissions(administrator=True)
async def clear_history(ctx):
    """[Admin] Wipe out the entire player database."""
    save_data({})
    await ctx.send("🧹 **Database fully cleared.**  All player profiles & registered Asphalt game IDs have been deleted globally.")

@bot.command(name="listplayers")
@commands.has_permissions(administrator=True)
async def list_players(ctx):
    """[Admin] View database profiles."""
    data = load_data()
    if not data:
        return await ctx.send("🧹 **Database Empty** 🧹")
    
    embed = discord.Embed(title="📋 Registered Profiles", color=discord.Color.blue())
    for disc_id, info in data.items():
        pref = "✅ Enabled" if info.get("dm_enabled", True) else "❌ Disabled"
        embed.add_field(name=f"User: {info['username']}", value=f"**Game ID: {info['player_id']} | DMs: {pref}**", inline=False)
        
    await ctx.send(embed=embed)

@bot.command(name="test_code")
@commands.has_permissions(administrator=True)
async def test_code(ctx):
    """[Admin] Test command to verify DM formatting."""
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id not in data:
        config = load_config()
        guild_id = str(ctx.guild.id)
        p = config.get(guild_id, {}).get("prefix", "!")
        return await ctx.send(f"⚠️ You need to link your own Asphalt game ID with `{p}set_id` first to test this command.")
    
    test_code_str = "TEST12345"
    info = data[user_id]
    prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends?playerId={info['player_id']}&code={test_code_str}"
    
    embed = discord.Embed(
        title="🧪 Admin Test Redeem Code Delivery 🧪",
        description=f"Testing code delivery script.\n"
f"**Redeem Code:** `{test_code_str}`",
        color=discord.Color.orange()
    )
    embed.add_field(name="__Your Pre-filled Portal Link__", value=f"[Click Here to open your portal!]({prefilled_url})")
    
    try:
        await ctx.author.send(embed=embed)
        await ctx.send("📥 **Success!**  Sent a test redemption link directly to your DMs.")
    except discord.Forbidden:
        await ctx.send("❌ **Error!**  I cannot send you DMs.  Please check your privacy settings for this server.")

@bot.command(name="redeem")
@commands.has_permissions(administrator=True)
async def redeem(ctx, code: str = None):
    """[Admin] Announces a code in the designated channel and blasts DM links."""
    if not code:
        return await ctx.send("⚠️ Please input a redeem code example:  `!redeem RACING2026`")
    
    config = load_config()
    guild_id = str(ctx.guild.id)
    target_channel_id = config.get(guild_id, {}).get("notification_channel")
    role_id = config.get(guild_id, {}).get("alert_role_id")
    
    if not target_channel_id:
        p = config.get(guild_id, {}).get("prefix", "!")
        return await ctx.send(f"⚠️ No notification channel has been set yet!  Go to your desired channel & type `{p}addchannel` first.")
    
    target_channel = bot.get_channel(target_channel_id)
    if not target_channel:
        return await ctx.send("⚠️ The configured notification channel could not be found.")
    
    ping_string = f"<@&{role_id}>" if role_id else "@everyone"
    data = load_data()
    
    public_embed = discord.Embed(
        title="🏎️ __New Asphalt Legends Redeem Code Released!__ 🏎️",
        description=f"🚨 New global redeem code is active! 🚨\n\n"
f"**Redeem Code:** `{code.upper()}`",
        color=discord.Color.gold()
    )
    public_embed.add_field(
        name="__How to Redeem__", 
        value="If you registered your Asphalt game ID with `!set_id`, check your DMs for a custom fast claim link!  Otherwise, claim manually at: [Gameloft Portal](https://www.gameloft.com/redeem/asphalt-legends)", 
        inline=False
    )
    public_embed.set_footer(text="Hurry!  Redemption cap limits might apply!")
    
    await target_channel.send(content=ping_string, embed=public_embed)
    
    if ctx.channel.id != target_channel_id:
        await ctx.send(f"✅ Redeem code broadcasted publicly in {target_channel.mention} & processing player DMs...")
    
    if not data:
        return

    success_count = 0
    opt_out_count = 0
    fail_count = 0
    
    for user_id, info in data.items():
        if not info.get("dm_enabled", True):
            opt_out_count += 1
            continue
            
        member = ctx.guild.get_member(int(user_id))
        if member:
            prefilled_url = f"https://www.gameloft.com/redeem/asphalt-legends?playerId={info['player_id']}&code={code.upper()}"
            
            dm_embed = discord.Embed(
                title="🏁 Your Custom Fast-Redeem Link 🏁",
                description=f"**Code:** `{code.upper()}`\n\n"
f"Click below to open the portal with your Asphalt game ID filled out!",
                color=discord.Color.green()
            )
            dm_embed.add_field(name="__Your Pre-filled Portal Link__", value=f"[Click here to claim rewards Now]({prefilled_url})")
            try:
                await member.send(embed=dm_embed)
                success_count += 1
                await asyncio.sleep(0.5)
            except discord.Forbidden:
                fail_count += 1
        else:
            fail_count += 1
            
    print(f"📊 Delivery Report for code {code.upper()}: Delivered: {success_count} | Opted Out: {opt_out_count} | Failed: {fail_count}")


# Error handler for permission blocks
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You lack the permissions required to utilize admin utilities.")

# --- SECURE TOKEN RUNNER (WITH LOCAL FALLBACK) ---
config = load_config()
# Pulled via environment variable fallback for hosting environments
token = os.environ.get("DISCORD_BOT_TOKEN", "")

if not token:
    if os.path.exists("token.txt"):
        with open("token.txt", "r", encoding="utf-8") as tf:
            token = tf.read().strip()

if not token or token == "YOUR_TOKEN_HERE":
    print("❌ ERROR: Please create a simple text file named 'token.txt' right next to this script and paste your Discord Bot Token inside it or use the DISCORD_BOT_TOKEN env variable!")
else:
    bot.run(token)
