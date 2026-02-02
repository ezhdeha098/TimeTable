# utils.py
import math
import pandas as pd
import re  # Added for regex to remove suffixes

def build_sections_for_semester(semester_num, num_students, section_size=50, program_code="A"):
    count = math.ceil(num_students / section_size)
    sections = []
    for i in range(count):
        sections.append(f"S{semester_num}{program_code}{i+1}")
    return sections

def build_section_dataframe(
    section_name,
    courses,
    schedule_map,
    DAYS,
    THEORY_TIMESLOTS,
    TIMESLOT_LABELS,
    LAB_SLOTS,
    LAB_SLOT_LABELS,
    theory_rooms,
    lab_rooms,
    special_lab_rooms
):
    """
    Updated to split multi-slot labs into multiple output rows
    (e.g. S1A1-A, S1A1-B) instead of a single row with two slots combined.
    Also removing -A, -B suffixes from cohort course sections (like C08-A -> C08).
    """
    # We won't alter how the solver schedules rooms.
    # We'll only change how we present them in the final DataFrame.
    rows = []

    # Helper function to remove -A, -B suffixes from section names
    def clean_section_name(section):
        if section and re.match(r'^C\d+-[A-Z]$', section):  # Matches patterns like C08-A
            return section.split('-')[0]  # Return only C08 part
        return section

    # For each course in this section, collect all assigned (day, slot, room, occupant_cohort).
    for (code, cname, is_lab, times_needed, credit_hour) in courses:

        # We will group the occupant assignments by occupant_cohort,
        # because for cohort-based courses, occupant_cohort might differ.
        # If occupant_cohort is None, treat it as a single group "None".
        occupant_groups = {}  # occupant_cohort -> list of (day, slot, room)

        for (day, slot, room), occupant in schedule_map.items():
            if occupant is None:
                continue
            if len(occupant) != 3:
                continue
            (occ_sec, occ_code, occ_cohort) = occupant

            # We only care about occupant assignments that match
            # (this section, this course code).
            if occ_sec == section_name and occ_code == code:
                occupant_groups.setdefault(occ_cohort, []).append((day, slot, room))

        # If no occupant assignments at all, just produce an empty row
        if not occupant_groups:
            row_data = {
                "Course Code": code,
                "Course Name": cname,
                "Credit hour": credit_hour,
                "Section": section_name
            }
            for d in DAYS:
                row_data[d] = ""
            rows.append(row_data)
            continue

        # For each occupant_cohort we found:
        for occupant_cohort, assignments_list in occupant_groups.items():
            if not is_lab:
                # ---------- THEORY: keep the old approach (one row, multiple time slots) ----------
                day_to_display = {d: [] for d in DAYS}
                # Gather all assigned day/time
                for (day, slot, room) in assignments_list:
                    label = TIMESLOT_LABELS.get(slot, f"Slot {slot}")
                    display_str = f"{room} [{label}]"  # Add back room number
                    day_to_display[day].append(display_str)

                # Build a single row with the occupant_cohort if it exists:
                final_section_label = occupant_cohort if occupant_cohort else section_name
                # Clean section name to remove -A, -B suffixes
                final_section_label = clean_section_name(final_section_label)
                
                row_data = {
                    "Course Code": code,
                    "Course Name": cname,
                    "Credit hour": credit_hour,
                    "Section": final_section_label
                }
                for d in DAYS:
                    row_data[d] = ", ".join(day_to_display[d]) if day_to_display[d] else ""
                rows.append(row_data)

            else:
                # ---------- LAB: if multiple slots, split them so each slot is its own row ----------
                # If occupant_cohort is given, start from that name; otherwise use section_name.
                base_label = occupant_cohort if occupant_cohort else section_name
                # Clean section name to remove -A, -B suffixes
                base_label = clean_section_name(base_label)

                # If there's only 1 assignment for this occupant_cohort, just do a single row
                if len(assignments_list) == 1:
                    (day, slot, room) = assignments_list[0]
                    label = LAB_SLOT_LABELS.get(slot, f"LabSlot {slot}")
                    display_str = f"{room} [{label}]"  # Add back room number
                    row_data = {
                        "Course Code": code,
                        "Course Name": cname,
                        "Credit hour": credit_hour,
                        "Section": base_label
                    }
                    for d in DAYS:
                        row_data[d] = ""
                    row_data[day] = display_str
                    rows.append(row_data)
                else:
                    # We have multiple lab slots => produce multiple sub-rows
                    for i, (day, slot, room) in enumerate(assignments_list):
                        sub_suffix = chr(65 + i)  # A, B, C, ...
                        label = LAB_SLOT_LABELS.get(slot, f"LabSlot {slot}")
                        display_str = f"{room} [{label}]"  # Add back room number

                        row_data = {
                            "Course Code": code,
                            "Course Name": cname,
                            "Credit hour": credit_hour,
                            # e.g. "S1A1-A" or "Physics101-B"
                            "Section": f"{base_label}-{sub_suffix}"
                        }
                        # blank out all columns
                        for d in DAYS:
                            row_data[d] = ""
                        # place the single lab timeslot
                        row_data[day] = display_str
                        rows.append(row_data)

    # After building up the row list, convert to DataFrame
    df = pd.DataFrame(rows, columns=["Course Code", "Course Name", "Credit hour", "Section", *DAYS])
    return df

def build_room_usage_df(
    room,
    schedule_map,
    is_lab,
    DAYS,
    THEORY_TIMESLOTS,
    TIMESLOT_LABELS,
    LAB_SLOTS,
    LAB_SLOT_LABELS
):
    # Helper function to remove -A, -B suffixes from section names
    def clean_section_name(section):
        if section and re.match(r'^C\d+-[A-Z]$', section):  # Matches patterns like C08-A
            return section.split('-')[0]  # Return only C08 part
        return section
        
    data = []
    if not is_lab:
        for day in DAYS:
            row = {}
            for t in THEORY_TIMESLOTS:
                occupant = schedule_map.get((day, t, room))
                if occupant is None:
                    row[t] = "Free"
                else:
                    (secName, code, cohortSec) = occupant
                    label_sec = cohortSec if cohortSec else secName
                    label_sec = clean_section_name(label_sec)
                    row[t] = f"{label_sec}-{code}"
            data.append(row)
        df = pd.DataFrame(data, index=DAYS)
        df.columns = [TIMESLOT_LABELS.get(t, f"Slot {t}") for t in THEORY_TIMESLOTS]
    else:
        for day in DAYS:
            row = {}
            for ls in LAB_SLOTS:
                occupant = schedule_map.get((day, ls, room))
                if occupant is None:
                    row[ls] = "Free"
                else:
                    (secName, code, cohortSec) = occupant
                    label_sec = cohortSec if cohortSec else secName
                    label_sec = clean_section_name(label_sec)
                    row[ls] = f"{label_sec}-{code}"
            data.append(row)
        df = pd.DataFrame(data, index=DAYS)
        df.columns = [LAB_SLOT_LABELS.get(ls, f"LabSlot {ls}") for ls in LAB_SLOTS]
    return df

def build_full_room_usage_df(
    room: str,
    rtype: str,
    usage_data: dict,
    schedule_map: dict,
    DAYS: list,
    THEORY_TIMESLOTS: list,
    LAB_SLOTS: list,
    TIMESLOT_LABELS: dict,
    LAB_SLOT_LABELS: dict
):
    import pandas as pd
    
    # Helper function to remove -A, -B suffixes from section names
    def clean_section_name(section):
        if section and re.match(r'^C\d+-[A-Z]$', section):  # Matches patterns like C08-A
            return section.split('-')[0]  # Return only C08 part
        return section

    if rtype == "theory":
        slot_list = THEORY_TIMESLOTS
        slot_labels = TIMESLOT_LABELS
        old_dict = usage_data["theory"]
    else:
        slot_list = LAB_SLOTS
        slot_labels = LAB_SLOT_LABELS
        old_dict = usage_data["lab"]

    old_room_usage = old_dict.get(room, {})
    data = []
    for day in DAYS:
        row = {}
        for slot in slot_list:
            previously_used = False
            if day in old_room_usage:
                if slot in old_room_usage[day]:
                    previously_used = True

            occupant = schedule_map.get((day, slot, room), None)
            if occupant:
                (secName, code, csec) = occupant
                label_sec = csec if csec else secName
                label_sec = clean_section_name(label_sec)
                row[slot] = f"{label_sec}-{code}"
            else:
                row[slot] = "(Previously Occupied)" if previously_used else "Free"
        data.append(row)

    df = pd.DataFrame(data, index=DAYS)
    df.rename(columns={s: slot_labels.get(s, f"Slot {s}") for s in slot_list}, inplace=True)
    return df

def build_elective_dataframe(
    electives_list,
    schedule_map_elec,
    DAYS,
    THEORY_TIMESLOTS,
    LAB_SLOTS,
    TIMESLOT_LABELS,
    LAB_SLOT_LABELS
):
    import pandas as pd

    rows = []
    for elec in electives_list:
        e_code = elec["code"]
        e_name = elec["name"]
        sec_count = elec["sections_count"]
        e_cred = elec.get("credit_hour", 0)

        for idx in range(sec_count):
            day_map = {d: [] for d in DAYS}
            assigned_slots = schedule_map_elec.get((e_code, idx), [])
            for (rtype, room, d, slot) in assigned_slots:
                if rtype == "theory":
                    lbl = TIMESLOT_LABELS.get(slot, f"Slot {slot}")
                else:
                    lbl = LAB_SLOT_LABELS.get(slot, f"LabSlot {slot}")
                day_map[d].append(f"{room} [{lbl}]")

            row_data = {
                "Elective Code": e_code,
                "Elective Name": e_name,
                "Credit hour": e_cred,
                "Section": f"A{idx+1}"
            }
            for d in DAYS:
                row_data[d] = ", ".join(day_map[d]) if day_map[d] else ""
            rows.append(row_data)

    df = pd.DataFrame(rows, columns=["Elective Code", "Elective Name", "Credit hour", "Section", *DAYS])
    return df
