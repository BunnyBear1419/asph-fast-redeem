import discord
from discord import app_commands
from discord.ext import commands

TOOL_DEFINITIONS = {
    "upgrades": {"label": "Car Upgrades Calculator", "emoji": "🔧", "description": "Plan upgrade paths and compare target configurations.", "fields": ["Car", "Current star", "Target star", "Current upgrades"]},
    "comparator": {"label": "Comparator", "emoji": "📊", "description": "Compare two cars or configurations side by side.", "fields": ["Car A", "Car B", "Comparison criteria"]},
    "priority": {"label": "Priority", "emoji": "🏆", "description": "Organize upgrade and garage priorities.", "fields": ["Car", "Goal", "Priority", "Notes"]},
    "calendar": {"label": "Season Calendar", "emoji": "📅", "description": "View season, event, and calendar information.", "fields": ["Season or event", "Date range"]},
    "faq": {"label": "FAQ", "emoji": "❓", "description": "Find answers to frequently asked questions.", "fields": ["Question or topic"]},
    "hunt": {"label": "Hunt Game", "emoji": "🚙", "description": "Estimate races needed for a card or blueprint goal.", "fields": ["Car / hunt", "Current cards", "Target cards", "Drop rate"]},
    "simulation": {"label": "Simulation", "emoji": "🏎️", "description": "Run matchup simulations when verified car data is available.", "fields": ["Car A", "Car B", "Races"]},
    "maps": {"label": "Race Maps", "emoji": "🗺️", "description": "Browse race maps and track variants.", "fields": ["Map or track"]},
    "rating": {"label": "Rating Predictor", "emoji": "🔮", "description": "Analyze a Gauntlet rating against verified reference data.", "fields": ["Gauntlet rating", "Season / context"]},
    "cost": {"label": "Cost Calculator", "emoji": "💸", "description": "Calculate upgrade costs once verified game cost data is connected.", "fields": ["Car", "Current star", "Target star"]},
    "events": {"label": "Event Calculator", "emoji": "🏁", "description": "Plan event stages, attempts, rewards, and targets.", "fields": ["Event", "Stage", "Target reward"]},
    "notes": {"label": "Notes & Reminders", "emoji": "📝", "description": "Create private notes and reminder entries.", "fields": ["Title", "Note", "Reminder"]},
}

TEAL = discord.Color.from_rgb(7, 24, 27)


class ToolInputModal(discord.ui.Modal):
    def __init__(self, key: str):
        tool = TOOL_DEFINITIONS[key]
        super().__init__(title=tool["label"][:45])
        self.key = key
        for index, field_name in enumerate(tool["fields"][:5]):
            self.add_item(discord.ui.TextInput(
                label=field_name[:45],
                custom_id=f"field_{index}",
                required=index == 0,
                max_length=500,
                style=discord.TextStyle.paragraph if field_name in {"Notes", "Question or topic", "Map or track"} else discord.TextStyle.short,
            ))

    async def on_submit(self, interaction: discord.Interaction):
        tool = TOOL_DEFINITIONS[self.key]
        values = []
        for item in self.children:
            value = getattr(item, "value", "").strip()
            if value:
                values.append(f"**{item.label}:** {value}")
        embed = discord.Embed(
            title=f'{tool["emoji"]} {tool["label"]}',
            description=("Your inputs were received and the tool interface is ready.\n\n" + "\n".join(values) +
                         "\n\n⚠️ **Data status:** This repository does not currently contain a verified Asphalt Legends Unite data set for numerical results. No game values are being invented. The calculation/data engine can be connected separately when verified data is available."),
            color=TEAL,
        )
        embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ToolActionView(discord.ui.View):
    def __init__(self, key: str):
        super().__init__(timeout=300)
        self.key = key

    @discord.ui.button(label="Enter Tool Inputs", style=discord.ButtonStyle.primary, emoji="🧰")
    async def inputs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ToolInputModal(self.key))

    @discord.ui.button(label="Back to Tools", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=AsphaltToolsView())


def build_tool_embed(key: str) -> discord.Embed:
    tool = TOOL_DEFINITIONS[key]
    embed = discord.Embed(title=f'{tool["emoji"]} {tool["label"]}', description=tool["description"], color=TEAL)
    embed.add_field(name="Discord Interface", value="Use **Enter Tool Inputs** to open the input form for this tool.", inline=False)
    embed.add_field(name="Planned data layer", value="The interface is separated from the calculation/data engine so verified ALU data can be added without rebuilding the Discord UI.", inline=False)
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed


def build_dashboard_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🏁 Shohan's Companion • Asphalt Legends Unite Tools",
        description=("Select a tool below to open its Discord interface.\n\nThe 12 tools shown here match the current Shohan's Companion tool list. Each tool has its own input flow, while numerical game data remains separate."),
        color=TEAL,
    )
    embed.add_field(name="Available Tools", value="🔧 Upgrades  •  📊 Comparator  •  🏆 Priority  •  📅 Calendar\n❓ FAQ  •  🚙 Hunt  •  🏎️ Simulation  •  🗺️ Maps\n🔮 Rating  •  💸 Cost  •  🏁 Events  •  📝 Notes", inline=False)
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed


class AsphaltToolsSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=data["label"], value=key, emoji=data["emoji"], description=data["description"][:100]) for key, data in TOOL_DEFINITIONS.items()]
        super().__init__(placeholder="Select an Asphalt Legends Unite tool...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=build_tool_embed(self.values[0]), view=ToolActionView(self.values[0]))


class AsphaltToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(AsphaltToolsSelect())


class AsphaltToolsCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot

    @app_commands.command(name="tools", description="🛠️ Open the Asphalt Legends Unite tools dashboard.")
    async def tools(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=build_dashboard_embed(), view=AsphaltToolsView(), ephemeral=True)


async def setup_alu_tools(bot):
    await bot.add_cog(AsphaltToolsCog(bot))
