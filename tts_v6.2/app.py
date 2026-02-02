import streamlit as st
import os
import math
import pandas as pd
import io
from io import BytesIO
from openpyxl import workbook

from data.data_io import (
    load_usage,
    save_usage,
    reset_usage,
    parse_single_excel,
    parse_cohort_excel,
    validate_input_files  # (Still used for cohort capacity consistency)
)
from data.consistency_check import validate_main_excel, validate_cohort_excel

# Import optimized solver with automatic hierarchical solving for large problems
from scheduling.solver_optimized import schedule_with_auto_optimization

from scheduling.electives_solver import schedule_electives
from scheduling.utils import (
    build_full_room_usage_df,
    build_section_dataframe,
    build_room_usage_df,
    build_elective_dataframe
)

def main():
    st.title("UMT Timetable Scheduler")

    # Basic scheduling parameters
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    THEORY_TIMESLOTS = [0, 1, 2, 3, 4, 5, 6]
    LAB_SLOTS = [0, 1, 2, 3]
    TIMESLOT_LABELS = {
        0: "8:00-9:15",
        1: "9:30-10:45",
        2: "11:00-12:15",
        3: "12:30-1:45",
        4: "2:00-3:15",
        5: "3:30-4:45",
        6: "5:00-6:15"
    }
    LAB_SLOT_LABELS = {
        0: "8:00-10:30",
        1: "11:00-1:30",
        2: "2:00-4:30",
        3: "5:00-7:30"
    }
    LAB_OVERLAP_MAP = {
        0: [0, 1],
        1: [2, 3],
        2: [4, 5],
        3: [6]
    }

    # Sidebar Actions
    st.sidebar.subheader("Actions")
    if st.sidebar.button("Reset Usage Data"):
        reset_usage(os.path.join("data", "usage_data.json"))
        for key in [
            "excel_file", "cohort_file", "main_timetable_excel", 
            "remcap_excel", "elec_excel", "remcap_elec_excel",
            "timetable_data", "electives_data"
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if st.sidebar.button("Schedule a New Timetable"):
        for key in [
            "excel_file", "cohort_file", "main_timetable_excel", 
            "remcap_excel", "elec_excel", "remcap_elec_excel",
            "timetable_data", "electives_data"
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    use_previous = st.sidebar.checkbox("Use previous slots", value=True)

    # --- Upload Main Excel and run consistency check ---
    st.sidebar.subheader("Upload Main Excel")
    excel_file = st.sidebar.file_uploader(
        "Roadmap/Rooms/Capacities/Electives/SpecialLabs",
        type=["xlsx"],
        key="excel_file"
    )
    if not excel_file:
        st.info("Please upload the main Excel file.")
        return

    # Read file bytes to run consistency check and then parse the file
    excel_file.seek(0)
    excel_bytes = excel_file.read()
    excel_file.seek(0)
    # Validate main Excel file consistency
    main_errors = validate_main_excel(excel_bytes)
    if main_errors:
        for err in main_errors:
            st.error(err)
        st.stop()

    with st.spinner("Reading main Excel..."):
        try:
            (semester_courses_map,
             excel_theory_rooms,
             excel_lab_rooms,
             student_capacities,
             electives_list,
             special_lab_rooms) = parse_single_excel(BytesIO(excel_bytes))
        except Exception as e:
            st.error(f"Error reading Excel: {e}")
            return
    st.success("Main Excel loaded!")

    # Load usage data (previously saved room usage)
    usage_path = os.path.join("data", "usage_data.json")
    if use_previous:
        usage_data = load_usage(usage_path)
    else:
        usage_data = {"theory": {}, "lab": {}}

    # Combine discovered rooms from usage data with those from Excel
    if "theory_rooms_current" not in st.session_state:
        st.session_state["theory_rooms_current"] = list(
            set(excel_theory_rooms) | set(usage_data["theory"].keys())
        )
    if "lab_rooms_current" not in st.session_state:
        # Include special lab rooms in the lab rooms list
        special_lab_room_names = set()
        for lab_list in special_lab_rooms.values():
            special_lab_room_names.update(lab_list)
        st.session_state["lab_rooms_current"] = list(
            set(excel_lab_rooms) | set(usage_data["lab"].keys()) | special_lab_room_names
        )
    if "special_lab_rooms" not in st.session_state:
        st.session_state["special_lab_rooms"] = special_lab_rooms

    current_theory_rooms = st.session_state["theory_rooms_current"]
    current_lab_rooms = st.session_state["lab_rooms_current"]
    special_lab_rooms = st.session_state["special_lab_rooms"]

    # --- Manage Rooms Sidebar ---
    st.sidebar.subheader("Manage Rooms")
    theory_remove = st.sidebar.multiselect("Remove Theory Rooms", current_theory_rooms)
    lab_remove = st.sidebar.multiselect("Remove Lab Rooms", current_lab_rooms)
    if st.sidebar.button("Remove Selected Rooms"):
        for r in theory_remove:
            if r in current_theory_rooms:
                current_theory_rooms.remove(r)
                st.sidebar.success(f"Removed theory room '{r}'.")
        for r in lab_remove:
            if r in current_lab_rooms:
                current_lab_rooms.remove(r)
                st.sidebar.success(f"Removed lab room '{r}'.")
    st.sidebar.subheader("Add a New Room")
    new_room_name = st.sidebar.text_input("Room Name", "")
    new_room_type = st.sidebar.selectbox("Room Type", ["theory", "lab"])
    if st.sidebar.button("Add Room"):
        if new_room_name.strip():
            if new_room_type == "theory":
                if new_room_name not in current_theory_rooms:
                    current_theory_rooms.append(new_room_name)
                    st.sidebar.success(f"Added theory room '{new_room_name}'.")
                    if new_room_name not in usage_data["theory"]:
                        usage_data["theory"][new_room_name] = {}
                        save_usage(usage_path, usage_data)
                else:
                    st.sidebar.error(f"Theory room '{new_room_name}' already exists.")
            else:
                if new_room_name not in current_lab_rooms:
                    current_lab_rooms.append(new_room_name)
                    st.sidebar.success(f"Added lab room '{new_room_name}'.")
                    if new_room_name not in usage_data["lab"]:
                        usage_data["lab"][new_room_name] = {}
                        save_usage(usage_path, usage_data)
                else:
                    st.sidebar.error(f"Lab room '{new_room_name}' already exists.")
        else:
            st.sidebar.error("Please enter a valid room name.")

    # --- Manage Special Labs ---
    st.sidebar.subheader("Manage Special Labs")
    if special_lab_rooms:
        for code, labs in special_lab_rooms.items():
            st.sidebar.write(f"**{code}** => {labs}")
    spec_remove = st.sidebar.multiselect("Remove Special Lab Keys", list(special_lab_rooms.keys()))
    if st.sidebar.button("Remove Selected Special Labs"):
        for key in spec_remove:
            special_lab_rooms.pop(key, None)
            st.sidebar.success(f"Removed special lab for '{key}'.")
    new_spec_key = st.sidebar.text_input("New Special Lab Course Code", key="new_spec_key")
    new_spec_rooms = st.sidebar.text_input("Special Lab Rooms (comma separated)", key="new_spec_rooms")
    if st.sidebar.button("Add/Update Special Lab"):
        if new_spec_key.strip() and new_spec_rooms.strip():
            labs = [x.strip() for x in new_spec_rooms.split(",") if x.strip()]
            special_lab_rooms[new_spec_key.strip()] = labs
            st.sidebar.success(f"Set special labs for {new_spec_key.strip()} = {labs}")
        else:
            st.sidebar.error("Please provide both a course code and room names.")

    # --- Semesters and Student Capacities ---
    st.sidebar.subheader("Select Semesters")
    all_semesters = sorted(semester_courses_map.keys())
    selected_semesters = st.sidebar.multiselect("Semesters", all_semesters, default=all_semesters)
    if not selected_semesters:
        st.warning("No semester selected.")
        return
    st.sidebar.subheader("Student Capacities")
    final_capacities = {}
    for sem in selected_semesters:
        def_val = student_capacities.get(sem, 50)
        val = st.sidebar.number_input(f"Semester {sem} Students", min_value=1, value=def_val)
        final_capacities[sem] = val

    st.sidebar.subheader("Program Code")
    program_code = st.sidebar.text_input("Program Code", value="A")
    st.sidebar.subheader("Output Filenames")
    out_file = st.sidebar.text_input("Main Timetable Filename", "timetables.xlsx")
    remcap_file = st.sidebar.text_input("Remaining Capacity Workbook", "remaining_capacity.xlsx")
    elec_out_file = st.sidebar.text_input("Electives Timetable Filename", "electives_timetable.xlsx")
    remcap_elec_file = st.sidebar.text_input("Remaining Capacity After Electives", "remaining_capacity_electives.xlsx")

    # --- Cohort Scheduling ---
    enable_cohort = st.sidebar.checkbox("Include Cohort Courses?")
    cohort_map = None
    if enable_cohort:
        cohort_file = st.sidebar.file_uploader("Upload Cohort Excel", type=["xlsx"], key="cohort_file")
        if cohort_file:
            cohort_file.seek(0)
            cohort_bytes = cohort_file.read()
            cohort_file.seek(0)
            # Validate the cohort file consistency
            cohort_errors = validate_cohort_excel(cohort_bytes)
            if cohort_errors:
                for err in cohort_errors:
                    st.error(err)
                st.stop()
            with st.spinner("Reading Cohort Excel..."):
                try:
                    cohort_map = parse_cohort_excel(BytesIO(cohort_bytes))
                except Exception as e:
                    st.error(f"Error reading cohort Excel: {e}")
                    return
            st.success("Cohort Excel loaded!")
            # Validate capacity consistency between main and cohort files
            errors = validate_input_files(semester_courses_map, student_capacities, cohort_map, section_size=50)
            if errors:
                for err in errors:
                    st.error(err)
                st.stop()
        else:
            st.info("No cohort file uploaded, but 'Include Cohort Courses?' is checked.")

    # --- Room Capacity Calculation ---
    def get_free_slot_count(rtype, room_name):
        if rtype == "theory":
            # Total theory slots = 6 days * 7 slots - 1 blocked Friday slot = 41 slots
            total = len(DAYS) * len(THEORY_TIMESLOTS) - 1  # Subtract 1 for Friday slot 3
            used = sum(len(usage_data["theory"].get(room_name, {}).get(day, [])) for day in DAYS)
            return total - used
        else:
            total = len(DAYS) * len(LAB_SLOTS)
            used = sum(len(usage_data["lab"].get(room_name, {}).get(day, [])) for day in DAYS)
            return total - used

    filtered_theory_rooms = [r for r in st.session_state["theory_rooms_current"] if get_free_slot_count("theory", r) > 0]
    filtered_lab_rooms = [r for r in st.session_state["lab_rooms_current"] if get_free_slot_count("lab", r) > 0]

    st.write("### Current Rooms (with >0 free slots)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**Theory Rooms:**")
        st.write(filtered_theory_rooms)
    with col2:
        st.write("**Lab Rooms:**")
        st.write(filtered_lab_rooms)
    with col3:
        st.write("**Special Labs:**")
        st.write(special_lab_rooms)

    # --- Quick Slot Capacity Check ---
    total_needed_theory_slots = 0
    total_needed_lab_slots = 0
    total_needed_special_lab = 0
    special_lab_details = {}

    for sem in selected_semesters:
        sec_count = math.ceil(final_capacities[sem] / 50)
        for (code, cname, is_lab, times_needed, _ch) in semester_courses_map[sem]:
            if enable_cohort and cohort_map and (sem, code) in cohort_map:
                continue
            if is_lab:
                if code in special_lab_rooms:
                    needed_slots = times_needed * sec_count
                    total_needed_special_lab += needed_slots
                    special_lab_details[code] = needed_slots
                else:
                    total_needed_lab_slots += (times_needed * sec_count)
            else:
                total_needed_theory_slots += (times_needed * sec_count)

    free_theory_cap = sum(get_free_slot_count("theory", r) for r in filtered_theory_rooms)
    
    # Calculate normal lab capacity (excluding special lab rooms)
    special_lab_room_names = set()
    for lab_list in special_lab_rooms.values():
        special_lab_room_names.update(lab_list)
    normal_lab_rooms = [r for r in filtered_lab_rooms if r not in special_lab_room_names]
    free_lab_cap = sum(get_free_slot_count("lab", r) for r in normal_lab_rooms)
    
    # Calculate special lab capacity per course
    special_lab_capacities = {}
    total_special_lab_cap = 0
    for code, lab_list in special_lab_rooms.items():
        course_capacity = sum(get_free_slot_count("lab", r) for r in lab_list if r in st.session_state["lab_rooms_current"])
        special_lab_capacities[code] = course_capacity
        total_special_lab_cap += course_capacity

    st.write("### Required vs. Available Slots (Main Courses)")
    st.write(f"- **Theory:** Needed = {total_needed_theory_slots}, Available = {free_theory_cap}")
    st.write(f"- **Lab:** Needed = {total_needed_lab_slots}, Available = {free_lab_cap}")
    if special_lab_details:
        st.write("- **Special Lab:**")
        for code, needed in special_lab_details.items():
            available = special_lab_capacities.get(code, 0)
            st.write(f"  -> {code}: Needed = {needed}, Available = {available}")

    with st.expander("Show Detailed Slot Requirements & Minimum Room Suggestions"):
        st.write("#### Detailed Slot Requirements")
        st.write(f"* Theory slots needed: {total_needed_theory_slots}")
        st.write(f"* Lab slots needed (normal): {total_needed_lab_slots}")
        st.write(f"* Special lab slots needed: {total_needed_special_lab}")
        st.write(f"* Theory free slots: {free_theory_cap}")
        st.write(f"* Lab free slots (normal): {free_lab_cap}")
        st.write(f"* Special lab free slots: {total_special_lab_cap}")
        if special_lab_capacities:
            st.write("* Special lab breakdown:")
            for code, capacity in special_lab_capacities.items():
                st.write(f"  - {code}: {capacity} slots available")
        theory_capacity_per_room = len(DAYS) * len(THEORY_TIMESLOTS) - 1  # Account for blocked Friday slot
        lab_capacity_per_room = len(DAYS) * len(LAB_SLOTS)
        min_theory_rooms = math.ceil(total_needed_theory_slots / theory_capacity_per_room) if theory_capacity_per_room > 0 else 0
        min_lab_rooms = math.ceil((total_needed_lab_slots + total_needed_special_lab) / lab_capacity_per_room) if lab_capacity_per_room > 0 else 0
        st.write("#### Minimum Room Suggestions:")
        st.write(f"* Minimum Theory Rooms Needed: {min_theory_rooms}")
        st.write(f"* Minimum Lab Rooms Needed: {min_lab_rooms}")

    # Check if each special lab course has enough capacity
    special_labs_feasible = True
    for code, needed in special_lab_details.items():
        available = special_lab_capacities.get(code, 0)
        if needed > available:
            special_labs_feasible = False
            break
    
    can_generate_main = (total_needed_theory_slots <= free_theory_cap and 
                        total_needed_lab_slots <= free_lab_cap and 
                        special_labs_feasible)

    if "timetable_data" not in st.session_state:
        st.session_state["timetable_data"] = {}
    if "electives_data" not in st.session_state:
        st.session_state["electives_data"] = {}

    # --- Main Timetable Generation ---
    if st.button("Generate Timetable (Main)", disabled=not can_generate_main):
        if not can_generate_main:
            st.error("Not enough slots for main courses.")
            st.stop()

        with st.spinner("Scheduling main timetable..."):
            usage_now = load_usage(usage_path)
            try:
                # Use optimized solver with automatic hierarchical solving for large problems
                result = schedule_with_auto_optimization(
                    selected_semesters=selected_semesters,
                    semester_courses_map=semester_courses_map,
                    section_sizes=final_capacities,
                    usage_data=usage_now,
                    DAYS=DAYS,
                    THEORY_TIMESLOTS=THEORY_TIMESLOTS,
                    TIMESLOT_LABELS=TIMESLOT_LABELS,
                    LAB_SLOTS=LAB_SLOTS,
                    LAB_SLOT_LABELS=LAB_SLOT_LABELS,
                    LAB_OVERLAP_MAP=LAB_OVERLAP_MAP,
                    theory_rooms=filtered_theory_rooms,
                    lab_rooms=filtered_lab_rooms,
                    special_lab_rooms=special_lab_rooms,
                    section_size=50,
                    program_code=program_code,
                    cohort_map=cohort_map,
                    enable_cohort=enable_cohort,
                    hierarchical_threshold=300  # Auto uses hierarchical if > 300 courses
                )
            except ValueError as e:
                st.error(f"Scheduling error: {e}")
                st.stop()

            if not result:
                st.error("No feasible solution found for main timetable. Try adding more rooms.")
                st.stop()

            schedule_map, sem_sections_map, new_allocs = result

            usage_data_current = load_usage(usage_path)
            for (rtype, rname, day, slot, occupant) in new_allocs:
                usage_data_current.setdefault(rtype, {})
                usage_data_current[rtype].setdefault(rname, {})
                usage_data_current[rtype][rname].setdefault(day, [])
                if slot not in usage_data_current[rtype][rname][day]:
                    usage_data_current[rtype][rname][day].append(slot)
            save_usage(usage_path, usage_data_current)

            all_frames = []
            timetable_buffer = io.BytesIO()
            with pd.ExcelWriter(timetable_buffer, engine="openpyxl") as writer:
                for sem, sections in sem_sections_map.items():
                    frames = []
                    for sec in sections:
                        courses = semester_courses_map[sem]
                        df_sec = build_section_dataframe(
                            section_name=sec,
                            courses=courses,
                            schedule_map=schedule_map,
                            DAYS=DAYS,
                            THEORY_TIMESLOTS=THEORY_TIMESLOTS,
                            TIMESLOT_LABELS=TIMESLOT_LABELS,
                            LAB_SLOTS=LAB_SLOTS,
                            LAB_SLOT_LABELS=LAB_SLOT_LABELS,
                            theory_rooms=filtered_theory_rooms,
                            lab_rooms=filtered_lab_rooms,
                            special_lab_rooms=special_lab_rooms
                        )
                        df_sec.insert(0, "Semester", sem)
                        frames.append(df_sec)
                        all_frames.append(df_sec)
                    if frames:
                        df_sem = pd.concat(frames, ignore_index=True)
                        df_sem.to_excel(writer, sheet_name=f"Semester_{sem}", index=False)
                if all_frames:
                    df_all = pd.concat(all_frames, ignore_index=True)
                    df_all.to_excel(writer, sheet_name="All_Sections", index=False)
            timetable_buffer.seek(0)
            st.session_state["main_timetable_excel"] = timetable_buffer.getvalue()

            summary_rows = []
            for r in filtered_theory_rooms:
                used = sum(len(usage_data_current["theory"].get(r, {}).get(day, [])) for day in DAYS)
                total = len(DAYS) * len(THEORY_TIMESLOTS) - 1  # Account for blocked Friday slot
                summary_rows.append([r, "Theory", used, total - used, total])
            for r in filtered_lab_rooms:
                used = sum(len(usage_data_current["lab"].get(r, {}).get(day, [])) for day in DAYS)
                total = len(DAYS) * len(LAB_SLOTS)
                summary_rows.append([r, "Lab", used, total - used, total])
            df_main_sum = pd.DataFrame(summary_rows, columns=["Room", "Type", "Used Slots", "Free Slots", "Total Slots"])
            remcap_buffer = io.BytesIO()
            with pd.ExcelWriter(remcap_buffer, engine="openpyxl") as writer2:
                df_main_sum.to_excel(writer2, sheet_name="Summary", index=False)
                for rr in filtered_theory_rooms:
                    df_tr = build_full_room_usage_df(
                        room=rr,
                        rtype="theory",
                        usage_data=usage_data_current,
                        schedule_map=schedule_map,
                        DAYS=DAYS,
                        THEORY_TIMESLOTS=THEORY_TIMESLOTS,
                        LAB_SLOTS=LAB_SLOTS,
                        TIMESLOT_LABELS=TIMESLOT_LABELS,
                        LAB_SLOT_LABELS=LAB_SLOT_LABELS
                    )
                    df_tr.to_excel(writer2, sheet_name=(rr[:20] + "_Usage"), index=True)
                for lb in filtered_lab_rooms:
                    df_lb = build_full_room_usage_df(
                        room=lb,
                        rtype="lab",
                        usage_data=usage_data_current,
                        schedule_map=schedule_map,
                        DAYS=DAYS,
                        THEORY_TIMESLOTS=THEORY_TIMESLOTS,
                        LAB_SLOTS=LAB_SLOTS,
                        TIMESLOT_LABELS=TIMESLOT_LABELS,
                        LAB_SLOT_LABELS=LAB_SLOT_LABELS
                    )
                    df_lb.to_excel(writer2, sheet_name=(lb[:20] + "_Usage"), index=True)
            remcap_buffer.seek(0)
            st.session_state["remcap_excel"] = remcap_buffer.getvalue()

            table_data = {}
            for sem, sec_list in sem_sections_map.items():
                sem_dict = {}
                for sec in sec_list:
                    df_sec = build_section_dataframe(
                        section_name=sec,
                        courses=semester_courses_map[sem],
                        schedule_map=schedule_map,
                        DAYS=DAYS,
                        THEORY_TIMESLOTS=THEORY_TIMESLOTS,
                        TIMESLOT_LABELS=TIMESLOT_LABELS,
                        LAB_SLOTS=LAB_SLOTS,
                        LAB_SLOT_LABELS=LAB_SLOT_LABELS,
                        theory_rooms=filtered_theory_rooms,
                        lab_rooms=filtered_lab_rooms,
                        special_lab_rooms=special_lab_rooms
                    )
                    sem_dict[sec] = df_sec
                table_data[sem] = sem_dict
            st.session_state["timetable_data"] = {
                "semester_sections": table_data,
                "room_summary": df_main_sum
            }

    if "timetable_data" in st.session_state and "semester_sections" in st.session_state["timetable_data"]:
        st.header("Generated Timetables by Section (Main)")
        for sem, sec_map in st.session_state["timetable_data"]["semester_sections"].items():
            with st.expander(f"Semester {sem}", expanded=False):
                for sec, df_sec in sec_map.items():
                    st.markdown(f"**Section {sec}**")
                    st.table(df_sec)
        st.header("Room Usage & Remaining Capacity (Main)")
        with st.expander("Show Room Summary"):
            st.table(st.session_state["timetable_data"]["room_summary"])

    if "main_timetable_excel" in st.session_state:
        st.download_button(
            label="Download Main Timetable Excel",
            data=st.session_state["main_timetable_excel"],
            file_name=out_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    if "remcap_excel" in st.session_state:
        st.download_button(
            label="Download Remaining Capacity Workbook",
            data=st.session_state["remcap_excel"],
            file_name=remcap_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- Electives Scheduling ---
    if electives_list:
        st.header("Schedule Electives")
        if "main_timetable_excel" not in st.session_state:
            st.info("Generate the main timetable first.")
        else:
            leftover_theory = sum(get_free_slot_count("theory", r) for r in filtered_theory_rooms)
            leftover_lab = sum(get_free_slot_count("lab", r) for r in filtered_lab_rooms)
            max_theory_needed = 0
            max_lab_needed = 0
            for elec in electives_list:
                if elec["can_theory"]:
                    max_theory_needed += 2 * elec["sections_count"]
                if elec["can_lab"]:
                    max_lab_needed += 1 * elec["sections_count"]
            st.write(f"Potentially, up to {max_theory_needed} theory slots & {max_lab_needed} lab slots needed.")
            st.write(f"Leftover theory capacity: {leftover_theory}, leftover lab capacity: {leftover_lab}")
            if st.button("Generate Electives Timetable"):
                with st.spinner("Scheduling electives..."):
                    usage_latest = load_usage(usage_path)
                    result_elec = schedule_electives(
                        electives_list=electives_list,
                        usage_data=usage_latest,
                        DAYS=DAYS,
                        THEORY_TIMESLOTS=THEORY_TIMESLOTS,
                        LAB_SLOTS=LAB_SLOTS,
                        theory_rooms=filtered_theory_rooms,
                        lab_rooms=filtered_lab_rooms,
                        timeslot_labels=TIMESLOT_LABELS,
                        lab_slot_labels=LAB_SLOT_LABELS,
                        theory_needed=2,
                        lab_needed=1
                    )
                if result_elec is None:
                    st.error("No feasible solution found for electives. Try adding more rooms.")
                else:
                    schedule_map_elec, new_allocs_elec = result_elec
                    st.success("Electives scheduled successfully!")
                    usage_latest2 = load_usage(usage_path)
                    for (rtype, rname, day, slot, occupant) in new_allocs_elec:
                        usage_latest2.setdefault(rtype, {})
                        usage_latest2[rtype].setdefault(rname, {})
                        usage_latest2[rtype][rname].setdefault(day, [])
                        if slot not in usage_latest2[rtype][rname][day]:
                            usage_latest2[rtype][rname][day].append(slot)
                    save_usage(usage_path, usage_latest2)
                    df_elec = build_elective_dataframe(
                        electives_list,
                        schedule_map_elec,
                        DAYS,
                        THEORY_TIMESLOTS,
                        LAB_SLOTS,
                        TIMESLOT_LABELS,
                        LAB_SLOT_LABELS
                    )
                    st.session_state["electives_data"]["df_elec"] = df_elec
                    summary_rows_e = []
                    for r in filtered_theory_rooms:
                        used = sum(len(usage_latest2["theory"].get(r, {}).get(day, [])) for day in DAYS)
                        total = len(DAYS) * len(THEORY_TIMESLOTS) - 1  # Account for blocked Friday slot
                        summary_rows_e.append([r, "Theory", used, total - used, total])
                    for r in filtered_lab_rooms:
                        used = sum(len(usage_latest2["lab"].get(r, {}).get(day, [])) for day in DAYS)
                        total = len(DAYS) * len(LAB_SLOTS)
                        summary_rows_e.append([r, "Lab", used, total - used, total])
                    df_elec_sum = pd.DataFrame(summary_rows_e, columns=["Room", "Type", "Used Slots", "Free Slots", "Total Slots"])
                    remcap_elec_buf = io.BytesIO()
                    with pd.ExcelWriter(remcap_elec_buf, engine="openpyxl") as writerx:
                        df_elec_sum.to_excel(writerx, sheet_name="Summary", index=False)
                    remcap_elec_buf.seek(0)
                    st.session_state["remcap_elec_excel"] = remcap_elec_buf.getvalue()
            if "df_elec" in st.session_state["electives_data"]:
                with st.expander("Electives Timetable", expanded=False):
                    st.table(st.session_state["electives_data"]["df_elec"])
            if "df_elec" in st.session_state["electives_data"]:
                elec_buffer = io.BytesIO()
                with pd.ExcelWriter(elec_buffer, engine="openpyxl") as writer3:
                    st.session_state["electives_data"]["df_elec"].to_excel(writer3, index=False)
                elec_buffer.seek(0)
                st.session_state["elec_excel"] = elec_buffer.getvalue()
                st.download_button(
                    label="Download Electives Timetable Excel",
                    data=st.session_state["elec_excel"],
                    file_name=elec_out_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            if "remcap_elec_excel" in st.session_state:
                st.download_button(
                    label="Download Remaining Capacity (After Electives)",
                    data=st.session_state["remcap_elec_excel"],
                    file_name=remcap_elec_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
