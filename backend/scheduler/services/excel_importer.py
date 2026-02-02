import pandas as pd
from django.db import transaction
from scheduler.models import (
    Semester, StudentCapacity, Subject, Section, SectionSubject,
    Room, SpecialLab, ElectiveConfig, CohortCourse, CohortSubSection, TimeSlot
)

class ExcelImportError(Exception):
    pass


class ExcelImporter:

    REQUIRED_SHEETS = ["Roadmap", "Rooms", "StudentCapacity"]

    OPTIONAL_SHEETS = ["Electives", "SpecialLabs", "TimeSlots"]

    def __init__(self, main_excel, cohort_excel=None):
        self.main_excel = main_excel
        self.cohort_excel = cohort_excel

    # ---------- helpers ----------
    @staticmethod
    def _normalize_columns(df: pd.DataFrame, aliases: dict | None = None) -> pd.DataFrame:
        """Return a copy of df with normalized lowercase underscore column names and optional alias remapping.
        - Lowercase
        - Trim
        - Replace any non-alphanum with underscore
        - Apply alias map (normalized keys)
        """
        import re
        out = df.copy()
        norm_map = {}
        for col in out.columns:
            key = re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower())
            norm_map[col] = key
        out.rename(columns=norm_map, inplace=True)
        if aliases:
            # Normalize alias keys and values the same way
            def norm(s: str) -> str:
                return re.sub(r"[^a-z0-9]+", "_", s.strip().lower())
            ali_norm = {norm(k): [norm(v) for v in vals] for k, vals in aliases.items()}
            for target, alts in ali_norm.items():
                if target in out.columns:
                    continue
                for alt in alts:
                    if alt in out.columns:
                        out.rename(columns={alt: target}, inplace=True)
                        break
        return out

    @staticmethod
    def _parse_cohort_cell(val):
        """Parse a cohort day cell which can be:
        - empty/NaN -> None
        - integer -> timeslot id
        - string like "09:30-10:45", optionally with type indicator (lab/theory)
        Returns dict or None: { 'timeslot_id': int } OR { 'start': time, 'end': time, 'slot_type': 'lab'|'theory'|None }
        """
        import pandas as _pd
        from datetime import time as _time
        if _pd.isna(val):
            return None
        s = str(val).strip()
        if not s or s.lower() in {"-", "na", "n/a", "none", "0"}:
            return None
        # integer id
        try:
            tid = int(s)
            return {"timeslot_id": tid}
        except Exception:
            pass
        # pattern "start-end [type]"
        import re
        parts = re.split(r"\s*(?:-|to|–|—)\s*", s, maxsplit=1)
        if len(parts) == 2:
            start_s, rest = parts[0], parts[1]
            rest_parts = rest.split()
            end_s = rest_parts[0]
            remainder = " ".join(rest_parts[1:]).lower()
            try:
                from datetime import datetime as _dt
                st = ExcelImporter._parse_time(start_s)
                en = ExcelImporter._parse_time(end_s)
            except Exception:
                return None
            slot_type = None
            if any(k in remainder for k in ["lab", " l "]):
                slot_type = "lab"
            elif any(k in remainder for k in ["theory", " lec", " lecture", " t "]):
                slot_type = "theory"
            return {"start": st, "end": en, "slot_type": slot_type}
        return None
    @staticmethod
    def _parse_bool(val) -> bool:
        s = str(val).strip().lower()
        return s in {"1", "true", "yes", "y", "t"}

    @staticmethod
    def _parse_day(val) -> int:
        """
        Accepts numeric (0..5) or strings like Mon, Monday, Tue, Tuesday, ...
        Returns 0..5 (Mon..Sat). Raises ExcelImportError if invalid.
        """
        if pd.isna(val):
            raise ExcelImportError("Day value is NaN/empty")
        # numeric (int or numeric string)
        try:
            num = int(str(val).strip())
            if 0 <= num <= 5:
                return num
        except Exception:
            pass
        s = str(val).strip().lower()
        mapping = {
            "mon": 0, "monday": 0,
            "tue": 1, "tues": 1, "tuesday": 1,
            "wed": 2, "weds": 2, "wednesday": 2,
            "thu": 3, "thur": 3, "thurs": 3, "thursday": 3,
            "fri": 4, "friday": 4,
            "sat": 5, "saturday": 5,
        }
        if s in mapping:
            return mapping[s]
        raise ExcelImportError(f"Unrecognized day value: {val}")

    @staticmethod
    def _parse_time(val):
        """
        Accept various time formats or actual time/Timestamp.
        Returns datetime.time
        """
        from datetime import time, datetime
        if pd.isna(val):
            raise ExcelImportError("Time value is NaN/empty")
        # If already a time
        if hasattr(val, "hour") and hasattr(val, "minute") and not hasattr(val, "date"):
            # likely datetime.time
            return val
        # If pandas Timestamp or datetime
        if hasattr(val, "to_pydatetime"):
            dt = val.to_pydatetime()
            return dt.time()
        if isinstance(val, datetime):
            return val.time()
        s = str(val).strip()
        fmts = ["%H:%M", "%H.%M", "%I:%M %p", "%I:%M%p", "%I %p", "%H"]
        for f in fmts:
            try:
                return datetime.strptime(s, f).time()
            except Exception:
                continue
        raise ExcelImportError(f"Unrecognized time format: {val}")

    @staticmethod
    def _parse_slot_type(val) -> str:
        s = str(val).strip().lower()
        if s in {"theory", "t", "lec", "lecture"}:
            return "theory"
        if s in {"lab", "l"}:
            return "lab"
        raise ExcelImportError(f"Unrecognized slot_type: {val}")

    def read_sheet(self, sheet_name, required=True):
        try:
            df = pd.read_excel(self.main_excel, sheet_name=sheet_name)
            return df
        except Exception:
            if required:
                raise ExcelImportError(f"Missing required sheet: {sheet_name}")
            return None

    def validate_and_import(self):
        with transaction.atomic():

            # ========== 1️⃣ Validate & Load Roadmap ==========
            roadmap = self.read_sheet("Roadmap")

            required_cols = {"semester", "course_code", "course_name", "is_lab", "times_needed"}
            if not required_cols.issubset(roadmap.columns):
                raise ExcelImportError(f"Roadmap must contain columns: {required_cols}")

            for _, row in roadmap.iterrows():
                sem, _ = Semester.objects.get_or_create(number=int(row["semester"]))

                # Subject
                subj, _ = Subject.objects.get_or_create(
                    code=row["course_code"],
                    defaults={
                        "name": row["course_name"],
                        "is_lab": self._parse_bool(row["is_lab"]),
                        "times_needed": int(row["times_needed"])
                    }
                )

            # ========== 2️⃣ Rooms ==========
            rooms = self.read_sheet("Rooms")
            if not {"room_name", "room_type"}.issubset(rooms.columns):
                raise ExcelImportError("Rooms sheet columns: room_name, room_type")

            for _, r in rooms.iterrows():
                rt = self._parse_slot_type(r["room_type"])  # validates
                if rt not in ("theory", "lab"):
                    raise ExcelImportError(f"Invalid room type: {r['room_type']}")

                Room.objects.get_or_create(
                    name=r["room_name"],
                    room_type=rt
                )

            # ========== 3️⃣ Student Capacity ==========
            sc_df = self.read_sheet("StudentCapacity")

            if not {"semester", "student_count"}.issubset(sc_df.columns):
                raise ExcelImportError("StudentCapacity sheet columns: semester, student_count")

            for _, s in sc_df.iterrows():
                sem = Semester.objects.get(number=int(s["semester"]))
                StudentCapacity.objects.update_or_create(
                    semester=sem,
                    defaults={"student_count": int(s["student_count"])}
                )

                # auto create sections based on 50-student rule
                total = int(s["student_count"])
                sections_needed = max(1, (total + 49) // 50)  # round-up /50

                for i in range(sections_needed):
                    Section.objects.get_or_create(
                        semester=sem,
                        name=f"S{sem.number}A{i+1}"
                    )

            # Link every section of a semester to all subjects listed for that semester
            # so the scheduler can derive semester_courses_map from SectionSubject
            for sem in Semester.objects.all():
                sem_subjects = Subject.objects.filter(
                    code__in=roadmap.loc[roadmap["semester"] == sem.number, "course_code"].tolist()
                ).distinct()
                for sec in Section.objects.filter(semester=sem):
                    for subj in sem_subjects:
                        SectionSubject.objects.get_or_create(section=sec, subject=subj)

            # ========== 4️⃣ TimeSlots (Optional, else seed defaults) ==========
            ts_df = self.read_sheet("TimeSlots", required=False)
            if ts_df is not None:
                # Expect columns: day (0-5), start (HH:MM), end (HH:MM), slot_type (theory/lab)
                req_ts = {"day", "start", "end", "slot_type"}
                if not req_ts.issubset(ts_df.columns):
                    raise ExcelImportError("TimeSlots sheet columns: day, start, end, slot_type")
                TimeSlot.objects.all().delete()
                for _, r in ts_df.iterrows():
                    start_t = self._parse_time(r["start"])
                    end_t = self._parse_time(r["end"])
                    TimeSlot.objects.create(
                        day=self._parse_day(r["day"]),
                        start_time=start_t,
                        end_time=end_t,
                        slot_type=self._parse_slot_type(r["slot_type"]),
                    )
            else:
                # Seed default times matching solver timing assumptions
                from datetime import time
                # Monday..Saturday => 0..5
                theory_times = [
                    (time(8,0), time(9,15)),
                    (time(9,30), time(10,45)),
                    (time(11,0), time(12,15)),
                    (time(12,30), time(13,45)),
                    (time(14,0), time(15,15)),
                    (time(15,30), time(16,45)),
                    (time(17,0), time(18,15)),
                ]
                lab_times = [
                    (time(8,0), time(10,30)),
                    (time(11,0), time(13,30)),
                    (time(14,0), time(16,30)),
                    (time(17,0), time(19,30)),
                ]
                if TimeSlot.objects.count() == 0:
                    for d in range(6):
                        for (s,e) in theory_times:
                            TimeSlot.objects.create(day=d, start_time=s, end_time=e, slot_type="theory")
                        for (s,e) in lab_times:
                            TimeSlot.objects.create(day=d, start_time=s, end_time=e, slot_type="lab")

            # ========== 5️⃣ Electives (Optional) ==========
            elective_df = self.read_sheet("Electives", required=False)
            if elective_df is not None:
                req_cols = {"elective_code", "elective_name", "sections_count", "can_use_theory", "can_use_lab"}
                if not req_cols.issubset(elective_df.columns):
                    raise ExcelImportError(f"Electives must contain {req_cols}")

                for _, e in elective_df.iterrows():
                    code = str(e["elective_code"]).strip()
                    name = str(e.get("elective_name") or "").strip() or code
                    # Ensure Subject exists for this elective; default to theory and 0 times_needed
                    subj, _ = Subject.objects.get_or_create(
                        code=code,
                        defaults={
                            "name": name,
                            "is_lab": False,
                            "times_needed": 0,
                        },
                    )
                    ElectiveConfig.objects.update_or_create(
                        subject=subj,
                        defaults={
                            "sections_count": int(e["sections_count"]),
                            "can_use_theory": self._parse_bool(e["can_use_theory"]),
                            "can_use_lab": self._parse_bool(e["can_use_lab"])
                        }
                    )

            # ========== 6️⃣ Special Labs (optional) ==========
            sl_df = self.read_sheet("SpecialLabs", required=False)
            if sl_df is not None:
                # Normalize headers and accept common aliases
                sl_df = self._normalize_columns(
                    sl_df,
                    aliases={
                        "course_code": ["coursecode", "code", "subject_code", "subject", "course"],
                        "room_name": ["roomname", "room", "lab_room", "lab"],
                    },
                )
                # Support multi-room columns like 'lab_rooms' or 'rooms' (comma/semicolon separated)
                if "room_name" not in sl_df.columns:
                    multi_cols = [c for c in ("lab_rooms", "rooms", "labrooms") if c in sl_df.columns]
                    if multi_cols:
                        col = multi_cols[0]
                        exploded_rows = []
                        for _, r in sl_df.iterrows():
                            code = str(r.get("course_code", "")).strip()
                            raw = str(r.get(col, "")).strip()
                            # split on comma or semicolon
                            parts = [p.strip() for p in raw.replace(";", ",").split(",") if p and p.strip().lower() != "nan"]
                            for rn in parts:
                                if rn:
                                    exploded_rows.append({"course_code": code, "room_name": rn})
                        sl_df = pd.DataFrame(exploded_rows)
                if not {"course_code", "room_name"}.issubset(sl_df.columns):
                    raise ExcelImportError(
                        f"SpecialLabs sheet must contain columns: course_code, room_name. Found: {list(sl_df.columns)}"
                    )

                for _, s in sl_df.iterrows():
                    code = str(s["course_code"]).strip()
                    try:
                        subj = Subject.objects.get(code=code)
                    except Subject.DoesNotExist:
                        raise ExcelImportError(f"SpecialLabs refers to unknown course_code '{code}'. Add it to Roadmap first.")
                    room_name = str(s["room_name"]).strip()
                    try:
                        room = Room.objects.get(name=room_name)
                    except Room.DoesNotExist:
                        # Auto-create as a lab room to reduce friction; capacity default 30
                        room = Room.objects.create(name=room_name, room_type="lab", capacity=30)
                    SpecialLab.objects.get_or_create(subject=subj, room=room)

            # ========== 7️⃣ Cohort File ==========
            if self.cohort_excel:
                cohort_df = pd.read_excel(self.cohort_excel)
                # Normalize and map common aliases
                cohort_df = self._normalize_columns(
                    cohort_df,
                    aliases={
                        "cohort_semester": ["cohortsemester", "semester", "sem", "sem_no", "semnumber", "sem_number"],
                        "course_code": ["coursecode", "code", "subject_code", "subjectcode", "course"],
                        "section": ["cohort_section", "cohortsection", "cohort", "section_label", "sectionlabel", "section_name"],
                        "capacity": ["cap", "size", "count", "student_count"],
                        "day": ["weekday", "day_of_week", "weekday_index"],
                        "timeslot": ["timeslotid", "slot_id", "slotid", "timeslot_id", "timeslot_index"],
                        "start": ["start_time", "starttime", "begin", "from"],
                        "end": ["end_time", "endtime", "finish", "to"],
                        "slot_type": ["slottype", "type", "class_type"],
                        # day columns
                        "mon": ["monday"],
                        "tue": ["tuesday", "tues"],
                        "wed": ["wednesday", "weds"],
                        "thu": ["thursday", "thur", "thurs"],
                        "fri": ["friday"],
                        "sat": ["saturday"],
                    },
                )

                # Two supported formats: single 'day' or per-day columns (mon..sat)
                has_day = "day" in cohort_df.columns
                day_cols = [c for c in ["mon", "tue", "wed", "thu", "fri", "sat"] if c in cohort_df.columns]

                base_req = {"cohort_semester", "course_code", "section", "capacity"}
                if not base_req.issubset(cohort_df.columns):
                    raise ExcelImportError(f"Cohort file must contain {base_req} plus either 'day' or any of mon..sat. Found: {list(cohort_df.columns)}")

                if not has_day and not day_cols:
                    raise ExcelImportError("Cohort file must include either a 'day' column or daily columns like mon,tue,wed,thu,fri,sat")

                def resolve_timeslot(day_idx, cell_value, row_ctx):
                    parsed = ExcelImporter._parse_cohort_cell(cell_value)
                    if not parsed:
                        return None
                    if "timeslot_id" in parsed:
                        try:
                            return TimeSlot.objects.get(id=int(parsed["timeslot_id"]))
                        except Exception:
                            raise ExcelImportError(f"Cohort references unknown TimeSlot id {parsed['timeslot_id']}")
                    st = parsed["start"]
                    en = parsed["end"]
                    stype = parsed.get("slot_type")
                    qs = TimeSlot.objects.filter(day=day_idx, start_time=st, end_time=en)
                    if stype:
                        qs = qs.filter(slot_type=stype)
                    ts = qs.first()
                    if not ts:
                        raise ExcelImportError(
                            f"Cohort row could not resolve a TimeSlot with Day={day_idx}, Start={st}, End={en}{' ' + stype if stype else ''}. Check TimeSlots sheet."
                        )
                    return ts

                for _, c in cohort_df.iterrows():
                    sem = Semester.objects.get(number=int(c["cohort_semester"]))
                    code = str(c["course_code"]).strip()
                    try:
                        subj = Subject.objects.get(code=code)
                    except Subject.DoesNotExist:
                        raise ExcelImportError(f"Cohort references unknown CourseCode '{code}'. Add it to Roadmap first.")

                    section_label = str(c["section"]).strip()
                    cap_total = int(c["capacity"])

                    if has_day:
                        ts = None
                        if "timeslot" in cohort_df.columns and pd.notna(c.get("timeslot")):
                            try:
                                ts = TimeSlot.objects.get(id=int(c["timeslot"]))
                            except Exception:
                                ts = None
                        if ts is None and {"start", "end", "slot_type"}.issubset(set(cohort_df.columns)):
                            st = self._parse_time(c["start"]) 
                            en = self._parse_time(c["end"]) 
                            try:
                                ts = TimeSlot.objects.get(
                                    day=self._parse_day(c["day"]),
                                    start_time=st,
                                    end_time=en,
                                    slot_type=self._parse_slot_type(c["slot_type"]),
                                )
                            except TimeSlot.DoesNotExist:
                                raise ExcelImportError(
                                    f"Cohort row could not resolve a TimeSlot with Day={c['day']}, Start={c['start']}, End={c['end']}, SlotType={c['slot_type']}. Check TimeSlots sheet."
                                )
                        if ts is None:
                            raise ExcelImportError("Cohort row could not resolve a TimeSlot by id or by Start/End/SlotType")

                        cohort = CohortCourse.objects.create(
                            semester=sem,
                            subject=subj,
                            section_label=section_label,
                            fixed_day=self._parse_day(c["day"]),
                            fixed_timeslot=ts,
                            capacity=cap_total,
                        )

                        # split >50 capacity rule
                        cap = cap_total
                        while cap > 50:
                            CohortSubSection.objects.create(cohort=cohort, size=50)
                            cap -= 50
                        CohortSubSection.objects.create(cohort=cohort, size=cap)

                    else:
                        # per-day columns: create a CohortCourse per non-empty day cell
                        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5}
                        for col, d_idx in day_map.items():
                            if col not in day_cols:
                                continue
                            val = c.get(col)
                            ts = resolve_timeslot(d_idx, val, c)
                            if not ts:
                                continue
                            cohort = CohortCourse.objects.create(
                                semester=sem,
                                subject=subj,
                                section_label=section_label,
                                fixed_day=d_idx,
                                fixed_timeslot=ts,
                                capacity=cap_total,
                            )
                            cap = cap_total
                            while cap > 50:
                                CohortSubSection.objects.create(cohort=cohort, size=50)
                                cap -= 50
                            CohortSubSection.objects.create(cohort=cohort, size=cap)
