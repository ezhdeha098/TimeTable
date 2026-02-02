from django.contrib import admin
from django.contrib import messages

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
)
from .services.section_generator import generate_sections_default


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
	list_display = ("number",)
	actions = ["generate_sections"]

	def generate_sections(self, request, queryset):
		created = generate_sections_default()
		self.message_user(request, f"Generated or ensured Sections for all semesters. Created: {created}", level=messages.SUCCESS)

	generate_sections.short_description = "Auto-generate Sections (size=50, code='A')"


@admin.register(StudentCapacity)
class StudentCapacityAdmin(admin.ModelAdmin):
	list_display = ("semester", "student_count")
	actions = ["generate_sections"]

	def generate_sections(self, request, queryset):
		created = generate_sections_default()
		self.message_user(request, f"Generated or ensured Sections for all semesters. Created: {created}", level=messages.SUCCESS)

	generate_sections.short_description = "Auto-generate Sections (size=50, code='A')"


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
	list_display = ("name", "semester")
	list_filter = ("semester",)
	search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
	list_display = ("code", "name", "is_lab", "times_needed")
	list_filter = ("is_lab",)
	search_fields = ("code", "name")


@admin.register(SectionSubject)
class SectionSubjectAdmin(admin.ModelAdmin):
	list_display = ("section", "subject")
	list_filter = ("section__semester",)
	autocomplete_fields = ("section", "subject")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = ("name", "room_type", "capacity")
	list_filter = ("room_type",)
	search_fields = ("name",)


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
	list_display = ("day", "start_time", "end_time", "slot_type")
	list_filter = ("day", "slot_type")
	ordering = ("day", "start_time")


@admin.register(SpecialLab)
class SpecialLabAdmin(admin.ModelAdmin):
	list_display = ("subject", "room")
	autocomplete_fields = ("subject", "room")


@admin.register(ElectiveConfig)
class ElectiveConfigAdmin(admin.ModelAdmin):
	list_display = ("subject", "sections_count", "can_use_theory", "can_use_lab")
	autocomplete_fields = ("subject",)


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
	list_display = ("section", "subject", "room", "timeslot")
	list_filter = ("section__semester", "room__room_type")
	search_fields = ("section__name", "subject__code", "room__name")


@admin.register(ElectiveSlot)
class ElectiveSlotAdmin(admin.ModelAdmin):
	list_display = ("elective", "room", "timeslot")
	list_filter = ("room__room_type",)
