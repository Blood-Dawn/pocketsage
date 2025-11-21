from pathlib import Path

from pocketsage.desktop.charts import debt_payoff_chart_png


def test_debt_payoff_chart_creates_image(tmp_path: Path) -> None:
    schedule = [
        {
            "date": "2024-01-01",
            "payments": {
                "debt_1": {"payment_amount": 200.0, "remaining_balance": 800.0},
                "debt_2": {"payment_amount": 150.0, "remaining_balance": 450.0},
            },
        },
        {
            "date": "2024-02-01",
            "payments": {
                "debt_1": {"payment_amount": 200.0, "remaining_balance": 600.0},
                "debt_2": {"payment_amount": 150.0, "remaining_balance": 300.0},
            },
        },
    ]

    chart_path = debt_payoff_chart_png(schedule)

    assert chart_path.exists()
    assert chart_path.suffix == ".png"
    # Ensure we can move the file (mimicking export behavior)
    target = tmp_path / "out.png"
    target.write_bytes(chart_path.read_bytes())
