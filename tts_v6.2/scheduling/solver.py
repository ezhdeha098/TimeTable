from ortools.sat.python import cp_model
from .utils import build_sections_for_semester

def schedule_timetable(
    selected_semesters,
    semester_courses_map,
    section_sizes,
    usage_data,
    DAYS,
    THEORY_TIMESLOTS,
    TIMESLOT_LABELS,
    LAB_SLOTS,
    LAB_SLOT_LABELS,
    LAB_OVERLAP_MAP,   # e.g. {0:[0,1], 1:[2,3], 2:[4,5], 3:[6]}
    theory_rooms,
    lab_rooms,
    special_lab_rooms,
    section_size=50,
    program_code="A",
    cohort_map=None,
    enable_cohort=False,
    constraints=None,
):
    """
    Returns (schedule_map, semester_sections_map, new_allocations) or None if infeasible.

    schedule_map is a dict: 
        (day, slot, room) => (sectionName, courseCode, cohortSectionOrNone)

    Key constraints:
      - No overlapping or partial-overlapping classes for the same section on the same day.
      - No consecutive-day scheduling for the same (section, course) if it’s a theory class.
      - Skips theory slot=3 only on Friday.
      - Optional cohort-based constraints (if enable_cohort + cohort_map).
      - Optional runtime constraints via `constraints` dict (backward compatible):
          * maxHoursPerDay (hours, int)
          * workingDaysPerWeek (int)
          * minGapMinutes (int)
          * noClassesAfterHour (0-23, int)
    """

    # Backward-compatible defaults for optional constraints
    constraints = constraints or {}
    max_hours_per_day = int(constraints.get("maxHoursPerDay", 8))
    working_days_per_week = int(constraints.get("workingDaysPerWeek", 6))
    min_gap_minutes = int(constraints.get("minGapMinutes", 15))
    no_classes_after_hour = constraints.get("noClassesAfterHour", None)
    try:
        no_classes_after_hour = (
            None if no_classes_after_hour is None else int(no_classes_after_hour)
        )
    except Exception:
        no_classes_after_hour = None

    # 1) Map lab-slot -> overlapping theory-slots, and vice versa
    theory_to_lab_map = {}
    for ls in LAB_SLOTS:
        overlap_th = LAB_OVERLAP_MAP.get(ls, [])
        for t in overlap_th:
            theory_to_lab_map.setdefault(t, []).append(ls)

    # 2) Distinguish normal labs vs. special labs
    all_special_labs = set()
    for slist in special_lab_rooms.values():
        for lab_name in slist:
            all_special_labs.add(lab_name.strip())

    lab_rooms = [lr.strip() for lr in lab_rooms]
    normal_labs = [lr for lr in lab_rooms if lr not in all_special_labs]
    combined_labs = list(set(normal_labs) | all_special_labs)

    # 3) Basic usage checks (theory/lab needed vs. available)
    theory_used = 0
    for r in usage_data["theory"]:
        for d in usage_data["theory"][r]:
            theory_used += len(usage_data["theory"][r][d])

    lab_used = 0
    for r in usage_data["lab"]:
        for d in usage_data["lab"][r]:
            lab_used += len(usage_data["lab"][r][d])

    total_theory_capacity = len(DAYS) * len(THEORY_TIMESLOTS) * len(theory_rooms)
    total_lab_capacity = len(DAYS) * len(LAB_SLOTS) * len(combined_labs)
    available_theory = total_theory_capacity - theory_used
    available_lab = total_lab_capacity - lab_used

    needed_theory = 0
    needed_lab = 0
    for sem in selected_semesters:
        for (code, cname, is_lab, times_needed, *maybe_ch) in semester_courses_map[sem]:
            if is_lab:
                needed_lab += times_needed
            else:
                needed_theory += times_needed

    if needed_theory > available_theory:
        raise ValueError(
            f"Not enough free THEORY slots. Need={needed_theory}, Have={available_theory}."
        )
    if needed_lab > available_lab:
        raise ValueError(
            f"Not enough free LAB slots. Need={needed_lab}, Have={available_lab}."
        )

    # 4) Build sections for each selected semester
    semester_sections_map2 = {}
    all_sections = []
    for sem in selected_semesters:
        n_students = section_sizes[sem]
        secs = build_sections_for_semester(sem, n_students, section_size, program_code)
        semester_sections_map2[sem] = secs
        all_sections.extend(secs)

    model = cp_model.CpModel()

    # Identify which (sem, code) are cohort
    is_cohort_course = {}
    if enable_cohort and cohort_map:
        for (coh_sem, coh_code) in cohort_map.keys():
            is_cohort_course.setdefault(coh_sem, set()).add(coh_code)

    # 5) Create boolean variables for cohort assignment
    assigned_cohort_sec = {}
    if enable_cohort and cohort_map:
        for sem in selected_semesters:
            for (code, cname, is_lab, times_needed, *rest) in semester_courses_map[sem]:
                if code in is_cohort_course.get(sem, []):
                    csections = cohort_map.get((sem, code), [])
                    for normal_sec in semester_sections_map2[sem]:
                        for csec_data in csections:
                            csec_name = csec_data["cohort_section"]
                            vkey = (normal_sec, code, csec_name)
                            assigned_cohort_sec[vkey] = model.NewBoolVar(
                                f"CohortAssign_{normal_sec}_{code}_{csec_name}"
                            )

    # 6) Normal assignment variables
    assignments = {}
    day_assigned = {}
    for sem in selected_semesters:
        for sec in semester_sections_map2[sem]:
            for (code, cname, is_lab, times_needed, *rest) in semester_courses_map[sem]:
                # Skip normal var creation if it's a cohort course
                if enable_cohort and code in is_cohort_course.get(sem, []):
                    continue

                if not is_lab:
                    # Theory
                    for d in DAYS:
                        day_assigned[(sec, code, d)] = model.NewBoolVar(
                            f"day_{sec}_{code}_{d}"
                        )
                    for d in DAYS:
                        for t in THEORY_TIMESLOTS:
                            if d == "Friday" and t == 3:
                                continue
                            for r in theory_rooms:
                                used_slots = usage_data["theory"].get(r, {}).get(d, [])
                                if t in used_slots:
                                    continue
                                key = (sec, code, d, t, r)
                                assignments[key] = model.NewBoolVar(
                                    f"Theory_{sec}_{code}_{d}_{t}_{r}"
                                )
                else:
                    # Lab
                    if code in special_lab_rooms:
                        valid_labs = [x.strip() for x in special_lab_rooms[code]]
                    else:
                        valid_labs = normal_labs
                    for d in DAYS:
                        for ls in LAB_SLOTS:
                            for labr in valid_labs:
                                used_slots = usage_data["lab"].get(labr, {}).get(d, [])
                                if ls in used_slots:
                                    continue
                                key = (sec, code, d, ls, labr)
                                assignments[key] = model.NewBoolVar(
                                    f"Lab_{sec}_{code}_{d}_{ls}_{labr}"
                                )

    # 7) Times-needed constraints for non-cohort
    for sem in selected_semesters:
        for sec in semester_sections_map2[sem]:
            for (code, cname, is_lab, times_needed, *rest) in semester_courses_map[sem]:
                if enable_cohort and code in is_cohort_course.get(sem, []):
                    continue

                if is_lab:
                    if code in special_lab_rooms:
                        labs_ = [x.strip() for x in special_lab_rooms[code]]
                    else:
                        labs_ = normal_labs
                    lab_vars = []
                    for d in DAYS:
                        for ls in LAB_SLOTS:
                            for lbr in labs_:
                                v = assignments.get((sec, code, d, ls, lbr), None)
                                if v is not None:
                                    lab_vars.append(v)
                    model.Add(sum(lab_vars) == times_needed)
                else:
                    th_vars = []
                    for d in DAYS:
                        for t in THEORY_TIMESLOTS:
                            if d == "Friday" and t == 3:
                                continue
                            for r in theory_rooms:
                                v = assignments.get((sec, code, d, t, r), None)
                                if v is not None:
                                    th_vars.append(v)
                    model.Add(sum(th_vars) == times_needed)

                    # Distinct-day logic for that theory course
                    model.Add(
                        sum(day_assigned[(sec, code, d)] for d in DAYS) == times_needed
                    )
                    for d in DAYS:
                        relevant_vars = []
                        for t in THEORY_TIMESLOTS:
                            if d == "Friday" and t == 3:
                                continue
                            for r in theory_rooms:
                                av = assignments.get((sec, code, d, t, r), None)
                                if av is not None:
                                    relevant_vars.append(av)
                        model.Add(sum(relevant_vars) >= day_assigned[(sec, code, d)])
                        model.Add(
                            sum(relevant_vars)
                            <= len(THEORY_TIMESLOTS) * day_assigned[(sec, code, d)]
                        )

                    # No consecutive-day scheduling for theory courses
                    if times_needed > 1:
                        for i in range(len(DAYS) - 1):
                            d1 = DAYS[i]
                            d2 = DAYS[i + 1]
                            model.Add(
                                day_assigned[(sec, code, d1)]
                                + day_assigned[(sec, code, d2)]
                                <= 1
                            )

    # 8) No double-booking of rooms
    for d in DAYS:
        for t in THEORY_TIMESLOTS:
            if d == "Friday" and t == 3:
                continue
            for r in theory_rooms:
                model.Add(
                    sum(
                        assignments.get((sec, c, d, t, r), 0)
                        for sem2 in selected_semesters
                        for sec in semester_sections_map2[sem2]
                        for (c, cname, lb, timesN, *rx) in semester_courses_map[sem2]
                        if not lb and (not enable_cohort or c not in is_cohort_course.get(sem2, []))
                    )
                    <= 1
                )

    for d in DAYS:
        for ls in LAB_SLOTS:
            for labr in combined_labs:
                model.Add(
                    sum(
                        assignments.get((sec, c, d, ls, labr), 0)
                        for sem2 in selected_semesters
                        for sec in semester_sections_map2[sem2]
                        for (c, cname, lb, timesN, *rx) in semester_courses_map[sem2]
                        if lb and (not enable_cohort or c not in is_cohort_course.get(sem2, []))
                    )
                    <= 1
                )

    # 9) No double-booking or partial overlap within a section
    for sec in all_sections:
        for d in DAYS:
            for t in THEORY_TIMESLOTS:
                if d == "Friday" and t == 3:
                    continue
                model.Add(
                    sum(
                        assignments.get((sec, c, d, t, r), 0)
                        for sem2 in selected_semesters
                        for (c, cname, lb, timesN, *rx) in semester_courses_map[sem2]
                        if not lb and (not enable_cohort or c not in is_cohort_course.get(sem2, []))
                        for r in theory_rooms
                    )
                    <= 1
                )
            for ls in LAB_SLOTS:
                model.Add(
                    sum(
                        assignments.get((sec, c, d, ls, labr), 0)
                        for sem2 in selected_semesters
                        for (c, cname, lb, timesN, *rx) in semester_courses_map[sem2]
                        if lb and (not enable_cohort or c not in is_cohort_course.get(sem2, []))
                        for labr in combined_labs
                    )
                    <= 1
                )

        for d in DAYS:
            for sem2 in selected_semesters:
                for (c, cname, lbFlag, tNeeded, *rx) in semester_courses_map[sem2]:
                    if not lbFlag or (enable_cohort and c in is_cohort_course.get(sem2, [])):
                        continue
                    if c in special_lab_rooms:
                        lab_candidates = [x.strip() for x in special_lab_rooms[c]]
                    else:
                        lab_candidates = normal_labs
                    for ls in LAB_SLOTS:
                        overlap_list = LAB_OVERLAP_MAP.get(ls, [])
                        for labr in lab_candidates:
                            lab_var = assignments.get((sec, c, d, ls, labr), None)
                            if lab_var is None:
                                continue
                            for sem3 in selected_semesters:
                                for (c2, cname2, lb2, tN2, *xx) in semester_courses_map[sem3]:
                                    if lb2 or (enable_cohort and c2 in is_cohort_course.get(sem3, [])):
                                        continue
                                    for t2 in overlap_list:
                                        if d == "Friday" and t2 == 3:
                                            continue
                                        for rr2 in theory_rooms:
                                            tv = assignments.get((sec, c2, d, t2, rr2), None)
                                            if tv is not None:
                                                model.Add(lab_var + tv <= 1)

    # 10) Cohort logic
    if enable_cohort and cohort_map:
        # (A) Exactly one cohort section per normal section
        for sem in selected_semesters:
            for (code, cname, is_lab, timesN, *rx) in semester_courses_map[sem]:
                if code not in is_cohort_course.get(sem, []):
                    continue
                csections = cohort_map.get((sem, code), [])
                for normal_sec in semester_sections_map2[sem]:
                    var_list = [
                        assigned_cohort_sec[(normal_sec, code, csec_data["cohort_section"])]
                        for csec_data in csections
                        if (normal_sec, code, csec_data["cohort_section"]) in assigned_cohort_sec
                    ]
                    model.Add(sum(var_list) == 1)

        # (B) Capacity constraints
        for (csem, ccode) in cohort_map.keys():
            if csem not in selected_semesters:
                continue
            for csec_data in cohort_map[(csem, ccode)]:
                csec_name = csec_data["cohort_section"]
                ccap = csec_data["capacity"]
                usage_expr = [
                    assigned_cohort_sec[(normal_sec, ccode, csec_name)] * 50
                    for normal_sec in semester_sections_map2[csem]
                    if (normal_sec, ccode, csec_name) in assigned_cohort_sec
                ]
                model.Add(sum(usage_expr) <= ccap)

        # (C) Block overlapping times for normal sections
        for sem in selected_semesters:
            for (code, cname, is_lab, timesN, *rx) in semester_courses_map[sem]:
                if code not in is_cohort_course.get(sem, []):
                    continue
                csections = cohort_map.get((sem, code), [])
                for csec_data in csections:
                    csec_name = csec_data["cohort_section"]
                    day_time_list = csec_data["day_time_list"]
                    for normal_sec in semester_sections_map2[sem]:
                        vkey = (normal_sec, code, csec_name)
                        if vkey not in assigned_cohort_sec:
                            continue
                        var_cohort = assigned_cohort_sec[vkey]
                        for (the_day, the_slot) in day_time_list:
                            if the_day == "Friday" and the_slot == 3:
                                continue
                            for semX in selected_semesters:
                                for (c2, cname2, lb2, tN2, *xx) in semester_courses_map[semX]:
                                    if c2 == code or (enable_cohort and c2 in is_cohort_course.get(semX, [])):
                                        continue
                                    if not lb2:
                                        if the_day == "Friday" and the_slot == 3:
                                            continue
                                        for r2 in theory_rooms:
                                            tv = assignments.get((normal_sec, c2, the_day, the_slot, r2), None)
                                            if tv is not None:
                                                model.Add(var_cohort + tv <= 1)
                                    else:
                                        labs2 = normal_labs if c2 not in special_lab_rooms else [x.strip() for x in special_lab_rooms[c2]]
                                        for lbX in labs2:
                                            lv = assignments.get((normal_sec, c2, the_day, the_slot, lbX), None)
                                            if lv is not None:
                                                model.Add(var_cohort + lv <= 1)

                            if the_slot in LAB_SLOTS:
                                overlap_th = LAB_OVERLAP_MAP.get(the_slot, [])
                                for t2 in overlap_th:
                                    if the_day == "Friday" and t2 == 3:
                                        continue
                                    for semX in selected_semesters:
                                        for (c2, cname2, lb2, tN2, *xx) in semester_courses_map[semX]:
                                            if c2 == code or (enable_cohort and c2 in is_cohort_course.get(semX, [])):
                                                continue
                                            if not lb2:
                                                for rr2 in theory_rooms:
                                                    tv2 = assignments.get((normal_sec, c2, the_day, t2, rr2), None)
                                                    if tv2 is not None:
                                                        model.Add(var_cohort + tv2 <= 1)

                            if the_slot in THEORY_TIMESLOTS:
                                if the_day == "Friday" and the_slot == 3:
                                    continue
                                over_labs = theory_to_lab_map.get(the_slot, [])
                                for ls2 in over_labs:
                                    for semX in selected_semesters:
                                        for (c2, cname2, lb2, tN2, *xx) in semester_courses_map[semX]:
                                            if c2 == code or (enable_cohort and c2 in is_cohort_course.get(semX, [])):
                                                continue
                                            if lb2:
                                                labs2 = normal_labs if c2 not in special_lab_rooms else [x.strip() for x in special_lab_rooms[c2]]
                                                for lbX in labs2:
                                                    lv2 = assignments.get((normal_sec, c2, the_day, ls2, lbX), None)
                                                    if lv2 is not None:
                                                        model.Add(var_cohort + lv2 <= 1)

        # (D) Prevent overlapping cohort courses
        def slots_overlap(day1, slot1, is_lab1, day2, slot2, is_lab2, LAB_OVERLAP_MAP):
            if day1 != day2:
                return False
            if not is_lab1 and not is_lab2:
                return slot1 == slot2
            elif is_lab1 and is_lab2:
                return slot1 == slot2
            elif not is_lab1 and is_lab2:
                overlapping_theory = LAB_OVERLAP_MAP.get(slot2, [])
                return slot1 in overlapping_theory
            elif is_lab1 and not is_lab2:
                overlapping_theory = LAB_OVERLAP_MAP.get(slot1, [])
                return slot2 in overlapping_theory
            return False

        course_is_lab = {(sem, code): is_lab for sem in selected_semesters for (code, cname, is_lab, timesN, ch) in semester_courses_map[sem]}
        for sem in selected_semesters:
            cohort_courses = [
                (code, cname, is_lab, timesN, ch)
                for (code, cname, is_lab, timesN, ch) in semester_courses_map[sem]
                if (sem, code) in cohort_map
            ]
            for i in range(len(cohort_courses)):
                for j in range(i + 1, len(cohort_courses)):
                    code1, code2 = cohort_courses[i][0], cohort_courses[j][0]
                    is_lab1, is_lab2 = course_is_lab[(sem, code1)], course_is_lab[(sem, code2)]
                    for csec1 in cohort_map[(sem, code1)]:
                        for csec2 in cohort_map[(sem, code2)]:
                            overlap = any(
                                slots_overlap(d1, s1, is_lab1, d2, s2, is_lab2, LAB_OVERLAP_MAP)
                                for (d1, s1) in csec1["day_time_list"]
                                for (d2, s2) in csec2["day_time_list"]
                            )
                            if overlap:
                                for normal_sec in semester_sections_map2[sem]:
                                    v1 = assigned_cohort_sec.get((normal_sec, code1, csec1["cohort_section"]), None)
                                    v2 = assigned_cohort_sec.get((normal_sec, code2, csec2["cohort_section"]), None)
                                    if v1 is not None and v2 is not None:
                                        model.Add(v1 + v2 <= 1)

    # 11) At most 5 days used per section
    day_in_use = {}
    BIG_M = 999
    for sec in all_sections:
        for d in DAYS:
            day_in_use[(sec, d)] = model.NewBoolVar(f"day_in_use_{sec}_{d}")

    for sem in selected_semesters:
        for sec in semester_sections_map2[sem]:
            for d in DAYS:
                normal_vars = []
                for (c, cname, lb, tNeeded, *xx) in semester_courses_map[sem]:
                    if enable_cohort and c in is_cohort_course.get(sem, []):
                        continue
                    if not lb:
                        for t in THEORY_TIMESLOTS:
                            if d == "Friday" and t == 3:
                                continue
                            for r in theory_rooms:
                                av = assignments.get((sec, c, d, t, r))
                                if av is not None:
                                    normal_vars.append(av)
                    else:
                        labs_ = normal_labs if c not in special_lab_rooms else [x.strip() for x in special_lab_rooms[c]]
                        for ls in LAB_SLOTS:
                            for lbR in labs_:
                                av = assignments.get((sec, c, d, ls, lbR))
                                if av is not None:
                                    normal_vars.append(av)
                model.Add(sum(normal_vars) >= day_in_use[(sec, d)])
                model.Add(sum(normal_vars) <= BIG_M * day_in_use[(sec, d)])

    if enable_cohort and cohort_map:
        for sem in selected_semesters:
            for sec in semester_sections_map2[sem]:
                for (code, cname, lb, tNeeded, *xx) in semester_courses_map[sem]:
                    if code not in is_cohort_course.get(sem, []):
                        continue
                    csections = cohort_map.get((sem, code), [])
                    for csec_data in csections:
                        csec_name = csec_data["cohort_section"]
                        vkey = (sec, code, csec_name)
                        if vkey not in assigned_cohort_sec:
                            continue
                        var_cohort = assigned_cohort_sec[vkey]
                        for (the_day, the_slot) in csec_data["day_time_list"]:
                            if the_day == "Friday" and the_slot == 3:
                                continue
                            model.Add(var_cohort <= day_in_use[(sec, the_day)])

    for sec in all_sections:
        model.Add(sum(day_in_use[(sec, d)] for d in DAYS) <= working_days_per_week)

    # 12) New constraint: Time span from earliest start to latest end <= 8 hours
    theory_start_times = {
        0: 480,  # 8:00
        1: 570,  # 9:30
        2: 660,  # 11:00
        3: 750,  # 12:30
        4: 840,  # 14:00
        5: 930,  # 15:30
        6: 1020  # 17:00
    }
    theory_end_times = {
        0: 555,  # 9:15
        1: 645,  # 10:45
        2: 735,  # 12:15
        3: 825,  # 13:45
        4: 915,  # 15:15
        5: 1005, # 16:45
        6: 1095  # 18:15
    }
    lab_start_times = {
        0: 480,  # 8:00
        1: 660,  # 11:00
        2: 840,  # 14:00
        3: 1020  # 17:00
    }
    lab_end_times = {
        0: 630,  # 10:30
        1: 810,  # 13:30
        2: 990,  # 16:30
        3: 1170  # 19:30
    }
    BIG_M = 1440  # Minutes in a day
    allowed_span_minutes = max(0, int(max_hours_per_day * 60))

    # Disallow classes after a given hour, if requested
    if no_classes_after_hour is not None:
        cutoff_end_minute = no_classes_after_hour * 60
        # Disable any normal assignment variable that would end after the cutoff
        for key, var in list(assignments.items()):
            # key shapes: (sec, code, d, t_or_ls, room)
            slot = key[3]
            if slot in THEORY_TIMESLOTS:
                if theory_end_times.get(slot, 0) > cutoff_end_minute:
                    model.Add(var == 0)
            elif slot in LAB_SLOTS:
                if lab_end_times.get(slot, 0) > cutoff_end_minute:
                    model.Add(var == 0)
        # Also disable any cohort option whose fixed time extends past cutoff
        if enable_cohort and cohort_map:
            for sem in selected_semesters:
                for (code, cname, is_lab, timesN, *rx) in semester_courses_map[sem]:
                    if code not in is_cohort_course.get(sem, []):
                        continue
                    csections = cohort_map.get((sem, code), [])
                    for csec_data in csections:
                        csec_name = csec_data.get("cohort_section")
                        violates = False
                        for (the_day, the_slot) in csec_data.get("day_time_list", []):
                            if the_slot in THEORY_TIMESLOTS:
                                if theory_end_times.get(the_slot, 0) > cutoff_end_minute:
                                    violates = True
                                    break
                            elif the_slot in LAB_SLOTS:
                                if lab_end_times.get(the_slot, 0) > cutoff_end_minute:
                                    violates = True
                                    break
                        if violates:
                            for normal_sec in semester_sections_map2[sem]:
                                vkey = (normal_sec, code, csec_name)
                                if vkey in assigned_cohort_sec:
                                    model.Add(assigned_cohort_sec[vkey] == 0)

    # Define slot usage for normal assignments
    has_normal_theory = {}
    has_normal_lab = {}
    for sec in all_sections:
        for d in DAYS:
            for t in THEORY_TIMESLOTS:
                if d == "Friday" and t == 3:
                    continue
                has_normal_theory[(sec, d, t)] = model.NewBoolVar(f'has_normal_theory_{sec}_{d}_{t}')
                relevant_assignments = [
                    assignments.get((sec, c, d, t, r), None)
                    for sem2 in selected_semesters
                    for (c, cname, lb, timesN, *rx) in semester_courses_map[sem2]
                    if not lb and (not enable_cohort or c not in is_cohort_course.get(sem2, []))
                    for r in theory_rooms
                    if assignments.get((sec, c, d, t, r), None) is not None
                ]
                if relevant_assignments:
                    model.Add(has_normal_theory[(sec, d, t)] == sum(relevant_assignments))
                else:
                    model.Add(has_normal_theory[(sec, d, t)] == 0)
            for ls in LAB_SLOTS:
                has_normal_lab[(sec, d, ls)] = model.NewBoolVar(f'has_normal_lab_{sec}_{d}_{ls}')
                relevant_lab_assignments = [
                    assignments.get((sec, c, d, ls, labr), None)
                    for sem2 in selected_semesters
                    for (c, cname, lb, timesN, *rx) in semester_courses_map[sem2]
                    if lb and (not enable_cohort or c not in is_cohort_course.get(sem2, []))
                    for labr in combined_labs
                    if assignments.get((sec, c, d, ls, labr), None) is not None
                ]
                if relevant_lab_assignments:
                    model.Add(has_normal_lab[(sec, d, ls)] == sum(relevant_lab_assignments))
                else:
                    model.Add(has_normal_lab[(sec, d, ls)] == 0)

    # Define slot usage for cohort assignments
    if enable_cohort and cohort_map:
        has_cohort_theory = {}
        has_cohort_lab = {}
        for sec in all_sections:
            for d in DAYS:
                for t in THEORY_TIMESLOTS:
                    if d == "Friday" and t == 3:
                        continue
                    has_cohort_theory[(sec, d, t)] = model.NewIntVar(0, 1, f'has_cohort_theory_{sec}_{d}_{t}')
                    cohort_sum = 0
                    for sem in selected_semesters:
                        for (code, cname, is_lab, timesN, *rx) in semester_courses_map[sem]:
                            if not is_lab and code in is_cohort_course.get(sem, []):
                                for csec_data in cohort_map.get((sem, code), []):
                                    if (d, t) in csec_data["day_time_list"]:
                                        vkey = (sec, code, csec_data["cohort_section"])
                                        if vkey in assigned_cohort_sec:
                                            cohort_sum += assigned_cohort_sec[vkey]
                    model.Add(has_cohort_theory[(sec, d, t)] == cohort_sum)
                for ls in LAB_SLOTS:
                    has_cohort_lab[(sec, d, ls)] = model.NewIntVar(0, 1, f'has_cohort_lab_{sec}_{d}_{ls}')
                    cohort_sum = 0
                    for sem in selected_semesters:
                        for (code, cname, is_lab, timesN, *rx) in semester_courses_map[sem]:
                            if is_lab and code in is_cohort_course.get(sem, []):
                                for csec_data in cohort_map.get((sem, code), []):
                                    if (d, ls) in csec_data["day_time_list"]:
                                        vkey = (sec, code, csec_data["cohort_section"])
                                        if vkey in assigned_cohort_sec:
                                            cohort_sum += assigned_cohort_sec[vkey]
                    model.Add(has_cohort_lab[(sec, d, ls)] == cohort_sum)

    # Combine normal and cohort slot usage
    has_theory = {}
    has_lab = {}
    for sec in all_sections:
        for d in DAYS:
            for t in THEORY_TIMESLOTS:
                if d == "Friday" and t == 3:
                    continue
                if enable_cohort and cohort_map:
                    has_theory[(sec, d, t)] = model.NewIntVar(0, 2, f'has_theory_{sec}_{d}_{t}')
                    model.Add(has_theory[(sec, d, t)] == has_normal_theory[(sec, d, t)] + has_cohort_theory[(sec, d, t)])
                else:
                    has_theory[(sec, d, t)] = model.NewBoolVar(f'has_theory_{sec}_{d}_{t}')
                    model.Add(has_theory[(sec, d, t)] == has_normal_theory[(sec, d, t)])
            for ls in LAB_SLOTS:
                if enable_cohort and cohort_map:
                    has_lab[(sec, d, ls)] = model.NewIntVar(0, 2, f'has_lab_{sec}_{d}_{ls}')
                    model.Add(has_lab[(sec, d, ls)] == has_normal_lab[(sec, d, ls)] + has_cohort_lab[(sec, d, ls)])
                else:
                    has_lab[(sec, d, ls)] = model.NewBoolVar(f'has_lab_{sec}_{d}_{ls}')
                    model.Add(has_lab[(sec, d, ls)] == has_normal_lab[(sec, d, ls)])

    # Enforce minimum gap between classes on the same day, if requested
    if min_gap_minutes and min_gap_minutes > 0:
        for sec in all_sections:
            for d in DAYS:
                # theory-theory pairs
                for i, t1 in enumerate(THEORY_TIMESLOTS):
                    if d == "Friday" and t1 == 3:
                        continue
                    for t2 in THEORY_TIMESLOTS[i+1:]:
                        if d == "Friday" and t2 == 3:
                            continue
                        gap = theory_start_times[t2] - theory_end_times[t1]
                        if gap < min_gap_minutes:
                            model.Add(has_theory[(sec, d, t1)] + has_theory[(sec, d, t2)] <= 1)

                # lab-lab pairs
                for i, ls1 in enumerate(LAB_SLOTS):
                    for ls2 in LAB_SLOTS[i+1:]:
                        gap = lab_start_times[ls2] - lab_end_times[ls1]
                        if gap < min_gap_minutes:
                            model.Add(has_lab[(sec, d, ls1)] + has_lab[(sec, d, ls2)] <= 1)

                # theory-lab pairs (both orders)
                for t in THEORY_TIMESLOTS:
                    if d == "Friday" and t == 3:
                        continue
                    for ls in LAB_SLOTS:
                        # theory then lab
                        gap1 = lab_start_times[ls] - theory_end_times[t]
                        if gap1 < min_gap_minutes:
                            model.Add(has_theory[(sec, d, t)] + has_lab[(sec, d, ls)] <= 1)
                        # lab then theory
                        gap2 = theory_start_times[t] - lab_end_times[ls]
                        if gap2 < min_gap_minutes:
                            model.Add(has_theory[(sec, d, t)] + has_lab[(sec, d, ls)] <= 1)

    # Enforce daily time-span constraint (parametrized)
    for sec in all_sections:
        for d in DAYS:
            min_start = model.NewIntVar(0, BIG_M, f'min_start_{sec}_{d}')
            max_end = model.NewIntVar(0, BIG_M, f'max_end_{sec}_{d}')

            theory_start_vars = []
            theory_end_vars = []
            for t in THEORY_TIMESLOTS:
                if d == "Friday" and t == 3:
                    continue
                start_var = model.NewIntVar(0, BIG_M, f'theory_start_var_{sec}_{d}_{t}')
                end_var = model.NewIntVar(0, BIG_M, f'theory_end_var_{sec}_{d}_{t}')
                model.Add(start_var == theory_start_times[t]).OnlyEnforceIf(has_theory[(sec, d, t)])
                model.Add(start_var == BIG_M).OnlyEnforceIf(has_theory[(sec, d, t)].Not())
                model.Add(end_var == theory_end_times[t]).OnlyEnforceIf(has_theory[(sec, d, t)])
                model.Add(end_var == 0).OnlyEnforceIf(has_theory[(sec, d, t)].Not())
                theory_start_vars.append(start_var)
                theory_end_vars.append(end_var)

            lab_start_vars = []
            lab_end_vars = []
            for ls in LAB_SLOTS:
                start_var = model.NewIntVar(0, BIG_M, f'lab_start_var_{sec}_{d}_{ls}')
                end_var = model.NewIntVar(0, BIG_M, f'lab_end_var_{sec}_{d}_{ls}')
                model.Add(start_var == lab_start_times[ls]).OnlyEnforceIf(has_lab[(sec, d, ls)])
                model.Add(start_var == BIG_M).OnlyEnforceIf(has_lab[(sec, d, ls)].Not())
                model.Add(end_var == lab_end_times[ls]).OnlyEnforceIf(has_lab[(sec, d, ls)])
                model.Add(end_var == 0).OnlyEnforceIf(has_lab[(sec, d, ls)].Not())
                lab_start_vars.append(start_var)
                lab_end_vars.append(end_var)
            model.AddMinEquality(min_start, theory_start_vars + lab_start_vars)
            model.AddMaxEquality(max_end, theory_end_vars + lab_end_vars)
            model.Add(max_end - min_start <= allowed_span_minutes)

    # 13) Solve with tuning parameters
    solver = cp_model.CpSolver()
    
    # Apply solver tuning parameters if provided in constraints
    solver_params = constraints.get('solver_params', {})
    
    if 'max_time_in_seconds' in solver_params:
        solver.parameters.max_time_in_seconds = float(solver_params['max_time_in_seconds'])
    
    if 'num_search_workers' in solver_params:
        solver.parameters.num_search_workers = int(solver_params['num_search_workers'])
    
    if solver_params.get('log_search_progress', False):
        solver.parameters.log_search_progress = True
    
    # Enable better search strategies for large problems
    if solver_params.get('use_fixed_search', False):
        solver.parameters.search_branching = cp_model.FIXED_SEARCH
    
    status = solver.Solve(model)
    
    if status not in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        return None

    # 14) Build schedule_map and new_allocations
    schedule_map = {}
    new_allocations = []

    for sem in selected_semesters:                
        for sec in semester_sections_map2[sem]:
            for (code, cname, lb, timesN, *rx) in semester_courses_map[sem]:
                if enable_cohort and code in is_cohort_course.get(sem, []):
                    continue
                occupant_label = f"{sec}-{code}"
                if not lb:
                    for d in DAYS:
                        for t in THEORY_TIMESLOTS:
                            if d == "Friday" and t == 3:
                                continue
                            for r in theory_rooms:
                                var = assignments.get((sec, code, d, t, r))
                                if var is not None and solver.Value(var) == 1:
                                    schedule_map[(d, t, r)] = (sec, code, None)
                                    new_allocations.append(("theory", r, d, t, occupant_label))
                else:
                    labs_ = normal_labs if code not in special_lab_rooms else [x.strip() for x in special_lab_rooms[code]]
                    for d in DAYS:
                        for s in LAB_SLOTS:
                            for lbR in labs_:
                                var = assignments.get((sec, code, d, s, lbR))
                                if var is not None and solver.Value(var) == 1:
                                    schedule_map[(d, s, lbR)] = (sec, code, None)
                                    new_allocations.append(("lab", lbR, d, s, occupant_label))

    if enable_cohort and cohort_map:
        for sem in selected_semesters:
            for (code, cname, lb, timesN, *rest) in semester_courses_map[sem]:
                if code not in is_cohort_course.get(sem, []):
                    continue
                possible_csections = cohort_map.get((sem, code), [])
                for sec in semester_sections_map2[sem]:
                    occupant_label = f"{sec}-{code}"
                    chosen_data = None
                    for csec_data in possible_csections:
                        csec_name = csec_data["cohort_section"]
                        vkey = (sec, code, csec_name)
                        if vkey in assigned_cohort_sec and solver.Value(assigned_cohort_sec[vkey]) == 1:
                            chosen_data = csec_data
                            break
                    if chosen_data:
                        csec_name = chosen_data["cohort_section"]
                        actual_room = chosen_data.get("cohort_room", f"CohortRoom({code}-{csec_name})")
                        for (the_day, the_slot) in chosen_data["day_time_list"]:
                            if the_day == "Friday" and the_slot == 3:
                                continue
                            schedule_map[(the_day, the_slot, actual_room)] = (sec, code, csec_name)
                            new_allocations.append(("cohort", actual_room, the_day, the_slot, occupant_label))

    return schedule_map, semester_sections_map2, new_allocations