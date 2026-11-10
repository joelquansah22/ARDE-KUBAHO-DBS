"""Upload Excel (ARDE/KUBAHO workbook mode): check a newer copy of the MEAL workbook, then add it.

1. Upload the file. It is recognised as ARDE's MEAL workbook by its sheet names (config/arde_format.yaml:
   required_sheets); any other file is refused with the missing sheets named.
2. "Check the file" reads a copy exactly as the pipeline would and runs every check. It shows the rows per sheet,
   values held back and for review, the data-quality score, and what is new or changed against the workbook now in
   use. Nothing is added yet.
3. "Add this file" keeps it in data/real/uploads/ (earlier copies and the original are never deleted or changed)
   and prepares the figures from it.
"""

import subprocess
import sys

import pandas as pd
import streamlit as st

import ui                # first: it makes src/ importable
import arde_pipeline     # noqa: E402
import arde_reader       # noqa: E402
import arde_store        # noqa: E402

f = ui.arde_filters()
ui.page_header("Upload Excel", "arde_upload")
ui.how_to_read("arde_upload")
who, labels, ready = ui.staff_picker("uploading a file")

file = st.file_uploader("ARDE/KUBAHO MEAL workbook (.xlsx)", type=["xlsx"], key="arde_upload_file")
if file is None:
    st.session_state.pop("arde_upload_check", None)
else:
    data = file.getvalue()
    if st.button("Check the file", type="primary", key="arde_upload_check_btn"):
        with st.spinner("Reading a copy of the file as the pipeline would..."):
            try:
                names = arde_reader.sheet_names(data)
                if not arde_reader.is_arde_workbook(names):
                    missing = sorted(set(arde_reader.layout()["required_sheets"]) - set(names))
                    raise arde_reader.WorkbookError(
                        "This is not ARDE/KUBAHO's MEAL workbook: these sheets are missing: " + ", ".join(missing)
                        + ". (Blank templates for the demonstration data are used in synthetic mode only.)")
                run = arde_pipeline.build(data, file.name, with_updates=False)
                st.session_state["arde_upload_check"] = (file.file_id, run, None)
            except arde_reader.WorkbookError as err:
                st.session_state["arde_upload_check"] = (file.file_id, None, str(err))
    held = st.session_state.get("arde_upload_check")
    if held and held[0] == file.file_id:
        _, run, error = held
        if error:
            st.error(error)
        else:
            s = run["summary"]
            t = run["tables"]
            st.markdown("#### What the check found")
            ui.tiles([("Projects / KPIs", f"{len(t['dim_project']):,} / {len(t['fact_kpi']):,}",
                       f"{len(t['fact_result']):,} results, {len(t['fact_project_activity']):,} activities"),
                      ("Held back", f"{int(s.loc[s['level'] == 'held_back', 'flagged'].sum()):,}",
                       "values not used until corrected"),
                      ("For review", f"{int(s.loc[s['level'] == 'review', 'flagged'].sum()):,}", "used, to be checked"),
                      ("Data-quality score", f"{run['score']:.1f}%", "average pass rate of the checks")])
            if run["problems"]:
                st.error("The file cannot be added: " + " ".join(run["problems"]))
            # Against the workbook in use
            now = ui.query("SELECT kpi_code, achieved, kpi_status FROM fact_kpi")
            new = t["fact_kpi"][["kpi_code", "achieved", "kpi_status"]]
            m = now.merge(new, on="kpi_code", how="outer", suffixes=(" now", " in file"), indicator=True)
            changed = m[(m["_merge"] == "both") & ((m["achieved now"] != m["achieved in file"])
                                                   | (m["kpi_status now"] != m["kpi_status in file"]))]
            st.markdown(f"**Against the workbook in use:** {int((m['_merge'] == 'right_only').sum())} new KPIs, "
                        f"{int((m['_merge'] == 'left_only').sum())} KPIs no longer in the file, {len(changed)} KPIs "
                        "with a different achieved value or status.")
            if len(changed):
                ui.table(changed.drop(columns="_merge").rename(columns={"kpi_code": "KPI"}), "upload_changed_kpis",
                         height=220)
            same = arde_store.same_file_uploads(data)
            if same:
                st.warning(f"**This exact file is already in use or was uploaded before** ({same[0]['upload_id']}, "
                           f"{same[0]['uploaded_at']}).")
            _, uploaded_at = arde_store.current_workbook()
            pending = arde_store.current_updates(since=uploaded_at)
            if len(pending):
                st.warning(f"**{len(pending)} KPI updates made on the dashboard** will be replaced by this file's "
                           "values. To keep them, download the register first (Register page), copy the values into "
                           "your file, and upload that.")
            with st.expander("Rows read per sheet, and every check"):
                ui.table(pd.DataFrame({"Sheet": [n for n in run["sheets"] if not n.startswith("_")],
                                       "Rows": [len(v) for n, v in run["sheets"].items() if not n.startswith("_")]}),
                         "upload_sheets")
                ui.table(s[["label", "level", "checked", "flagged"]].rename(
                    columns={"label": "Check", "level": "Kind", "checked": "Checked", "flagged": "Flagged"}),
                    "upload_checks")
            agree = st.checkbox("I have checked the summary and want this file to be used from now on.",
                                key="arde_upload_agree")
            if st.button("Add this file", type="primary", disabled=not (ready and agree and not run["problems"]),
                         key="arde_upload_add"):
                summary = {"kpis": len(t["fact_kpi"]), "projects": len(t["dim_project"]),
                           "held_back": int(s.loc[s["level"] == "held_back", "flagged"].sum()),
                           "to_review": int(s.loc[s["level"] == "review", "flagged"].sum())}
                with st.spinner("Keeping the file and preparing the figures..."):
                    stored = arde_store.add_upload(data, file.name, who, summary)
                    r = subprocess.run([sys.executable, str(ui.ROOT / "src" / "pipeline.py")], cwd=ui.ROOT,
                                       capture_output=True, text=True)
                st.session_state.pop("arde_upload_check", None)
                st.session_state["arde_upload_message"] = (stored, r.returncode == 0, (r.stdout + r.stderr)[-600:])
                st.rerun()

if "arde_upload_message" in st.session_state:
    stored, ok, log = st.session_state.pop("arde_upload_message")
    (st.success if ok else st.error)(f"Added as {stored['upload_id']} ({stored['stored_file']}). "
                                     + ("The figures are up to date." if ok else "The figures could not be prepared: "
                                        "ask the MEAL officer to run the pipeline (maintenance guide). " + log))

st.markdown("#### Workbooks used so far")
done = pd.DataFrame(arde_store.table("uploads"))
original = ui.SETTINGS["arde"]["workbook"]
rows = [{"Upload": "original", "When": "as received", "Who": "-", "File": original.split("/")[-1], "Kept as": original}]
for u in done.to_dict("records") if len(done) else []:
    rows.append({"Upload": u["upload_id"], "When": u["uploaded_at"].replace("T", " ")[:16], "Who": u["uploaded_by"],
                 "File": u["original_name"], "Kept as": u["stored_file"]})
table = pd.DataFrame(rows)
table["In use"] = ["yes" if i == len(table) - 1 else "" for i in range(len(table))]
ui.table(table, "workbooks_used")
ui.footer()
