"""Upload Excel: staff upload a filled template here instead of copying files into data/raw.

1. Download a blank template (top of the page), fill it in Excel.
2. Upload it and click "Check the file": the page reads it exactly as the pipeline would (src/uploads.py) and says,
   in plain words, how many rows are accepted, held back for correction (with the row number and the reason), sent
   for review, and any sheet that was SKIPPED. It warns if the same file, or one with the same records, was already
   uploaded. Nothing is added yet.
3. Click "Add this file": the file is kept in data/raw/ with the date and the staff code of the person who uploaded
   it, recorded in the uploads list, and the figures are prepared again.

To correct rows that were held back: correct them in the Excel file and upload it again, choosing to replace the
earlier file (it is kept in data/app/replaced_files/, never deleted).
"""

import pandas as pd
import streamlit as st

import ui                 # first: it makes src/ importable
import app_store          # noqa: E402
import uploads            # noqa: E402

f = ui.filters(sex_applies=False)
ui.page_header("Upload Excel", "upload_excel")
ui.how_to_read("upload_excel")

who, labels, ready = ui.staff_picker("uploading a file")

# ------------------------------------------------------------------ blank templates
st.markdown("#### 1. Blank templates")
cols = st.columns(len(uploads.TEMPLATES))
for col, (kind, name) in zip(cols, uploads.TEMPLATES.items()):
    path = ui.ROOT / "templates" / name
    col.download_button(f"⬇ {uploads.KINDS[kind]}", path.read_bytes() if path.exists() else b"", file_name=name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        disabled=not path.exists(), key=f"dl_template_{kind}", width="stretch")
st.caption("Each template has an Instructions sheet and drop-down lists. Keep the column headings as they are.")

# ------------------------------------------------------------------ upload and check
st.markdown("#### 2. Upload a filled template")
file = st.file_uploader("Excel file (.xlsx)", type=["xlsx"], key="upload_file")
if file is None:
    st.session_state.pop("upload_summary", None)
else:
    data = file.getvalue()
    guess = uploads.guess_kind(data)
    kinds = list(uploads.KINDS)
    kind = st.selectbox("What kind of file is it?", kinds, index=kinds.index(guess) if guess else 0,
                        format_func=uploads.KINDS.get, key=f"upload_kind_{file.file_id}",
                        help="Worked out from the sheet names; change it if it is wrong.")
    if st.button("Check the file", type="primary", key="upload_check"):
        with st.spinner("Reading the file as the pipeline would..."):
            st.session_state["upload_summary"] = (file.file_id, kind, uploads.check(data, file.name, kind))
    held = st.session_state.get("upload_summary")
    if held and held[0] == file.file_id and held[1] == kind:
        s = held[2]
        if s["error"]:
            st.error(s["error"])
        else:
            st.markdown("#### 3. What the check found")
            ui.tiles([("Rows read", f"{s['rows_read']:,}", "data rows in the file"),
                      ("Accepted", f"{s['accepted']:,}", "go into the figures"),
                      ("Held back for correction", f"{s['held_back']:,}", "not counted until corrected"),
                      ("Sent for review", f"{s['to_review']:,}", "counted, to be checked")])
            if s["removed"]:
                st.caption(f"{s['removed']} rows were exact repeats of another row in the file and are counted once.")
            for message in s["skipped"]:
                st.warning(f"SKIPPED: {message}")
            if not s["rows_read"] and not s["skipped"]:
                st.warning("No data rows were found. Check that this is a filled template of the kind chosen above.")
            if s["same_file"]:
                u = s["same_file"][0]
                st.warning(f"**This exact file was already uploaded**: by {u['uploaded_by']} on "
                           f"{u['uploaded_at'][:16].replace('T', ' ')} ({u['original_name']}, {u['upload_id']}). "
                           "Adding it again would count its records twice.")
            replace = []
            if s["overlaps"]:
                st.warning("**Some records are already in other files** (same project, activity, date, place and "
                           "participants; or the same report, person or opportunity):\n\n"
                           + "\n".join(f"- {n:,} rows match {name}" for name, n in s["overlaps"].items())
                           + "\n\nIf this file is a corrected version, replace the earlier file so the records are not "
                             "counted twice.")
                replace = st.multiselect("Replace these earlier files (they are kept in data/app/replaced_files/)",
                                         list(s["overlaps"]), key="upload_replace")
            if len(s["held_list"]):
                st.markdown(f"**Held back for correction ({len(s['held_list'])} rows).** Correct these rows in the "
                            "Excel file and upload it again.")
                ui.table(s["held_list"], "upload_held_back", height=240)
            if len(s["review_list"]):
                st.markdown(f"**Sent for review ({len(s['review_list'])} rows).** They are counted; the MEAL officer "
                            "checks them on the Data quality page.")
                ui.table(s["review_list"], "upload_for_review", height=240)
            st.markdown("#### 4. Add the file")
            risky = bool(s["same_file"]) or (bool(s["overlaps"]) and not replace)
            agree = st.checkbox("Add it anyway: I have checked the warnings above." if risky else
                                "I have checked the summary and want to add this file.", key="upload_agree")
            if st.button("Add this file", type="primary", disabled=not (ready and agree and s["rows_read"]),
                         key="upload_accept"):
                with st.spinner("Keeping the file and preparing the figures (about 20 seconds)..."):
                    result = uploads.accept(data, file.name, kind, who, s, replace)
                st.session_state.pop("upload_summary", None)
                st.session_state["upload_message"] = result
                st.rerun()

if "upload_message" in st.session_state:
    r = st.session_state.pop("upload_message")
    (st.success if r["pipeline_ok"] else st.error)(
        f"Added as {r['upload_id']} ({r['stored_file']})."
        + (" The figures are up to date." if r["pipeline_ok"] else
           " The figures could not be prepared: ask the MEAL officer to run the pipeline (maintenance guide)."))

# ------------------------------------------------------------------ uploads so far
st.markdown("#### Files uploaded so far")
done = pd.DataFrame(app_store.table("uploads"))
if not len(done):
    st.caption("None yet. Files copied into data/raw by hand are read too; they are listed on the Data quality page.")
else:
    done = done.sort_values("row_id", ascending=False)
    ui.table(pd.DataFrame({
        "Upload": done["upload_id"], "When": done["uploaded_at"].str[:16].str.replace("T", " "),
        "Who": done["uploaded_by"], "File uploaded": done["original_name"], "Kept as": done["stored_file"],
        "Kind": done["kind"].map(uploads.KINDS), "Rows": done["rows_read"], "Accepted": done["accepted"],
        "Held back": done["held_back"], "For review": done["to_review"],
        "Status": done["status"].where(done["status"] != "replaced", "replaced by " + done["replaced_by"].fillna(""))}),
        "uploads")

ui.footer()
