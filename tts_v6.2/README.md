# UMT Timetable Scheduler

This repository contains a Streamlit-based timetable scheduler that reads an Excel workbook (Roadmap/Rooms/StudentCapacity etc.) and uses OR-Tools CP-SAT to generate timetables for theory and lab courses (including specialized handling for cohort scheduling and electives).

## Quick overview
- `app.py` - Streamlit UI and main integration logic.
- `data/` - parsing, validation, and usage persistence:
  - `data/data_io.py` - parsing Excel sheets, loading/saving `usage_data.json`, cohort parsing.
  - `data/consistency_check.py` - validators for the main Excel and cohort Excel.
  - `data/usage_data.json` - prior room usage (updated by the app).
- `scheduling/` - OR-Tools models and helpers:
  - `scheduling/solver.py` - main CP-SAT model for scheduling main courses.
  - `scheduling/electives_solver.py` - CP-SAT model for electives.
  - `scheduling/utils.py` - helper functions for building DataFrames and sections.

## Requirements
A recommended small virtual environment and the following Python packages are required. See `requirements.txt` for the exact list.

## Running locally (Windows PowerShell)
Open PowerShell in the project root and run the provided script which will create a `.venv` (if needed), install dependencies, and launch Streamlit:

```powershell
# Make the script executable and run it from project root
.\scripts\run_streamlit.ps1
```

Alternatively run manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Expected Excel structure
The main Excel (uploaded in the Streamlit UI) must include these sheets:
- `Roadmap` (required columns): `semester`, `course_code`, `course_name`, `is_lab`, `times_needed` (optional: `credit_hour`).
- `Rooms` (required columns): `room_name`, `room_type` (`theory` or `lab`).
- `StudentCapacity` (required columns): `semester`, `student_count`.
- Optional sheets: `Electives` and `SpecialLabs` (see `data/data_io.py` for expected column names).

If using cohort scheduling, upload a cohort Excel with headers: `CohortSemester`, `CourseCode`, `CourseName`, `Section`, `Capacity` and optional per-day columns (`Mon`, `Tue`, etc.) with slot indices.

## Notes & tips
- The system skips theory timeslot index `3` on Friday by business rule; many validations and constraints assume that.
- Cohort rows with `Capacity > 50` are split automatically into sub-sections of ~50 each.
- `data/usage_data.json` is used to store previously-occupied room slots; use the `Reset Usage Data` button in the UI to clear it.

## Troubleshooting
- If the solver returns infeasible, try increasing rooms or deselecting semesters, or toggle off "Use previous slots" to ignore prior usage.
- For debugging solver performance consider adding logging around solver calls and reducing the number of selected semesters while experimenting.

## Files added
- `README.md` (this file)
- `requirements.txt` (dependency pins)
- `scripts/run_streamlit.ps1` (PowerShell helper to create a venv, install deps, and run Streamlit)

If you'd like, I can also add a small smoke test and CI job to run it automatically.
