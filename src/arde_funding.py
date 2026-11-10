"""Funding opportunities in ARDE/KUBAHO workbook mode: one definition for the Executive summary and Donor pipeline.

The workbook holds funding RECEIVED (Stakeholders sheet: the funding history). Opportunities still being pursued
are entered on the Donor entry page and kept in data/real/app/entries.db (src/app_store.py, which uses that file in
arde mode). They are read straight from that file, so a new opportunity shows at once.

Definitions are the demo's (config/settings.yaml: donor_pipeline): open = a stage in open_stages; weighted value =
amount requested x probability; deadlines and overdue next actions are counted from "today" (arde.as_of_date).
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

import app_store
from common import load_settings

COLUMNS = ["opportunity_id", "donor", "title", "thematic_fit", "stage", "deadline", "requested_amount_rwf",
           "awarded_amount_rwf", "probability", "owner", "next_action", "next_action_date", "is_open", "weighted"]


def opportunities() -> pd.DataFrame:
    """Every opportunity entered on the Donor entry page, with the donor's name (individuals unnamed)."""
    opps = pd.DataFrame(app_store.table("opportunities"))
    if not len(opps):
        return pd.DataFrame(columns=COLUMNS)
    donors = pd.DataFrame(app_store.table("donors"))
    names = {}
    for i, d in enumerate(donors.to_dict("records") if len(donors) else [], start=1):
        names[d["donor_id"]] = d["donor_name"] or f"Individual donor #{i:03d}"
    opps["donor"] = opps["donor_id"].map(names).fillna("")
    for col in ("deadline", "next_action_date"):
        opps[col] = pd.to_datetime(opps[col], errors="coerce").dt.date
    s = load_settings()["donor_pipeline"]
    opps["is_open"] = opps["stage"].isin(s["open_stages"])
    opps["weighted"] = opps["requested_amount_rwf"].fillna(0) * opps["probability"].fillna(0)
    return opps[COLUMNS]


def deadlines_within(opps: pd.DataFrame, today: dt.date, days: int) -> pd.DataFrame:
    """Open opportunities whose deadline falls in the next `days` days."""
    end = today + dt.timedelta(days=days)
    keep = opps["is_open"] & opps["deadline"].map(lambda d: d is not None and not pd.isna(d) and today <= d <= end)
    return opps[keep].sort_values("deadline")


def overdue_actions(opps: pd.DataFrame, today: dt.date) -> pd.DataFrame:
    """Open opportunities whose next action date has passed."""
    keep = opps["is_open"] & opps["next_action_date"].map(lambda d: d is not None and not pd.isna(d) and d < today)
    return opps[keep].sort_values("next_action_date")
