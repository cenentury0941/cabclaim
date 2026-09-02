from pathlib import Path
from decimal import Decimal
import shutil
import pymupdf

from utils import (
    get_fare_amount_uber,
    get_fare_amount_rapido,
)

MAX_AMOUNT = Decimal("6000.00")

UBER_DIR = Path("workspace/uber_receipts")
RAPIDO_DIR = Path("workspace/rapido_receipts")

UBER_OVERLIMIT_DIR = Path("workspace/overlimit_uber_receipts")
RAPIDO_OVERLIMIT_DIR = Path("workspace/overlimit_rapido_receipts")


def load_receipts(folder, fare_function, provider):
    receipts = []

    for pdf_file in sorted(folder.glob("*.pdf")):
        try:
            with pymupdf.open(pdf_file) as receipt:
                fare = fare_function(receipt)

            receipts.append({
                "provider": provider,
                "path": pdf_file,
                "fare": fare,
            })

        except Exception as e:
            print(f"Skipping {pdf_file.name}: {e}")

    return receipts


def find_best_subset(receipts, limit):
    """
    Returns the subset with the largest total <= limit.
    Uses dynamic programming (optimal solution).
    """

    limit_paise = int(limit * 100)

    # sum_in_paise -> list of receipt indices
    dp = {0: []}

    for idx, receipt in enumerate(receipts):
        fare = int(receipt["fare"] * 100)

        updates = {}

        for current_sum, chosen in dp.items():
            new_sum = current_sum + fare

            if new_sum <= limit_paise and new_sum not in dp and new_sum not in updates:
                updates[new_sum] = chosen + [idx]

        dp.update(updates)

    best_sum = max(dp.keys())
    kept_indices = set(dp[best_sum])

    kept = [receipts[i] for i in kept_indices]
    moved = [r for i, r in enumerate(receipts) if i not in kept_indices]

    return kept, moved, Decimal(best_sum) / 100


def move_receipt(receipt, *, uber_overlimit_dir, rapido_overlimit_dir):
    if receipt["provider"] == "uber":
        destination_dir = uber_overlimit_dir
    else:
        destination_dir = rapido_overlimit_dir

    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / receipt["path"].name
    shutil.move(str(receipt["path"]), str(destination))


def main(
    max_amount=None,
    uber_dir=None,
    rapido_dir=None,
    uber_overlimit_dir=None,
    rapido_overlimit_dir=None,
):
    limit = Decimal(str(max_amount)) if max_amount is not None else MAX_AMOUNT
    uber = Path(uber_dir or UBER_DIR)
    rapido = Path(rapido_dir or RAPIDO_DIR)
    uber_over = Path(uber_overlimit_dir or UBER_OVERLIMIT_DIR)
    rapido_over = Path(rapido_overlimit_dir or RAPIDO_OVERLIMIT_DIR)

    receipts = []

    receipts.extend(
        load_receipts(
            uber,
            get_fare_amount_uber,
            "uber",
        )
    )

    receipts.extend(
        load_receipts(
            rapido,
            get_fare_amount_rapido,
            "rapido",
        )
    )

    if not receipts:
        print("No receipt PDFs found in the configured folders.")
        return

    kept, moved, total = find_best_subset(receipts, limit)

    for receipt in moved:
        move_receipt(
            receipt,
            uber_overlimit_dir=uber_over,
            rapido_overlimit_dir=rapido_over,
        )

    uber_kept = sum(1 for r in kept if r["provider"] == "uber")
    rapido_kept = sum(1 for r in kept if r["provider"] == "rapido")

    uber_moved = sum(1 for r in moved if r["provider"] == "uber")
    rapido_moved = sum(1 for r in moved if r["provider"] == "rapido")

    print("\n========== RESULTS ==========")
    print(f"Limit           : ₹{limit:.2f}")
    print(f"Optimal Total   : ₹{total:.2f}")
    print()

    print(f"Uber kept       : {uber_kept}")
    print(f"Uber moved      : {uber_moved}")
    print()

    print(f"Rapido kept     : {rapido_kept}")
    print(f"Rapido moved    : {rapido_moved}")
    print()

    print("Kept receipts:")
    kept_sorted = sorted(
        kept,
        key=lambda r: (r["provider"], r["path"].name)
    )

    running_total = Decimal("0.00")
    for receipt in kept_sorted:
        running_total += receipt["fare"]
        print(
            f"{receipt['provider']:7} "
            f"₹{receipt['fare']:7.2f}  "
            f"{receipt['path'].name}"
        )

    print(f"\nFinal total: ₹{running_total:.2f}")


if __name__ == "__main__":
    main()