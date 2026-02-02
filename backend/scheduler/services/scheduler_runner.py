import os
import sys
import json
import hashlib
from typing import Dict, List, Tuple, Any

from django.db import transaction

from ..models import (
    Semester,
    StudentCapacity,
    Section,
    Subject,
    SectionSubject,
    Room,
    TimeSlot,
    SpecialLab,
    ElectiveConfig,
    TimetableSlot,
    ElectiveSlot,
    ScheduleRun,
)


def _ensure_external_scheduler_on_path():
    """Add the external tts_v6.2 folder so 'scheduling' package can be imported."""
    # BASE_DIR: backend project root is two dirs above this file
    backend_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    time_root = os.path.abspath(os.path.join(backend_dir, ".."))
    sched_path = os.path.join(time_root, "tts_v6.2")
    if os.path.isdir(sched_path) and sched_path not in sys.path:
        sys.path.insert(0, sched_path)


def _day_index_to_name(idx: int) -> str:
    # Solver expects full names and explicitly checks for "Friday"
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return days[idx]


def _build_slot_mappings():
    """
    Build consistent indices for theory and lab slots and an overlap map between them.
    Returns:
        theory_slots: List[TimeSlot]
        lab_slots: List[TimeSlot]
        theory_index: dict[TimeSlot.id -> index]
        lab_index: dict[TimeSlot.id -> index]
        LAB_OVERLAP_MAP: dict[lab_index -> list[theory_index]]
        TIMESLOT_LABELS, LAB_SLOT_LABELS: index->label
    """
    theory_qs = TimeSlot.objects.filter(slot_type="theory").order_by("day", "start_time")
    lab_qs = TimeSlot.objects.filter(slot_type="lab").order_by("day", "start_time")

    # Build per-day ordered lists, then derive unique time patterns by time-of-day ordering
    # For solver, we need global indices independent of day. We'll map by daily position.
    # Assume all days share the same set and ordering of time windows.
    def unique_by_time(qs):
        seen = []
        for ts in qs:
            key = (ts.start_time, ts.end_time)
            if key not in [ (x.start_time, x.end_time) for x in seen ]:
                seen.append(ts)
        return seen

    # Probe Monday entries to infer the canonical ordered slots
    theory_canonical = unique_by_time(TimeSlot.objects.filter(slot_type="theory", day=0).order_by("start_time"))
    lab_canonical = unique_by_time(TimeSlot.objects.filter(slot_type="lab", day=0).order_by("start_time"))

    # Fallback if a specific day has no slots; use the first available day
    if not theory_canonical:
        any_theory = TimeSlot.objects.filter(slot_type="theory").order_by("day", "start_time")
        theory_canonical = unique_by_time(any_theory)
    if not lab_canonical:
        any_lab = TimeSlot.objects.filter(slot_type="lab").order_by("day", "start_time")
        lab_canonical = unique_by_time(any_lab)

    theory_index = {}
    lab_index = {}
    TIMESLOT_LABELS = {}
    LAB_SLOT_LABELS = {}

    for i, ts in enumerate(theory_canonical):
        theory_index[(ts.start_time, ts.end_time)] = i
        TIMESLOT_LABELS[i] = f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}"

    for i, ts in enumerate(lab_canonical):
        lab_index[(ts.start_time, ts.end_time)] = i
        LAB_SLOT_LABELS[i] = f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}"

    # Build overlap map: for each lab slot, which theory indices overlap by time window
    from datetime import datetime, date

    def time_to_minutes(t):
        # t is a datetime.time
        return t.hour * 60 + t.minute

    LAB_OVERLAP_MAP = {}
    for lab_ts in lab_canonical:
        ls = lab_index[(lab_ts.start_time, lab_ts.end_time)]
        l_start = time_to_minutes(lab_ts.start_time)
        l_end = time_to_minutes(lab_ts.end_time)
        overlaps = []
        for th_ts in theory_canonical:
            ti = theory_index[(th_ts.start_time, th_ts.end_time)]
            t_start = time_to_minutes(th_ts.start_time)
            t_end = time_to_minutes(th_ts.end_time)
            # Overlap if intervals intersect
            if not (t_end <= l_start or l_end <= t_start):
                overlaps.append(ti)
        LAB_OVERLAP_MAP[ls] = overlaps

    return (
        theory_canonical,
        lab_canonical,
        theory_index,
        lab_index,
        LAB_OVERLAP_MAP,
        TIMESLOT_LABELS,
        LAB_SLOT_LABELS,
    )


def _build_usage_data(theory_rooms: List[str], lab_rooms: List[str], DAYS: List[str], THEORY_TIMESLOTS: List[int], LAB_SLOTS: List[int], theory_index, lab_index):
    """Build usage_data from existing TimetableSlot/ElectiveSlot in DB so solver avoids collisions."""
    usage = {"theory": {}, "lab": {}}

    # Initialize empty maps
    for r in theory_rooms:
        usage["theory"][r] = {d: [] for d in DAYS}
    for r in lab_rooms:
        usage["lab"][r] = {d: [] for d in DAYS}

    # Fill from existing TimetableSlots
    for tt in TimetableSlot.objects.select_related("room", "timeslot"):
        day_name = _day_index_to_name(tt.timeslot.day)
        if tt.room.room_type == "theory":
            idx = theory_index.get((tt.timeslot.start_time, tt.timeslot.end_time))
            if idx is not None and day_name in usage["theory"][tt.room.name]:
                usage["theory"][tt.room.name][day_name].append(idx)
        else:
            idx = lab_index.get((tt.timeslot.start_time, tt.timeslot.end_time))
            if idx is not None and day_name in usage["lab"][tt.room.name]:
                usage["lab"][tt.room.name][day_name].append(idx)

    # Fill from ElectiveSlot as well
    for es in ElectiveSlot.objects.select_related("room", "timeslot"):
        day_name = _day_index_to_name(es.timeslot.day)
        if es.room.room_type == "theory":
            idx = theory_index.get((es.timeslot.start_time, es.timeslot.end_time))
            if idx is not None and day_name in usage["theory"][es.room.name]:
                usage["theory"][es.room.name][day_name].append(idx)
        else:
            idx = lab_index.get((es.timeslot.start_time, es.timeslot.end_time))
            if idx is not None and day_name in usage["lab"][es.room.name]:
                usage["lab"][es.room.name][day_name].append(idx)

    return usage


def _canonical_time_windows(ts_list: List[TimeSlot]) -> List[str]:
    """Return sorted list of time window strings HH:MM-HH:MM from TimeSlots (ignoring day)."""
    windows = {f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}" for ts in ts_list}
    return sorted(windows)


def _hash_dict(payload: Dict[str, Any]) -> str:
    as_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(as_json.encode("utf-8")).hexdigest()


def _build_semester_courses_map(selected_semesters: List[int]) -> Dict[int, List[Tuple]]:
    """Map semester -> list of tuples (code, name, is_lab, times_needed, credit_hour)."""
    # We derive courses from SectionSubject assignments in each semester.
    result = {}
    for sem_num in selected_semesters:
        subjects = (
            Subject.objects.filter(
                id__in=SectionSubject.objects.filter(
                    section__semester__number=sem_num
                ).values_list("subject_id", flat=True)
            )
            .distinct()
            .order_by("code")
        )
        lst = []
        for s in subjects:
            lst.append((s.code, s.name, s.is_lab, s.times_needed, 0))
        result[sem_num] = lst
    return result


def _build_special_lab_rooms() -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for sp in SpecialLab.objects.select_related("subject", "room"):
        mapping.setdefault(sp.subject.code, []).append(sp.room.name)
    return mapping


def run_main_schedule(selected_semesters: List[int] | None, section_size: int = 50, program_code: str = "A", enable_cohort: bool = False, clear_existing: bool = True, constraints: dict | None = None):
    _ensure_external_scheduler_on_path()
    from scheduling.solver import schedule_timetable  # type: ignore

    # Resolve semesters
    if not selected_semesters:
        selected_semesters = list(Semester.objects.values_list("number", flat=True).order_by("number"))

    # Rooms
    theory_rooms = list(Room.objects.filter(room_type="theory").values_list("name", flat=True))
    lab_rooms = list(Room.objects.filter(room_type="lab").values_list("name", flat=True))

    # Slots and maps
    (
        theory_canonical,
        lab_canonical,
        theory_index_map,
        lab_index_map,
        LAB_OVERLAP_MAP,
        TIMESLOT_LABELS,
        LAB_SLOT_LABELS,
    ) = _build_slot_mappings()

    THEORY_TIMESLOTS = list(range(len(theory_canonical)))
    LAB_SLOTS = list(range(len(lab_canonical)))
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    # Student capacities per semester
    section_sizes = {sc.semester.number: sc.student_count for sc in StudentCapacity.objects.select_related("semester")}

    # Courses map
    semester_courses_map = _build_semester_courses_map(selected_semesters)

    # Cohort map: build from CohortCourse if present
    cohort_map = None
    if enable_cohort:
        cohort_map = {}
        from ..models import CohortCourse
        for cc in CohortCourse.objects.select_related("subject", "fixed_timeslot", "semester"):
            # Convert to solver structure: key (sem, code) -> list of dicts
            day_name = _day_index_to_name(cc.fixed_timeslot.day)
            # determine theory or lab slot index
            if cc.fixed_timeslot.slot_type == "theory":
                slot_idx = theory_index_map[(cc.fixed_timeslot.start_time, cc.fixed_timeslot.end_time)]
                is_lab = False
            else:
                slot_idx = lab_index_map[(cc.fixed_timeslot.start_time, cc.fixed_timeslot.end_time)]
                is_lab = True
            cohort_map.setdefault((cc.semester.number, cc.subject.code), []).append({
                "cohort_section": cc.section_label,
                "capacity": cc.capacity,
                # solver expects (day_name, slot_idx) tuples
                "day_time_list": [(day_name, slot_idx)],
            })

    special_lab_rooms = _build_special_lab_rooms()

    # Build deterministic fingerprint of inputs (exclude dynamic usage)
    main_fingerprint_payload = {
        "selected_semesters": sorted(selected_semesters),
        "section_sizes": {str(k): int(v) for k, v in sorted(section_sizes.items())},
        "semester_courses": {
            str(sem): [(code, bool(is_lab), int(times), int(credit)) for (code, name, is_lab, times, credit) in sorted(courses, key=lambda x: x[0])]
            for sem, courses in sorted(semester_courses_map.items())
        },
        "theory_rooms": sorted(theory_rooms),
        "lab_rooms": sorted(lab_rooms),
        "theory_windows": _canonical_time_windows(theory_canonical),
        "lab_windows": _canonical_time_windows(lab_canonical),
        "special_lab_rooms": {code: sorted(rooms) for code, rooms in sorted(special_lab_rooms.items())},
        "cohort": None,
        "program_code": program_code,
        "section_size": int(section_size),
        "enable_cohort": bool(enable_cohort),
        "constraints": constraints or {},
    }
    if enable_cohort and cohort_map is not None:
        flat = []
        for (sem, code), entries in cohort_map.items():
            for e in entries:
                for (day_name, slot_idx, is_lab) in e["day_time_list"]:
                    flat.append((int(sem), code, e["cohort_section"], int(e["capacity"]), day_name, int(slot_idx), bool(is_lab)))
        main_fingerprint_payload["cohort"] = sorted(flat)

    input_hash = _hash_dict(main_fingerprint_payload)

    # Short-circuit: if last main run matches and timetable exists, no need to reschedule
    last_run = ScheduleRun.objects.filter(run_type="main").order_by("-created_at").first()
    if last_run and last_run.input_hash == input_hash and TimetableSlot.objects.exists():
        return {"status": "no-change", "created": 0, "hash": input_hash}

    # Build usage only when proceeding to run solver
    usage_data = _build_usage_data(theory_rooms, lab_rooms, DAYS, THEORY_TIMESLOTS, LAB_SLOTS, theory_index_map, lab_index_map)

    # Run solver
    out = schedule_timetable(
        selected_semesters=selected_semesters,
        semester_courses_map=semester_courses_map,
        section_sizes=section_sizes,
        usage_data=usage_data,
        DAYS=DAYS,
        THEORY_TIMESLOTS=THEORY_TIMESLOTS,
        TIMESLOT_LABELS=TIMESLOT_LABELS,
        LAB_SLOTS=LAB_SLOTS,
        LAB_SLOT_LABELS=LAB_SLOT_LABELS,
        LAB_OVERLAP_MAP=LAB_OVERLAP_MAP,
        theory_rooms=theory_rooms,
        lab_rooms=lab_rooms,
        special_lab_rooms=special_lab_rooms,
        section_size=section_size,
        program_code=program_code,
        cohort_map=cohort_map,
        enable_cohort=enable_cohort,
        constraints=constraints,
    )

    if out is None:
        return {"status": "infeasible"}

    schedule_map, semester_sections_map, new_allocations = out

    # Persist to DB
    with transaction.atomic():
        if clear_existing:
            TimetableSlot.objects.all().delete()

        # Ensure Sections exist (solver may synthesize names)
        for sem, secs in semester_sections_map.items():
            sem_obj, _ = Semester.objects.get_or_create(number=sem)
            for s in secs:
                Section.objects.get_or_create(semester=sem_obj, name=s)

        # Index lookup helpers
        room_by_name = {r.name: r for r in Room.objects.all()}
        # map (day, slot, type) -> TimeSlot
        ts_index = {}
        for ts in TimeSlot.objects.all():
            if ts.slot_type == "theory":
                idx = theory_index_map.get((ts.start_time, ts.end_time))
            else:
                idx = lab_index_map.get((ts.start_time, ts.end_time))
            if idx is not None:
                ts_index[(ts.day, idx, ts.slot_type)] = ts

        # Save allocations
        created = 0
        for (day_name, slot_idx, room_name), occ in schedule_map.items():
            if occ is None:
                continue
            sec_name, course_code, cohort_sec = occ
            # Resolve models
            try:
                section = Section.objects.select_related("semester").get(name=sec_name)
            except Section.DoesNotExist:
                # Try to infer semester from name like S3A1 -> 3
                import re
                m = re.match(r"S(\d+).+", sec_name)
                if m:
                    sem_obj, _ = Semester.objects.get_or_create(number=int(m.group(1)))
                    section = Section.objects.create(semester=sem_obj, name=sec_name)
                else:
                    continue
            try:
                subject = Subject.objects.get(code=course_code)
            except Subject.DoesNotExist:
                continue

            room = room_by_name.get(room_name)
            if not room:
                continue

            day_idx = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(day_name)
            slot_type = "lab" if room.room_type == "lab" else "theory"
            ts = ts_index.get((day_idx, slot_idx, slot_type))
            if not ts:
                continue

            TimetableSlot.objects.get_or_create(
                section=section,
                subject=subject,
                room=room,
                timeslot=ts,
            )
            created += 1

    # Record the successful run
    ScheduleRun.objects.create(
        run_type="main",
        input_hash=input_hash,
        created_count=created,
        params={
            "selected_semesters": sorted(selected_semesters),
            "program_code": program_code,
            "section_size": section_size,
            "enable_cohort": enable_cohort,
            "constraints": constraints or {},
        },
    )

    return {"status": "ok", "created": created, "hash": input_hash}


def run_electives(theory_needed: int = 2, lab_needed: int = 1, clear_existing: bool = True):
    _ensure_external_scheduler_on_path()
    from scheduling.electives_solver import schedule_electives  # type: ignore

    # Rooms
    theory_rooms = list(Room.objects.filter(room_type="theory").values_list("name", flat=True))
    lab_rooms = list(Room.objects.filter(room_type="lab").values_list("name", flat=True))

    # Slots and maps
    (
        theory_canonical,
        lab_canonical,
        theory_index_map,
        lab_index_map,
        LAB_OVERLAP_MAP,
        TIMESLOT_LABELS,
        LAB_SLOT_LABELS,
    ) = _build_slot_mappings()

    THEORY_TIMESLOTS = list(range(len(theory_canonical)))
    LAB_SLOTS = list(range(len(lab_canonical)))
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    usage_data = _build_usage_data(theory_rooms, lab_rooms, DAYS, THEORY_TIMESLOTS, LAB_SLOTS, theory_index_map, lab_index_map)

    electives_list = []
    for ec in ElectiveConfig.objects.select_related("subject"):
        electives_list.append({
            "code": ec.subject.code,
            "name": ec.subject.name,
            "sections_count": ec.sections_count,
            "can_theory": ec.can_use_theory,
            "can_lab": ec.can_use_lab,
            "credit_hour": 0,
        })

    # Build deterministic fingerprint including electives list and current timetable footprint
    timetable_fp = []
    for tt in TimetableSlot.objects.select_related("room", "timeslot"):
        timetable_fp.append((
            tt.room.room_type,
            tt.room.name,
            _day_index_to_name(tt.timeslot.day),
            tt.timeslot.start_time.strftime('%H:%M'),
            tt.timeslot.end_time.strftime('%H:%M'),
        ))
    electives_fingerprint_payload = {
        "theory_rooms": sorted(theory_rooms),
        "lab_rooms": sorted(lab_rooms),
        "theory_windows": _canonical_time_windows(theory_canonical),
        "lab_windows": _canonical_time_windows(lab_canonical),
        "electives": [
            (e["code"], int(e["sections_count"]), bool(e["can_theory"]), bool(e["can_lab"])) for e in sorted(electives_list, key=lambda x: x["code"])
        ],
        "theory_needed": int(theory_needed),
        "lab_needed": int(lab_needed),
        "timetable": sorted(timetable_fp),
    }
    electives_hash = _hash_dict(electives_fingerprint_payload)

    last_e = ScheduleRun.objects.filter(run_type="electives").order_by("-created_at").first()
    if last_e and last_e.input_hash == electives_hash and ElectiveSlot.objects.exists():
        return {"status": "no-change", "created": 0, "hash": electives_hash}

    out = schedule_electives(
        electives_list=electives_list,
        usage_data=usage_data,
        DAYS=DAYS,
        THEORY_TIMESLOTS=THEORY_TIMESLOTS,
        LAB_SLOTS=LAB_SLOTS,
        theory_rooms=theory_rooms,
        lab_rooms=lab_rooms,
        timeslot_labels=TIMESLOT_LABELS,
        lab_slot_labels=LAB_SLOT_LABELS,
        theory_needed=theory_needed,
        lab_needed=lab_needed,
    )

    if out is None:
        return {"status": "infeasible"}

    schedule_map, new_allocations = out

    with transaction.atomic():
        if clear_existing:
            ElectiveSlot.objects.all().delete()

        room_by_name = {r.name: r for r in Room.objects.all()}
        ts_index_theory = {}
        ts_index_lab = {}
        for ts in TimeSlot.objects.all():
            if ts.slot_type == "theory":
                idx = theory_index_map.get((ts.start_time, ts.end_time))
                if idx is not None:
                    ts_index_theory[(ts.day, idx)] = ts
            else:
                idx = lab_index_map.get((ts.start_time, ts.end_time))
                if idx is not None:
                    ts_index_lab[(ts.day, idx)] = ts

        created = 0
        for (rtype, room_name, day_name, slot_idx, label) in new_allocations:
            room = room_by_name.get(room_name)
            if not room:
                continue
            day_idx = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(day_name)
            if rtype == "theory":
                ts = ts_index_theory.get((day_idx, slot_idx))
            else:
                ts = ts_index_lab.get((day_idx, slot_idx))
            if not ts:
                continue

            # Link to ElectiveConfig by code in label
            # label looks like Elective-<code>-A1
            try:
                code = label.split("-")[1]
                ec = ElectiveConfig.objects.select_related("subject").get(subject__code=code)
            except Exception:
                continue

            ElectiveSlot.objects.get_or_create(
                elective=ec,
                room=room,
                timeslot=ts,
            )
            created += 1

    # Record the successful run
    ScheduleRun.objects.create(
        run_type="electives",
        input_hash=electives_hash,
        created_count=created,
        params={
            "theory_needed": theory_needed,
            "lab_needed": lab_needed,
        },
    )

    return {"status": "ok", "created": created, "hash": electives_hash}
