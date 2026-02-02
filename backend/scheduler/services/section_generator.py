from typing import Tuple

from ..models import Semester, StudentCapacity, Section


def generate_sections_default(section_size: int = 50, program_code: str = "A") -> int:
    """Generate Section rows for all semesters based on StudentCapacity.

    Uses a simple naming scheme S{semester}{program_code}{i} matching the solver utils.
    Returns number of sections created (existing ones are left as-is).
    """
    created = 0
    capacities = StudentCapacity.objects.select_related("semester").all()
    for sc in capacities:
        sem = sc.semester
        students = sc.student_count
        # compute count like in utils.build_sections_for_semester
        import math
        count = max(1, math.ceil(students / section_size)) if students else 0
        for i in range(count):
            name = f"S{sem.number}{program_code}{i+1}"
            _, was_created = Section.objects.get_or_create(semester=sem, name=name)
            created += 1 if was_created else 0
    return created
