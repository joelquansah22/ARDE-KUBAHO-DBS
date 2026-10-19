"""Shared helpers for the dashboard pages: data access, filters, labels and tables.

The dashboard only READS the warehouse (data/warehouse/arde.duckdb). Queries are cached and the cache
is refreshed automatically when the pipeline rebuilds the warehouse.
"""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "src", Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from common import fiscal_year_label, load_settings, load_yaml, resolve_path  # noqa: E402

SETTINGS = load_settings()
OPEN_STAGES = SETTINGS["donor_pipeline"]["open_stages"]
LABELS = SETTINGS["labels"]

# Colours: config/theme.yaml (brand colours to be confirmed with partner). Status colours are fixed and separate.
THEME = load_yaml("theme.yaml")
COLOURS = THEME["colours"]
CHART = THEME["chart_categorical"]           # chart series, in order
_S = THEME["status"]
WARNING = _S["at_risk"]                      # over-budget and "check this" marks (the fixed amber)
COMPARE = CHART[2]                           # targets, records, amounts requested: the comparison series

# Traffic lights never rely on colour alone: every status has a symbol and words.
STATUS = {
    "on track": ("✔", "On track", _S["on_track"]),
    "at risk": ("▲", "At risk", _S["at_risk"]),
    "off track": ("✖", "Off track", _S["off_track"]),
    "target incomplete": ("◔", "Target incomplete", _S["no_target"]),
    "no target set": ("–", "No target set", _S["no_target"]),
    "no data": ("…", "No data", _S["no_target"]),
}


def _register_chart_template() -> None:
    """Every Plotly chart uses the brand palette (config/theme.yaml: chart_categorical) on a white chart area."""
    import plotly.graph_objects as go
    import plotly.io as pio
    pio.templates["arde"] = go.layout.Template(layout=dict(
        colorway=CHART, font=dict(color=COLOURS["text"]), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        legend=dict(font=dict(color=COLOURS["text"]))))
    pio.templates.default = "plotly_white+arde"


_register_chart_template()


# ---------------------------------------------------------------- data access
def db_path() -> Path:
    return resolve_path("warehouse")


@st.cache_resource(show_spinner=False)
def _connection(version: float):
    return duckdb.connect(str(db_path()), read_only=True)


def db_version() -> float:
    path = db_path()
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False, max_entries=500)
def _query(sql: str, params: tuple, version: float) -> pd.DataFrame:
    return _connection(version).cursor().execute(sql, list(params)).df()


NOT_BUILT = """
### The figures have not been prepared yet

The dashboard reads the figures that the **pipeline** prepares from the Excel files, and it has not been run on this
computer yet (or its results were deleted).

**What to do:**
1. Close this window.
2. Double-click **`run_dashboard.bat`** in the project folder. It prepares the figures first (about one minute)
   and then opens the dashboard again.

Or, in a terminal in the project folder: `python src/pipeline.py`, then refresh this page.
If this message comes back, see "Problems and what to do" in `docs/user_guide.md`.
"""


def require_warehouse() -> None:
    """A friendly message (instead of an error) when the pipeline has not been run yet."""
    if not db_path().exists():
        st.info(NOT_BUILT)
        st.stop()


def query(sql: str, *params) -> pd.DataFrame:
    """Run a read-only SQL query on the warehouse (cached until the warehouse is rebuilt)."""
    require_warehouse()
    return _query(sql, tuple(params), db_version())


@st.cache_data(show_spinner=False)
def catalogue() -> dict:
    return {i["code"]: i for i in load_yaml("indicator_catalogue.yaml")["indicators"]}


# ---------------------------------------------------------------- filters
@dataclass
class Filters:
    programme_id: str | None
    project_id: str | None
    district: str | None
    start: dt.date
    end: dt.date
    sex: str | None          # None, "female" or "male"
    currency: str            # RWF or USD

    @property
    def project_ids(self) -> list[str]:
        projects = query("SELECT project_id, programme_id FROM dim_project")
        if self.project_id:
            return [self.project_id]
        if self.programme_id:
            return list(projects.loc[projects["programme_id"] == self.programme_id, "project_id"])
        return list(projects["project_id"])

    @property
    def scope_text(self) -> str:
        parts = [self.project_id or (self.programme_id and f"programme {self.programme_id}") or "all projects",
                 self.district or "all districts"]
        return ", ".join(parts)


def _remember(key: str, default):
    """Keep a filter's value when moving between pages."""
    if key not in st.session_state:
        st.session_state[key] = default
    return key


def sidebar_filters(sex_applies: bool) -> Filters:
    programmes = query("SELECT programme_id, name FROM dim_programme ORDER BY 1")
    projects = query("SELECT project_id, programme_id, name FROM dim_project ORDER BY 1")
    districts = query("SELECT DISTINCT district FROM dim_location WHERE location_level = 'village' ORDER BY 1")
    window = SETTINGS["reporting_window"]
    sb = st.sidebar
    sb.markdown("**Filters**")
    prog_names = {"All programmes": None} | {f"{r.programme_id} {r.name}": r.programme_id for r in programmes.itertuples()}
    prog_label = sb.selectbox("Programme", list(prog_names), key=_remember("f_programme", "All programmes"))
    programme_id = prog_names[prog_label]
    shown = projects if not programme_id else projects[projects["programme_id"] == programme_id]
    proj_names = {"All projects": None} | {f"{r.project_id} {r.name}": r.project_id for r in shown.itertuples()}
    if st.session_state.get("f_project") not in proj_names:
        st.session_state["f_project"] = "All projects"
    proj_label = sb.selectbox("Project", list(proj_names), key=_remember("f_project", "All projects"))
    dist_label = sb.selectbox("District", ["All districts"] + list(districts["district"]),
                              key=_remember("f_district", "All districts"))
    dates = sb.date_input("Date range", key=_remember("f_dates", (window["start"], window["end"])),
                          min_value=dt.date(window["start"].year - 1, 1, 1), max_value=dt.date(window["end"].year + 1, 12, 31),
                          format="DD/MM/YYYY")
    start, end = (dates if isinstance(dates, (tuple, list)) and len(dates) == 2 else (window["start"], window["end"]))
    sex = sb.radio("Sex", ["All", "Female", "Male"], key=_remember("f_sex", "All"), horizontal=True,
                   disabled=not sex_applies,
                   help="Applies to people counts and to indicators broken down by sex. Not used on this page."
                   if not sex_applies else "Applies to people counts and to indicators broken down by sex.")
    currency = (sb.radio("Currency", ["RWF", "USD"], key=_remember("f_currency", "RWF"), horizontal=True,
                         help=f"USD at {SETTINGS['currency']['usd_to_rwf']:,} RWF per USD (settings.yaml).")
                if SETTINGS["currency"].get("show_usd_option", True) else "RWF")
    return Filters(programme_id, proj_names[proj_label], None if dist_label == "All districts" else dist_label,
                   start, end, None if (sex == "All" or not sex_applies) else sex.lower(), currency)


def filters(sex_applies: bool = True) -> Filters:
    """The sidebar filters. Normally set up by app.py; if a page is run on its own (for example by the tests,
    or with `streamlit run dashboard/pages/...`), the page sets up the banner and filters itself."""
    if "filters" not in st.session_state or st.session_state.get("_standalone"):
        st.session_state["_standalone"] = True
        st.markdown(CSS, unsafe_allow_html=True)
        sidebar_logo()
        banner()
        require_warehouse()
        st.session_state["filters"] = sidebar_filters(sex_applies)
        source_files_in_sidebar()
    return st.session_state["filters"]


# ---------------------------------------------------------------- labels and formatting
def banner() -> None:
    if SETTINGS.get("synthetic_mode"):
        st.markdown(f"<div class='synthetic-banner'>⚠ {SETTINGS['synthetic_banner']}</div>", unsafe_allow_html=True)


def how_to_read(page: str) -> None:
    """The collapsed "How to read this page" guide (text in config/page_help.yaml, editable by staff)."""
    text = load_yaml("page_help.yaml").get(page)
    if text:
        with st.expander("How to read this page"):
            st.markdown(text)


def no_data(what: str = "for this selection") -> None:
    """A plain message instead of empty charts and tables."""
    st.info(f"Nothing was recorded {what}. Try a wider date range, or another programme, project or district "
            "in the filters on the left.")


@st.cache_data(show_spinner=False)
def _source_files(version: float) -> pd.DataFrame:
    return _connection(version).cursor().execute(
        "SELECT DISTINCT source_file FROM dq_by_source_file ORDER BY 1").df()


def data_updated() -> tuple[str, list[str]]:
    """When the figures were last prepared (the warehouse file's time) and the Excel files they came from."""
    version = db_version()
    when = dt.datetime.fromtimestamp(version).strftime("%d %B %Y, %H:%M") if version else "never"
    files = list(_source_files(version)["source_file"]) if version else []
    return when, files


def footer() -> None:
    """One line at the bottom of every page (also printed): when the data was last updated, from which files.
    The list of files is in the sidebar ("Source files"), so the line stays short."""
    when, files = data_updated()
    st.markdown(f"<div class='muted' style='margin-top:0.6rem;border-top:1px solid {COLOURS['border']};padding-top:0.3rem'>"
                f"Data last updated {when} from {len(files)} source files (listed in the sidebar). Figures as of "
                f"{as_of():%d %B %Y}.</div>", unsafe_allow_html=True)


def source_files_in_sidebar() -> None:
    """The sidebar's data date and "Source files" list, on every page."""
    when, files = data_updated()
    st.sidebar.caption(f"Data as of {as_of():%d %B %Y}; last updated {when}. Figures are worked out by the pipeline; "
                       "see the data dictionary for definitions.")
    with st.sidebar.expander(f"Source files ({len(files)})"):
        st.markdown("\n".join(f"- {f}" for f in files) or "None")


def status_label(status: str, note: str | None = None) -> str:
    symbol, words, _ = STATUS.get(status, ("", str(status), _S["no_target"]))
    return f"{symbol} {words}" + (f" ({note})" if note else "")


def status_html(status: str, note: str | None = None) -> str:
    symbol, words, colour = STATUS.get(status, ("", str(status), _S["no_target"]))
    extra = f" <span class='muted'>({note})</span>" if note else ""
    return f"<span style='color:{colour};font-weight:600'>{symbol} {words}</span>{extra}"


def money(rwf, currency: str | None = None, short: bool = False) -> str:
    if currency is None:
        chosen = st.session_state.get("filters")
        currency = chosen.currency if chosen is not None else "RWF"
    if rwf is None or pd.isna(rwf):
        return "–"
    value = float(rwf) / (SETTINGS["currency"]["usd_to_rwf"] if currency == "USD" else 1)
    if short and abs(value) >= 1_000_000_000:
        return f"{currency} {value / 1_000_000_000:,.2f}bn"
    if short and abs(value) >= 1_000_000:
        return f"{currency} {value / 1_000_000:,.1f}m"
    return f"{currency} {value:,.0f}"


def number(x, unit: str = "number") -> str:
    if x is None or pd.isna(x):
        return "–"
    if unit == "percent":
        return f"{x:,.1f}%"
    if unit == "hectares":
        return f"{x:,.1f} ha"
    if unit == "RWF":
        return money(x)
    return f"{x:,.0f}"


def sparkline(values, width: int = 84, height: int = 22) -> str:
    """A tiny line chart (inline SVG, no extra library) of a monthly series, in the brand colour."""
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    step = width / (len(vals) - 1)
    points = " ".join(f"{i * step:.1f},{height - 2 - (v - lo) / span * (height - 4):.1f}" for i, v in enumerate(vals))
    return (f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}' role='img' "
            f"aria-label='trend over the months'><polyline fill='none' stroke='{COLOURS['primary']}' stroke-width='1.6' "
            f"points='{points}'/></svg>")


def trend(values, months: int = 3) -> str:
    """Words and an arrow: the last N months against the N before, e.g. '▲ up 12% on the previous 3 months'."""
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    if len(vals) < 2 * months:
        return ""
    last, before = sum(vals[-months:]), sum(vals[-2 * months:-months])
    if not before:
        return ""
    change = 100 * (last - before) / before
    arrow, word = ("▲", "up") if change > 0.5 else ("▼", "down") if change < -0.5 else ("▶", "level")
    return f"{arrow} {word} {abs(change):.0f}% on the previous {months} months" if word != "level" else \
        f"{arrow} level with the previous {months} months"


def tile(label: str, value: str, note: str = "", series=None) -> str:
    """A KPI card. With a monthly series it also shows a sparkline and a trend arrow in words."""
    note_html = f"<div class='tile-note'>{note}</div>" if note else ""
    trend_html = ""
    if series is not None and len(series):
        trend_html = f"<div class='tile-trend'>{sparkline(series)}<span>{trend(series)}</span></div>"
    return (f"<div class='tile'><div class='tile-label'>{label}</div><div class='tile-value'>{value}</div>"
            f"{trend_html}{note_html}</div>")


def page_header(title: str, page: str) -> None:
    """The coloured band at the top of a page: the title and one line on what the page answers
    (config/page_help.yaml: summaries)."""
    import html
    summary = (load_yaml("page_help.yaml").get("summaries") or {}).get(page, "")
    st.markdown(f"<div class='page-header'><h1>{html.escape(title)}</h1>"
                + (f"<p>{html.escape(summary)}</p>" if summary else "") + "</div>", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def startup_backup() -> str:
    """Once each time the dashboard starts: a dated copy of the donor entries (data/app/backups/)."""
    import app_store
    copy = app_store.backup(reason="start")
    return copy.name if copy else ""


def donor_sources_note() -> str:
    """Where the donor figures come from: the Donor entry page (incl. rows imported from the Excel tracker), and any
    rows still read from the Excel tracker (the offline fallback)."""
    import app_store
    counts = query("SELECT source_file = 'entries.db' AS app, COUNT(*) AS n FROM fact_opportunity GROUP BY 1")
    app_n = int(counts.loc[counts["app"], "n"].sum()) if len(counts) else 0
    excel_n = int(counts.loc[~counts["app"].astype(bool), "n"].sum()) if len(counts) else 0
    _, moved = app_store.imported_ids()
    history = [h for h in app_store.table("change_history") if h["action"] == "imported from the Excel tracker"]
    when = f" on {dt.datetime.fromisoformat(history[0]['changed_at']):%d %b %Y}" if history else ""
    if moved:
        text = (f"Donor data is kept on the Donor entry page: {app_n} opportunities, of which {len(moved)} were moved "
                f"from the Excel tracker{when}; those Excel rows are no longer read.")
        text += (f" {excel_n} more come from the Excel tracker, used only as an offline fallback." if excel_n
                 else " The Excel tracker is now only an offline fallback.")
    else:
        text = (f"{excel_n} opportunities come from the Excel tracker and {app_n} from the Donor entry page. To keep "
                "donor data in one place, use \"Import from the Excel tracker\" on the Donor entry page (once).")
    return text + " Figures change after the pipeline runs."


def staff_picker(what: str = "anything") -> tuple[str, dict, bool]:
    """'You are': there is no login, so the person picks their staff code (config/staff.yaml). The choice is kept
    between the entry pages. Returns (code, {code: label}, ready)."""
    import app_store
    labels = {p["code"]: f"{p['code']} ({p['role']})" for p in app_store.staff()}
    who = st.selectbox("You are", ["Choose your name..."] + list(labels), format_func=lambda c: labels.get(c, c),
                       key=_remember("entry_staff", "Choose your name..."),
                       help="There is no login: pick yourself. Every change is recorded with this code.")
    ready = who in labels
    if not ready:
        st.info(f"Choose your name above before {what}.")
    return who, labels, ready


def update_figures_button(ready: bool, where: str) -> None:
    """Run the pipeline (about 20 seconds) so new entries and uploads appear on the other pages."""
    import subprocess
    import sys
    st.markdown(f"**Update the dashboard figures** so the entries appear on {where} (about 20 seconds).")
    if st.button("Update the figures now", disabled=not ready, key="update_figures"):
        with st.spinner("Preparing the figures..."):
            r = subprocess.run([sys.executable, str(ROOT / "src" / "pipeline.py")], cwd=ROOT, capture_output=True,
                               text=True)
        if r.returncode == 0:
            st.success("The figures are up to date.")
        else:
            st.error("The figures could not be updated. Ask the MEAL officer to run the pipeline (maintenance guide):"
                     + chr(10) * 2 + (r.stdout + r.stderr)[-800:])


def sidebar_logo() -> None:
    """The logo at the top of the sidebar, with the organisation name (only if the logo file exists)."""
    path = ROOT / THEME.get("logo", "")
    if THEME.get("logo") and path.is_file():
        st.logo(str(path), size="large")


def tiles(items: list[tuple]) -> None:
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.markdown(tile(*item), unsafe_allow_html=True)


def table(df: pd.DataFrame, name: str, height: int | None = None, **kwargs) -> None:
    """A table with a download button underneath (brief: a download button on every table)."""
    if height:
        kwargs["height"] = height
    st.dataframe(df, hide_index=True, width="stretch", **kwargs)
    st.download_button(f"⬇ Download ({len(df):,} row{'s' if len(df) != 1 else ''}, CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{name}.csv", mime="text/csv", key=f"dl_{name}")


def html_table(df: pd.DataFrame, name: str, widths: dict | None = None, html_columns: tuple = (),
               max_rows: int | None = None) -> None:
    """A compact table whose text WRAPS (nothing is cut off at 1366 px), with a download button underneath.
    html_columns: columns that already hold HTML (e.g. coloured statuses); everything else is escaped.
    The download has the plain text."""
    import html as _html
    widths = widths or {}
    head = "".join(f"<th style='width:{widths[c]}'>{_html.escape(str(c))}</th>" if c in widths
                   else f"<th>{_html.escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(
        f"<td>{v if c in html_columns else _html.escape('' if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))}</td>"
        for c, v in zip(df.columns, row)) + "</tr>" for row in df.head(max_rows or len(df)).itertuples(index=False))
    st.markdown(f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{head}</tr></thead><tbody>{body}</tbody>"
                "</table></div>", unsafe_allow_html=True)
    if max_rows and len(df) > max_rows:
        st.caption(f"The first {max_rows} of {len(df):,} rows are shown; the download has them all.")
    plain = df.copy()
    for c in html_columns:
        plain[c] = plain[c].astype(str).str.replace(r"<[^>]+>", "", regex=True)
    st.download_button(f"⬇ Download ({len(df):,} row{'s' if len(df) != 1 else ''}, CSV)", plain.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{name}.csv", mime="text/csv", key=f"dl_{name}")


def axis_title(code: str) -> str:
    """The chart axis title for an indicator, e.g. "Number of people" (catalogue: axis_label)."""
    ind = catalogue()[code]
    return ind.get("axis_label") or {"percent": "Percentage", "hectares": "Hectares", "RWF": "RWF"}.get(
        ind["unit"], "Number")


def pending_note(people: dict, f) -> str:
    """The note under every people count: how many of them are pending duplicate review, against the whole register.
    The two can differ legitimately: the register holds everyone ever registered, the count only the people
    reached in the selection."""
    import measures
    register = measures.pending_in_register(query)
    return f"includes {people['pending']} people pending duplicate review ({register} in the whole register)"


def month_axis(fig, title: str = "") -> None:
    """Dates on the x axis as 'Mar 2024' (month over year, so labels are never cut off)."""
    fig.update_xaxes(tickformat="%b<br>%Y", title_text=title, automargin=True)
    fig.update_yaxes(automargin=True)
    legend_on_top(fig)


def legend_on_top(fig) -> None:
    """Legend in one line above the chart, so it never covers the axis labels."""
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
                      margin=dict(t=40))


def issue_label(code: str) -> str:
    return LABELS["issue"].get(code, code.replace("_", " ").capitalize())


def issues_in_words(text) -> str:
    """'missing_required, sex_unmapped' -> 'Required field left blank; Sex not recognised'."""
    if text is None or (isinstance(text, float) and pd.isna(text)) or not str(text).strip():
        return ""
    return "; ".join(issue_label(c.strip()) for c in str(text).split(","))


def details_in_words(text) -> str:
    """Replace issue codes at the start of each detail ('sex_unmapped: ...') with plain words."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    out = str(text)
    for code in sorted(LABELS["issue"], key=len, reverse=True):
        out = out.replace(code + ":", LABELS["issue"][code] + ":").replace(code, LABELS["issue"][code])
    return out


def entity_label(code: str) -> str:
    return LABELS["entity"].get(code, str(code).replace("_", " ").capitalize())


def current_quarter() -> tuple[str, dt.date, dt.date]:
    """The fiscal quarter of the as-of date (settings), e.g. FY2025/26 Q4."""
    as_of = SETTINGS["as_of_date"] or dt.date.today()
    start_month = SETTINGS["fiscal_year"]["start_month"]
    q = ((as_of.month - start_month) % 12) // 3 + 1
    first_month = (start_month - 1 + 3 * (q - 1)) % 12 + 1
    year = as_of.year if first_month <= as_of.month else as_of.year - 1
    start = dt.date(year, first_month, 1)
    end = (pd.Timestamp(start) + pd.DateOffset(months=3) - pd.Timedelta(days=1)).date()
    return f"{fiscal_year_label(as_of, start_month)} Q{q}", start, end


def as_of() -> dt.date:
    return SETTINGS["as_of_date"] or dt.date.today()


def in_list(values: list) -> str:
    """SQL placeholders for an IN (...) list."""
    return "(" + ", ".join("?" for _ in values) + ")" if values else "(NULL)"


CSS = """
<style>
.block-container {padding-top: 2.6rem; padding-bottom: 1rem; max-width: 100%;}
h1 {font-size: 1.55rem !important; margin-bottom: 0.2rem !important;}
h3 {font-size: 1.1rem !important;}
h4 {font-size: 1.0rem !important; margin: 0.2rem 0 0.3rem 0 !important;}
.synthetic-banner {background: #fff3cd; border: 1px solid #e0b100; color: #5c4400; padding: 0.3rem 0.8rem;
                   border-radius: 6px; font-weight: 600; font-size: 0.85rem; margin-bottom: 0.4rem;}
.tile {border-radius: 8px; padding: 0.45rem 0.7rem;}
.tile-label {font-size: 0.75rem;}
.tile-value {font-weight: 700; line-height: 1.25;}
.tile-note {font-size: 0.72rem;}
.muted {font-size: 0.8rem;}
.answer ul {margin: 0.1rem 0 0.2rem 1rem; padding: 0; font-size: 0.82rem;}
.answer li {margin-bottom: 0.1rem;}
.small {font-size: 0.82rem;}
@page {size: A4 landscape; margin: 10mm;}
@media print {
  [data-testid="stExpander"] details:not([open]) {display: none !important;}
  .js-plotly-plot, [data-testid="stPlotlyChart"] {break-inside: avoid;}
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"], .stDownloadButton,
  [data-testid="stBaseButton-secondary"] {display: none !important;}
  .block-container {padding: 0 !important;}
  table.tbl {font-size: 0.7rem;}
}
.tbl-wrap {overflow-x: auto; margin-bottom: 0.3rem;}
table.tbl {border-collapse: collapse; width: 100%; font-size: 0.8rem; table-layout: auto;}
table.tbl th {text-align: left; padding: 0.3rem 0.45rem; vertical-align: bottom;}
table.tbl td {padding: 0.25rem 0.45rem; vertical-align: top; white-space: normal; overflow-wrap: break-word;}
</style>
"""


def _theme_css() -> str:
    """dashboard/theme.css with its {placeholders} filled from config/theme.yaml."""
    css = (Path(__file__).resolve().parent / "theme.css").read_text(encoding="utf-8")
    values = {**COLOURS, "organisation_name": THEME.get("organisation_name", "")}
    for key, value in values.items():
        css = css.replace("{" + key + "}", str(value))
    return "<style>\n" + css + "\n</style>\n"


CSS = CSS + _theme_css()
