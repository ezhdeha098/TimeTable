## ⚠️ MANUAL FIX REQUIRED

The file `solver.py` needs a manual fix due to corruption during automated editing.

### Problem
Lines 705-754 jump directly from model building to result extraction, **skipping the solver initialization and execution**.

### Fix Location
Between line 704 and line 705 in `solver.py`

**Line 704:** `lab_end_vars.append(end_var)`  
**Line 705:** `for sec in semester_sections_map2[sem]:`  

### Code to Insert

Copy and paste the following code **between lines 704 and 705**:

```python
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
```

### How to Apply

1. **Open** `tts_v6.2/scheduling/solver.py` in your code editor
2. **Find** line 704: `lab_end_vars.append(end_var)`
3. **Position** cursor at the end of line 704, press Enter to create a new line
4. **Paste** the entire code block above
5. **Check** indentation - the first 3 lines should align with the `for` loop above them
6. **Save** the file

### Verify the Fix

After applying, search for `solver = cp_model.CpSolver()` - it should be around line 710.

The file should have:
- Line 704: `lab_end_vars.append(end_var)`
- Lines 705-708: Close the model building (AddMinEquality, etc.)
- Lines 709-735: Solver initialization and execution  
- Line 736+: Result building starting with `for sem in selected_semesters:`

### Alternative: Use the Patch File

See `scheduling/SOLVER_FIX_PATCH.py` for the same fix with detailed instructions.

---

## ✅ What's Already Done

1. ✅ `app.py` - Updated to use `schedule_with_auto_optimization`
2. ✅ `solver_optimized.py` - Hierarchical solver created
3. ✅ `optimization_utils.py` - Utility functions created

After fixing `solver.py`, the entire optimization will be complete!
