import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
import pymongo
import asyncio
import re
from datetime import datetime
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "asphalt_bot_db")
if not BOT_TOKEN:
    print("Configuration Error: Missing BOT_TOKEN inside Environment Variables configuration arrays.")
if not MONGO_URI:
    print("Configuration Error: Missing MONGO_URI inside Environment Variables configuration arrays.")
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[MONGO_DB_NAME]
    guild_config_col = db["guild_config"]
    scraper_cache_col = db["scraper_cache"]
    mongo_client.server_info()
    print("🟢 MongoDB Cloud Instance Handshake: Success!")
except Exception as db_err:
    print(f"🔴 MongoDB Connection Status: Connection Failed: {db_err}")
intents = discord.Intents.default()
intents.message_content = True

class AsphaltBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.auto_code_scraper_loop.start()
        await self.tree.sync()
        print("🎯 Application Slash Directory Commands synchronized successfully.")
    @tasks.loop(minutes=10.0)
    async def auto_code_scraper_loop(self):
        await self.wait_until_ready()
        print(f"🔍 Background loop trigger: Scanning for Asphalt Legends Unite codes... [{datetime.now().strftime('%H:%M:%S')}]")
        async with aiohttp.ClientSession() as session:
            try:
                target_url = "https://ggrecon.com" 
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                
                async with session.get(target_url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        raw_html = await response.text()
                        soup = BeautifulSoup(raw_html, 'html.parser')
                        potential_codes = []
                        for strong_tag in soup.find_all(['strong', 'b']):
                            text = strong_tag.get_text().strip()
                            if re.match(r'^[A-Z0-9]{4,15}$', text):
                                potential_codes.append(text)
                        for code in set(potential_codes):
                            loop = asyncio.get_event_loop()
                            exists = await loop.run_in_executor(None, lambda: scraper_cache_col.find_one({"code_string": code}))
                            if not exists:
                                new_entry = {
                                    "code_string": code,
                                    "scraped_timestamp": datetime.utcnow()
                                }
                                await loop.run_in_executor(None, lambda: scraper_cache_col.insert_one(new_entry))
                                print(f"✨ New verified Asphalt Legends Unite voucher drop logged into cache tracker: {code}")
                                await self.broadcast_new_code(code)
            except Exception as scraper_err:
                print(f"⚠️ Scraper operation exception pipeline failure tracker warning: {scraper_err}")
    async def broadcast_new_code(self, code: str):
        loop = asyncio.get_event_loop()
        active_guilds = await loop.run_in_executor(None, lambda: list(guild_config_col.find()))
        
        for config in active_guilds:
            channel_id = config.get("channel_id")
            if not channel_id:
                continue
                
            channel = self.get_channel(int(channel_id))
            if not channel:
                continue
            embed = discord.Embed(
                title="🎁 NEW REWARD DROP DETECTED!",
                description=f"A fresh code has been discovered for **Asphalt Legends Unite**!\n\n🔑 **Code:** `{code}`\n\nClick the speed-redeem button below to immediately claim your assets on your game profile page!",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Asphalt Legends Unite Fast-Redeem Engine")
            if config.get("banner_url"):
                embed.set_image(url=config.get("banner_url"))
            if config.get("thumbnail_url"):
                embed.set_thumbnail(url=config.get("thumbnail_url"))
            redeem_url = f"https://gameloft.com{code}&game=asphalt_unite"
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="🚀 Fast Redeem Link", url=redeem_url, style=discord.ButtonStyle.link))
            
            try:
                await channel.send(embed=embed, view=view)
            except Exception:
                pass
bot = AsphaltBot()
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="About the Bot", description="ℹ️ Explains the automated scraper & purpose.", value="about", emoji="ℹ️"),
            discord.SelectOption(label="Player Commands", description="👥 List of commands available for all members.", value="player", emoji="👥"),
            discord.SelectOption(label="Admin Commands", description="🛡️ System overrides & diagnostics configurations.", value="admin", emoji="🛡️")
        ]
        super().__init__(placeholder="Select an information directory category...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        
        if selection == "about":
            embed = discord.Embed(
                title="ℹ️ About Asphalt Legends Unite Fast Redeem Bot",
                description=(
                    "This integration provides an automated system to solve manual lookup bottlenecks "
                    "for limited reward voucher distributions across the server community infrastructure.\n\n"
                    "**How It Works Core Engine Architecture:**\n"
                    "🔹 **Automated Hunter Crawl:** System loops wake up **every 10 minutes** executing background non-blocking scraping cycles tracking indexing channels.\n"
                    "🔹 **Strict Scope Narrowing:** Filters verify all found strings exclusively target **Asphalt Legends Unite** content models parameters.\n"
                    "🔹 **Smart Deduplication Node:** Checks against MongoDB records to drop duplicates before notification delivery, preventing channel notification fatigue.\n"
                    "🔹 **One-Click Delivery Mapping:** Alerts embed prefilled button hyperlinks sending players straight to Gameloft's active portal endpoints (`&game=asphalt_unite`) with zero manual copying needed."
                ),
                color=discord.Color.blue()
            )
        elif selection == "player":
            embed = discord.Embed(
                title="👥 Public Utilities Command Manifest Directory",
                description=(
                    "Regular community members can call these commands inside text permissions spaces:\n\n"
                    "📝 `/help` - Launches this comprehensive interactive dropdown options navigation system map.\n\n"
                    "📜 `/history` - Queries the database to list the **top 10 most recent voucher drops** preserved inside the `scraper_cache` table repository. "
                    "Perfect for checking if you missed items over the weekend."
                ),
                color=discord.Color.green()
            )
        elif selection == "admin":
            embed = discord.Embed(
                title="🛡️ Administrative Operations & Controls Directory",
                description=(
                    "Management systems overrides restricted to designated server roles parameters:\n\n"
                    "🩺 `/diagnose` - Triggers real-time connectivity validation sweeps, profiling satellite latency, MongoDB database cluster authorization checks, and total logs inventory numbers.\n\n"
                    "🎨 `/admin_set_media` - Custom dashboard UI visual canvas adjustments override. "
                    "Expects a direct **drag-and-drop file attachment parameter** (`discord.Attachment`). "
                    "Verifies container types (`image/`) before pinning your custom visual banner or thumbnail directly to new coupon broadcasts layouts."
                ),
                color=discord.Color.red()
            )
            
        await interaction.response.edit_message(embed=embed, view=self.view)
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())

def is_admin_or_delegated():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)
@bot.tree.command(name="help", description="📖 Comprehensive interactive dropdown assistance matrix.")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Asphalt Legends Unite Help Center",
        description="Welcome to the system documentation directory interface launcher. Please select a selection tab category from the dropdown choice box component layout lower controls lane to view exact operational parameters details.",
        color=discord.Color.purple()
    )
    view = HelpView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
@bot.tree.command(name="history", description="📜 Public Tool: Lists the last 10 discovered reward vouchers logs.")
async def history_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    loop = asyncio.get_event_loop()
    past_codes = await loop.run_in_executor(None, lambda: list(scraper_cache_col.find().sort("scraped_timestamp", pymongo.DESCENDING).limit(10)))
    
    if not past_codes:
        return await interaction.followup.send("❌ No historical voucher drops found recorded inside the target database collection tables cache.", ephemeral=True)
        
    embed = discord.Embed(
        title="📜 Historical Reward Drops Manifest Index",
        description="Below are the 10 most recent verified codes discovered by the automated crawler engine. Click the prefilled links to check your claim status.",
        color=discord.Color.blue()
    )
    for idx, item in enumerate(past_codes, 1):
        code_str = item.get("code_string")
        ts = item.get("scraped_timestamp").strftime("%Y-%m-%d %H:%M UTC")
        redeem_url = f"https://gameloft.com{code_str}&game=asphalt_unite"
        embed.add_field(name=f"{idx}. ✨ Code: {code_str}", value=f"Captured: `{ts}`\n🔗 [Direct Link Link Checkout Mapping]({redeem_url})", inline=False)
        
    await interaction.followup.send(embed=embed)
@bot.tree.command(name="diagnose", description="🩺 Admin Tool: Execute infrastructure system checks validations profiles.")
@is_admin_or_delegated()
async def diagnose_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    latency = round(bot.latency * 1000)
    db_status = "🟢 Connected"
    total_entries = 0
    try:
        mongo_client.server_info()
        loop = asyncio.get_event_loop()
        total_entries = await loop.run_in_executor(None, lambda: scraper_cache_col.count_documents({}))
    except Exception as err:
        db_status = f"🔴 Connection Failed: bad auth : authentication failed, full error detail logs data block: {err}"
        
    embed = discord.Embed(title="🛡️ System Diagnostics Status Report", description="Current tracking snapshot across underlying cluster operational metrics.", color=discord.Color.green() if db_status.startswith("🟢") else discord.Color.red())
    embed.add_field(name="📡 Satellite Delay Latency", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="🗄️ MongoDB Connection Status", value=f"`{db_status}`", inline=False)
    embed.add_field(name="🗂️ Live Entries in Cache Collection", value=f"`{total_entries} documents`", inline=True)
    await interaction.followup.send(embed=embed)
@bot.tree.command(name="admin_set_media", description="⚙️ Admin Tool: Custom graphics attachments upload mapping.")
@app_commands.choices(element=[app_commands.Choice(name="Banner", value="banner"), app_commands.Choice(name="Thumbnail", value="thumbnail")])
@is_admin_or_delegated()
async def admin_set_media_slash(interaction: discord.Interaction, element: app_commands.Choice[str], image_file: discord.Attachment):
    if not image_file.content_type or not image_file.content_type.startswith("image/"):
        return await interaction.response.send_message("⚠️ Exception constraints requirements: Target file container structure must be an image type format description asset block maps.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    saved_url = image_file.url
    guild_id = str(interaction.guild_id)
    field = "banner_url" if element.value == "banner" else "thumbnail_url"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: guild_config_col.update_one({"guild_id": guild_id}, {"$set": {field: saved_url, "channel_id": str(interaction.channel_id)}}, upsert=True))
    await interaction.followup.send(f"🎯 Success theme matrix asset overrides saved! The {element.name} has been updated via file upload in this notification channel environment mapping.")

@bot.event
async def on_ready():
    print(f"==========================================\n🤖 Bot application logged in as: {bot.user}\n🛡️ Infrastructure systems running optimally.\n==========================================")

if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("CRITICAL SHUTDOWN CRASH: Execution blocked due to empty system runtime tokens arrays.")
