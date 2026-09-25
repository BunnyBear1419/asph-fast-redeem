import discord
from discord import app_commands
from discord.ext import commands


TOOL_DEFINITIONS = {
    "upgrades": {
        "label": "Car Upgrades Calculator",
        "emoji": "🔧",
        "description": "Plan your upgrades and optimize your build.",
    },
    "comparator": {
        "label": "Comparator",
        "emoji": "📊",
        "description": "Compare Between Cars.",
    },
    "priority": {
        "label": "Priority",
        "emoji": "🏆",
        "description": "Manage your priority.",
    },
    "calendar": {
        "label": "Season Calendar",
        "emoji": "📅",
        "description": "Stay on top of events, cups, and seasons.",
    },
    "faq": {
        "label": "FAQ",
        "emoji": "❓",
        "description": "Frequently Asked Questions.",
    },
    "hunt": {
        "label": "Hunt Game",
        "emoji": "🚙",
        "description": "How many times you have to play to get all those cards.",
    },
    "simulation": {
        "label": "Simulation",
        "emoji": "🏎️",
        "description": "Simulations between car winning rate.",
    },
    "maps": {
        "label": "Race Maps",
        "emoji": "🗺️",
        "description": "Full maps and the track variants played on them.",
    },
    "rating": {
        "label": "Rating Predictor",
        "emoji": "🔮",
        "description": "Guess on opponent's config from their Gauntlet rating number.",
    },
    "cost": {
        "label": "Cost Calculator",
        "emoji": "💸",
        "description": "Plan upgrades for your whole garage – credits, parts and garage value to a target star.",
    },
    "events": {
        "label": "Event Calculator",
        "emoji": "🏁",
        "description": "Plan limited-time Spotlight events – stage-by-stage reward simulation.",
    },
    "notes": {
        "label": "Notes & Reminders",
        "emoji": "📝",
        "description": "Your own notes for events, cars and other games – with reminders and notifications.",
    },
}


class AsphaltToolsSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=data["label"],
                value=key,
                emoji=data["emoji"],
                description=data["description"][:100],
            )
            for key, data in TOOL_DEFINITIONS.items()
        ]
        super().__init__(
            placeholder="Select an Asphalt Legends Unite tool...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        tool = TOOL_DEFINITIONS[key]

        embed = discord.Embed(
            title=f'{tool["emoji"]} {tool["label"]}',
            description=tool["description"],
            color=discord.Color.from_rgb(14, 21, 46),
        )
        embed.add_field(
            name="Asphalt Legends Unite",
            value="This tool is available from the Discord Tools Hub.",
            inline=False,
        )
        embed.set_footer(text="Asphalt Legends Unite • Tools")

        await interaction.response.edit_message(
            embed=embed,
            view=AsphaltToolsView(),
        )


class AsphaltToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(AsphaltToolsSelect())


class AsphaltToolsCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot

    @app_commands.command(
        name="tools",
        description="🛠️ Open the Asphalt Legends Unite tools dashboard.",
    )
    async def tools(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏁 Asphalt Legends Unite Tools",
            description=(
                "Select a tool below to open it in Discord.\n\n"
                "This dashboard contains the tools available for Asphalt Legends Unite."
            ),
            color=discord.Color.from_rgb(14, 21, 46),
        )
        embed.set_footer(text="Asphalt Legends Unite • Tools Hub")
        await interaction.response.send_message(
            embed=embed,
            view=AsphaltToolsView(),
            ephemeral=True,
        )


async def setup_alu_tools(bot):
    await bot.add_cog(AsphaltToolsCog(bot))
