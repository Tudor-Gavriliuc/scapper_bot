from __future__ import annotations

from datetime import datetime

from main import main as run_products_pipeline
from send_local_revista_to_telegram import main as send_local_revista
from send_nr1_booklet_to_telegram import main as send_nr1_revista


def _log(message: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")


def main() -> None:
    _log("Daily posting job started")

    try:
        _log("Running products pipeline (Kaufland + Linella + Metro)")
        run_products_pipeline()
    except Exception as exc:
        _log(f"Products pipeline failed: {exc}")

    try:
        _log("Sending Nr1 revista link")
        send_nr1_revista()
    except Exception as exc:
        _log(f"Nr1 sending failed: {exc}")

    try:
        _log("Sending Local revista link")
        send_local_revista()
    except Exception as exc:
        _log(f"Local sending failed: {exc}")

    _log("Daily posting job finished")


if __name__ == "__main__":
    main()
