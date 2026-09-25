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
