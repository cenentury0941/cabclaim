"""Upload Receipts — upload Uber and Rapido PDFs to Concur."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

import upload_rapido_to_concur
import upload_uber_to_concur
from web.concur_form import fetch_concur_form_values
from web.field_cookies import hydrate_text_fields, mark_field_dirty, persist_dirty_fields
from web.page_consent import require_page_consent
from web.pdf_preview import list_pdfs
from web.runner import run_streaming
from web.session_state import ensure_ephemeral_text
from web.workspace import clear_workspace_on_session_start, workspace_paths

st.set_page_config(page_title="Upload Receipts — CabClaim", layout="wide")
require_page_consent()
clear_workspace_on_session_start()
paths = workspace_paths()

UBER_FOLDER = paths.uber_receipts
RAPIDO_FOLDER = paths.rapido_receipts

# Concur location list (id → preferredDisplay) for expense locationId.
CONCUR_LOCATIONS: dict[str, str] = {
    "B40D3324AD004966804DDC2B2B160CCF": "Chennai (Ex Madras), INDIA",
    "9060EA8CAE3D411CB92C755DF1F3FDAD": "Hyderabad, INDIA",
    "FE8D20F79A204BA7B2E1B492FDEF3C51": "Bangalore, INDIA",
    "5CC920A84A43436AB5E8EB84F8FF41F3": "Coimbatore, INDIA",
}
DEFAULT_LOCATION_ID = "B40D3324AD004966804DDC2B2B160CCF"

st.title("Upload Receipts")
st.write(
    "Upload optimized receipt PDFs to Concur as expense entries. "
    "Configure shared Concur settings below, then run Uber or Rapido upload separately."
)

hydrate_text_fields("concur_report_id", "concur_user_id", "concur_location_id")
ensure_ephemeral_text("concur_cookie_header")
if st.session_state.get("concur_location_id") not in CONCUR_LOCATIONS:
    st.session_state["concur_location_id"] = DEFAULT_LOCATION_ID

st.subheader("Concur settings")

col_report, col_user = st.columns(2)
with col_report:
    st.text_input(
        "Report ID",
        key="concur_report_id",
        on_change=mark_field_dirty,
        args=("concur_report_id",),
    )
with col_user:
    st.text_input(
        "User ID",
        key="concur_user_id",
        on_change=mark_field_dirty,
        args=("concur_user_id",),
    )

st.selectbox(
    "Location",
    options=list(CONCUR_LOCATIONS.keys()),
    format_func=lambda loc_id: CONCUR_LOCATIONS[loc_id],
    key="concur_location_id",
    on_change=mark_field_dirty,
    args=("concur_location_id",),
)

st.text_area(
    "Concur Cookie Header",
    key="concur_cookie_header",
    height=140,
    help="Browser Cookie header for concursolutions.com",
)
ensure_ephemeral_text("concur_cookie_header")
persist_dirty_fields()


def _shared_kwargs() -> dict:
    return {
        "report_id": (st.session_state.get("concur_report_id") or "").strip(),
        "user_id": (st.session_state.get("concur_user_id") or "").strip(),
        "cookie_header": (st.session_state.get("concur_cookie_header") or "").strip(),
        "location_id": st.session_state.get("concur_location_id") or DEFAULT_LOCATION_ID,
    }


def _validate_concur_settings() -> str | None:
    kwargs = _shared_kwargs()
    if not kwargs["report_id"]:
        return "Report ID is empty."
    if not kwargs["user_id"]:
        return "User ID is empty."
    if not kwargs["cookie_header"]:
        return "Concur Cookie Header is empty."
    if kwargs["location_id"] not in CONCUR_LOCATIONS:
        return "Location is invalid."
    return None


def _form_inject_kwargs() -> dict[str, str]:
    values_by_field = {
        field["field_id"]: field["id"]
        for field in st.session_state.get("concur_main_form_values", [])
    }
    return {
        "org_unit1_id": values_by_field.get("orgUnit1", ""),
        "org_unit2_id": values_by_field.get("orgUnit2", ""),
        "org_unit3_id": values_by_field.get("orgUnit3", ""),
        "policy_id": st.session_state.get("concur_policy_id") or "",
        "expense_list_detail_form_id": (
            st.session_state.get("concur_expense_list_detail_form_id") or ""
        ),
    }


def _validate_form_inject_values() -> str | None:
    context = st.session_state.get("concur_main_form_context")
    settings = _shared_kwargs()
    if context != {
        "report_id": settings["report_id"],
        "user_id": settings["user_id"],
    }:
        return "Fetch the Concur form values for the current Report ID and User ID."
    injected = _form_inject_kwargs()
    if not all(
        injected[key]
        for key in (
            "org_unit1_id",
            "org_unit2_id",
            "org_unit3_id",
            "policy_id",
            "expense_list_detail_form_id",
        )
    ):
        return (
            "Concur form values must include IDs for orgUnit1–3, policyId, "
            "and expenseListDetailFormId."
        )
    return None


def _render_concur_form_values() -> None:
    st.subheader("Concur form values")
    st.caption(
        "Fetch policy IDs and the current list values for mainForm fields 24, 25, and 26."
    )

    if st.button("Fetch form values", key="fetch_concur_form_values"):
        error = _validate_concur_settings()
        if error:
            st.error(error)
        else:
            st.session_state.pop("concur_main_form_values", None)
            st.session_state.pop("concur_main_form_context", None)
            st.session_state.pop("concur_policy_id", None)
            st.session_state.pop("concur_expense_list_detail_form_id", None)
            try:
                with st.spinner("Fetching form values from Concur…"):
                    settings = _shared_kwargs()
                    fetched = fetch_concur_form_values(
                        report_id=settings["report_id"],
                        user_id=settings["user_id"],
                        cookie_header=settings["cookie_header"],
                    )
            except Exception as exc:
                st.error(f"Could not fetch Concur form values: {exc}")
            else:
                st.session_state["concur_main_form_values"] = fetched["fields"]
                st.session_state["concur_policy_id"] = fetched["policy_id"]
                st.session_state["concur_expense_list_detail_form_id"] = fetched[
                    "expense_list_detail_form_id"
                ]
                st.session_state["concur_main_form_context"] = {
                    "report_id": settings["report_id"],
                    "user_id": settings["user_id"],
                }
                st.success("Concur form values fetched.")

    policy_id = st.session_state.get("concur_policy_id")
    form_id = st.session_state.get("concur_expense_list_detail_form_id")
    if policy_id or form_id:
        st.markdown("**Policy**")
        policy_col, form_col = st.columns(2)
        st.session_state["concur_form_policy_id_display"] = policy_id or ""
        st.session_state["concur_form_expense_list_detail_form_id_display"] = (
            form_id or ""
        )
        with policy_col:
            st.text_input(
                "policyId",
                key="concur_form_policy_id_display",
                disabled=True,
            )
        with form_col:
            st.text_input(
                "expenseListDetailFormId",
                key="concur_form_expense_list_detail_form_id_display",
                disabled=True,
            )

    for field in st.session_state.get("concur_main_form_values", []):
        st.markdown(
            f"**Field {field['field_index']} — {field['label']} "
            f"(`{field['field_id']}`)**"
        )
        id_col, value_col = st.columns(2)
        id_key = f"concur_form_{field['field_index']}_id"
        value_key = f"concur_form_{field['field_index']}_value"
        st.session_state[id_key] = field["id"]
        st.session_state[value_key] = field["value"]
        with id_col:
            st.text_input("ID", key=id_key, disabled=True)
        with value_col:
            st.text_input("Value", key=value_key, disabled=True)


def _render_live_expenses(
    results: list[dict],
    *,
    highlight: str | None = None,
    container,
) -> None:
    with container.container():
        st.markdown("**Expenses (live)**")
        if not results:
            st.caption("Waiting for uploads…")
            return
        for item in results:
            filename = item["filename"]
            if item.get("pending"):
                label = f"{filename} — uploading…"
            elif item.get("success"):
                expense_id = item.get("expense_id") or "created"
                label = f"{filename} → {expense_id}"
            else:
                label = f"{filename} — failed"
            if highlight and filename == highlight:
                st.markdown(f"- **{label}**")
            else:
                st.markdown(f"- {label}")


def _run_upload_section(
    *,
    label: str,
    folder: Path,
    upload_main: Callable,
    button_key: str,
) -> None:
    count = len(list_pdfs(folder))
    st.caption(f"Found **{count}** receipt(s) ready to upload.")

    progress_slot = st.empty()
    status_slot = st.empty()
    log_slot = st.empty()
    live_list_slot = st.empty()

    if not st.button(f"Upload {label}", type="primary", key=button_key):
        return

    error = _validate_concur_settings()
    if error:
        st.error(error)
        return
    error = _validate_form_inject_values()
    if error:
        st.error(error)
        return
    if count == 0:
        st.error(f"No {label} receipt PDFs found. Run earlier pipeline steps first.")
        return

    results: list[dict] = []
    progress_slot.progress(0, text="Starting…")
    status_slot.info(f"Uploading {label} receipts…")
    _render_live_expenses(results, container=live_list_slot)

    def on_output(text: str) -> None:
        log_slot.code(text or "(no output)", language="text")

    def on_progress(event: dict) -> None:
        phase = event.get("phase")
        index = int(event.get("index") or 0)
        total = int(event.get("total") or 0)
        filename = event.get("filename") or ""

        if phase == "start":
            progress_slot.progress(0, text=f"Found {total} receipt(s) — starting…")
            status_slot.info(f"Uploading 0 / {total}…")
        elif phase == "processing":
            results[:] = [
                item for item in results if item.get("filename") != filename
            ]
            results.append({"filename": filename, "pending": True})
            frac = ((index - 1) / total) if total else 0.0
            progress_slot.progress(
                min(frac, 1.0),
                text=f"Upload {index} / {total}: {filename}",
            )
            status_slot.info(f"Uploading {index} / {total}: {filename}")
            _render_live_expenses(results, highlight=filename, container=live_list_slot)
        elif phase == "expense":
            for item in results:
                if item.get("filename") == filename:
                    item["pending"] = False
                    item["success"] = bool(event.get("success"))
                    item["expense_id"] = event.get("expense_id")
                    break
            else:
                results.append({
                    "filename": filename,
                    "pending": False,
                    "success": bool(event.get("success")),
                    "expense_id": event.get("expense_id"),
                })
            frac = (index / total) if total else 1.0
            state = "created" if event.get("success") else "failed"
            progress_slot.progress(
                min(frac, 1.0),
                text=f"Upload {index} / {total}: {filename} ({state})",
            )
            status_slot.info(f"Uploaded {index} / {total}…")
            _render_live_expenses(results, highlight=filename, container=live_list_slot)
        elif phase == "done":
            progress_slot.progress(1.0, text="Complete")
            _render_live_expenses(results, container=live_list_slot)

    ok, log = run_streaming(
        lambda: upload_main(
            **_shared_kwargs(),
            **_form_inject_kwargs(),
            pdf_folder=str(folder),
            on_progress=on_progress,
        ),
        label=f"Upload {label} Receipts",
        on_output=on_output,
    )

    log_slot.code(log or "(no output)", language="text")
    if ok:
        status_slot.success(f"{label} upload finished.")
        progress_slot.progress(1.0, text="Complete")
    else:
        status_slot.error(f"{label} upload failed — see log above.")


st.divider()
_render_concur_form_values()

st.divider()
st.subheader("Upload Uber receipts")
st.caption(f"PDF folder: `{UBER_FOLDER}`")
_run_upload_section(
    label="Uber",
    folder=UBER_FOLDER,
    upload_main=upload_uber_to_concur.main,
    button_key="upload_uber",
)

st.divider()
st.subheader("Upload Rapido receipts")
st.caption(f"PDF folder: `{RAPIDO_FOLDER}`")
_run_upload_section(
    label="Rapido",
    folder=RAPIDO_FOLDER,
    upload_main=upload_rapido_to_concur.main,
    button_key="upload_rapido",
)
