from django.db import models
from django.utils import timezone

# --------------------
# Teachers
# --------------------

class Teacher(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class TeacherPreference(models.Model):
    """Stores teacher assignment preferences from Excel upload"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='preferences')
    course_code = models.CharField(max_length=20)  # Can be '*' for any course
    sections_count = models.PositiveIntegerField()  # Number of sections to assign
    can_theory = models.BooleanField(default=True)
    can_lab = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.teacher.name} - {self.course_code} ({self.sections_count} sections)"

    class Meta:
        ordering = ['teacher', 'course_code']


# --------------------
# Academic Structure
# --------------------

class Semester(models.Model):
    number = models.PositiveIntegerField(unique=True)

    def __str__(self):
        return f"Semester {self.number}"


class StudentCapacity(models.Model):
    semester = models.OneToOneField(Semester, on_delete=models.CASCADE)
    student_count = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.semester} - {self.student_count} students"


class Section(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)  # e.g. S3-A1

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('semester', 'name')


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    is_lab = models.BooleanField(default=False)
    times_needed = models.PositiveIntegerField()  # Weekly sessions count

    def __str__(self):
        return f"{self.code} - {self.name}"


class SectionSubject(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.section} -> {self.subject}"

    class Meta:
        unique_together = ('section', 'subject')


# --------------------
# Rooms & Timeslots
# --------------------

class Room(models.Model):
    ROOM_TYPES = (
        ("theory", "Theory Room"),
        ("lab", "Lab Room")
    )
    name = models.CharField(max_length=50, unique=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES)
    capacity = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"{self.name} ({self.room_type})"


class TimeSlot(models.Model):
    DAY_CHOICES = (
        (0, "Mon"),
        (1, "Tue"),
        (2, "Wed"),
        (3, "Thu"),
        (4, "Fri"),
        (5, "Sat"),
    )

    SLOT_TYPES = (
        ("theory", "Theory"),
        ("lab", "Lab"),
    )

    day = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_type = models.CharField(max_length=10, choices=SLOT_TYPES)

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time}-{self.end_time} ({self.slot_type})"


class SpecialLab(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject.code} -> {self.room.name}"


# --------------------
# Electives
# --------------------

class ElectiveConfig(models.Model):
    subject = models.OneToOneField(Subject, on_delete=models.CASCADE)
    sections_count = models.PositiveIntegerField()
    can_use_theory = models.BooleanField(default=True)
    can_use_lab = models.BooleanField(default=False)

    def __str__(self):
        return f"Elective: {self.subject.code}"


# --------------------
# Cohort Support
# --------------------

class CohortCourse(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    section_label = models.CharField(max_length=20)  # Excel value e.g. "C08-A"
    fixed_day = models.IntegerField()  # numeric weekday index
    fixed_timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.subject.code} Cohort {self.section_label}"


class CohortSubSection(models.Model):
    cohort = models.ForeignKey(CohortCourse, on_delete=models.CASCADE)
    size = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.cohort.section_label} ({self.size})"


# --------------------
# Generated Timetable
# --------------------

class TimetableSlot(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('room', 'timeslot')  # no double booking

    def __str__(self):
        return f"{self.section} - {self.subject.code} @ {self.timeslot}"


class ElectiveSlot(models.Model):
    elective = models.ForeignKey(ElectiveConfig, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.elective.subject.code} Elective @ {self.timeslot}"


# --------------------
# Run Metadata / Change Detection
# --------------------

class ScheduleRun(models.Model):
    RUN_TYPES = (
        ("main", "Main Schedule"),
        ("electives", "Electives"),
    )

    run_type = models.CharField(max_length=20, choices=RUN_TYPES, db_index=True)
    input_hash = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    params = models.JSONField(blank=True, null=True)
    created_count = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["run_type", "created_at"]),
            models.Index(fields=["run_type", "input_hash"]),
        ]

    def __str__(self):
        return f"{self.run_type} @ {self.created_at:%Y-%m-%d %H:%M} (hash={self.input_hash[:8]}...)"
