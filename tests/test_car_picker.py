from types import SimpleNamespace

from alu_car_picker import CAR_PAGE_SIZE, car_description, car_fields_for_tool


def test_car_fields_detects_single_and_dual_car_inputs():
    assert car_fields_for_tool({"fields": ["Car", "Current star"]}) == ["Car"]
    assert car_fields_for_tool({"fields": ["Car A", "Car B", "Stats A"]}) == ["Car A", "Car B"]


def test_car_description_stays_within_discord_limit():
    car = SimpleNamespace(
        name="Example",
        manufacturer="Manufacturer",
        class_name="S",
        max_rank=9999,
    )
    assert len(car_description(car)) <= 100


def test_discord_picker_page_size_is_25():
    assert CAR_PAGE_SIZE == 25



def test_reference_catalog_populates_all_five_classes():
    from alu_data import load_default_store

    store = load_default_store()
    cars = store.search_cars("")
    assert len(cars) >= 300
    assert {car.class_name for car in cars} == {"D", "C", "B", "A", "S"}
    assert store.source("asphalt_fandom") is not None
    assert store.source("asphalt_fandom").verification.value == "older_reference"


def test_reference_catalog_has_unique_ids_and_names():
    from alu_data import load_default_store

    cars = load_default_store().search_cars("")
    assert len({car.id for car in cars}) == len(cars)
    assert len({car.name.casefold() for car in cars}) == len(cars)
