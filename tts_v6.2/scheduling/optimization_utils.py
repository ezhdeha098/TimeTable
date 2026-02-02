"""
Optimization utilities for large-scale timetable scheduling.
Provides helpers for smart variable creation and performance improvements.
"""

from typing import List, Dict, Set, Tuple


def filter_valid_rooms_by_capacity(
    rooms: List[str],
    room_capacities: Dict[str, int],
    required_capacity: int,
    margin: float = 1.0
) -> List[str]:
    """
    Filter rooms that can accommodate the required capacity.
    
    Args:
        rooms: List of room names
        room_capacities: Dict mapping room name to capacity
        required_capacity: Minimum required capacity (e.g., section size)
        margin: Capacity margin multiplier (1.0 = exact, 1.2 = 20% buffer)
    
    Returns:
        List of room names that meet capacity requirements
    """
    min_capacity = int(required_capacity * margin)
    return [
        room for room in rooms 
        if room_capacities.get(room, 0) >= min_capacity
    ]


def filter_rooms_by_type(
    rooms: List[str],
    room_types: Dict[str, str],
    required_type: str
) -> List[str]:
    """
    Filter rooms by type (theory/lab).
    
    Args:
        rooms: List of room names
        room_types: Dict mapping room name to type ('theory' or 'lab')
        required_type: Required room type
    
    Returns:
        List of rooms matching the required type
    """
    return [
        room for room in rooms 
        if room_types.get(room, '') == required_type
    ]


def get_valid_rooms_for_course(
    course_code: str,
    is_lab: bool,
    section_size: int,
    theory_rooms: List[str],
    lab_rooms: List[str],
    special_lab_rooms: Dict[str, List[str]],
    room_capacities: Dict[str, int],
    capacity_margin: float = 1.0
) -> List[str]:
    """
    Get list of valid rooms for a specific course.
    Combines type filtering, capacity filtering, and special lab assignments.
    
    Args:
        course_code: Course identifier
        is_lab: Whether this is a lab course
        section_size: Number of students in section
        theory_rooms: List of all theory room names
        lab_rooms: List of all lab room names
        special_lab_rooms: Dict mapping course codes to their required labs
        room_capacities: Dict mapping room names to capacities
        capacity_margin: Capacity buffer (1.0 = exact fit)
    
    Returns:
        List of valid room names for this course
    """
    # Check if course has special lab requirement
    if is_lab and course_code in special_lab_rooms:
        candidate_rooms = [r.strip() for r in special_lab_rooms[course_code]]
    elif is_lab:
        candidate_rooms = lab_rooms
    else:
        candidate_rooms = theory_rooms
    
    # Filter by capacity
    valid_rooms = filter_valid_rooms_by_capacity(
        candidate_rooms,
        room_capacities,
        section_size,
        capacity_margin
    )
    
    return valid_rooms


def precompute_section_courses(
    selected_semesters: List[int],
    semester_sections_map: Dict[int, List[str]],
    semester_courses_map: Dict[int, List[Tuple]]
) -> Dict[str, List[Tuple]]:
    """
    Precompute which courses belong to each section.
    Avoids repeated nested loops during constraint generation.
    
    Args:
        selected_semesters: List of semester numbers
        semester_sections_map: Dict mapping semester to list of section names
        semester_courses_map: Dict mapping semester to list of course tuples
    
    Returns:
        Dict mapping section name to list of course tuples
    """
    section_courses = {}
    
    for sem in selected_semesters:
        sections = semester_sections_map.get(sem, [])
        courses = semester_courses_map.get(sem, [])
        
        for section in sections:
            section_courses[section] = courses
    
    return section_courses


def estimate_problem_size(
    num_sections: int,
    num_courses: int,
    num_days: int,
    num_slots: int,
    num_rooms: int
) -> Dict[str, int]:
    """
    Estimate the problem size and resource requirements.
    
    Returns:
        Dict with estimated variables, constraints, and memory usage
    """
    # Rough estimates
    variables = num_sections * num_courses * num_days * num_slots * num_rooms
    constraints = variables * 2  # Rough multiplier
    memory_mb = variables * 0.0001  # Very rough estimate (100 bytes per var)
    
    return {
        'variables': variables,
        'constraints': constraints,
        'memory_mb': int(memory_mb),
        'is_large': variables > 5_000_000,
        'is_very_large': variables > 20_000_000
    }


def merge_usage_data(
    existing_usage: Dict,
    new_allocations: List[Tuple[str, str, str, int, str]]
) -> Dict:
    """
    Merge new allocations into existing usage data.
    Used for hierarchical solving to track cumulative room usage.
    
    Args:
        existing_usage: Current usage data dict with structure:
            {'theory': {room: {day: [slots]}}, 'lab': {room: {day: [slots]}}}
        new_allocations: List of (rtype, room, day, slot, label) tuples
    
    Returns:
        Updated usage data dict
    """
    import copy
    usage = copy.deepcopy(existing_usage)
    
    # Ensure structure exists
    if 'theory' not in usage:
        usage['theory'] = {}
    if 'lab' not in usage:
        usage['lab'] = {}
    
    for (rtype, room, day, slot, label) in new_allocations:
        if room not in usage[rtype]:
            usage[rtype][room] = {}
        if day not in usage[rtype][room]:
            usage[rtype][room][day] = []
        
        # Add slot if not already present
        if slot not in usage[rtype][room][day]:
            usage[rtype][room][day].append(slot)
    
    return usage


def should_use_hierarchical_solving(
    num_semesters: int,
    total_courses: int,
    threshold: int = 300
) -> bool:
    """
    Determine if hierarchical solving should be used based on problem size.
    
    Args:
        num_semesters: Number of semesters to schedule
        total_courses: Total number of courses across all semesters
        threshold: Course count above which to use hierarchical approach
    
    Returns:
        True if hierarchical solving is recommended
    """
    # Use hierarchical if:
    # 1. Total courses exceeds threshold
    # 2. Multiple semesters are being scheduled
    return total_courses > threshold and num_semesters > 1


class ProgressTracker:
    """Simple progress tracker for hierarchical solving."""
    
    def __init__(self, total_semesters: int):
        self.total = total_semesters
        self.current = 0
        self.failed = []
    
    def start_semester(self, semester: int):
        """Mark start of semester scheduling."""
        self.current += 1
        print(f"\n{'='*60}")
        print(f"Scheduling Semester {semester} ({self.current}/{self.total})")
        print(f"{'='*60}")
    
    def complete_semester(self, semester: int, success: bool, solve_time: float = 0):
        """Mark completion of semester scheduling."""
        if success:
            print(f"✅ Semester {semester} completed in {solve_time:.2f}s")
        else:
            print(f"❌ Semester {semester} FAILED")
            self.failed.append(semester)
    
    def summary(self):
        """Print summary of scheduling progress."""
        print(f"\n{'='*60}")
        print(f"Scheduling Complete: {self.current - len(self.failed)}/{self.total} succeeded")
        if self.failed:
            print(f"Failed semesters: {', '.join(map(str, self.failed))}")
        print(f"{'='*60}\n")
