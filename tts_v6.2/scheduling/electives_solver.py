# electives_solver.py
from ortools.sat.python import cp_model

def schedule_electives(
    electives_list,
    usage_data,
    DAYS,
    THEORY_TIMESLOTS,
    LAB_SLOTS,
    theory_rooms,
    lab_rooms,
    timeslot_labels=None,
    lab_slot_labels=None,
    theory_needed=2,
    lab_needed=1
):
    """
    Schedules electives in either:
      - 2 theory slots on distinct, non-consecutive days (if can_theory == True), or
      - 1 lab slot (if can_lab == True).
    We do NOT allow a single elective section to be both theory and lab.
    Now also skipping:
      - slot=3 for theory on ALL days.
      - (Removed the old skip for Friday-lab-slot=1).
    """

    model = cp_model.CpModel()

    used_theory = set()
    for r in usage_data["theory"]:
        for day in usage_data["theory"][r]:
            for ts in usage_data["theory"][r][day]:
                used_theory.add((r, day, ts))

    used_lab = set()
    for r in usage_data["lab"]:
        for day in usage_data["lab"][r]:
            for ts in usage_data["lab"][r][day]:
                used_lab.add((r, day, ts))

    # Build all possible theory combos, excluding timeslot=3 (12:30-1:45) for any day
    theory_combos = []
    for r in theory_rooms:
        for d in DAYS:
            for ts in THEORY_TIMESLOTS:
                # 1) Exclude timeslot=3 entirely
                if d == "Friday" and ts == 3:
                    continue
                # 2) We already skip if it's used
                if (r, d, ts) in used_theory:
                    continue
                theory_combos.append((r, d, ts))

    # Build all possible lab combos (no skip for Friday-lab-slot=1 anymore)
    lab_combos = []
    for r in lab_rooms:
        for d in DAYS:
            for ls in LAB_SLOTS:
                if (r, d, ls) in used_lab:
                    continue
                lab_combos.append((r, d, ls))

    assignments = {}
    choose_theory = {}
    day_assigned = {}

    # For day-gap checking, map days to indices
    day_index_map = { day: idx for idx, day in enumerate(DAYS) }

    for elec in electives_list:
        e_code = elec["code"]
        sec_count = elec["sections_count"]
        can_th = elec["can_theory"]
        can_lb = elec["can_lab"]

        for idx in range(sec_count):
            # If can_theory=1 => choose_theory=1 is allowed
            # If can_lab=1 => choose_theory=0 is allowed
            # If both => solver decides which is feasible.
            choose_var = model.NewBoolVar(f"ChooseTheory_{e_code}_{idx}")
            choose_theory[(e_code, idx)] = choose_var

            if not can_th:
                # must be lab
                model.Add(choose_var == 0)
            if not can_lb:
                # must be theory
                model.Add(choose_var == 1)

            # Distinct-day logic if we do theory
            for d in DAYS:
                day_assigned[(e_code, idx, d)] = model.NewBoolVar(
                    f"DayAsg_{e_code}_{idx}_{d}"
                )

            # Build assignment vars
            # Theory
            for (room, dd, ts) in theory_combos:
                var = model.NewBoolVar(f"T_{e_code}_{idx}_{room}_{dd}_{ts}")
                assignments[(e_code, idx, "theory", room, dd, ts)] = var
                # var <= choose_theory
                model.Add(var <= choose_var)

            # Lab
            for (room, dd, ls) in lab_combos:
                var = model.NewBoolVar(f"L_{e_code}_{idx}_{room}_{dd}_{ls}")
                assignments[(e_code, idx, "lab", room, dd, ls)] = var
                # var <= (1 - choose_theory)
                model.Add(var <= (1 - choose_var))

    # Distinct-day logic if choose_theory=1 => we want theory_needed distinct days
    for elec in electives_list:
        e_code = elec["code"]
        sec_count = elec["sections_count"]
        for idx in range(sec_count):
            model.Add(
                sum(day_assigned[(e_code, idx, d)] for d in DAYS)
                == theory_needed * choose_theory[(e_code, idx)]
            )
            # Link day_assigned to actual theory slots
            for d in DAYS:
                relevant_th = []
                for (room, dd, ts) in theory_combos:
                    if dd == d:
                        relevant_th.append(
                            assignments[(e_code, idx, "theory", room, dd, ts)]
                        )
                model.Add(sum(relevant_th) >= day_assigned[(e_code, idx, d)])
                model.Add(sum(relevant_th) <= len(relevant_th)*day_assigned[(e_code, idx, d)])

            # No consecutive days if it's a theory assignment
            # i.e. day_assigned[d1] + day_assigned[d2] <= 1 for consecutive d1, d2
            # only if we actually chose theory (choose_var=1).
            # We can do: day_assigned[d1] + day_assigned[d2] <= (1 - something) + ??? 
            # Simpler approach: for i in range(len(DAYS)-1) => ...
            # to enforce no consecutive days if chooseTheory=1.
            for i in range(len(DAYS) - 1):
                d1 = DAYS[i]
                d2 = DAYS[i + 1]
                # we only need the constraint to apply if choose_theory=1
                # so: day_assigned(...) + day_assigned(...) <= 1 or choose_theory=0
                # Easiest is: day_assigned(...) + day_assigned(...) <= 2*(1 - chooseVar) + 1*(chooseVar=1 ???)
                # Alternatively, do a big-M. We'll do:
                # day_assigned(d1) + day_assigned(d2) <= 1 + (1 - choose_theory)
                # If choose_theory=1 => left side <= 1 => no consecutive day
                # If choose_theory=0 => left side <= 2 => no real restriction
                model.Add(
                    day_assigned[(e_code, idx, d1)] +
                    day_assigned[(e_code, idx, d2)]
                    <= 1 + (1 - choose_theory[(e_code, idx)])
                )

    # times needed constraints:
    # if choose_theory=1 => exactly 'theory_needed' total theory slots
    # if choose_theory=0 => exactly 'lab_needed' total lab slots
    for elec in electives_list:
        e_code = elec["code"]
        sec_count = elec["sections_count"]
        for idx in range(sec_count):
            all_th_vars = []
            all_lb_vars = []
            for (room, dd, ts) in theory_combos:
                all_th_vars.append(assignments[(e_code, idx, "theory", room, dd, ts)])
            for (room, dd, ls) in lab_combos:
                all_lb_vars.append(assignments[(e_code, idx, "lab", room, dd, ls)])
            model.Add(sum(all_th_vars) == theory_needed * choose_theory[(e_code, idx)])
            model.Add(sum(all_lb_vars) == lab_needed * (1 - choose_theory[(e_code, idx)]))

    # no double-booking same room/time
    for (room, d, ts) in theory_combos:
        model.Add(
            sum(
                assignments[(elec["code"], i, "theory", room, d, ts)]
                for elec in electives_list
                for i in range(elec["sections_count"])
            ) 
            <= 1
        )
    for (room, d, ls) in lab_combos:
        model.Add(
            sum(
                assignments[(elec["code"], i, "lab", room, d, ls)]
                for elec in electives_list
                for i in range(elec["sections_count"])
            ) 
            <= 1
        )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        return None

    # build schedule_map
    schedule_map = {}
    new_allocations = []
    for elec in electives_list:
        e_code = elec["code"]
        sec_count = elec["sections_count"]
        for idx in range(sec_count):
            occupant_label = f"Elective-{e_code}-A{idx+1}"
            assigned_slots = []
            # gather theory
            for (room, d, ts) in theory_combos:
                if solver.Value(assignments[(e_code, idx, "theory", room, d, ts)]) == 1:
                    assigned_slots.append(("theory", room, d, ts))
            # gather lab
            for (room, d, ls) in lab_combos:
                if solver.Value(assignments[(e_code, idx, "lab", room, d, ls)]) == 1:
                    assigned_slots.append(("lab", room, d, ls))
            schedule_map[(e_code, idx)] = assigned_slots
            for (rtype, rname, day, slot) in assigned_slots:
                new_allocations.append((rtype, rname, day, slot, occupant_label))

    return schedule_map, new_allocations
