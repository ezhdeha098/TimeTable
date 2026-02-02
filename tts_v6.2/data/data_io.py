# data_io.py
import os
import json
import pandas as pd
import math

def load_usage(json_path: str) -> dict:
    if not os.path.exists(json_path):
        return {"theory": {}, "lab": {}}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_usage(json_path: str, usage_data: dict):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(usage_data, f, indent=2)

def reset_usage(json_path: str):
    empty_data = {"theory": {}, "lab": {}}
    save_usage(json_path, empty_data)

def parse_single_excel(file):
    xls = pd.ExcelFile(file)

    df_roadmap = pd.read_excel(xls, "Roadmap")
    semester_courses_map = {}
    for _, row in df_roadmap.iterrows():
        sem = int(row["semester"])
        code = str(row["course_code"]).strip()
        cname = str(row["course_name"]).strip()
        is_lab = str(row["is_lab"]).strip().lower() == "true"
        times_needed = int(row["times_needed"])
        credit_hour = 0
        if "credit_hour" in df_roadmap.columns and not pd.isna(row.get("credit_hour", None)):
            credit_hour = int(row["credit_hour"])
        semester_courses_map.setdefault(sem, [])
        semester_courses_map[sem].append((code, cname, is_lab, times_needed, credit_hour))

    df_rooms = pd.read_excel(xls, "Rooms")
    theory_rooms = []
    lab_rooms = []
    for _, row in df_rooms.iterrows():
        rname = str(row["room_name"]).strip()
        rtype = str(row["room_type"]).strip().lower()
        if rtype == "theory":
            theory_rooms.append(rname)
        else:
            lab_rooms.append(rname)

    df_cap = pd.read_excel(xls, "StudentCapacity")
    df_cap.columns = df_cap.columns.str.lower().str.strip()
    if "semester" not in df_cap.columns or "student_count" not in df_cap.columns:
        raise ValueError("StudentCapacity sheet must have 'semester' and 'student_count' columns.")
    student_capacities = {}
    for _, row in df_cap.iterrows():
        sem = int(row["semester"])
        student_capacities[sem] = int(row["student_count"])

    electives_list = []
    if "Electives" in xls.sheet_names:
        df_elec = pd.read_excel(xls, "Electives")
        df_elec.columns = df_elec.columns.str.lower().str.strip()
        for _, row in df_elec.iterrows():
            code = str(row["elective_code"]).strip()
            name = str(row["elective_name"]).strip()
            sec_count = int(row["sections_count"])
            can_th = (str(row["can_use_theory"]).lower() == "true")
            can_lb = (str(row["can_use_lab"]).lower() == "true")
            c_hour = 0
            if "credit_hour" in df_elec.columns and not pd.isna(row.get("credit_hour", None)):
                c_hour = int(row["credit_hour"])
            electives_list.append({
                "code": code,
                "name": name,
                "sections_count": sec_count,
                "can_theory": can_th,
                "can_lab": can_lb,
                "credit_hour": c_hour
            })

    special_lab_rooms = {}
    if "SpecialLabs" in xls.sheet_names:
        df_spec = pd.read_excel(xls, "SpecialLabs")
        df_spec.columns = df_spec.columns.str.lower().str.strip()
        required_cols = ["course_code", "lab_rooms"]
        for col in required_cols:
            if col not in df_spec.columns:
                raise ValueError(f"SpecialLabs sheet must have '{col}' column.")
        for _, row in df_spec.iterrows():
            course_code = str(row["course_code"]).strip()
            labs_str = str(row["lab_rooms"]).strip()
            labs = [x.strip() for x in labs_str.split(",") if x.strip()]
            if labs:
                special_lab_rooms[course_code] = labs

    return (
        semester_courses_map,
        theory_rooms,
        lab_rooms,
        student_capacities,
        electives_list,
        special_lab_rooms
    )
'''
def parse_cohort_excel(cohort_file) -> dict:
    df = pd.read_excel(cohort_file)
    df.columns = df.columns.str.strip()

    has_cohort_room = "CohortRoom" in df.columns
    cohort_map = {}

    day_map = {
        "Mon": "Monday",
        "Tue": "Tuesday",
        "Wed": "Wednesday",
        "Thu": "Thursday",
        "Fri": "Friday",
        "Sat": "Saturday"
    }

    for _, row in df.iterrows():
        sem = int(row["CohortSemester"])
        code = str(row["CourseCode"]).strip()
        cname = str(row["CourseName"]).strip()
        section = str(row["Section"]).strip()
        capacity = int(row["Capacity"])

        if has_cohort_room and pd.notna(row["CohortRoom"]) and str(row["CohortRoom"]).strip():
            actual_room = str(row["CohortRoom"]).strip()
        else:
            actual_room = f"CohortRoom({code}-{section})"

        day_time_list = []
        for short_day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            if short_day in df.columns:
                if pd.notna(row[short_day]):
                    slot = int(row[short_day])
                    full_day = day_map[short_day]
                    day_time_list.append((full_day, slot))

        entry = {
            "course_name": cname,
            "cohort_section": section,
            "capacity": capacity,
            "day_time_list": day_time_list,
            "cohort_room": actual_room
        }

        key = (sem, code)
        cohort_map.setdefault(key, []).append(entry)

    return cohort_map
'''
def parse_cohort_excel(cohort_file) -> dict:
    """
    Modified to split rows where 'Capacity' > 50 into multiple sub-sections
    with suffixes -A, -B, etc.
    """
    df = pd.read_excel(cohort_file)
    df.columns = df.columns.str.strip()

    has_cohort_room = "CohortRoom" in df.columns
    cohort_map = {}

    day_map = {
        "Mon": "Monday",
        "Tue": "Tuesday",
        "Wed": "Wednesday",
        "Thu": "Thursday",
        "Fri": "Friday",
        "Sat": "Saturday"
    }

    # We'll temporarily collect "split" entries here before populating cohort_map
    split_entries = []

    for _, row in df.iterrows():
        sem = int(row["CohortSemester"])
        code = str(row["CourseCode"]).strip()
        cname = str(row["CourseName"]).strip()
        section = str(row["Section"]).strip()
        capacity = int(row["Capacity"])

        if has_cohort_room and pd.notna(row["CohortRoom"]) and str(row["CohortRoom"]).strip():
            actual_room = str(row["CohortRoom"]).strip()
        else:
            actual_room = f"CohortRoom({code}-{section})"

        # Gather the day/time list
        day_time_list = []
        for short_day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            if short_day in df.columns and pd.notna(row[short_day]):
                slot = int(row[short_day])
                full_day = day_map[short_day]
                day_time_list.append((full_day, slot))

        # If the user already used a dash in Section (e.g. "C8-A"),
        # we assume they've already split it how they want. So no further slicing.
        if "-" in section:
            split_entries.append({
                "semester": sem,
                "code": code,
                "course_name": cname,
                "cohort_section": section,
                "capacity": capacity,
                "day_time_list": day_time_list,
                "cohort_room": actual_room
            })
        else:
            # Otherwise, if capacity > 50, split it into sub-sections of size 50
            leftover = capacity
            sub_index = 0
            base_name = section  # e.g. "C8"

            while leftover > 50:
                split_entries.append({
                    "semester": sem,
                    "code": code,
                    "course_name": cname,
                    "cohort_section": f"{base_name}-{chr(65 + sub_index)}",
                    "capacity": 50,
                    "day_time_list": day_time_list,
                    "cohort_room": actual_room
                })
                leftover -= 50
                sub_index += 1

            # Add the final chunk (could be <=50)
            split_entries.append({
                "semester": sem,
                "code": code,
                "course_name": cname,
                "cohort_section": f"{base_name}-{chr(65 + sub_index)}",
                "capacity": leftover,
                "day_time_list": day_time_list,
                "cohort_room": actual_room
            })

    # Build the final cohort_map from our split entries
    for entry in split_entries:
        key = (entry["semester"], entry["code"])
        csec_data = {
            "course_name": entry["course_name"],
            "cohort_section": entry["cohort_section"],
            "capacity": entry["capacity"],
            "day_time_list": entry["day_time_list"],
            "cohort_room": entry["cohort_room"]
        }
        cohort_map.setdefault(key, []).append(csec_data)

    return cohort_map

def validate_input_files(semester_courses_map, student_capacities, cohort_map, section_size=50):
    """
    Revised validation to handle large capacities:
      - For each course that is "cohort scheduled," the sum of the capacities in the cohort file
        must be >= (n_sections * 50).
    """
    errors = []
    for sem, courses in semester_courses_map.items():
        # Number of normal sections for the entire semester, e.g. for 100 students => 2 sections at 50 each
        n_sections = math.ceil(student_capacities.get(sem, 50) / section_size)

        for (code, cname, is_lab, times_needed, credit_hour) in courses:
            # If this course is in the cohort map => check if total capacity is enough
            if cohort_map and (sem, code) in cohort_map:
                # sum up all capacities in cohort_map for (sem, code)
                total_cohort_capacity = sum(x["capacity"] for x in cohort_map[(sem, code)])
                needed_seats = n_sections * 50

                # If total_cohort_capacity < needed_seats => error
                if total_cohort_capacity < needed_seats:
                    errors.append(
                        f"Semester {sem} course {code} ({cname}) requires cohort scheduling, "
                        f"but total capacity in cohort file = {total_cohort_capacity} is less "
                        f"than {needed_seats} seats needed for {n_sections} section(s)."
                    )

    return errors
