"""Reusable ALU car-picker UI helpers.

The picker is intentionally data-source agnostic: it reads the centralized ALU
data store and never invents car records. Discord select menus support at most
25 options, so results are paginated and searchable.
"""
from __future__ import annotations

import discord

CAR_PAGE_SIZE = 25


def car_fields_for_tool(tool_definition: dict) -> list[str]:
    return [
        field for field in tool_definition.get("fields", [])
        if field == "Car" or field.startswith("Car ")
    ]


def car_description(car) -> str:
    parts = []
    if getattr(car, "manufacturer", None):
        parts.append(str(car.manufacturer))
    if getattr(car, "class_name", None):
        parts.append(str(car.class_name))
    if getattr(car, "max_rank", None):
        parts.append(f"Max rank {car.max_rank}")
    return " • ".join(parts)[:100] or "ALU car record"


def search_cars(store, query: str = ""):
    return store.search_cars(query or "")


class CarPickerSelect(discord.ui.Select):
    def __init__(self, picker_view, field_name: str, cars: list, page: int):
        self.picker_view = picker_view
        self.field_name = field_name
        self.cars = cars
        self.page = page
        start = page * CAR_PAGE_SIZE
        options = [
            discord.SelectOption(
                label=car.name[:100],
                value=car.id[:100],
                description=car_description(car),
            )
            for car in cars[start:start + CAR_PAGE_SIZE]
        ]
        super().__init__(
            placeholder=f"Choose a car for {field_name}…",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        car = next((item for item in self.cars if item.id == self.values[0]), None)
        if car is None:
            await interaction.response.send_message(
                "⚠️ That car is no longer available.", ephemeral=True
            )
            return
        self.picker_view.owner_view.prefill_values[self.field_name] = car.name
        await interaction.response.edit_message(
            embed=self.picker_view.owner_view.build_embed(),
            view=self.picker_view.owner_view,
        )


class CarSearchModal(discord.ui.Modal):
    def __init__(self, owner_view, field_name: str, store):
        super().__init__(title="🔎 Search ALU Cars")
        self.owner_view = owner_view
        self.field_name = field_name
        self.store = store
        self.query = discord.ui.TextInput(
            label="Car name",
            placeholder="Type part of a car name, e.g. Jesko",
            max_length=100,
            required=True,
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        view = CarPickerView(
            self.owner_view,
            self.field_name,
            self.store,
            query=self.query.value.strip(),
        )
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)


class CarPickerView(discord.ui.View):
    def __init__(self, owner_view, field_name: str, store, page: int = 0, query: str = ""):
        super().__init__(timeout=300)
        self.owner_view = owner_view
        self.field_name = field_name
        self.store = store
        self.query = query.strip()
        self.cars = search_cars(store, self.query)
        self.page = max(0, page)
        self.total_pages = max(1, (len(self.cars) + CAR_PAGE_SIZE - 1) // CAR_PAGE_SIZE)
        self.page = min(self.page, self.total_pages - 1)

        if self.cars:
            self.add_item(CarPickerSelect(self, field_name, self.cars, self.page))

        previous = discord.ui.Button(
            label="Previous", style=discord.ButtonStyle.secondary,
            emoji="◀️", row=1, disabled=self.page <= 0
        )
        next_button = discord.ui.Button(
            label="Next", style=discord.ButtonStyle.secondary,
            emoji="▶️", row=1, disabled=self.page >= self.total_pages - 1
        )
        search = discord.ui.Button(
            label="Search", style=discord.ButtonStyle.primary,
            emoji="🔎", row=1
        )
        back = discord.ui.Button(
            label="Back to Tool", style=discord.ButtonStyle.secondary,
            emoji="↩️", row=1
        )

        async def go_search(interaction):
            await interaction.response.send_modal(
                CarSearchModal(self.owner_view, self.field_name, self.store)
            )

        async def go_previous(interaction):
            await interaction.response.edit_message(
                embed=self.embed(), view=CarPickerView(
                    self.owner_view, self.field_name, self.store,
                    self.page - 1, self.query
                )
            )

        async def go_next(interaction):
            await interaction.response.edit_message(
                embed=self.embed(), view=CarPickerView(
                    self.owner_view, self.field_name, self.store,
                    self.page + 1, self.query
                )
            )

        async def go_back(interaction):
            await interaction.response.edit_message(
                embed=self.owner_view.build_embed(), view=self.owner_view
            )

        previous.callback = go_previous
        next_button.callback = go_next
        search.callback = go_search
        back.callback = go_back
        self.add_item(previous)
        self.add_item(next_button)
        self.add_item(search)
        self.add_item(back)

    def embed(self):
        if not self.cars:
            description = (
                "No car records are loaded in the centralized ALU data layer yet. "
                "The picker will populate automatically when the verified/reference "
                "car dataset is imported."
            )
        else:
            start = self.page * CAR_PAGE_SIZE + 1
            end = min((self.page + 1) * CAR_PAGE_SIZE, len(self.cars))
            filter_text = f" matching **{self.query}**" if self.query else ""
            description = (
                f"Select a car for **{self.field_name}**{filter_text}. "
                f"Showing **{start}–{end}** of **{len(self.cars)}** cars."
            )
        return discord.Embed(
            title="🚗 Choose an ALU Car",
            description=description,
            color=discord.Color.from_rgb(7, 24, 27),
        )
