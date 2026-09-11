"""Fetch selected default values from Concur's new-expense form."""

from __future__ import annotations

import uuid

import requests

GRAPHQL_URL = "https://www-us2.api.concursolutions.com/spend-graphql/graphql"
TARGET_FIELD_INDEXES = (24, 25, 26)

NEW_EXPENSE_FORM_QUERY = """
query GetNewExpenseEntry(
  $reportIdAsID: ID!
  $userIdAsID: ID!
  $expenseTypeId: ID!
  $contextRole: ContextRoleType!
) {
  newExpenseForm(
    dataContext: {
      reportId: $reportIdAsID
      expenseTypeId: $expenseTypeId
      expenseTypeChangeContext: null
    }
    userContext: {userId: $userIdAsID, contextType: $contextRole}
  ) {
    mainForm {
      fields {
        id
        label
        value {
          ... on ListValue {
            listValue: value {
              id
              value
            }
          }
        }
      }
    }
  }
}
"""


def _cookies_from_header(cookie_header: str) -> dict[str, str]:
    cookies = {}
    for cookie in cookie_header.strip().split(";"):
        if "=" in cookie:
            name, value = cookie.strip().split("=", 1)
            cookies[name] = value
    return cookies


def fetch_main_form_list_values(
    *,
    report_id: str,
    user_id: str,
    cookie_header: str,
) -> list[dict[str, str]]:
    """Return the listValue ID and value for mainForm fields 24 through 26."""
    payload = {
        "operationName": "GetNewExpenseEntry",
        "variables": {
            "contextRole": "TRAVELER",
            "userIdAsID": user_id,
            "reportIdAsID": report_id,
            "expenseTypeId": "01102",
        },
        "query": NEW_EXPENSE_FORM_QUERY,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Accept-Language": "en",
        "Content-Type": "application/json",
        "concur-correlationid": str(uuid.uuid4()),
    }

    response = requests.post(
        GRAPHQL_URL,
        headers=headers,
        cookies=_cookies_from_header(cookie_header),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in result["errors"]
        )
        raise RuntimeError(messages)

    try:
        fields = result["data"]["newExpenseForm"]["mainForm"]["fields"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Concur response did not include mainForm fields.") from exc

    if len(fields) <= TARGET_FIELD_INDEXES[-1]:
        raise RuntimeError(
            f"Concur returned {len(fields)} mainForm fields; expected at least 27."
        )

    values = []
    for index in TARGET_FIELD_INDEXES:
        field = fields[index]
        list_value = (field.get("value") or {}).get("listValue")
        if not list_value:
            raise RuntimeError(
                f"mainForm field {index} ({field.get('label') or field.get('id')}) "
                "did not include a listValue."
            )
        values.append({
            "field_index": str(index),
            "field_id": field.get("id") or f"field_{index}",
            "label": field.get("label") or f"Field {index}",
            "id": list_value.get("id") or "",
            "value": list_value.get("value") or "",
        })

    return values
