import os
import shutil
from pathlib import Path

import pymupdf  # PyMuPDF

from utils import pdf_contains_pin

# -----------------------------
# Configuration
# -----------------------------
PINCODE = "600032"

INGEST_FOLDER = Path("rapido_ingest")
KEEP_FOLDER = Path("workspace/rapido_receipts")
DELETE_FOLDER = Path("workspace/deleted_rapido_receipts")

# Create destination folders if they don't exist
KEEP_FOLDER.mkdir(parents=True, exist_ok=True)
DELETE_FOLDER.mkdir(parents=True, exist_ok=True)


def main():
    pdf_files = list(INGEST_FOLDER.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    kept = 0
    deleted = 0

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        filepath = os.path.join(INGEST_FOLDER, pdf_file.name)
        if pdf_contains_pin(filepath, PINCODE):
            destination = KEEP_FOLDER / pdf_file.name
            kept += 1
            print("  -> Pincode found. Moving to rapido_receipts.")
        else:
            destination = DELETE_FOLDER / pdf_file.name
            deleted += 1
            print("  -> Pincode not found. Moving to deleted_rapido_receipts.")

        # Move the file (removes it from ingest folder)
        shutil.move(str(pdf_file), str(destination))

    print("\nDone!")
    print(f"Kept: {kept}")
    print(f"Deleted: {deleted}")
    print(f"Total: {len(pdf_files)}")


if __name__ == "__main__":
    main()