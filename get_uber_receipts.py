import json
import os
import requests
import pymupdf
import shutil

from utils import pdf_contains_pin

BASE_URL = "https://riders.uber.com/trips/{}/receipt?contentType=PDF"

ACTIVITIES_FILE = "Activities.json"
COOKIE_FILE = "Uber_Cookie.txt"
OUTPUT_DIR = "workspace/uber_receipts"
DELETED_DIR = "workspace/deleted_uber_receipts"

# Three-letter month abbreviation (Jan, Feb, Mar, ...)
TARGET_MONTH = "Jul"

# Change to the PIN you want to keep. Defaults to 600032 (Ekkatuthangal)
TARGET_PIN = "600032"


def load_cookies(cookie_file):
    """Load cookies from a Uber_Cookie.txt file."""
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookie_string = f.read().strip()

    # Remove "Cookie:" prefix if present
    if cookie_string.lower().startswith("cookie:"):
        cookie_string = cookie_string[7:].strip()

    cookies = {}
    for cookie in cookie_string.split(";"):
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            cookies[key.strip()] = value.strip()

    return cookies


def filter_receipts_by_pin():
    """Delete uber_receipts that do not contain the target PIN."""
    print(f"\nFiltering uber_receipts for PIN {TARGET_PIN}...\n")

    kept = 0
    deleted = 0

    for filename in os.listdir(OUTPUT_DIR):
        if not filename.lower().endswith(".pdf"):
            continue

        filepath = os.path.join(OUTPUT_DIR, filename)
        delete_path = os.path.join(DELETED_DIR, filename)

        if pdf_contains_pin(filepath, TARGET_PIN):
            print(f"✓ Keeping {filename}")
            kept += 1
        else:
            shutil.move(filepath, delete_path)
            print(f"✗ Deleted {filename}")
            deleted += 1

    print("\nFiltering complete.")
    print(f"Kept: {kept}")
    print(f"Deleted: {deleted}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DELETED_DIR, exist_ok=True)

    with open(ACTIVITIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = requests.Session()
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
        if TARGET_MONTH.lower() in a.get("subtitle", "").lower()
        and not a.get("description", "").startswith("₹0.00")
    ]

    print(f"Found {len(activities)} matching trips for {TARGET_MONTH}.\n")

    for index, activity in enumerate(activities, start=1):
        trip_uuid = activity["uuid"]
        subtitle = activity.get("subtitle", "")
        title = activity.get("title", "Unknown")
        amount = activity.get("description", "")

        url = BASE_URL.format(trip_uuid)

        print(f"[{index}/{len(activities)}] {subtitle}")
        print(f"    {title}")
        print(f"    {amount}")

        try:
            response = session.get(url, timeout=30)

            if (
                response.status_code == 200
                and response.headers.get("Content-Type", "").startswith("application/pdf")
            ):
                filename = os.path.join(
                    OUTPUT_DIR,
                    f"{subtitle.replace(' • ', '_')}_{trip_uuid}.pdf"
                )

                with open(filename, "wb") as pdf:
                    pdf.write(response.content)

                print(f"    ✓ Saved: {filename}")

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

    filter_receipts_by_pin()


if __name__ == "__main__":
    main()