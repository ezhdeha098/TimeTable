# consistency_check.py
import pandas as pd
from io import BytesIO

def validate_main_excel(excel_bytes, section_size=50):
    """
    Validate the main Excel file for:
      - Required sheets: Roadmap, Rooms, StudentCapacity (Electives is optional)
      - Roadmap: check required headers, unique course codes per semester,
          valid is_lab values (must be "true"/"false") and times_needed is not 3.
      - Rooms: check required headers, non-blank room names, and valid room type ('theory' or 'lab').
      - StudentCapacity: check required headers, semester provided and unique, student_count > 0.
      - Electives (if present): check required headers, can_use_theory and can_use_lab must have opposite values,
          and sections_count > 0.
    Returns a list of error messages (empty if no errors).
    """
    errors = []
    excel_io = BytesIO(excel_bytes)
    try:
        xls = pd.ExcelFile(excel_io)
    except Exception as e:
        errors.append(f"Error reading Excel file: {e}")
        return errors

    # Check required sheets
    required_sheets = ["Roadmap", "Rooms", "StudentCapacity"]
    for sheet in required_sheets:
        if sheet not in xls.sheet_names:
            errors.append(f"Missing required sheet '{sheet}' in main Excel file.")

    if errors:
        return errors

    # ---- Roadmap Sheet Validation ----
    try:
        df_roadmap = pd.read_excel(xls, "Roadmap")
    except Exception as e:
        errors.append(f"Error reading 'Roadmap' sheet: {e}")
        return errors

    expected_headers = ["semester", "course_code", "course_name", "is_lab", "times_needed"]
    df_roadmap.columns = df_roadmap.columns.str.lower().str.strip()
    for header in expected_headers:
        if header not in df_roadmap.columns:
            errors.append(f"Roadmap sheet is missing required header '{header}'.")

    # Unique course code per semester
    if "semester" in df_roadmap.columns and "course_code" in df_roadmap.columns:
        for sem, group in df_roadmap.groupby("semester"):
            if group["course_code"].duplicated().any():
                errors.append(f"Roadmap sheet: Duplicate course codes found in semester {sem}.")

    # Check is_lab values (should be "true" or "false")
    if "is_lab" in df_roadmap.columns:
        for idx, val in df_roadmap["is_lab"].items():
            if str(val).strip().lower() not in ["true", "false"]:
                errors.append(f"Roadmap sheet: Row {idx+2} has invalid 'is_lab' value '{val}'. Expected 'true' or 'false'.")

    # Check that times_needed is never 3
    if "times_needed" in df_roadmap.columns:
        if (df_roadmap["times_needed"] == 3).any():
            errors.append("Roadmap sheet: 'times_needed' cannot be 3.")

    # ---- Rooms Sheet Validation ----
    try:
        df_rooms = pd.read_excel(xls, "Rooms")
    except Exception as e:
        errors.append(f"Error reading 'Rooms' sheet: {e}")
        return errors

    expected_headers_rooms = ["room_name", "room_type"]
    df_rooms.columns = df_rooms.columns.str.lower().str.strip()
    for header in expected_headers_rooms:
        if header not in df_rooms.columns:
            errors.append(f"Rooms sheet is missing required header '{header}'.")

    # Check each row in Rooms sheet
    for idx, row in df_rooms.iterrows():
        room_name = str(row.get("room_name", "")).strip()
        if not room_name:
            errors.append(f"Rooms sheet: Row {idx+2} has blank room name.")
        room_type = str(row.get("room_type", "")).strip().lower()
        if room_type not in ["theory", "lab"]:
            errors.append(f"Rooms sheet: Row {idx+2} has invalid room type '{row.get('room_type')}'. Expected 'theory' or 'lab'.")

    # ---- StudentCapacity Sheet Validation ----
    try:
        df_cap = pd.read_excel(xls, "StudentCapacity")
    except Exception as e:
        errors.append(f"Error reading 'StudentCapacity' sheet: {e}")
        return errors

    expected_headers_cap = ["semester", "student_count"]
    df_cap.columns = df_cap.columns.str.lower().str.strip()
    for header in expected_headers_cap:
        if header not in df_cap.columns:
            errors.append(f"StudentCapacity sheet is missing required header '{header}'.")

    # Check that semester is provided and unique
    if "semester" in df_cap.columns:
        if df_cap["semester"].isnull().any():
            errors.append("StudentCapacity sheet: Some rows are missing 'semester'.")
        if df_cap["semester"].duplicated().any():
            errors.append("StudentCapacity sheet: Duplicate semesters found.")

    # Check student_count is a positive integer (non zero)
    if "student_count" in df_cap.columns:
        for idx, count in df_cap["student_count"].items():
            try:
                count_int = int(count)
                if count_int <= 0:
                    errors.append(f"StudentCapacity sheet: Row {idx+2} has non-positive student_count '{count}'.")
            except:
                errors.append(f"StudentCapacity sheet: Row {idx+2} has invalid student_count '{count}'.")

    # ---- Electives Sheet Validation (if present) ----
    if "Electives" in xls.sheet_names:
        try:
            df_elec = pd.read_excel(xls, "Electives")
        except Exception as e:
            errors.append(f"Error reading 'Electives' sheet: {e}")
            return errors

        expected_headers_elec = ["elective_code", "elective_name", "sections_count", "can_use_theory", "can_use_lab"]
        df_elec.columns = df_elec.columns.str.lower().str.strip()
        for header in expected_headers_elec:
            if header not in df_elec.columns:
                errors.append(f"Electives sheet is missing required header '{header}'.")

        # Check that can_use_theory and can_use_lab have opposite values,
        # and that sections_count is not null/0.
        for idx, row in df_elec.iterrows():
            can_th = str(row.get("can_use_theory", "")).strip().lower()
            can_lb = str(row.get("can_use_lab", "")).strip().lower()
            if can_th not in ["true", "false"] or can_lb not in ["true", "false"]:
                errors.append(f"Electives sheet: Row {idx+2} has invalid boolean values in 'can_use_theory' or 'can_use_lab'.")
            else:
                if can_th == can_lb:
                    errors.append(
                        f"Electives sheet: Row {idx+2} has inconsistent boolean values: "
                        f"can_use_theory is {can_th} and can_use_lab is {can_lb}. They should never both be TRUE or both be FALSE."
                    )
            try:
                sec_count = int(row.get("sections_count", 0))
                if sec_count <= 0:
                    errors.append(f"Electives sheet: Row {idx+2} has invalid 'sections_count' '{sec_count}'. It must be greater than 0.")
            except:
                errors.append(f"Electives sheet: Row {idx+2} has invalid 'sections_count' value '{row.get('sections_count')}'.")

    return errors

def validate_cohort_excel(cohort_bytes, section_size=50):
    """
    Validate the cohort Excel file for:
      - Required headers: CohortSemester, CourseCode, CourseName, Section, Capacity.
      - Capacity must be a positive integer.
      - CohortSemester must be provided.
    Returns a list of error messages.
    """
    errors = []
    excel_io = BytesIO(cohort_bytes)
    try:
        df = pd.read_excel(excel_io)
    except Exception as e:
        errors.append(f"Error reading Cohort Excel file: {e}")
        return errors

    df.columns = df.columns.str.strip()
    required_headers = ["CohortSemester", "CourseCode", "CourseName", "Section", "Capacity"]
    for header in required_headers:
        if header not in df.columns:
            errors.append(f"Cohort Excel is missing required header '{header}'.")

    # Check Capacity is a positive integer
    if "Capacity" in df.columns:
        for idx, cap in df["Capacity"].items():
            try:
                cap_int = int(cap)
                if cap_int <= 0:
                    errors.append(f"Cohort Excel: Row {idx+2} has non-positive Capacity '{cap}'.")
            except:
                errors.append(f"Cohort Excel: Row {idx+2} has invalid Capacity '{cap}'.")

    # Check that CohortSemester is provided
    if "CohortSemester" in df.columns:
        if df["CohortSemester"].isnull().any():
            errors.append("Cohort Excel: Some rows are missing 'CohortSemester'.")

    return errors
