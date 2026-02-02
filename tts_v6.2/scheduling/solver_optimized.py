"""
Optimized solver wrapper for large-scale timetable scheduling.
Implements hierarchical solving and performance optimizations.
"""

from ortools.sat.python import cp_model
from .solver import schedule_timetable
from .optimization_utils import (
    merge_usage_data,
    should_use_hierarchical_solving,
    ProgressTracker,
    estimate_problem_size
)
import time
from typing import Dict, List, Tuple, Optional


def schedule_hierarchical(
    selected_semesters: List[int],
    semester_courses_map: Dict,
    section_sizes: Dict,
    usage_data: Dict,
    DAYS: List[str],
    THEORY_TIMESLOTS: List[int],
    TIMESLOT_LABELS: Dict,
    LAB_SLOTS: List[int],
    LAB_SLOT_LABELS: Dict,
    LAB_OVERLAP_MAP: Dict,
    theory_rooms: List[str],
    lab_rooms: List[str],
    special_lab_rooms: Dict,
    section_size: int = 50,
    program_code: str = "A",
    cohort_map: Optional[Dict] = None,
    enable_cohort: bool = False,
    constraints: Optional[Dict] = None,
    solver_config: Optional[Dict] = None
) -> Tuple[Dict, Dict, List]:
    """
    Schedule semesters hierarchically (one at a time) for better scalability.
    
    This approach reduces the problem size by 8× for 8 semesters, making
    1000+ subject scheduling feasible.
    
    Args:
        (same as schedule_timetable, plus:)
        solver_config: Optional dict with solver tuning parameters:
            - 'max_time_per_semester': timeout in seconds (default: 300)
            - 'num_workers': parallel workers (default: 8)
            - 'log_progress': enable logging (default: True)
            - 'semester_order': 'ascending' or 'descending' (default: 'ascending')
    
    Returns:
        Combined (schedule_map, semester_sections_map, all_allocations) or None if any fails
    """
    # Parse solver config
    solver_config = solver_config or {}
    max_time_per_sem = solver_config.get('max_time_per_semester', 300)
    num_workers = solver_config.get('num_workers', 8)
    log_progress = solver_config.get('log_progress', True)
    semester_order = solver_config.get('semester_order', 'ascending')
    
    # Initialize trackers
    tracker = ProgressTracker(len(selected_semesters)) if log_progress else None
    combined_schedule_map = {}
    combined_sections_map = {}
    all_allocations = []
    current_usage = usage_data.copy()
    
    # Sort semesters
    sorted_semesters = sorted(
        selected_semesters,
        reverse=(semester_order == 'descending')
    )
    
    if log_progress:
        total_courses = sum(len(semester_courses_map.get(s, [])) for s in sorted_semesters)
        print(f"\n🚀 Hierarchical Scheduling Mode")
        print(f"   Semesters: {len(sorted_semesters)}")
        print(f"   Total courses: {total_courses}")
        print(f"   Timeout per semester: {max_time_per_sem}s")
        print(f"   Parallel workers: {num_workers}")
    
    # Schedule each semester individually
    for semester in sorted_semesters:
        if tracker:
            tracker.start_semester(semester)
        
        start_time = time.time()
        
        # Prepare solver config for this semester
        semester_constraints = constraints.copy() if constraints else {}
        
        # Add solver-specific parameters
        if 'solver_params' not in semester_constraints:
            semester_constraints['solver_params'] = {}
        
        semester_constraints['solver_params'].update({
            'max_time_in_seconds': max_time_per_sem,
            'num_search_workers': num_workers,
            'log_search_progress': log_progress
        })
        
        # Schedule this one semester
        result = schedule_timetable(
            selected_semesters=[semester],  # Only this semester!
            semester_courses_map=semester_courses_map,
            section_sizes=section_sizes,
            usage_data=current_usage,
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
            constraints=semester_constraints
        )
        
        solve_time = time.time() - start_time
        
        if result is None:
            if tracker:
                tracker.complete_semester(semester, False, solve_time)
                tracker.summary()
            
            print(f"\n❌ FAILED: Semester {semester} is infeasible or timed out")
            print(f"   Possible solutions:")
            print(f"   1. Increase timeout (current: {max_time_per_sem}s)")
            print(f"   2. Add more rooms")
            print(f"   3. Reduce constraints")
            print(f"   4. Check room capacities")
            return None
        
        schedule_map, sections_map, new_allocations = result
        
        # Merge results
        combined_schedule_map.update(schedule_map)
        combined_sections_map.update(sections_map)
        all_allocations.extend(new_allocations)
        
        # Update usage data with new allocations
        current_usage = merge_usage_data(current_usage, new_allocations)
        
        if tracker:
            tracker.complete_semester(semester, True, solve_time)
    
    if tracker:
        tracker.summary()
    
    return combined_schedule_map, combined_sections_map, all_allocations


def schedule_with_auto_optimization(
    selected_semesters: List[int],
    semester_courses_map: Dict,
    section_sizes: Dict,
    usage_data: Dict,
    DAYS: List[str],
    THEORY_TIMESLOTS: List[int],
    TIMESLOT_LABELS: Dict,
    LAB_SLOTS: List[int],
    LAB_SLOT_LABELS: Dict,
    LAB_OVERLAP_MAP: Dict,
    theory_rooms: List[str],
    lab_rooms: List[str],
    special_lab_rooms: Dict,
    section_size: int = 50,
    program_code: str = "A",
    cohort_map: Optional[Dict] = None,
    enable_cohort: bool = False,
    constraints: Optional[Dict] = None,
    force_hierarchical: bool = False,
    hierarchical_threshold: int = 300
):
    """
    Automatically choose between standard and hierarchical solving based on problem size.
    
    Args:
        (same as schedule_timetable, plus:)
        force_hierarchical: Force hierarchical mode regardless of size
        hierarchical_threshold: Course count above which to use hierarchical
    
    Returns:
        (schedule_map, semester_sections_map, allocations) or None
    """
    # Calculate total courses
    total_courses = sum(len(semester_courses_map.get(s, [])) for s in selected_semesters)
    total_sections = sum(
        len([1 for _ in range(0, section_sizes.get(s, 0), section_size)])
        for s in selected_semesters
    )
    
    # Estimate problem size
    avg_slots = len(THEORY_TIMESLOTS) + len(LAB_SLOTS)
    avg_rooms = (len(theory_rooms) + len(lab_rooms)) // 2
    estimate = estimate_problem_size(
        total_sections,
        total_courses,
        len(DAYS),
        avg_slots,
        avg_rooms
    )
    
    # Decide on approach
    use_hierarchical = (
        force_hierarchical or
        should_use_hierarchical_solving(
            len(selected_semesters),
            total_courses,
            hierarchical_threshold
        )
    )
    
    print(f"\n📊 Problem Size Estimation:")
    print(f"   Courses: {total_courses}")
    print(f"   Sections: {total_sections}")
    print(f"   Est. variables: {estimate['variables']:,}")
    print(f"   Est. memory: ~{estimate['memory_mb']} MB")
    print(f"   Approach: {'HIERARCHICAL' if use_hierarchical else 'STANDARD'}")
    
    if use_hierarchical:
        print(f"   Reason: Problem size > {hierarchical_threshold} courses or very large variable count")
        
        # Use hierarchical solver
        return schedule_hierarchical(
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
            constraints=constraints
        )
    else:
        print(f"   Reason: Small problem, standard solver is more optimal")
        
        # Use standard solver
        return schedule_timetable(
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
            constraints=constraints
        )
