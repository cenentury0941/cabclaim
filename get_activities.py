import json
import time
import requests

# Calculate timestamps (last 65 days)
end_time_ms = int(time.time() * 1000)
start_time_ms = end_time_ms - (65 * 24 * 60 * 60 * 1000)

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

# Load cookies from Uber_Cookie.txt
with open("Uber_Cookie.txt", "r", encoding="utf-8") as f:
    cookie_header = f.read().strip()

# Parse "name=value; name2=value2; ..."
for cookie in cookie_header.split(";"):
    if "=" in cookie:
        name, value = cookie.strip().split("=", 1)
        session.cookies.set(name, value)

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
    "query": """
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
}

response = session.post(
    "https://riders.uber.com/graphql",
    json=payload,
)

print(f"Status: {response.status_code}")

response.raise_for_status()

# Save the response JSON to Activities.json
with open("Activities.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=2, ensure_ascii=False)

print("Saved response to Activities.json")