# Timetable Frontend (Vite + React)

## Dev

```powershell
# from this folder
npm install
npm run dev
```

- The dev server runs on http://127.0.0.1:5173.
- API calls to `/api/*` are proxied to `http://127.0.0.1:8000` (see `vite.config.ts`).
- Alternatively, set `VITE_API_BASE` in `.env` to point directly to your backend (already defaults to `http://127.0.0.1:8000/api`).

## Build

```powershell
npm run build
npm run preview
```

## Components
- UploadExcel: uploads main/cohort Excel files
- RunSchedule: triggers schedule generation
- RunElectives: triggers elective allocation
- ExportButton: downloads the generated timetable as XLSX