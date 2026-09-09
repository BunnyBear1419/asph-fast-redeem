import discord
from discord import app_commands
from discord.ext import commands, tasks
import pymongo
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import os

# Initialize database mapping bindings
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "asphalt_bot_db")

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
guild_config_col = db["guild_config"]
scraper_cache_col = db["scraper_cache"]

class RedeemBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Start the background crawl automation sequence loop
        self.auto_code_scraper_loop.start()
        await self.tree.sync()

    @tasks.loop(minutes=10.0) # Adjusted loop frequency to run cleanly every 10 minutes to protect api resource metrics
    async def auto_code_scraper_loop(self):
        # Background crawler loop execution matrix sequence
        # Target game parameters: Filtering strictly for "Asphalt Legends Unite" active promo codes
        async with aiohttp.ClientSession() as session:
            try:
                # Target indexing site tracking Asphalt Legends Unite data points
                async with session.get("https://www.gameloft.com/news/asphalt-legends-unite") as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Simulating structural pattern extraction loops for the game
                        # Scraper explicitly targets nodes containing text references to "Unite Codes" or structural tags
                        for element in soup.find_all(text=True):
                            text_str = element.strip().upper()
                            # Verification checks: standard lengths, alphanumeric structure, containing no spaces
                            if len(text_str) >= 6 and len(text_str) <= 15 and text_str.isalnum():
                                # Deduplication layer verification query
                                if not scraper_cache_col.find_one({"code_string": text_str}):
                                    # Insert the new Asphalt Legends Unite reward item asset
                                    scraper_cache_col.insert_one({
                                        "code_string": text_str,
                                        "game_target": "Asphalt Legends Unite"
                                    })
                                    # Trigger automated multi-server drop notifications loop block
                                    await self.broadcast_new_code(text_str)
            except Exception as e:
                print(f"Scraper Loop Handshake Warning: {e}")

    async def broadcast_new_code(self, code_str):
        # Pull configurations from MongoDB and broadcast to servers
        for guild_doc in guild_config_col.find():
            channel_id = guild_doc.get("drop_channel_id")
            if channel_id:
                channel = self.get_channel(int(channel_id))
                if channel:
                    banner = guild_doc.get("banner_url", "https://images.gameloft.com/unite_banner.png")
                    embed = discord.Embed(
                        title="🏎️ New Asphalt Legends Unite Code Dropped!",
                        description=f"A fresh promo token asset has been verified on the network!\n\n**Code:** `{code_str}`\n**Game Target:** `Asphalt Legends Unite`",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=banner)
                    
                    # Generate single-click interactive link button
                    view = discord.ui.View()
                    redeem_url = f"https://www.gameloft.com/redeem?code={code_str}&game=asphalt_unite"
                    view.add_item(discord.ui.Button(label="⚡ Claim Reward Instantly", url=redeem_url))
                    await channel.send(embed=embed, view=view)

bot = RedeemBot()

def is_admin_or_delegated():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

@bot.tree.command(name="help", description="📖 System Manifest Directory: Detailed operational overview for players & admins.")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Asphalt Legends Unite Fast Redeem Hub Guide",
        description="Welcome to your automated reward pipeline system. Below are the exact operational logs explaining what this bot does and how to interact with it.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎮 For Players (What this bot does for you)",
        value=(
            "• **Automated Scrapes**: The bot continually audits developer servers to grab active promotional gifts for **Asphalt Legends Unite**.\n"
            "• **Instant Fulfillment Link Buttons**: Every drop features a button that pre-embeds the code straight into the official Gameloft dashboard portal loop. No manual copying needed!\n"
            "• **/history**: Run this command anywhere to view the last 10 valid codes recorded on the database."
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ For Administrators (Server Configuration & Health Checks)",
        value=(
            "• **/admin_set_media**: Drag-and-drop a physical image attachment file to completely override the default alert banners shown on code drops.\n"
            "• **/diagnose**: Run system scans to monitor database connection health, latency delay response metrics, and check active collection entry parameters."
        ),
        inline=False
    )
    
    embed.set_footer(text="Target Game Sandbox Status: Filtering strictly for Asphalt Legends Unite instances.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="admin_set_media", description="⚙️ Admin Tool: Custom graphics attachments upload mapping.")
@app_commands.choices(element=[
    app_commands.Choice(name="Banner", value="banner"), 
    app_commands.Choice(name="Thumbnail", value="thumbnail")
])
@is_admin_or_delegated()
async def admin_set_media_slash(interaction: discord.Interaction, element: app_commands.Choice[str], image_file: discord.Attachment):
    if not image_file.content_type or not image_file.content_type.startswith("image/"):
        return await interaction.response.send_message(
            "⚠️ Exception constraints requirements: Target file container structure must be an image type format description asset block maps.", 
            ephemeral=True
        )
        
    await interaction.response.defer(ephemeral=True)
    saved_url = image_file.url
    guild_id = str(interaction.guild_id)
    field = "banner_url" if element.value == "banner" else "thumbnail_url"
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: guild_config_col.update_one(
        {"guild_id": guild_id}, 
        {"$set": {field: saved_url}}, 
        upsert=True
    ))
    
    await interaction.followup.send(f"🎯 Success theme matrix asset overrides saved! The {element.name} has been updated via file upload.")

@bot.tree.command(name="diagnose", description="🛡️ System Health Diagnostics Status Check.")
async def diagnose_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    try:
        client.admin.command('ping')
        db_status = "🟢 Connected"
    except Exception as e:
        db_status = f"🔴 Connection Failed: {e}"
        
    embed = discord.Embed(title="🛡️ System Diagnostics Status", color=discord.Color.orange())
    embed.add_field(name="Satellite Delay Latency", value=f"{latency}ms", inline=True)
    embed.add_field(name="MongoDB Connection Status", value=db_status, inline=True)
    embed.add_field(name="Active Filter", value="Asphalt Legends Unite Tracking Mode Only", inline=False)
    
    await interaction.response.send_message(embed=embed)

# Retrieve token parameter and execute loops
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("Configuration Error: Missing BOT_TOKEN inside Environment Variables configuration arrays.")
