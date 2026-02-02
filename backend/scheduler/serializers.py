from rest_framework import serializers

from .models import (
    Semester,
    StudentCapacity,
    Section,
    Subject,
    SectionSubject,
    Room,
    TimeSlot,
    SpecialLab,
    ElectiveConfig,
    TimetableSlot,
    ElectiveSlot,
    Teacher,
    TeacherPreference,
)


class ExcelUploadSerializer(serializers.Serializer):
    main_file = serializers.FileField()
    cohort_file = serializers.FileField(required=False)


# Basic CRUD serializers for existing models (to satisfy registered routers)
class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = "__all__"


class StudentCapacitySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCapacity
        fields = "__all__"


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = "__all__"


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"


class SectionSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionSubject
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = "__all__"


class SpecialLabSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialLab
        fields = "__all__"


class ElectiveConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectiveConfig
        fields = "__all__"


class TimetableSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableSlot
        fields = "__all__"


class ElectiveSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectiveSlot
        fields = "__all__"


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = "__all__"


class TeacherPreferenceSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    
    class Meta:
        model = TeacherPreference
        fields = "__all__"


class TeacherUploadSerializer(serializers.Serializer):
    teacher_file = serializers.FileField()
    clear_existing = serializers.BooleanField(required=False, default=True)


class AssignTeachersRequestSerializer(serializers.Serializer):
    clear_existing = serializers.BooleanField(required=False, default=False)


# Scheduling API serializers
class ConstraintsSerializer(serializers.Serializer):
    maxHoursPerDay = serializers.IntegerField(required=False)
    workingDaysPerWeek = serializers.IntegerField(required=False)
    minGapMinutes = serializers.IntegerField(required=False)
    noClassesAfterHour = serializers.IntegerField(required=False, allow_null=True)


class RunScheduleRequestSerializer(serializers.Serializer):
    selected_semesters = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )
    section_size = serializers.IntegerField(required=False, default=50)
    program_code = serializers.CharField(required=False, default="A")
    enable_cohort = serializers.BooleanField(required=False, default=False)
    clear_existing = serializers.BooleanField(required=False, default=True)
    constraints = ConstraintsSerializer(required=False)


class RunElectivesRequestSerializer(serializers.Serializer):
    theory_needed = serializers.IntegerField(required=False, default=2)
    lab_needed = serializers.IntegerField(required=False, default=1)
    clear_existing = serializers.BooleanField(required=False, default=True)
