import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from utils import pdf_contains_pin

# -----------------------------
# Configuration
# -----------------------------
PINCODE = "600032"

INGEST_FOLDER = Path("rapido_ingest")
KEEP_FOLDER = Path("workspace/rapido_receipts")
DELETE_FOLDER = Path("workspace/deleted_rapido_receipts")


def is_cab_receipt(filename: str) -> bool:
    """Rapido cab receipts use CAB_RECEIPT_* filenames; autos use AUTO_RECEIPT_*."""
    return Path(filename).name.upper().startswith("CAB_RECEIPT")


def clear_ingest_folder(ingest_folder=None) -> Path:
    ingest = Path(ingest_folder or INGEST_FOLDER)
    ingest.mkdir(parents=True, exist_ok=True)
    for item in ingest.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    return ingest


def unpack_zip(zip_source, ingest_folder=None) -> int:
    """Unpack a zip archive into the ingest folder. Returns PDF count found."""
    ingest = clear_ingest_folder(ingest_folder)

    if isinstance(zip_source, (str, Path)):
        archive = zipfile.ZipFile(zip_source)
    else:
        archive = zipfile.ZipFile(BytesIO(zip_source))

    with archive:
        archive.extractall(ingest)

    pdf_count = len(list(ingest.rglob("*.pdf")))
    print(f"Unpacked zip — found {pdf_count} PDF(s).")
    return pdf_count


def main(
    pincode=None,
    ingest_folder=None,
    keep_folder=None,
    delete_folder=None,
    zip_source=None,
):
    pin = str(pincode if pincode is not None else PINCODE)
    ingest = Path(ingest_folder or INGEST_FOLDER)
    keep = Path(keep_folder or KEEP_FOLDER)
    delete = Path(delete_folder or DELETE_FOLDER)

    keep.mkdir(parents=True, exist_ok=True)
    delete.mkdir(parents=True, exist_ok=True)

    if zip_source is not None:
        unpack_zip(zip_source, ingest)

    pdf_files = sorted(ingest.rglob("*.pdf"), key=lambda p: p.name.lower())

    if not pdf_files:
        print("No PDF files found.")
        return

    kept = 0
    deleted = 0
    skipped_non_cab = 0

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        if not is_cab_receipt(pdf_file.name):
            destination = delete / pdf_file.name
            skipped_non_cab += 1
            print("  -> Not a cab receipt. Moving to deleted_rapido_receipts.")
            shutil.move(str(pdf_file), str(destination))
            continue

        if pdf_contains_pin(str(pdf_file), pin):
            destination = keep / pdf_file.name
            kept += 1
            print("  -> Pincode found. Moving to rapido_receipts.")
        else:
            destination = delete / pdf_file.name
            deleted += 1
            print("  -> Pincode not found. Moving to deleted_rapido_receipts.")

        # Move the file (removes it from ingest folder)
        shutil.move(str(pdf_file), str(destination))

    print("\nDone!")
    print(f"Kept: {kept}")
    print(f"Deleted: {deleted}")
    print(f"Skipped (non-cab): {skipped_non_cab}")
    print(f"Total: {len(pdf_files)}")


if __name__ == "__main__":
    import sys

    zip_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(zip_source=zip_arg)
