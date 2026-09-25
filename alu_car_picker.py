"""Reusable hierarchical ALU car-picker UI helpers.

Discord select menus support at most 25 options, so the picker uses a cascading
Class -> Manufacturer -> Car flow plus pagination and a quick-search modal.
The picker reads the centralized ALU data store and never creates car records.
"""
from __future__ import annotations

from collections import defaultdict
import re

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


# The imported reference catalog currently has manufacturer unset for many
# records. These prefixes are deliberately conservative and only provide a
# browsing label from the vehicle name; an explicit data-layer manufacturer
# always wins.
_MANUFACTURER_PREFIXES = (
    ("alfa romeo", "Alfa Romeo"),
    ("aston martin", "Aston Martin"),
    ("automobili pininfarina", "Automobili Pininfarina"),
    ("bmw", "BMW"),
    ("bugatti", "Bugatti"),
    ("cadillac", "Cadillac"),
    ("chevrolet", "Chevrolet"),
    ("citroen", "Citroën"),
    ("ds automobiles", "DS Automobiles"),
    ("dodge", "Dodge"),
    ("devel", "Devel"),
    ("ferrari", "Ferrari"),
    ("ferrante design", "Ferrante Design"),
    ("ford", "Ford"),
    ("ginetta", "Ginetta"),
    ("hennessey", "Hennessey"),
    ("hispano suiza", "Hispano Suiza"),
    ("htt", "HTT"),
    ("hyundai", "Hyundai"),
    ("infiniti", "Infiniti"),
    ("italdesign", "Italdesign"),
    ("jaguar", "Jaguar"),
    ("jeep", "Jeep"),
    ("koenigsegg", "Koenigsegg"),
    ("ktm", "KTM"),
    ("lamborghini", "Lamborghini"),
    ("lancia", "Lancia"),
    ("lotus", "Lotus"),
    ("maserati", "Maserati"),
    ("mclaren", "McLaren"),
    ("mercedes-amg", "Mercedes-AMG"),
    ("mercedes", "Mercedes-Benz"),
    ("mclaren", "McLaren"),
    ("mitsubishi", "Mitsubishi"),
    ("mosler", "Mosler"),
    ("nissan", "Nissan"),
    ("pagani", "Pagani"),
    ("peugeot", "Peugeot"),
    ("porsche", "Porsche"),
    ("praga", "Praga"),
    ("raesr", "RAESR"),
    ("renault", "Renault"),
    ("rimac", "Rimac"),
    ("shelby", "Shelby"),
    ("ssc", "SSC"),
    ("tvr", "TVR"),
    ("tesla", "Tesla"),
    ("toyota", "Toyota"),
    ("tushek", "Tushek"),
    ("volkswagen", "Volkswagen"),
    ("w motors", "W Motors"),
    ("zenvo", "Zenvo"),
    ("czinger", "Czinger"),
    ("deus", "Deus"),
    ("dallara", "Dallara"),
    ("apollo", "Apollo"),
    ("arash", "Arash"),
    ("aspark", "Aspark"),
    ("brabham", "Brabham"),
    ("bentley", "Bentley"),
    ("bizzarrini", "Bizzarrini"),
    ("bowler", "Bowler"),
    ("buick", "Buick"),
    ("chevrolet", "Chevrolet"),
    ("chrysler", "Chrysler"),
    ("cupra", "CUPRA"),
    ("donkervoort", "Donkervoort"),
    ("ed design", "ED Design"),
    ("gordon murray", "Gordon Murray Automotive"),
    ("lamborghini", "Lamborghini"),
    ("lewis hamilton", "Lewis Hamilton"),
    ("lucid", "Lucid"),
    ("noble", "Noble"),
    ("nissan", "Nissan"),
    ("polestar", "Polestar"),
    ("sbarro", "Sbarro"),
    ("w motors", "W Motors"),
)


def car_manufacturer(car) -> str:
    explicit = getattr(car, "manufacturer", None)
    if explicit and str(explicit).strip():
        return str(explicit).strip()

    normalized = re.sub(r"\s+", " ", str(getattr(car, "name", "")).strip().casefold())
    for prefix, manufacturer in _MANUFACTURER_PREFIXES:
        if normalized.startswith(prefix):
            return manufacturer

    # A few names begin with a model/variant rather than the manufacturer.
    # Keep these grouped rather than pretending we know more than the source.
    return "Other / Unspecified"


def manufacturer_options(cars: list) -> list[str]:
    return sorted({car_manufacturer(car) for car in cars}, key=str.casefold)


def class_options(cars: list) -> list[str]:
    return sorted(
        {str(car.class_name).strip() for car in cars if getattr(car, "class_name", None)},
        key=lambda value: ({"D": 0, "C": 1, "B": 2, "A": 3, "S": 4}.get(value.upper(), 99), value.casefold()),
    )


def filter_cars(cars: list, *, class_name: str = "", manufacturer: str = "", query: str = "") -> list:
    class_value = class_name.strip().casefold()
    manufacturer_value = manufacturer.strip().casefold()
    query_value = query.strip().casefold()

    filtered = []
    for car in cars:
        if class_value and str(getattr(car, "class_name", "")).casefold() != class_value:
            continue
        if manufacturer_value and car_manufacturer(car).casefold() != manufacturer_value:
            continue
        if query_value:
            haystack = " ".join(
                [
                    str(getattr(car, "name", "")),
                    str(getattr(car, "id", "")),
                    str(getattr(car, "manufacturer", "") or ""),
                    car_manufacturer(car),
                    str(getattr(car, "class_name", "") or ""),
                ]
            ).casefold()
            if query_value not in haystack:
                continue
        filtered.append(car)

    return sorted(filtered, key=lambda car: str(getattr(car, "name", "")).casefold())


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
            row=2,
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
    def __init__(self, owner_view, field_name: str, store, base_cars: list):
        super().__init__(title="🔎 Search ALU Cars")
        self.owner_view = owner_view
        self.field_name = field_name
        self.store = store
        self.base_cars = base_cars
        self.query = discord.ui.TextInput(
            label="Search car name, manufacturer, or class",
            placeholder="Try Jesko, Koenigsegg, or S",
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
            cars=self.base_cars,
        )
        await interaction.response.send_message(
            embed=view.embed(),
            view=view,
            ephemeral=True,
        )


class CarPickerView(discord.ui.View):
    def __init__(
        self,
        owner_view,
        field_name: str,
        store,
        page: int = 0,
        query: str = "",
        class_name: str = "",
        manufacturer: str = "",
        cars: list | None = None,
    ):
        super().__init__(timeout=300)
        self.owner_view = owner_view
        self.field_name = field_name
        self.store = store
        self.query = query.strip()
        self.class_name = class_name.strip()
        self.manufacturer = manufacturer.strip()
        self.all_cars = list(cars) if cars is not None else search_cars(store, "")
        self.cars = filter_cars(
            self.all_cars,
            class_name=self.class_name,
            manufacturer=self.manufacturer,
            query=self.query,
        )
        self.page = max(0, page)
        self.total_pages = max(1, (len(self.cars) + CAR_PAGE_SIZE - 1) // CAR_PAGE_SIZE)
        self.page = min(self.page, self.total_pages - 1)
        self._build()

    def _build(self):
        # Class selector
        class_select = discord.ui.Select(
            placeholder="1️⃣ Choose Class…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=f"Class {value}",
                    value=value,
                    default=value.casefold() == self.class_name.casefold(),
                )
                for value in class_options(self.all_cars)[:25]
            ],
            row=0,
        )

        async def choose_class(interaction: discord.Interaction):
            self.class_name = self._selected_value(class_select)
            self.manufacturer = ""
            self.page = 0
            await self._refresh(interaction)

        class_select.callback = choose_class
        self.add_item(class_select)

        # Manufacturer selector appears after a class is chosen.
        if self.class_name:
            class_cars = filter_cars(self.all_cars, class_name=self.class_name)
            manufacturers = manufacturer_options(class_cars)
            manufacturer_select = discord.ui.Select(
                placeholder="2️⃣ Choose Manufacturer…",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=value[:100],
                        value=value[:100],
                        default=value.casefold() == self.manufacturer.casefold(),
                    )
                    for value in manufacturers[:25]
                ],
                row=1,
            )

            async def choose_manufacturer(interaction: discord.Interaction):
                self.manufacturer = self._selected_value(manufacturer_select)
                self.page = 0
                await self._refresh(interaction)

            manufacturer_select.callback = choose_manufacturer
            self.add_item(manufacturer_select)

        # Car selector appears only after a manufacturer is chosen.
        if self.class_name and self.manufacturer and self.cars:
            self.add_item(
                CarPickerSelect(self, self.field_name, self.cars, self.page)
            )

        previous = discord.ui.Button(
            label="Previous", style=discord.ButtonStyle.secondary,
            emoji="◀️", row=3, disabled=self.page <= 0
        )
        next_button = discord.ui.Button(
            label="Next", style=discord.ButtonStyle.secondary,
            emoji="▶️", row=3, disabled=self.page >= self.total_pages - 1
        )
        search = discord.ui.Button(
            label="Search", style=discord.ButtonStyle.primary,
            emoji="🔎", row=3
        )
        reset = discord.ui.Button(
            label="Reset", style=discord.ButtonStyle.secondary,
            emoji="↻", row=3
        )
        back = discord.ui.Button(
            label="Back to Tool", style=discord.ButtonStyle.secondary,
            emoji="↩️", row=3
        )

        async def go_search(interaction):
            await interaction.response.send_modal(
                CarSearchModal(self.owner_view, self.field_name, self.store, self.all_cars)
            )

        async def go_previous(interaction):
            replacement = CarPickerView(
                self.owner_view, self.field_name, self.store,
                page=self.page - 1,
                query=self.query,
                class_name=self.class_name,
                manufacturer=self.manufacturer,
                cars=self.all_cars,
            )
            await interaction.response.edit_message(embed=replacement.embed(), view=replacement)

        async def go_next(interaction):
            replacement = CarPickerView(
                self.owner_view, self.field_name, self.store,
                page=self.page + 1,
                query=self.query,
                class_name=self.class_name,
                manufacturer=self.manufacturer,
                cars=self.all_cars,
            )
            await interaction.response.edit_message(embed=replacement.embed(), view=replacement)

        async def go_reset(interaction):
            replacement = CarPickerView(
                self.owner_view, self.field_name, self.store, cars=self.all_cars
            )
            await interaction.response.edit_message(embed=replacement.embed(), view=replacement)

        async def go_back(interaction):
            await interaction.response.edit_message(
                embed=self.owner_view.build_embed(), view=self.owner_view
            )

        previous.callback = go_previous
        next_button.callback = go_next
        search.callback = go_search
        reset.callback = go_reset
        back.callback = go_back
        self.add_item(previous)
        self.add_item(next_button)
        self.add_item(search)
        self.add_item(reset)
        self.add_item(back)

    @staticmethod
    def _selected_value(select: discord.ui.Select) -> str:
        return str(select.values[0]).strip()

    async def _refresh(self, interaction: discord.Interaction):
        replacement = CarPickerView(
            self.owner_view,
            self.field_name,
            self.store,
            page=self.page,
            query=self.query,
            class_name=self.class_name,
            manufacturer=self.manufacturer,
            cars=self.all_cars,
        )
        await interaction.response.edit_message(
            embed=replacement.embed(),
            view=replacement,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            str(interaction.guild_id) != self.owner_view.guild_id
            or str(interaction.user.id) != self.owner_view.user_id
        ):
            await interaction.response.send_message(
                "❌ This car picker belongs to another player.", ephemeral=True
            )
            return False
        return True

    def embed(self):
        if not self.cars:
            if self.query:
                description = (
                    f"No cars match **{self.query}**. "
                    "Use Search with a model, manufacturer, or class."
                )
            elif not self.class_name:
                description = (
                    "Browse the reference catalog in three steps: "
                    "**Class → Manufacturer → Car**. "
                    f"**{len(self.all_cars)}** reference cars are loaded."
                )
            elif not self.manufacturer:
                class_count = len(filter_cars(self.all_cars, class_name=self.class_name))
                description = (
                    f"**Class {self.class_name}** has **{class_count}** reference cars. "
                    "Choose a manufacturer to continue."
                )
            else:
                description = (
                    f"No cars are currently listed for **{self.manufacturer}** "
                    f"in **Class {self.class_name}**."
                )
        else:
            start = self.page * CAR_PAGE_SIZE + 1
            end = min((self.page + 1) * CAR_PAGE_SIZE, len(self.cars))
            filters = []
            if self.class_name:
                filters.append(f"Class {self.class_name}")
            if self.manufacturer:
                filters.append(self.manufacturer)
            if self.query:
                filters.append(f"search: {self.query}")
            scope = " • ".join(filters) or "All classes"
            description = (
                f"Select a car for **{self.field_name}**.\n"
                f"**{scope}**\n"
                f"Showing **{start}–{end}** of **{len(self.cars)}** matching cars."
            )

        return discord.Embed(
            title="🚗 Choose an ALU Car",
            description=description,
            color=discord.Color.from_rgb(7, 24, 27),
        )
