import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks
from bson import ObjectId

from alu_data import load_default_store
from alu_upgrade_resolver import ALUUpgradeResolver
from alu_calculators import number, parse_stats, compare_stats, hunt_estimate, priority_plan, race_model, rating_difference, event_plan, search_summary
from alu_planners import blueprint_plan, star_up_plan, upgrade_stage_plan, import_parts_plan, rank_progress, garage_progress, event_reward_plan, compare_cars, evo_compare
from alu_health import audit_data, verification_summary
from alu_tool_engine import resolve_tool_key, search_tools

ALU_DATA = load_default_store()
ALU_UPGRADES = ALUUpgradeResolver(ALU_DATA)

TOOL_DEFINITIONS = {
    "upgrades": {"label": "Car Upgrades Calculator", "emoji": "🔧", "description": "Plan an upgrade path from your current configuration to a target.", "fields": ["Car", "Current star", "Target star", "Current rank", "Target rank"]},
    "comparator": {"label": "Comparator", "emoji": "📊", "description": "Compare two cars or user-supplied configurations side by side.", "fields": ["Car A", "Car B", "Stats A", "Stats B", "Comparison criteria"]},
    "priority": {"label": "Priority", "emoji": "🏆", "description": "Organize active events and upgrade goals by the information you provide.", "fields": ["Car / Event", "Goal", "Days left", "Reward", "Progress / rank notes"]},
    "calendar": {"label": "Season Calendar", "emoji": "📅", "description": "Browse season and event information once verified event dates are connected.", "fields": ["Season or event", "Start date", "End date", "Event type", "Filter"]},
    "faq": {"label": "FAQ", "emoji": "❓", "description": "Find answers to frequently asked questions.", "fields": ["Question or topic"]},
    "hunt": {"label": "Hunt Game", "emoji": "🚙", "description": "Estimate attempts needed for a card or blueprint goal using your supplied drop rate.", "fields": ["Car / hunt", "Current cards", "Target cards", "Drop rate"]},
    "simulation": {"label": "Simulation", "emoji": "🏎️", "description": "Run a transparent input-only matchup model from supplied stats.", "fields": ["Car A", "Car B", "Stats A", "Stats B", "Races"]},
    "maps": {"label": "Race Maps", "emoji": "🗺️", "description": "Search and organize race maps and track variants.", "fields": ["Map or track", "Variant", "Direction"]},
    "rating": {"label": "Rating Predictor", "emoji": "🔮", "description": "Analyze a supplied Gauntlet rating against verified reference data.", "fields": ["Gauntlet rating", "Season / context", "Reference rating", "Sample size"]},
    "cost": {"label": "Cost Calculator", "emoji": "💸", "description": "Calculate upgrade costs when verified game cost data is available.", "fields": ["Car", "Current star", "Target star", "Current rank", "Target rank"]},
    "events": {"label": "Event Calculator", "emoji": "🏁", "description": "Plan event stages, attempts, rewards, and targets.", "fields": ["Event", "Stage", "Attempts available", "Target reward", "Current progress"]},
    "notes": {"label": "Notes & Reminders", "emoji": "📝", "description": "Create private notes and reminder entries.", "fields": ["Title", "Note", "Reminder"]},
    "blueprints": {"label": "Blueprint Planner", "emoji": "🧩", "description": "Calculate blueprint gaps from values you provide.", "fields": ["Car", "Current cards", "Target cards", "Owned cards", "Wild Cards"]},
    "upgrade_planner": {"label": "Upgrade Planner", "emoji": "🛠️", "description": "Build a verified upgrade-stage path when verified stage data exists.", "fields": ["Car", "Current star", "Current stage", "Target star", "Target stage"]},
    "import_parts": {"label": "Import Parts Planner", "emoji": "🔩", "description": "Compare current and target part counts.", "fields": ["Car", "Current parts", "Target parts"]},
    "rank": {"label": "Rank Calculator", "emoji": "📈", "description": "Measure supplied rank progress toward a target.", "fields": ["Car", "Current rank", "Target rank"]},
    "star_up": {"label": "Star-Up Planner", "emoji": "⭐", "description": "Calculate star-up card requirements from a supplied requirement table.", "fields": ["Car", "Current star", "Target star", "Requirements", "Current cards"]},
    "garage_progress": {"label": "Garage Progress Tracker", "emoji": "🚗", "description": "Track supplied garage completion totals.", "fields": ["Completed", "Total", "Goal", "Category"]},
    "event_rewards": {"label": "Event Reward Planner", "emoji": "🎁", "description": "Estimate reward progress from supplied attempt and reward values.", "fields": ["Event", "Attempts", "Reward per attempt", "Target reward", "Current reward"]},
    "evo": {"label": "EVO / Build Comparison", "emoji": "🧬", "description": "Compare verified EVO profiles without inventing missing values.", "fields": ["Car A", "Car B", "Context"]},
    "car_compare": {"label": "Car Comparison", "emoji": "🏎️", "description": "Compare centralized car records and their provenance.", "fields": ["Car A", "Car B", "Stats A", "Stats B", "Criteria"]},
    "data_health": {"label": "ALU Data Health", "emoji": "🩺", "description": "Inspect ALU data freshness, provenance, verification, and source-use state.", "fields": ["Report type"]},
    "search": {"label": "Global ALU Search", "emoji": "🔎", "description": "Search centralized cars, tracks, or events without leaving the dashboard.", "fields": ["Search type", "Query"]},
    "garage": {"label": "My Garage Snapshot", "emoji": "🚗", "description": "Analyze your current garage progress using values you provide.", "fields": ["Car / category", "Current progress", "Goal", "Notes"]},
    "redeem": {"label": "Redeem Center", "emoji": "🎁", "description": "Verified ALU redeem-code information when code records are available.", "fields": ["Code or search"]},
    "favorites": {"label": "Favorites & Recent Tools", "emoji": "⭐", "description": "Quick-access hub for your most-used tools.", "fields": ["Tool name"]},
    "settings": {"label": "Player Settings", "emoji": "⚙️", "description": "Configure companion preferences and notification behavior.", "fields": ["Setting", "Value"]},
}

TEAL = discord.Color.from_rgb(7, 24, 27)


class ToolInputModal(discord.ui.Modal):
    def __init__(self, key: str, cog=None, user_id=None):
        tool = TOOL_DEFINITIONS[key]
        super().__init__(title=tool["label"][:45])
        self.key = key
        self.cog = cog
        self.user_id = str(user_id) if user_id is not None else None
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
        if self.cog is not None and self.user_id is not None:
            await self.cog.record_tool_use(self.user_id, self.key)
            await self.cog.persist_tool_state(self.user_id, self.key, values)
            embed = await self.cog.build_personal_result_embed(self.key, values, self.user_id)
        else:
            embed = build_tool_result_embed(self.key, values)
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        await interaction.response.edit_message(
            embed=build_dashboard_embed(),
            view=CompanionDashboardView(self.cog, interaction.guild_id, interaction.user.id),
        )


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

FAQ_ANSWERS = {
    "What is Asphalt United Companion?": "A fan-made toolkit for organizing ALU car, event, track, upgrade, and planning information.",
    "Do I need an account?": "Only features that save data need your Discord/site identity. Reference tools can operate from supplied inputs.",
    "Is this affiliated with Gameloft?": "No. It is an independent fan project.",
    "Does it work on mobile?": "The Discord interface is designed around Discord's supported mobile and desktop UI controls.",
    "Is my data private?": "Saved notes are scoped to your Discord user ID. Do not put secrets or sensitive information into notes.",
    "How do I add a car?": "Use the garage/profile workflow when available; centralized reference data is separate from personal garage data.",
    "Can I update a car after adding it?": "Yes. Personal garage values should be treated as user-maintained state and can be updated without changing reference data.",
    "Why does the garage matter?": "Garage state lets planning tools compare your current progress with goals.",
    "What are Credits and Tokens?": "They are in-game currencies. Exact balances are personal values and must come from your supplied/account-synced data.",
    "Where do I update my balance?": "Use the personal garage/wallet workflow and enter the current values you actually have.",
    "What does the Priority tool do?": "It applies a transparent planning heuristic to time, reward, progress, and readiness inputs.",
    "How is priority calculated?": "The current heuristic weights urgency 35%, reward 25%, progress 20%, and readiness 20%. It is not an official game formula.",
    "What does the Flow Map show?": "It is intended to visualize planning dependencies and goals; it does not invent game requirements.",
    "How does the Season Calendar work?": "It searches the centralized event records. Event dates are shown only when those records are loaded and appropriately verified.",
    "What does a green dot on an event mean?": "Use the calendar's verification/source state rather than assuming a color represents current game data.",
    "Can I filter by event type?": "Yes, once event records are loaded, the event type can be used as a filter.",
    "What is the Car Info tool?": "It is a reference lookup for car records and their provenance.",
    "Can I compare stock vs max stats?": "Yes when both verified records are available; otherwise the tool can compare values you supply.",
    "How can I support this project?": "You can use the project's published support/donation options if provided by the site owner.",
    "Is donating required to use the site?": "Absolutely not. Everything is free. Donations are optional."
}

def build_faq_embed(category=None):
    title = "❓ FAQ" + (f" • {category.title()}" if category else "")
    embed = discord.Embed(title=title, description="20 questions across 7 topics. Select a topic and then a question to read its answer.", color=TEAL)
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed

class FAQCategorySelect(discord.ui.Select):
    def __init__(self, cog=None):
        self.cog = cog
        super().__init__(placeholder="Select an FAQ topic...", options=[discord.SelectOption(label=k.title(), value=k) for k in FAQ_CATEGORIES])
    async def callback(self, interaction):
        await interaction.response.edit_message(embed=build_faq_embed(self.values[0]), view=FAQQuestionView(self.values[0], cog=self.cog))

class FAQQuestionSelect(discord.ui.Select):
    def __init__(self, category, cog=None):
        self.category = category
        self.cog = cog
        super().__init__(placeholder="Select a question...", options=[discord.SelectOption(label=q[:100], value=q) for q in FAQ_CATEGORIES[category]])
    async def callback(self, interaction):
        question = self.values[0]
        answer = FAQ_ANSWERS.get(question, "The answer text for this FAQ entry was not included in the FAQ content supplied for this implementation.")
        embed = discord.Embed(title="❓ " + question, description=answer, color=TEAL)
        embed.add_field(name="Topic", value=self.category.title(), inline=False)
        embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
        await interaction.response.edit_message(embed=embed, view=FAQQuestionView(self.category, cog=self.cog))

class FAQQuestionView(discord.ui.View):
    def __init__(self, category, cog=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(FAQQuestionSelect(category, cog=self.cog))
    @discord.ui.button(label="FAQ Topics", style=discord.ButtonStyle.secondary, emoji="📚", row=1)
    async def topics(self, interaction, button):
        await interaction.response.edit_message(embed=build_faq_embed(), view=FAQView(cog=getattr(self, "cog", None)))
    @discord.ui.button(label="Back to Tools", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def back(self, interaction, button):
        if self.cog is not None:
            view = CompanionDashboardView(self.cog, interaction.guild_id, interaction.user.id)
        else:
            view = AsphaltToolsView()
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=view)

class FAQView(discord.ui.View):
    def __init__(self, cog=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(FAQCategorySelect(cog=self.cog))
    @discord.ui.button(label="Back to Tools", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def back(self, interaction, button):
        if self.cog is not None:
            view = CompanionDashboardView(self.cog, interaction.guild_id, interaction.user.id)
        else:
            view = AsphaltToolsView()
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=view)

def _number(value):
    return number(value)


def _lines_for_stats(rows):
    lines=[]
    for row in rows:
        a="—" if row["a"] is None else f'{row["a"]:g}'
        b="—" if row["b"] is None else f'{row["b"]:g}'
        delta="—" if row["delta"] is None else f'{row["delta"]:+g}'
        pct="—" if row["percent"] is None else f'{row["percent"]:+.1f}%'
        lines.append(f'**{row["stat"].replace("_"," ").title()}:** {a} → {b} ({delta}, {pct})')
    return lines


def build_tool_result_embed(key, values):
    tool=TOOL_DEFINITIONS[key]
    embed=discord.Embed(title=f'{tool["emoji"]} {tool["label"]} — Result', color=TEAL)
    lines=[]
    try:
        if key in {"upgrades","cost"}:
            cars=ALU_DATA.search_cars(values.get("Car", ""))[:1]
            if not cars:
                lines.append("Car not found in the centralized ALU data layer.")
            else:
                c=cars[0]
                lines.append(f'Data match: **{c.name}** • verification: **{c.verification.value}** • source: **{c.source}**')
                if c.verification.value != "verified_current":
                    lines.append("Exact game-value calculations are withheld because this record is not verified_current.")
                else:
                    current_star=int(number(values.get("Current star")) or 1)
                    target_star=int(number(values.get("Target star")) or current_star)
                    current_stage=int(number(values.get("Current stage")) or 0)
                    target_stage=int(number(values.get("Target stage")) or 4)
                    plan=[]
                    for star in range(current_star,target_star+1):
                        first=current_stage+1 if star==current_star else 1
                        for stage in range(first,target_stage+1):
                            row=ALU_DATA.upgrade_stage(c.id,star,stage)
                            if row is None or row.verification.value != "verified_current":
                                plan=[]; break
                            plan.append(row)
                        if not plan and target_star>=current_star: break
                    if plan:
                        totals={}
                        for row in plan:
                            for k,v in row.costs.items(): totals[k]=totals.get(k,0)+int(v)
                        lines.append(f'Verified stages found: **{len(plan)}**')
                        lines.append("Totals: " + ", ".join(f'**{k} {v:,}**' for k,v in totals.items()))
                    else:
                        lines.append("No complete verified stage path is loaded yet; no invented costs are shown.")
        elif key=="comparator":
            rows=compare_stats(parse_stats(values.get("Stats A")),parse_stats(values.get("Stats B")))
            lines.extend(_lines_for_stats(rows) or ["Enter Stats A and Stats B as stat=value pairs to compare them."])
        elif key=="priority":
            r=priority_plan(_number(values.get("Days left")),_number(values.get("Reward")),_number(values.get("Progress / rank notes")),_number(values.get("Readiness")))
            lines.append(f'Planning score: **{r["score"]:.2f}/100** (heuristic)')
            lines.append(" • ".join(f'{k.title()}: {v:.1f}' for k,v in r.items() if k!="score"))
        elif key=="calendar":
            rows=search_summary(ALU_DATA,"events",values.get("Season or event",values.get("Event","")))
            lines.extend([f'**{x["name"]}** • {x["verification"]} • source: {x["source"]}' for x in rows] or ["No matching centralized event records are loaded."])
        elif key=="hunt":
            r=hunt_estimate(_number(values.get("Current cards")) or 0,_number(values.get("Target cards")) or 0,_number(values.get("Drop rate")) or 0)
            lines += [f'Cards needed: **{r["missing"]:g}**',f'Expected attempts at {r["drop_rate"]:g}%: **{r["expected_attempts"]:.1f}**']
        elif key=="simulation":
            r=race_model(parse_stats(values.get("Stats A")),parse_stats(values.get("Stats B")),int(_number(values.get("Races")) or 1))
            lines += [f'Shared stats: **{", ".join(r["shared_stats"])}**',f'Input-model share: A **{r["a_share"]*100:.1f}%** • B **{r["b_share"]*100:.1f}%**',f'Expected wins: A **{r["expected_a_wins"]:.1f}** • B **{r["expected_b_wins"]:.1f}**']
            lines.append("This is an input-only model, not a game-physics simulation.")
        elif key=="maps":
            rows=search_summary(ALU_DATA,"tracks",values.get("Map or track", ""))
            lines.extend([f'**{x["name"]}** • {x["verification"]} • source: {x["source"]}' for x in rows] or ["No matching centralized track records are loaded."])
        elif key=="rating":
            r=rating_difference(_number(values.get("Gauntlet rating")) or 0,_number(values.get("Reference rating")) or 0)
            lines.append(f'Supplied rating difference: **{r["difference"]:+g}**')
            lines.append("This compares supplied values only; it does not predict future results.")
        elif key=="events":
            r=event_plan(_number(values.get("Attempts available")),_number(values.get("Current progress")),_number(values.get("Target reward")))
            lines.append(f'Attempts available: **{r["attempts"] if r["attempts"] is not None else "—"}**')
            if r["remaining"] is not None: lines.append(f'Remaining target: **{r["remaining"]:g}** • completion: **{r["completion_percent"]:.1f}%**')
            matches=search_summary(ALU_DATA,"events",values.get("Event", ""))
            if matches: lines.append(f'Centralized event matches: **{len(matches)}**')
        elif key=="blueprints":
            r=blueprint_plan(_number(values.get("Current cards")) or 0,_number(values.get("Target cards")) or 0,_number(values.get("Owned cards")) or 0,_number(values.get("Wild Cards")) or 0)
            lines += [f'Required cards: **{r["missing"]:g}**', f'Remaining after owned/wild cards: **{r["remaining"]:g}**']
        elif key=="upgrade_planner":
            cars=ALU_DATA.search_cars(values.get("Car",""))[:1]
            if not cars:
                lines.append("Car not found in the centralized ALU data layer.")
            else:
                r=upgrade_stage_plan(ALU_DATA,cars[0].id,int(_number(values.get("Current star")) or 1),int(_number(values.get("Current stage")) or 0),int(_number(values.get("Target star")) or 1),int(_number(values.get("Target stage")) or 4))
                lines.append(f'Status: **{r["status"]}**')
                if r.get("totals"): lines.append("Totals: " + ", ".join(f'**{k} {v:,}**' for k,v in r["totals"].items()))
        elif key=="import_parts":
            r=import_parts_plan(parse_stats(values.get("Current parts")),parse_stats(values.get("Target parts")))
            lines.extend([f'**{x["part"].replace("_"," ").title()}:** +{x["needed"]:g}' for x in r["rows"]])
        elif key=="rank":
            r=rank_progress(_number(values.get("Current rank")) or 0,_number(values.get("Target rank")) or 0)
            lines.append(f'Progress: **{r["completion_percent"]:.1f}%** • Delta to target: **{r["delta"]:+g}**')
        elif key=="star_up":
            req=[_number(x.strip()) for x in values.get("Requirements","").replace("; ",",").split(",") if x.strip()]
            r=star_up_plan(req,int(_number(values.get("Current star")) or 1),int(_number(values.get("Target star")) or 1),_number(values.get("Current cards")) or 0)
            lines.append(f'Required cards: **{r["required_cards"]:g}** • Remaining: **{r["remaining_cards"]:g}**')
        elif key=="garage_progress":
            r=garage_progress(_number(values.get("Completed")) or 0,_number(values.get("Total")) or 0)
            lines.append(f'Garage completion: **{r["completion_percent"]:.1f}%** • Remaining: **{r["remaining"]:g}**')
        elif key=="event_rewards":
            r=event_reward_plan(_number(values.get("Attempts")) or 0,_number(values.get("Reward per attempt")) or 0,_number(values.get("Target reward")) or 0,_number(values.get("Current reward")) or 0)
            lines.append(f'Remaining reward: **{r["remaining_reward"]:g}**')
            if r["expected_attempts"] is not None: lines.append(f'Expected attempts: **{r["expected_attempts"]:.1f}** • reachable: **{"yes" if r["target_reachable_with_capacity"] else "no"}**')
        elif key=="evo":
            r=evo_compare(ALU_DATA,values.get("Car A",""),values.get("Car B",""))
            lines.append(f'Status: **{r["status"]}**')
            if r.get("ok"): lines.append(f'Profiles loaded: **{r["a"].id}** vs **{r["b"].id}**')
        elif key=="data_health":
            report = audit_data(ALU_DATA)
            counts = verification_summary(ALU_DATA)
            lines.append(f'Overall status: **{report["status"]}**')
            lines.append(f'Sources registered: **{report["source_count"]}**')
            lines.append(f'Verification: **{", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "no records"}**')
            lines.append(f'Provenance gaps: **{len(report["missing_provenance"])}** • Duplicate IDs: **{sum(len(v) for v in report["duplicate_ids"].values())}**')
            if report["source_reuse_status"]:
                lines.append("Source-use state: " + ", ".join(f'**{k}={v}**' for k, v in report["source_reuse_status"].items()))
        elif key=="search":
            kind=(values.get("Search type","cars") or "cars").strip().casefold()
            kind={"car":"cars","cars":"cars","track":"tracks","tracks":"tracks","event":"events","events":"events"}.get(kind,kind)
            if kind not in {"cars","tracks","events"}: raise ValueError("Search type must be cars, tracks, or events.")
            query=values.get("Query","").strip()
            if not query: raise ValueError("Enter a search query.")
            rows=search_summary(ALU_DATA,kind,query)
            if not rows:
                lines.append("No matching centralized records were found.")
            else:
                lines.append(f"Found **{len(rows)}** matching {kind}.")
                lines.extend("• **" + row["name"] + "** — `" + row["id"] + "` • " + row["verification"] for row in rows[:15])
        elif key=="redeem":
            lines.append("Redeem-code records are intentionally shown only when a verified code source is connected.")
            lines.append("No verified redeem-code records are currently stored in the centralized ALU data layer.")
            lines.append("This prevents expired, guessed, or unverified codes from being presented as active.")
        elif key=="garage":
            progress=_number(values.get("Current progress"))
            goal=_number(values.get("Goal"))
            if progress is not None and goal is not None and goal>0:
                pct=max(0,min(100,(progress/goal)*100))
                lines.append(f"Progress: **{progress:g} / {goal:g} ({pct:.1f}%)**")
                lines.append(f"Remaining: **{max(0,goal-progress):g}**")
            else:
                lines.append("Snapshot received. Enter numeric Current progress and Goal values to calculate completion.")
        elif key=="favorites":
            lines.append("Favorites are designed as a quick-access layer for the dashboard. Selected tool: **" + (values.get("Tool name") or "not specified") + "**.")
            lines.append("Tool discovery remains centralized so new tools do not require new slash commands.")
        elif key=="settings":
            lines.append("Player preference request received.")
            lines.append("Supported preference areas: language, timezone, default dashboard section, and notification behavior.")
        elif key=="car_compare":
            r=compare_cars(ALU_DATA,values.get("Car A",""),values.get("Car B",""))
            if not r.get("ok"):
                lines.append("One or both cars were not found in centralized data.")
            else:
                lines.extend([f'**{x["stat"].replace("_"," ").title()}:** {x["a"] if x["a"] is not None else "—"} → {x["b"] if x["b"] is not None else "—"}' for x in r["stats"]])
                lines.append(f'Verification: A **{r["a"].verification.value}** • B **{r["b"].verification.value}**')
        else:
            lines.append("Inputs received and processed.")
    except ValueError as exc:
        lines.append(f"⚠️ {exc}")
    embed.description="\\n\\n".join(lines)
    if values:
        embed.add_field(name="Inputs",value="\\n".join(f'**{k}:** {v}' for k,v in values.items())[:1024],inline=False)
    embed.set_footer(text="🧪 Shohan's Lab  •  🌐 alu.shohanlab.com")
    return embed


class ToolActionView(discord.ui.View):
    def __init__(self, key: str, category: str = "garage", owner_view=None):
        super().__init__(timeout=300)
        self.key = key
        self.category = category
        self.owner_view = owner_view

    @discord.ui.button(label="Enter Tool Inputs", style=discord.ButtonStyle.primary, emoji="🧰")
    async def inputs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ToolInputModal(self.key, cog=self.owner_view.cog if self.owner_view else None, user_id=interaction.user.id))

    @discord.ui.button(label="↩️ Back", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.owner_view is not None:
            await self.owner_view.show_category(interaction, self.category)
        else:
            await interaction.response.edit_message(embed=build_dashboard_embed(), view=AsphaltToolsView())

    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.primary, emoji="🏠", row=1)
    async def home(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.owner_view is not None:
            await self.owner_view.show_home(interaction)
        else:
            await interaction.response.edit_message(embed=build_dashboard_embed(), view=AsphaltToolsView())


def build_tool_embed(key: str) -> discord.Embed:
    tool = TOOL_DEFINITIONS[key]
    embed = discord.Embed(title=f'{tool["emoji"]} {tool["label"]}', description=tool["description"], color=TEAL)
    embed.add_field(name="Discord Interface", value="Use **Enter Tool Inputs** to open the input form for this tool.", inline=False)
    status = ALU_DATA.data_status()
    embed.add_field(name="ALU data layer", value=(f"Centralized source registry active • {status['cars']} cars • {status['upgrade_stages']} upgrade stages • {status['tracks']} tracks • {status['events']} events.\\nGame values remain unavailable until imported and verified."), inline=False)
    embed.add_field(name="Data safety", value="Calculations use user inputs or verified_current centralized records. Unknown/older records are never presented as current game values.", inline=False)
    return embed


# Dashboard-first navigation mirrors the ALU Gauntlet menu pattern:
# one home embed -> section selector -> action selector -> contextual navigation.
TOOL_CATEGORIES = {
    "garage": {
        "label": "Garage & Upgrades",
        "emoji": "🚗",
        "description": "Garage progress, blueprints, upgrades, ranks, stars, parts and car builds.",
        "tools": ["upgrades", "blueprints", "upgrade_planner", "import_parts", "rank", "star_up", "garage_progress", "evo", "car_compare"],
    },
    "planning": {
        "label": "Calculators & Planning",
        "emoji": "🧮",
        "description": "Calculators, comparisons and goal-oriented planning tools.",
        "tools": ["comparator", "priority", "hunt", "simulation", "rating", "cost"],
    },
    "events": {
        "label": "Events & Season",
        "emoji": "🏁",
        "description": "Season calendar, event planning and documented event rewards.",
        "tools": ["calendar", "events", "event_rewards"],
    },
    "tracks": {
        "label": "Tracks & Knowledge",
        "emoji": "🗺️",
        "description": "Race maps, ALU reference information and frequently asked questions.",
        "tools": ["maps", "faq"],
    },
    "player": {
        "label": "Player Hub",
        "emoji": "👤",
        "description": "Garage snapshot, favorites, settings, and fast ALU search.",
        "tools": ["garage", "favorites", "search", "settings"],
    },
    "redeem": {
        "label": "Redeem Center",
        "emoji": "🎁",
        "description": "Verified redeem-code information with an explicit data-status safeguard.",
        "tools": ["redeem"],
    },
    "progress": {
        "label": "Progress & Data",
        "emoji": "📊",
        "description": "Personal notes, garage progress, and centralized ALU data health/provenance.",
        "tools": ["data_health", "notes", "garage_progress"],
    },
}


def build_dashboard_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🏁 ASPHALT LEGENDS UNITE • PLAYER TOOL DASHBOARD",
        description="**Welcome back, driver.** This is the main tool hub. Choose a section, then choose the tool you want — no command memorizing required.",
        color=TEAL,
    )
    for category in TOOL_CATEGORIES.values():
        embed.add_field(
            name=f'{category["emoji"]} {category["label"]}',
            value=category["description"],
            inline=False,
        )
    embed.set_footer(text="Shohan's Companion • ALU Tools Hub • Select a section to continue")
    return embed


class CompanionActionSelect(discord.ui.Select):
    def __init__(self, owner_view, category: str):
        self.owner_view = owner_view
        self.category = category
        options = [
            discord.SelectOption(
                label=TOOL_DEFINITIONS[key]["label"][:100],
                value=key,
                emoji=TOOL_DEFINITIONS[key]["emoji"],
                description=TOOL_DEFINITIONS[key]["description"][:100],
            )
            for key in TOOL_CATEGORIES[category]["tools"]
        ]
        super().__init__(placeholder="Choose an action…", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        if key == "faq":
            await interaction.response.edit_message(embed=build_faq_embed(), view=FAQView(cog=self.owner_view.cog))
            return
        if key == "notes":
            await self.owner_view.cog.show_notes(interaction)
            return
        await interaction.response.edit_message(
            embed=build_tool_embed(key),
            view=ToolActionView(key, category=self.category, owner_view=self.owner_view),
        )


class ToolSearchResultSelect(discord.ui.Select):
    def __init__(self, owner_view, results):
        self.owner_view = owner_view
        self.results = results
        options = [
            discord.SelectOption(
                label=result["label"][:100],
                value=result["key"],
                emoji=result.get("emoji"),
                description=result.get("description", "")[:100],
            )
            for result in results[:25]
        ]
        super().__init__(placeholder="Choose a matching tool…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        key = resolve_tool_key(self.values[0], TOOL_DEFINITIONS)
        if not key:
            await interaction.response.send_message("⚠️ That tool is no longer available.", ephemeral=True)
            return
        if key == "faq":
            await interaction.response.edit_message(embed=build_faq_embed(), view=FAQView(cog=self.owner_view.cog))
            return
        if key == "notes":
            await self.owner_view.cog.show_notes(interaction)
            return
        category = next((name for name, data in TOOL_CATEGORIES.items() if key in data["tools"]), "player")
        self.owner_view.current_category = category
        await interaction.response.edit_message(
            embed=build_tool_embed(key),
            view=ToolActionView(key, category=category, owner_view=self.owner_view),
        )


class ToolSearchView(discord.ui.View):
    def __init__(self, owner_view, results):
        super().__init__(timeout=300)
        self.owner_view = owner_view
        self.add_item(ToolSearchResultSelect(owner_view, results))

    @discord.ui.button(label="↩️ Back to Dashboard", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=self.owner_view)


class ToolSearchModal(discord.ui.Modal, title="🔎 Find an ALU Tool"):
    query = discord.ui.TextInput(
        label="Search for a tool",
        placeholder="Example: upgrade, car search, tracks, redeem, garage…",
        max_length=100,
        required=True,
    )

    def __init__(self, owner_view):
        super().__init__()
        self.owner_view = owner_view

    async def on_submit(self, interaction: discord.Interaction):
        results = search_tools(self.query.value, TOOL_DEFINITIONS, limit=25)
        if not results:
            await interaction.response.send_message(
                "🔎 No matching ALU tools were found. Try a car, track, event, upgrade, garage, redeem, or calculator term.",
                ephemeral=True,
            )
            return
        embed = discord.Embed(
            title="🔎 ALU Tool Search",
            description=f'Found **{len(results)}** matching tool(s) for **{self.query.value.strip()}**. Select one below to open it.',
            color=TEAL,
        )
        await interaction.response.edit_message(embed=embed, view=ToolSearchView(self.owner_view, results))


class CompanionDashboardView(discord.ui.View):
    def __init__(self, cog, guild_id: str, user_id: str):
        super().__init__(timeout=900)
        self.cog = cog
        self.guild_id = str(guild_id)
        self.user_id = str(user_id)
        self.current_category = None
        self._add_category_select()
        self._refresh_navigation()

    def _add_category_select(self):
        owner = self

        class CategorySelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(
                        label=data["label"],
                        value=key,
                        emoji=data["emoji"],
                        description=data["description"][:100],
                    )
                    for key, data in TOOL_CATEGORIES.items()
                ]
                super().__init__(placeholder="Choose an ALU section…", min_values=1, max_values=1, options=options, row=0)

            async def callback(self, interaction: discord.Interaction):
                await owner.show_category(interaction, self.values[0])

        self.add_item(CategorySelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.guild_id) != self.guild_id or str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This Companion dashboard belongs to another player.", ephemeral=True)
            return False
        return True

    def _refresh_navigation(self):
        # Match the Racing Syndicate League dashboard navigation pattern:
        # one persistent navigation row beneath the section/action selectors.
        nav_ids = {"companion_back", "companion_home", "companion_refresh", "companion_help", "companion_search", "companion_close"}
        for item in list(self.children):
            if getattr(item, "custom_id", None) in nav_ids:
                self.remove_item(item)

        back = discord.ui.Button(label="↩️ Back", style=discord.ButtonStyle.secondary, custom_id="companion_back", row=2, disabled=self.current_category is None)
        home = discord.ui.Button(label="🏠 Home", style=discord.ButtonStyle.primary, custom_id="companion_home", row=2)
        refresh = discord.ui.Button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="companion_refresh", row=2)
        help_button = discord.ui.Button(label="❓ Help", style=discord.ButtonStyle.secondary, custom_id="companion_help", row=2)
        search_button = discord.ui.Button(label="🔎 Find Tool", style=discord.ButtonStyle.secondary, custom_id="companion_search", row=3)
        close = discord.ui.Button(label="✖ Close", style=discord.ButtonStyle.danger, custom_id="companion_close", row=2)

        async def go_back(interaction):
            await self.show_home(interaction)

        async def go_home(interaction):
            await self.show_home(interaction)

        async def do_refresh(interaction):
            await self.refresh_current(interaction)

        async def show_help(interaction):
            await interaction.response.edit_message(embed=build_faq_embed(), view=FAQView(cog=self.cog))

        async def find_tool(interaction):
            await interaction.response.send_modal(ToolSearchModal(self))

        async def close_dashboard(interaction):
            self.stop()
            await interaction.response.edit_message(content="🏁 **Shohan's Companion dashboard closed.** Run /dashboard to reopen it.", embed=None, view=None)

        back.callback = go_back
        home.callback = go_home
        refresh.callback = do_refresh
        help_button.callback = show_help
        search_button.callback = find_tool
        close.callback = close_dashboard
        self.add_item(back)
        self.add_item(home)
        self.add_item(refresh)
        self.add_item(help_button)
        self.add_item(search_button)
        self.add_item(close)

    async def show_home(self, interaction: discord.Interaction):
        self.current_category = None
        for item in list(self.children):
            if isinstance(item, CompanionActionSelect):
                self.remove_item(item)
        self._refresh_navigation()
        await interaction.response.edit_message(embed=build_dashboard_embed(), view=self)

    async def show_category(self, interaction: discord.Interaction, category: str):
        self.current_category = category
        for item in list(self.children):
            if isinstance(item, CompanionActionSelect):
                self.remove_item(item)
        self.add_item(CompanionActionSelect(self, category))
        self._refresh_navigation()
        data = TOOL_CATEGORIES[category]
        embed = discord.Embed(
            title=f'{data["emoji"]} {data["label"].upper()}',
            description=f'{data["description"]}\n\n**Choose an action below.** Use ↩️ Back anytime to return to the hub.\n\n**Navigation:** ↩️ Back • 🏠 Home • 🔄 Refresh • ❓ Help • 🔎 Find Tool • ✖ Close',
            color=TEAL,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def refresh_current(self, interaction: discord.Interaction):
        if self.current_category is None:
            await interaction.response.edit_message(embed=build_dashboard_embed(), view=self)
            return
        await self.show_category(interaction, self.current_category)


class AsphaltToolsSelect(CompanionActionSelect):
    """Compatibility alias for older references."""
    def __init__(self):
        super().__init__(owner_view=None, category="garage")


class AsphaltToolsView(discord.ui.View):
    """Legacy empty compatibility view; new commands use CompanionDashboardView."""
    def __init__(self):
        super().__init__(timeout=300)


class AsphaltToolsCog(commands.Cog):
    def __init__(self, bot: discord.Client, notes_collection, garage_collection=None, favorites_collection=None, settings_collection=None, usage_collection=None, redeem_collection=None):
        self.bot = bot
        self.notes_collection = notes_collection
        self.garage_collection = garage_collection
        self.favorites_collection = favorites_collection
        self.settings_collection = settings_collection
        self.usage_collection = usage_collection
        self.redeem_collection = redeem_collection
        self.reminder_loop.start()

    async def build_personal_result_embed(self, key, values, user_id):
        loop = asyncio.get_event_loop()
        uid = str(user_id)
        if key == "redeem" and self.redeem_collection is not None:
            query = (values.get("Code or search") or "").strip().upper()
            now = datetime.now(timezone.utc)
            def find_codes():
                filt = {"verified": True, "$or": [{"expires_at": {"$exists": False}}, {"expires_at": None}, {"expires_at": {"$gt": now}}]}
                if query:
                    filt["code"] = {"$regex": query, "$options": "i"}
                return list(self.redeem_collection.find(filt).sort("first_seen_at", -1).limit(10))
            rows = await loop.run_in_executor(None, find_codes)
            embed = build_tool_result_embed(key, values)
            embed.description = "\n\n".join(["**" + row.get("code", "UNKNOWN") + "** • source: " + row.get("source", "unknown") + " • verified: yes" for row in rows] or ["No verified active redeem-code records match that search."])
            return embed
        if key == "favorites" and self.favorites_collection is not None:
            favorites = await loop.run_in_executor(None, lambda: list(self.favorites_collection.find({"user_id": uid}).sort("updated_at", -1).limit(15)))
            recent = await loop.run_in_executor(None, lambda: list(self.usage_collection.find({"user_id": uid}).sort("last_used_at", -1).limit(10))) if self.usage_collection is not None else []
            embed = build_tool_result_embed(key, values)
            embed.description = "**Favorites**\n" + ("\n".join("⭐ " + x.get("tool", "") for x in favorites) or "None saved yet.") + "\n\n**Recently used**\n" + ("\n".join("• " + x.get("tool", "") for x in recent) or "No usage history yet.")
            return embed
        if key == "settings" and self.settings_collection is not None:
            rows = await loop.run_in_executor(None, lambda: list(self.settings_collection.find({"user_id": uid}).sort("updated_at", -1).limit(20)))
            embed = build_tool_result_embed(key, values)
            embed.description = "**Saved settings**\n" + ("\n".join("⚙️ **" + x.get("setting", "") + "** = `" + x.get("value", "") + "`" for x in rows) or "No saved settings yet.")
            return embed
        if key == "garage" and self.garage_collection is not None:
            rows = await loop.run_in_executor(None, lambda: list(self.garage_collection.find({"user_id": uid}).sort("updated_at", -1).limit(15)))
            embed = build_tool_result_embed(key, values)
            if rows:
                embed.add_field(name="Saved garage snapshots", value="\n".join("🚗 **" + x.get("category", "") + "** — " + str(x.get("current", "?")) + " / " + str(x.get("goal", "?")) for x in rows)[:1024], inline=False)
            return embed
        return build_tool_result_embed(key, values)
    async def record_tool_use(self, user_id, key):
        if self.usage_collection is None: return
        now = datetime.now(timezone.utc)
        await asyncio.get_event_loop().run_in_executor(None, lambda: self.usage_collection.update_one({"user_id": str(user_id), "tool": key}, {"$set": {"last_used_at": now}, "$inc": {"use_count": 1}}, upsert=True))

    async def persist_tool_state(self, user_id, key, values):
        loop = asyncio.get_event_loop(); uid = str(user_id); now = datetime.now(timezone.utc)
        if key == "favorites" and self.favorites_collection is not None:
            name = (values.get("Tool name") or "").strip()
            if name: await loop.run_in_executor(None, lambda: self.favorites_collection.update_one({"user_id": uid, "tool": name}, {"$set": {"updated_at": now}}, upsert=True))
        elif key == "settings" and self.settings_collection is not None:
            setting = (values.get("Setting") or "").strip(); value = (values.get("Value") or "").strip()
            if setting and value: await loop.run_in_executor(None, lambda: self.settings_collection.update_one({"user_id": uid, "setting": setting}, {"$set": {"value": value, "updated_at": now}}, upsert=True))
        elif key == "garage" and self.garage_collection is not None:
            doc={"user_id":uid,"category":values.get("Car / category",""),"current":values.get("Current progress",""),"goal":values.get("Goal",""),"notes":values.get("Notes",""),"updated_at":now}
            await loop.run_in_executor(None, lambda: self.garage_collection.update_one({"user_id":uid,"category":doc["category"]},{"$set":doc},upsert=True))

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


async def setup_alu_tools(bot, notes_collection, garage_collection=None, favorites_collection=None, settings_collection=None, usage_collection=None, redeem_collection=None):
    await bot.add_cog(AsphaltToolsCog(bot, notes_collection, garage_collection, favorites_collection, settings_collection, usage_collection, redeem_collection))
