from app.services.value_extractor import ValueExtractor

extractor = ValueExtractor()


def test_money_million_to_million() -> None:
    old_values = extractor.extract_values("Revenue was $10 million.")
    new_values = extractor.extract_values("Revenue was $15 million.")
    assert old_values[0].normalized_value == 10_000_000
    assert new_values[0].normalized_value == 15_000_000
    deltas = extractor.compare_values(old_values, new_values)
    assert len(deltas) == 1
    assert deltas[0].absolute_change == 5_000_000
    assert deltas[0].percentage_change == 50.0


def test_compact_money_suffix() -> None:
    old_values = extractor.extract_values("Profit was $10M")
    new_values = extractor.extract_values("Profit was $15M")
    deltas = extractor.compare_values(old_values, new_values)
    assert deltas[0].old.normalized_value == 10_000_000
    assert deltas[0].new.normalized_value == 15_000_000


def test_cardinal_change() -> None:
    old_values = extractor.extract_values("The company employs 500 people.")
    new_values = extractor.extract_values("The company employs 750 people.")
    deltas = extractor.compare_values(old_values, new_values)
    assert deltas[0].old.normalized_value == 500
    assert deltas[0].new.normalized_value == 750
    assert deltas[0].percentage_change == 50.0


def test_percent_change() -> None:
    old_values = extractor.extract_values("Growth was 5%.")
    new_values = extractor.extract_values("Growth was 7%.")
    deltas = extractor.compare_values(old_values, new_values)
    assert deltas[0].old.normalized_value == 5
    assert deltas[0].new.normalized_value == 7


def test_zero_old_value_skips_percentage() -> None:
    old_values = extractor.extract_values("The balance was 0.")
    new_values = extractor.extract_values("The balance was 10.")
    deltas = extractor.compare_values(old_values, new_values)
    assert deltas[0].percentage_change is None
    assert deltas[0].absolute_change == 10


def test_crore_and_kg() -> None:
    money = extractor.extract_values("Investment was ₹5 crore.")
    qty = extractor.extract_values("The shipment weighed 10 kg.")
    assert money[0].normalized_value == 50_000_000
    assert money[0].currency == "INR"
    assert qty[0].normalized_value == 10
    assert qty[0].unit == "kg"


def test_temporal_day_difference() -> None:
    old_dates = extractor.extract_dates("The project deadline is March 15, 2026.")
    new_dates = extractor.extract_dates("The project deadline is April 30, 2026.")
    assert old_dates[0].iso_date == "2026-03-15"
    assert new_dates[0].iso_date == "2026-04-30"
    deltas = extractor.compare_dates(old_dates, new_dates)
    assert deltas[0].days_changed == 46


def test_additional_date_formats() -> None:
    assert extractor.extract_dates("15 March 2026")[0].iso_date == "2026-03-15"
    assert extractor.extract_dates("15/03/2026")[0].iso_date == "2026-03-15"
    assert extractor.extract_dates("2026-03-15")[0].iso_date == "2026-03-15"
    assert extractor.extract_dates("March 2026")[0].iso_date == "2026-03-01"
    quarter = extractor.extract_dates("Q2 2026")[0]
    assert quarter.iso_date == "2026-04-01"
    assert quarter.precision == "quarter"
