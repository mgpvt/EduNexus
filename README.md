# EduNexus — University Student Analytics & Insights

A production-style analytics application for student enrollment, workload, programs, campus,
demographics, withdrawals, Pell/financial aid, term trends, AI insights, student drill-down,
data quality monitoring and administration.

It reads **Excel today** and can switch to a **university database** by changing configuration only.

## Quick start (Windows)

1. Install Python 3.10+ from python.org (tick *Add Python to PATH*).
2. Double-click **`run.bat`**. On first run it creates a virtual environment and installs packages.
3. Your browser opens at <http://localhost:8501>.

Manual alternative:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Pages

| Section | Page | What it shows |
|---|---|---|
| Overview | Executive Overview | KPIs, level & time-status mix, top majors, key insights |
| | AI Insights | Rule-based findings (always on) + optional AI-written briefing |
| Analytics | Enrollment | Level, classification, student type, time status |
| | Academic Workload | Courses, credit/billed hours vs credit-load policy bands |
| | Programs & Majors | Rankings, treemap, Pell-vs-withdrawal bubble chart, drill-down |
| | Campus | Campus comparison and top majors per campus |
| | Demographics | Gender & ethnicity mix and outcome gaps |
| | Withdrawals | Rates by group, high-risk majors, multi-withdrawal student list |
| | Pell & Financial Aid | Pell share, Pell vs non-Pell outcomes, aid follow-up list |
| | Term Trends | Term-over-term change (activates when 2+ terms are loaded) |
| Students | Student Search | Search by ZID/PIDM/program/major, profile, peer comparison, flags |
| Governance | Data Quality | 15 rules, quality score, failing-record review, field profile |
| | Administration | Data source, column mapping, policy thresholds, code labels, cache |

All analytics pages share the sidebar filters (term, level, classification, campus, time status,
gender, ethnicity, Pell, major). Every table can be downloaded as CSV.

## Credit-load policy

Configured in `config/settings.yaml` → `credit_policy` (or the Administration page):

- Full-time: ≥ 12 credit hours per term
- Overload: > 18.5 requires department chair & Student Accounts permission
- Maximum: 24 credit hours per term
- Typical undergraduate load: 16

> **Data note (TestStudents.xlsx):** about 95% of undergraduate records exceed 24 credit hours
> (median ≈ 106, ≈ 9 hours per course), so CREDIT_HOURS/COURSES appear to be cumulative or
> mis-scaled in the extract. Values are shown as supplied; the Workload page shows a caveat and
> the Data Quality page lists every affected record so it can be fixed at source.

## Demo data vs real data

The app currently runs on **`data/TestStudents_demo.xlsx`**, a synthetic copy of the original upload:

- Kept from the original: every student, ZID/PIDM, program, major, campus, level, classification,
  time status, gender, ethnicity, Pell, and *which* students withdrew.
- Regenerated: COURSES, CREDIT_HOURS, BILL_HOURS and withdrawal counts. They follow the credit-load
  policy for each student's level and time status (e.g. UG full-time 12–18.5 mostly, ~10% approved
  overloads up to 24; graduate full-time 9–15). About 4% have small billed-hour differences.
- The workbook has a `README_SYNTHETIC` sheet, and every page shows a **DEMO DATA** banner.
- Rebuild it any time: `python scripts/make_demo_data.py` (fixed seed, so the output is reproducible).

**Switching to real data:** Administration → Data source:
- choose **Original upload** (the file as received), or
- **Upload real data** (the corrected extract, same 18 columns). It is saved under `data/`,
  added to the dataset list as real data, and the demo banner disappears once you apply it.

## Online test site

See **DEPLOY.md** to publish to GitHub and Streamlit Community Cloud with a tester login.
The published copy uses `data/EduNexus_public_demo.xlsx` (made-up IDs). Files with original IDs
are blocked from GitHub by `.gitignore`. Login is enabled only when `[auth]` passwords are present
in Streamlit secrets; locally, without secrets, the app opens directly with admin rights.

## Architecture

```
app.py                     Router (top navigation)
views/                     One file per page (UI only)
edunexus/
  config.py                Settings load/save, code labels
  data/sources.py          DataSource adapters: ExcelSource, DatabaseSource (SQLAlchemy)
  data/repository.py       Column mapping, typing, cleaning, derived fields
  metrics.py               KPI & aggregation functions (UI-independent)
  quality.py               Data quality rules & score
  insights.py              Rule-based insight engine + optional Anthropic AI narrative
  ui.py                    Theme, filters, KPI tiles, chart helpers
config/settings.yaml       All configuration
data/TestStudents.xlsx     Original upload
data/TestStudents_demo.xlsx Synthetic demo copy (policy-compliant workload)
scripts/make_demo_data.py  Regenerates the demo copy
tests/                     Unit tests + headless page smoke tests
```

Pages never read Excel directly. They call `get_data()`, which goes through the adapter selected
in settings, then the standardisation layer. New sources (API, Parquet, data warehouse) only need
a new `DataSource` class.

## Switching to the university database

1. Install the driver, e.g. `pip install psycopg2-binary` (PostgreSQL), `pyodbc` (SQL Server),
   `oracledb` (Oracle).
2. Set the connection URL as an environment variable (keeps passwords out of files):
   ```
   setx EDUNEXUS_DB_URL "mssql+pyodbc://user:pass@MyDSN"
   ```
3. Administration → Data source → **database**, enter the table/view (or a SQL query),
   adjust the column mapping if names differ, **Test connection**, then **Save settings**.

The source should return one row per student per term with the 18 standard fields.
Multiple terms in the same table automatically enable Term Trends.

## AI insights

The rule-based insight engine always runs locally. For an AI-written briefing:

```
pip install anthropic
setx ANTHROPIC_API_KEY "sk-ant-..."
```

Only aggregated statistics (counts and rates by group) are sent — never ZIDs, PIDMs or student rows.

## Code labels

Labels marked “(verify)” in settings are assumptions (e.g. Time_Status N/L/P/T, Level DE/CD/PH/DN,
Campus X). Confirm them with the Registrar and edit them on the Administration page. Student_Type
codes are shown as raw codes until labels are added.

## Tests

```bash
pip install pytest
pytest -q
```
