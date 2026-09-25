import asyncio
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from bson import ObjectId

from alu_data import load_default_store
from alu_upgrade_resolver import ALUUpgradeResolver

ALU_DATA = load_default_store()
ALU_UPGRADES = ALUUpgradeResolver(ALU_DATA)

TOOL_DEFINITIONS = {
    "upgrades": {"label": "Car Upgrades Calculator", "emoji": "🔧", "description": "Plan an upgrade path from your current configuration to a target.", "fields": ["Car", "Current star", "Target star", "Current rank", "Target rank"]},
    "comparator": {"label": "Comparator", "emoji": "📊", "description": "Compare two cars or user-supplied configurations side by side.", "fields": ["Car A", "Car B", "Stats A", "Stats B", "Comparison criteria"]},
    "priority": {"label": "Priority", "emoji": "🏆", "description": "Organize active events and upgrade goals by the information you provide.", "fields": ["Car / Event", "Goal", "Days left", "Reward", "Progress / rank notes"]},
    "calendar": {"label": "Season Calendar", "emoji": "📅", "description": "Browse season and event information once verified event dates are connected.", "fields": ["Season or event", "Start date", "End date", "Event type", "Filter"]},
    "faq": {"label": "FAQ", "emoji": "❓", "description": "Find answers to frequently asked questions.", "fields": ["Question or topic"]},
    "hunt": {"label": "Hunt Game", "emoji": "🚙", "description": "Estimate attempts needed for a card or blueprint goal using your supplied drop rate.", "fields": ["Car / hunt", "Current cards", "Target cards", "Drop rate"]},
    "simulation": {"label": "Simulation", "emoji": "🏎️", "description": "Prepare race simulations from supplied matchup inputs.", "fields": ["Car A", "Car B", "Track", "Races"]},
    "maps": {"label": "Race Maps", "emoji": "🗺️", "description": "Search and organize race maps and track variants.", "fields": ["Map or track", "Variant", "Direction"]},
    "rating": {"label": "Rating Predictor", "emoji": "🔮", "description": "Analyze a supplied Gauntlet rating against verified reference data.", "fields": ["Gauntlet rating", "Season / context", "Reference rating", "Sample size"]},
    "cost": {"label": "Cost Calculator", "emoji": "💸", "description": "Calculate upgrade costs when verified game cost data is available.", "fields": ["Car", "Current star", "Target star", "Current rank", "Target rank"]},
    "events": {"label": "Event Calculator", "emoji": "🏁", "description": "Plan event stages, attempts, rewards, and targets.", "fields": ["Event", "Stage", "Attempts available", "Target reward", "Current progress"]},
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
                style=discord.TextStyle.paragraph if field_name in {"Stats A", "Stats B", "Progress / rank notes"} else discord.TextStyle.short,
            ))

    async def on_submit(self, interaction: discord.Interaction):
        tool = TOOL_DEFINITIONS[self.key]
        values = {}
        for index, item in enumerate(self.children):
            value = getattr(item, "value", "").strip()
            if value:
                values[tool["fields"][index]] = value
        await interaction.response.send_message(embed=build_tool_result_embed(self.key, values), ephemeral=True)

class NotesHubView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="Add Note", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NoteModal(self.cog))

    @discord.ui.button(label="My Notes", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_notes(interaction)

    @discord.ui.button(label="Back to Tools", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=AsphaltToolsView())


class NoteModal(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="📝 Add Note / Reminder")
        self.cog = cog
        self.title_input = discord.ui.TextInput(label="Title", max_length=100, required=True)
        self.note_input = discord.ui.TextInput(label="Note", style=discord.TextStyle.paragraph, max_length=1500, required=True)
        self.reminder_input = discord.ui.TextInput(
            label="Reminder (optional, UTC)",
            placeholder="YYYY-MM-DD HH:MM",
            max_length=16,
            required=False,
        )
        self.add_item(self.title_input)
        self.add_item(self.note_input)
        self.add_item(self.reminder_input)

    async def on_submit(self, interaction: discord.Interaction):
        reminder_at = None
        raw_reminder = self.reminder_input.value.strip()
        if raw_reminder:
            try:
                reminder_at = datetime.strptime(raw_reminder, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                return await interaction.response.send_message(
                    "⚠️ Reminder format must be YYYY-MM-DD HH:MM in UTC.",
                    ephemeral=True,
                )

        doc = {
            "user_id": str(interaction.user.id),
            "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
            "username": interaction.user.name,
            "title": self.title_input.value.strip(),
            "note": self.note_input.value.strip(),
            "reminder_at": reminder_at,
            "notified": False,
            "created_at": datetime.now(timezone.utc),
        }
        await self.cog.insert_note(doc)
        reminder_text = f" for <t:{int(reminder_at.timestamp())}:F>" if reminder_at else ""
        await interaction.response.send_message(
            f"✅ Note saved.{reminder_text}\n\nUse My Notes to view your saved entries.",
            ephemeral=True,
        )


class NoteSelect(discord.ui.Select):
    def __init__(self, cog, notes):
        self.cog = cog
        self.notes = notes
        options = []
        for note in notes[:25]:
            note_id = str(note["_id"])
            title = note.get("title", "Untitled")[:100]
            description = note.get("note", "").replace("\n", " ")[:100] or "No note text"
            options.append(discord.SelectOption(label=title, value=note_id, description=description))
        super().__init__(placeholder="Select a note to view...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = next((n for n in self.notes if str(n["_id"]) == self.values[0]), None)
        if not selected:
            return await interaction.response.send_message("⚠️ That note is no longer available.", ephemeral=True)
        embed = discord.Embed(
            title=f'📝 {selected.get("title", "Untitled")}',
            description=selected.get("note", "No note text."),
            color=TEAL,
        )
        if selected.get("reminder_at"):
            reminder = selected["reminder_at"]
            if reminder.tzinfo is None:
                reminder = reminder.replace(tzinfo=timezone.utc)
            embed.add_field(name="⏰ Reminder", value=f"<t:{int(reminder.timestamp())}:F>", inline=False)
        embed.set_footer(text=f'Note ID: {selected["_id"]} • 🧪 Shohan\'s Lab  •  🌐 alu.shohanlab.com')
        await interaction.response.edit_message(embed=embed, view=NoteDetailView(self.cog, str(selected["_id"])))


class NotesListView(discord.ui.View):
    def __init__(self, cog, notes):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(NoteSelect(cog, notes))

    @discord.ui.button(label="Add Note", style=discord.ButtonStyle.primary, emoji="➕", row=1)
    async def add_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NoteModal(self.cog))

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_notes_embed(), view=NotesHubView(self.cog))


class NoteDetailView(discord.ui.View):
    def __init__(self, cog, note_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.note_id = note_id

    @discord.ui.button(label="Delete Note", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            deleted = await self.cog.delete_note(interaction.user.id, self.note_id)
        except Exception:
            deleted = False
        if deleted:
            await interaction.response.edit_message(embed=build_notes_embed(), view=NotesHubView(self.cog))
        else:
            await interaction.response.send_message("⚠️ Note not found or could not be deleted.", ephemeral=True)

    @discord.ui.button(label="Back to Notes", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_notes(interaction)


def build_notes_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📝 Notes & Reminders",
        description=(
            "Save private notes to MongoDB and optionally schedule a Discord DM reminder.\n\n"
            "Reminder format: YYYY-MM-DD HH:MM (UTC).\n"
            "Your saved notes are scoped to your Discord account."
        ),
        color=TEAL,
    )
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed


FAQ_CATEGORIES = {
    "GETTING STARTED": ["What is Asphalt United Companion?", "Do I need an account?", "Is this affiliated with Gameloft?", "Does it work on mobile?", "Is my data private?"],
    "GARAGE": ["How do I add a car?", "Can I update a car after adding it?", "Why does the garage matter?"],
    "WALLET": ["What are Credits and Tokens?", "Where do I update my balance?"],
    "PRIORITY PLANNER": ["What does the Priority tool do?", "How is priority calculated?", "What does the Flow Map show?"],
    "SEASON CALENDAR": ["How does the Season Calendar work?", "What does a green dot on an event mean?", "Can I filter by event type?"],
    "CAR INFO": ["What is the Car Info tool?", "Can I compare stock vs max stats?"],
    "DONATIONS": ["How can I support this project?", "Is donating required to use the site?"],
}

FAQ_ANSWERS = {"Is donating required to use the site?": "Absolutely not. Everything is free. Donations just help keep the project alive."}

def build_faq_embed(category=None):
    title = "❓ FAQ" + (f" • {category.title()}" if category else "")
    embed = discord.Embed(title=title, description="20 questions across 7 topics. Select a topic and then a question to read its answer.", color=TEAL)
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed

class FAQCategorySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select an FAQ topic...", options=[discord.SelectOption(label=k.title(), value=k) for k in FAQ_CATEGORIES])
    async def callback(self, interaction):
        await interaction.response.edit_message(embed=build_faq_embed(self.values[0]), view=FAQQuestionView(self.values[0]))

class FAQQuestionSelect(discord.ui.Select):
    def __init__(self, category):
        self.category = category
        super().__init__(placeholder="Select a question...", options=[discord.SelectOption(label=q[:100], value=q) for q in FAQ_CATEGORIES[category]])
    async def callback(self, interaction):
        question = self.values[0]
        answer = FAQ_ANSWERS.get(question, "The answer text for this FAQ entry was not included in the FAQ content supplied for this implementation.")
        embed = discord.Embed(title="❓ " + question, description=answer, color=TEAL)
        embed.add_field(name="Topic", value=self.category.title(), inline=False)
        embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
        await interaction.response.edit_message(embed=embed, view=FAQQuestionView(self.category))

class FAQQuestionView(discord.ui.View):
    def __init__(self, category):
        super().__init__(timeout=300)
        self.add_item(FAQQuestionSelect(category))
    @discord.ui.button(label="FAQ Topics", style=discord.ButtonStyle.secondary, emoji="📚", row=1)
    async def topics(self, interaction, button):
        await interaction.response.edit_message(embed=build_faq_embed(), view=FAQView())
    @discord.ui.button(label="Back to Tools", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def back(self, interaction, button):
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=AsphaltToolsView())

class FAQView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(FAQCategorySelect())
    @discord.ui.button(label="Back to Tools", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def back(self, interaction, button):
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=AsphaltToolsView())

def _number(value):
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def build_tool_result_embed(key, values):
    tool = TOOL_DEFINITIONS[key]
    embed = discord.Embed(title=f'{tool["emoji"]} {tool["label"]} — Result', color=TEAL)
    lines = []
    if key == "upgrades":
        current = _number(values.get("Current rank"))
        target = _number(values.get("Target rank"))
        if current is not None and target is not None:
            lines.append(f"Requested rank change: **{target-current:+g}**")
        lines.append("Upgrade path captured.")
        if values.get("Car"):
            matches = ALU_DATA.search_cars(values["Car"])
            if matches:
                car = matches[0]
                lines.append(f"Data match: **{car.name}** ({car.verification.value}).")
                target_star = int(_number(values.get("Target star")) or 0)
                if target_star > 0:
                    resolution = ALU_UPGRADES.resolve(car.id, target_star, 1)
                    lines.append(f"Upgrade resolver: **{resolution.status}** — {resolution.reason}")
                    if not resolution.can_calculate:
                        lines.append("No game-value cost/rank/parts calculation was returned because the source mapping is not verified.")
        days = _number(values.get("Days left"))
        lines.append(f"Days remaining: **{days:g}**" if days is not None else "Add days remaining to support urgency calculations.")
        lines.append("Priority factors: time remaining, reward, progress, and rank readiness.")
    elif key == "calendar":
        lines.append("Season/event request captured.")
        lines.append("Exact event dates require a verified season calendar data source.")
    elif key == "hunt":
        current, target, drop = map(_number, [values.get("Current cards"), values.get("Target cards"), values.get("Drop rate")])
        if current is not None and target is not None and drop is not None and drop > 0:
            missing=max(0,target-current)
            lines += [f"Cards needed: **{missing:g}**", f"Expected attempts at {drop:g}%: **{missing/(drop/100):.1f}**"]
        else:
            lines.append("Enter current cards, target cards, and drop rate (%) for an estimate.")
    elif key == "simulation":
        races=_number(values.get("Races"))
        lines.append(f"Races requested: **{races:g}**" if races is not None else "Enter a race count.")
        lines.append("Game-accurate outcomes require verified car, track, and performance data.")
    elif key == "maps":
        lines.append(f"Map: **{values.get('Map or track','—')}**")
        lines.append(f"Variant: **{values.get('Variant','—')}**")
    elif key == "rating":
        rating=_number(values.get("Gauntlet rating"))
        reference=_number(values.get("Reference rating"))
        if rating is not None and reference is not None:
            lines.append(f"Rating difference from supplied reference: **{rating-reference:+g}**")
        else:
            lines.append("Supply a rating and reference value for a factual comparison.")
        lines.append("No future rating outcome is guessed without verified historical data.")
    elif key == "cost":
        lines.append("Cost request captured.")
        if values.get("Car"):
            matches = ALU_DATA.search_cars(values["Car"])
            if matches:
                car = matches[0]
                target_star = int(_number(values.get("Target star")) or 0)
                resolution = ALU_UPGRADES.resolve(car.id, target_star, 1) if target_star > 0 else None
                lines.append(f"Data match: **{car.name}** ({car.verification.value}).")
                if resolution:
                    lines.append(f"Upgrade resolver: **{resolution.status}** — {resolution.reason}")
                    if not resolution.can_calculate:
                        lines.append("Exact Credits, Tokens, XP, and Import Parts are withheld until the source-table mapping is explicitly verified.")
            else:
                lines.append("Car was not found in the centralized ALU data layer.")
        else:
            lines.append("Enter a car to check the centralized upgrade resolver.")
    elif key == "events":
        attempts=_number(values.get("Attempts available"))
        progress=_number(values.get("Current progress"))
        if attempts is not None: lines.append(f"Attempts available: **{attempts:g}**")
        if progress is not None: lines.append(f"Current progress: **{progress:g}**")
        lines.append("Exact reward/stage calculations require verified event data.")
    else:
        lines.append("Inputs received.")
    embed.description="\n\n".join(lines)
    if values:
        embed.add_field(name="Inputs", value="\n".join(f"**{k}:** {v}" for k,v in values.items())[:1024], inline=False)
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed


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
    status = ALU_DATA.data_status()
    embed.add_field(name="ALU data layer", value=(f"Centralized source registry active • {status[\"cars\"]} cars • {status[\"upgrade_stages\"]} upgrade stages • {status[\"tracks\"]} tracks • {status[\"events\"]} events.\\nGame values remain unavailable until imported and verified."), inline=False)
    embed.add_field(name="Planned data layer", value="The interface is separated from the calculation/data engine so verified ALU data can be added or refreshed without rebuilding the Discord UI.", inline=False)


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
        key = self.values[0]
        if key == "faq":
            await interaction.response.edit_message(embed=build_faq_embed(), view=FAQView())
            return
        await interaction.response.edit_message(embed=build_tool_embed(key), view=ToolActionView(key))


class AsphaltToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(AsphaltToolsSelect())


class AsphaltToolsCog(commands.Cog):
    def __init__(self, bot: discord.Client, notes_collection):
        self.bot = bot
        self.notes_collection = notes_collection
        self.reminder_loop.start()

    async def insert_note(self, doc):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.notes_collection.insert_one(doc))

    async def show_notes(self, interaction: discord.Interaction):
        loop = asyncio.get_event_loop()
        user_id = str(interaction.user.id)
        notes = await loop.run_in_executor(
            None,
            lambda: list(self.notes_collection.find({"user_id": user_id}).sort("created_at", -1).limit(25)),
        )
        embed = discord.Embed(
            title="📋 My Notes",
            description=f"You have {len(notes)} saved note(s). Select one below to view or delete it.",
            color=TEAL,
        )
        if not notes:
            embed.description = "You have no saved notes yet."
            view = NotesHubView(self)
        else:
            view = NotesListView(self, notes)
        await interaction.response.edit_message(embed=embed, view=view)

    async def delete_note(self, user_id, note_id):
        loop = asyncio.get_event_loop()
        try:
            object_id = ObjectId(note_id)
        except Exception:
            return False
        result = await loop.run_in_executor(
            None,
            lambda: self.notes_collection.delete_one({"_id": object_id, "user_id": str(user_id)}),
        )
        return result.deleted_count == 1

    @tasks.loop(seconds=30)
    async def reminder_loop(self):
        now = datetime.now(timezone.utc)
        loop = asyncio.get_event_loop()
        reminders = await loop.run_in_executor(
            None,
            lambda: list(self.notes_collection.find({
                "reminder_at": {"$lte": now},
                "notified": {"$ne": True},
            }).limit(50)),
        )
        for note in reminders:
            user = self.bot.get_user(int(note["user_id"]))
            if user is None:
                try:
                    user = await self.bot.fetch_user(int(note["user_id"]))
                except Exception:
                    user = None
            if user is not None:
                try:
                    await user.send(
                        f"Shohan's Companion Reminder\n\n"
                        f"{note.get('title', 'Reminder')}\n{note.get('note', '')}"
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await loop.run_in_executor(
                None,
                lambda note_id=note["_id"]: self.notes_collection.update_one(
                    {"_id": note_id}, {"$set": {"notified": True, "notified_at": now}}
                ),
            )

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.reminder_loop.cancel()

    @app_commands.command(name="tools", description="🛠️ Open the Asphalt Legends Unite tools dashboard.")
    async def tools(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=build_dashboard_embed(), view=AsphaltToolsView(), ephemeral=True)

    @app_commands.command(name="notes", description="📝 Open your private Notes & Reminders.")
    async def notes(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=build_notes_embed(), view=NotesHubView(self), ephemeral=True)


async def setup_alu_tools(bot, notes_collection):
    await bot.add_cog(AsphaltToolsCog(bot, notes_collection))
