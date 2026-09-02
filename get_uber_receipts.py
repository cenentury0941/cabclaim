import json
import os
import requests
import shutil

from utils import pdf_contains_pin

BASE_URL = "https://riders.uber.com/trips/{}/receipt?contentType=PDF"

ACTIVITIES_FILE = "workspace/Activities.json"
COOKIE_FILE = "Uber_Cookie.txt"
OUTPUT_DIR = "workspace/uber_receipts"
DELETED_DIR = "workspace/deleted_uber_receipts"

# Three-letter month abbreviation (Jan, Feb, Mar, ...)
TARGET_MONTH = "Jul"

# Change to the PIN you want to keep. Defaults to 600032 (Ekkatuthangal)
TARGET_PIN = "600032"

MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def load_cookies_from_header(cookie_header):
    """Parse a Cookie header string into a dict."""
    cookie_string = cookie_header.strip()
    if cookie_string.lower().startswith("cookie:"):
        cookie_string = cookie_string[7:].strip()

    cookies = {}
    for cookie in cookie_string.split(";"):
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            cookies[key.strip()] = value.strip()

    return cookies


def load_cookies(cookie_file):
    """Load cookies from a Uber_Cookie.txt file."""
    with open(cookie_file, "r", encoding="utf-8") as f:
        return load_cookies_from_header(f.read())


def clear_folder(folder):
    """Remove all files and subfolders inside folder. Creates folder if missing."""
    os.makedirs(folder, exist_ok=True)
    removed = 0
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)
        removed += 1
    return removed


def filter_receipts_by_pin(
    target_pin,
    output_dir=OUTPUT_DIR,
    deleted_dir=DELETED_DIR,
    on_progress=None,
):
    """Move uber_receipts that do not contain the target PIN to deleted_dir."""
    print(f"\nFiltering uber_receipts for PIN {target_pin}...\n")

    os.makedirs(deleted_dir, exist_ok=True)

    kept = 0
    deleted = 0
    pdf_names = [f for f in os.listdir(output_dir) if f.lower().endswith(".pdf")]
    total = len(pdf_names)

    for index, filename in enumerate(pdf_names, start=1):
        filepath = os.path.join(output_dir, filename)
        delete_path = os.path.join(deleted_dir, filename)

        if pdf_contains_pin(filepath, str(target_pin)):
            print(f"✓ Keeping {filename}")
            kept += 1
            if on_progress:
                on_progress({
                    "phase": "filter",
                    "index": index,
                    "total": total,
                    "path": filepath,
                    "kept": True,
                    "filename": filename,
                })
        else:
            shutil.move(filepath, delete_path)
            print(f"✗ Deleted {filename}")
            deleted += 1
            if on_progress:
                on_progress({
                    "phase": "filter",
                    "index": index,
                    "total": total,
                    "path": None,
                    "kept": False,
                    "filename": filename,
                })

    print("\nFiltering complete.")
    print(f"Kept: {kept}")
    print(f"Deleted: {deleted}")


def main(
    target_month=None,
    target_pin=None,
    cookie_header=None,
    activities_file=None,
    output_dir=None,
    deleted_dir=None,
    on_progress=None,
):
    month = target_month or TARGET_MONTH
    pin = str(target_pin if target_pin is not None else TARGET_PIN)
    activities_path = activities_file or ACTIVITIES_FILE
    out_dir = output_dir or OUTPUT_DIR
    del_dir = deleted_dir or DELETED_DIR

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(del_dir, exist_ok=True)

    cleared = clear_folder(out_dir)
    print(f"Cleared {cleared} item(s) from {out_dir}.\n")
    if on_progress:
        on_progress({
            "phase": "cleared",
            "index": 0,
            "total": 0,
            "path": None,
            "cleared": cleared,
        })

    with open(activities_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = requests.Session()
    if cookie_header is not None:
        session.cookies.update(load_cookies_from_header(cookie_header))
    else:
        session.cookies.update(load_cookies(COOKIE_FILE))

    # Browser-like headers
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*",
        "Referer": "https://riders.uber.com/trips",
    })

    activities = data["data"]["activities"]["past"]["activities"]

    # Filter by month and ignore ₹0.00 / cancelled trips
    activities = [
        a for a in activities
        if month.lower() in a.get("subtitle", "").lower()
        and not a.get("description", "").startswith("₹0.00")
    ]

    total = len(activities)
    print(f"Found {total} matching trips for {month}.\n")

    if on_progress:
        on_progress({
            "phase": "start",
            "index": 0,
            "total": total,
            "path": None,
        })

    for index, activity in enumerate(activities, start=1):
        trip_uuid = activity["uuid"]
        subtitle = activity.get("subtitle", "")
        title = activity.get("title", "Unknown")
        amount = activity.get("description", "")

        url = BASE_URL.format(trip_uuid)

        print(f"[{index}/{total}] {subtitle}")
        print(f"    {title}")
        print(f"    {amount}")

        saved_path = None
        try:
            response = session.get(url, timeout=30)

            if (
                response.status_code == 200
                and response.headers.get("Content-Type", "").startswith("application/pdf")
            ):
                saved_path = os.path.join(
                    out_dir,
                    f"{subtitle.replace(' • ', '_')}_{trip_uuid}.pdf"
                )

                with open(saved_path, "wb") as pdf:
                    pdf.write(response.content)

                print(f"    ✓ Saved: {saved_path}")

            else:
                print(
                    f"    ✗ Failed: HTTP {response.status_code} "
                    f"({response.headers.get('Content-Type')})"
                )
                print(url)
                print(response.text)

        except requests.RequestException as e:
            print(f"    ✗ Request failed: {e}")

        print()

        if on_progress:
            on_progress({
                "phase": "download",
                "index": index,
                "total": total,
                "path": saved_path,
                "subtitle": subtitle,
            })

    filter_receipts_by_pin(
        pin,
        output_dir=out_dir,
        deleted_dir=del_dir,
        on_progress=on_progress,
    )

    if on_progress:
        on_progress({
            "phase": "done",
            "index": total,
            "total": total,
            "path": None,
        })


if __name__ == "__main__":
    main()
