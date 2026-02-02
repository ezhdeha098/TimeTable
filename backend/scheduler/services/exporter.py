from io import BytesIO
import pandas as pd

from ..models import TimetableSlot, ElectiveSlot


def export_timetable_xlsx() -> bytes:
    """Build a simple Excel workbook for generated timetable + electives."""
    # Timetable sheet
    tt_rows = []
    for tt in (
        TimetableSlot.objects
        .select_related("section", "section__semester", "subject", "room", "timeslot", "teacher")
        .all()
        .order_by("section__semester__number", "section__name", "timeslot__day", "timeslot__start_time")
    ):
        tt_rows.append({
            "Semester": tt.section.semester.number,
            "Section": tt.section.name,
            "Subject": tt.subject.code,
            "Room": tt.room.name,
            "Type": tt.room.room_type,
            "Day": tt.timeslot.get_day_display(),
            "Start": tt.timeslot.start_time.strftime("%H:%M"),
            "End": tt.timeslot.end_time.strftime("%H:%M"),
            "Teacher": tt.teacher.name if tt.teacher else "",
        })
    timetable_df = pd.DataFrame(tt_rows, columns=["Semester", "Section", "Subject", "Room", "Type", "Day", "Start", "End", "Teacher"]) if tt_rows else pd.DataFrame(columns=["Semester", "Section", "Subject", "Room", "Type", "Day", "Start", "End", "Teacher"])

    # Electives sheet
    el_rows = []
    for es in (
        ElectiveSlot.objects
        .select_related("elective", "elective__subject", "room", "timeslot")
        .all()
        .order_by("timeslot__day", "timeslot__start_time")
    ):
        el_rows.append({
            "Elective": es.elective.subject.code,
            "Room": es.room.name,
            "Type": es.room.room_type,
            "Day": es.timeslot.get_day_display(),
            "Start": es.timeslot.start_time.strftime("%H:%M"),
            "End": es.timeslot.end_time.strftime("%H:%M"),
        })
    electives_df = pd.DataFrame(el_rows, columns=["Elective", "Room", "Type", "Day", "Start", "End"]) if el_rows else pd.DataFrame(columns=["Elective", "Room", "Type", "Day", "Start", "End"])

    # Build a pivoted view with days as columns per Section and Time window rows
    if tt_rows:
        # Determine unique time windows across all slots, sorted by time
        # Build lookup: (Semester, Section, Day, Start, End) -> list of labels
        from collections import defaultdict
        time_keys = []  # list of (start_str, end_str)
        seen_times = set()
        cell_map = defaultdict(list)
        sections = set()
        for row in tt_rows:
            key = (row["Start"], row["End"])  # string HH:MM
            if key not in seen_times:
                seen_times.add(key)
                time_keys.append(key)
            sections.add((row["Semester"], row["Section"]))
            cell_key = (row["Semester"], row["Section"], row["Day"], row["Start"], row["End"])
            teacher_str = f" [{row['Teacher']}]" if row['Teacher'] else ""
            label = f"{row['Subject']} @ {row['Room']}{' (LAB)' if row['Type']=='lab' else ''}{teacher_str}"
            cell_map[cell_key].append(label)
        # Sort time_keys by Start then End
        def time_to_tuple(s):
            h, m = s.split(":"); return int(h), int(m)
        time_keys.sort(key=lambda x: (time_to_tuple(x[0]), time_to_tuple(x[1])))
        # Ordered sections by semester then name
        sections = sorted(list(sections), key=lambda x: (x[0], x[1]))
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

        pivot_rows = []
        for sem, sec in sections:
            for (start_s, end_s) in time_keys:
                row = {"Semester": sem, "Section": sec, "Time": f"{start_s}-{end_s}"}
                for d in days:
                    # cell_map stored full day names; map short to long
                    full = {"Mon": "Mon", "Tue": "Tue", "Wed": "Wed", "Thu": "Thu", "Fri": "Fri", "Sat": "Sat"}[d]
                    # Our Day column used get_day_display(), which is short label (Mon..Sat)
                    labels = cell_map.get((sem, sec, full, start_s, end_s), [])
                    row[d] = " | ".join(labels)
                pivot_rows.append(row)
        pivot_df = pd.DataFrame(pivot_rows, columns=["Semester", "Section", "Time", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]) if pivot_rows else pd.DataFrame(columns=["Semester", "Section", "Time", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
    else:
        pivot_df = pd.DataFrame(columns=["Semester", "Section", "Time", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])

    # Write workbook
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        timetable_df.to_excel(writer, sheet_name="Timetable", index=False)
        pivot_df.to_excel(writer, sheet_name="Timetable_Pivot", index=False)
        electives_df.to_excel(writer, sheet_name="Electives", index=False)
        
        # Add Teacher Schedule sheet
        teacher_rows = []
        for tt in (
            TimetableSlot.objects
            .select_related("teacher", "section", "subject", "room", "timeslot")
            .filter(teacher__isnull=False)
            .order_by("teacher__name", "timeslot__day", "timeslot__start_time")
        ):
            teacher_rows.append({
                "Teacher": tt.teacher.name,
                "Course": tt.subject.code,
                "Section": tt.section.name,
                "Room": tt.room.name,
                "Day": tt.timeslot.get_day_display(),
                "Time": f"{tt.timeslot.start_time.strftime('%H:%M')}-{tt.timeslot.end_time.strftime('%H:%M')}",
            })
        teacher_df = pd.DataFrame(teacher_rows) if teacher_rows else pd.DataFrame(columns=["Teacher", "Course", "Section", "Room", "Day", "Time"])
        teacher_df.to_excel(writer, sheet_name="Teacher_Schedule", index=False)
        
    return bio.getvalue()
