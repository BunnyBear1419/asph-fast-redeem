import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord
from discord import app_commands
from discord.ext import commands
from pymongo import MongoClient

from alu_tools import setup_alu_tools


PROJECT_NAME = "Shohan's Companion"

# Explicitly configure gateway intents before constructing the Bot.
# Message Content must also be enabled in the Discord Developer Portal.
BOT_INTENTS = discord.Intents.default()
BOT_INTENTS.message_content = True


class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Shohan's Companion is online.")

    def log_message(self, format, *args):
        return


class ResilientHTTPServer(HTTPServer):
    allow_reuse_address = True


def run_web_server():
    try:
        server = ResilientHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), KeepAliveHandler)
        server.serve_forever()
    except OSError as exc:
        print(f"Web keepalive unavailable: {exc}")


threading.Thread(target=run_web_server, daemon=True).start()


MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "myDiscordBot")

if not MONGO_URI:
    raise ValueError("MONGO_URI is required.")

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = mongo_client[MONGO_DB_NAME]

tool_notes_col = db["alu_tool_notes"]
garage_col = db["alu_player_garage"]
favorites_col = db["alu_player_favorites"]
settings_col = db["alu_player_settings"]
usage_col = db["alu_tool_usage"]
redeem_codes_col = db["alu_redeem_codes"]


class AsphaltBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=BOT_INTENTS)

    async def setup_hook(self):
        loop = asyncio.get_running_loop()

        def prepare_indexes():
            tool_notes_col.create_index([("user_id", 1), ("created_at", -1)])
            tool_notes_col.create_index([("reminder_at", 1), ("notified", 1)])
            garage_col.create_index([("user_id", 1), ("category", 1)], unique=True)
            favorites_col.create_index([("user_id", 1), ("tool", 1)], unique=True)
            settings_col.create_index([("user_id", 1), ("setting", 1)], unique=True)
            usage_col.create_index([("user_id", 1), ("tool", 1)], unique=True)
            usage_col.create_index([("user_id", 1), ("last_used_at", -1)])
            redeem_codes_col.create_index("code", unique=True)
            redeem_codes_col.create_index([("verified", 1), ("expires_at", 1)])

        await loop.run_in_executor(None, prepare_indexes)
        await setup_alu_tools(
            self,
            tool_notes_col,
            garage_collection=garage_col,
            favorites_collection=favorites_col,
            settings_collection=settings_col,
            usage_collection=usage_col,
            redeem_collection=redeem_codes_col,
        )
        synced = await self.tree.sync()
        print(f"ALU player-tool dashboard registered ({len(synced)} public commands).")
        print("Persistent garage, favorites, settings, usage, notes, and redeem-code storage initialized.")


bot = AsphaltBot()


@bot.event
async def on_ready():
    print("=" * 48)
    print(f"{PROJECT_NAME} online as {bot.user}")
    print(f"Guilds connected: {len(bot.guilds)}")
    print("=" * 48)


@bot.tree.command(name="dashboard", description="🏁 Open the Asphalt Legends Unite player tools dashboard.")
async def dashboard(interaction: discord.Interaction):
    from alu_tools import CompanionDashboardView, build_dashboard_embed
    cog = bot.get_cog("AsphaltToolsCog")
    view = CompanionDashboardView(cog, interaction.guild_id, interaction.user.id)
    await interaction.response.send_message(embed=build_dashboard_embed(), view=view, ephemeral=True)


@bot.tree.command(name="tools", description="🛠️ Open the Asphalt Legends Unite player tools dashboard.")
async def tools(interaction: discord.Interaction):
    from alu_tools import CompanionDashboardView, build_dashboard_embed
    cog = bot.get_cog("AsphaltToolsCog")
    view = CompanionDashboardView(cog, interaction.guild_id, interaction.user.id)
    await interaction.response.send_message(embed=build_dashboard_embed(), view=view, ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"App command error: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message("⚠️ The tool could not complete that action. Please try again.", ephemeral=True)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN is required.")
    bot.run(token)
