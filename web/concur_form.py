"""Fetch selected default values from Concur's new-expense form."""

from __future__ import annotations

import uuid

import requests

GRAPHQL_URL = "https://www-us2.api.concursolutions.com/spend-graphql/graphql"
TARGET_FIELD_INDEXES = (24, 25, 26)

NEW_EXPENSE_FORM_QUERY = """
query GetNewExpenseEntry(
  $reportId: String!
  $userId: String!
  $reportIdAsID: ID!
  $userIdAsID: ID!
  $expenseTypeId: ID!
  $contextRole: ContextRoleType!
) {
  employee(userId: $userId, contextRole: $contextRole) {
    expenseReport(reportId: $reportId) {
      reportDetails {
        policy {
          id
          expenseListDetailFormId
        }
      }
    }
  }
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


def fetch_concur_form_values(
    *,
    report_id: str,
    user_id: str,
    cookie_header: str,
) -> dict:
    """Return org-unit list values plus policy IDs from GetNewExpenseEntry."""
    payload = {
        "operationName": "GetNewExpenseEntry",
        "variables": {
            "contextRole": "TRAVELER",
            "userId": user_id,
            "userIdAsID": user_id,
            "reportId": report_id,
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
        policy = result["data"]["employee"]["expenseReport"]["reportDetails"]["policy"]
        fields = result["data"]["newExpenseForm"]["mainForm"]["fields"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            "Concur response did not include policy or mainForm fields."
        ) from exc

    policy_id = (policy or {}).get("id") or ""
    expense_list_detail_form_id = (policy or {}).get("expenseListDetailFormId") or ""
    if not policy_id or not expense_list_detail_form_id:
        raise RuntimeError(
            "Concur policy did not include id and expenseListDetailFormId."
        )

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

    return {
        "fields": values,
        "policy_id": policy_id,
        "expense_list_detail_form_id": expense_list_detail_form_id,
    }
