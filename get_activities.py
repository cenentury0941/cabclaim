import json
import time
from pathlib import Path

import requests

COOKIE_FILE = "Uber_Cookie.txt"
OUTPUT_FILE = "workspace/Activities.json"
LOOKBACK_DAYS = 65

ACTIVITIES_QUERY = """
query Activities(
  $cityID: Int,
  $endTimeMs: Float,
  $includePast: Boolean = true,
  $includeUpcoming: Boolean = true,
  $limit: Int = 5,
  $nextPageToken: String,
  $orderTypes: [RVWebCommonActivityOrderType!] = [RIDES, TRAVEL],
  $profileType: RVWebCommonActivityProfileType = PERSONAL,
  $startTimeMs: Float
) {
  activities(cityID: $cityID) {
    cityID
    past(
      endTimeMs: $endTimeMs
      limit: $limit
      nextPageToken: $nextPageToken
      orderTypes: $orderTypes
      profileType: $profileType
      startTimeMs: $startTimeMs
    ) @include(if: $includePast) {
      activities {
        ...RVWebCommonActivityFragment
        __typename
      }
      nextPageToken
      __typename
    }
    upcoming @include(if: $includeUpcoming) {
      activities {
        ...RVWebCommonActivityFragment
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment RVWebCommonActivityFragment on RVWebCommonActivity {
  buttons {
    isDefault
    startEnhancerIcon
    text
    url
    __typename
  }
  cardURL
  description
  imageURL {
    light
    dark
    __typename
  }
  subtitle
  title
  uuid
  __typename
}
"""


def load_cookie_header(cookie_file=COOKIE_FILE):
    with open(cookie_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def apply_cookie_header(session, cookie_header):
    header = cookie_header.strip()
    if header.lower().startswith("cookie:"):
        header = header[7:].strip()

    for cookie in header.split(";"):
        if "=" in cookie:
            name, value = cookie.strip().split("=", 1)
            session.cookies.set(name, value)


def main(cookie_header=None):
    if cookie_header is None:
        cookie_header = load_cookie_header()

    end_time_ms = int(time.time() * 1000)
    start_time_ms = end_time_ms - (LOOKBACK_DAYS * 24 * 60 * 60 * 1000)

    session = requests.Session()

    session.headers.update({
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "priority": "u=1, i",
        "sec-ch-prefers-color-scheme": "dark",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-csrf-token": "YOUR_CSRF_TOKEN",
        "x-uber-rv-session-type": "desktop_session",
        "referer": (
            f"https://riders.uber.com/trips"
            f"?from={start_time_ms}"
            f"&to={end_time_ms}"
            f"&profile=BUSINESS"
        ),
    })

    apply_cookie_header(session, cookie_header)

    payload = {
        "operationName": "Activities",
        "variables": {
            "includePast": True,
            "includeUpcoming": True,
            "limit": 1000,
            "orderTypes": [
                "RIDES",
                "TRAVEL"
            ],
            "profileType": "BUSINESS",
            "startTimeMs": start_time_ms,
            "endTimeMs": end_time_ms,
        },
        "query": ACTIVITIES_QUERY,
    }

    response = session.post(
        "https://riders.uber.com/graphql",
        json=payload,
    )

    print(f"Status: {response.status_code}")

    response.raise_for_status()

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(response.json(), f, indent=2, ensure_ascii=False)

    print(f"Saved response to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
