from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from .serializers import (
    ExcelUploadSerializer,
    SemesterSerializer,
    StudentCapacitySerializer,
    SectionSerializer,
    SubjectSerializer,
    SectionSubjectSerializer,
    RoomSerializer,
    TimeSlotSerializer,
    TimetableSlotSerializer,
    ElectiveConfigSerializer,
    ElectiveSlotSerializer,
    SpecialLabSerializer,
    RunScheduleRequestSerializer,
    RunElectivesRequestSerializer,
    TeacherSerializer,
    TeacherPreferenceSerializer,
    TeacherUploadSerializer,
    AssignTeachersRequestSerializer,
)
from .models import (
    Semester,
    StudentCapacity,
    Section,
    Subject,
    SectionSubject,
    Room,
    TimeSlot,
    TimetableSlot,
    ElectiveConfig,
    ElectiveSlot,
    SpecialLab,
    Teacher,
    TeacherPreference,
)
from .services.excel_importer import ExcelImporter, ExcelImportError
from .services.scheduler_runner import run_main_schedule, run_electives
from .services.exporter import export_timetable_xlsx
from django.http import HttpResponse

class UploadExcelView(APIView):
    def post(self, request):
        serializer = ExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        main_excel = serializer.validated_data["main_file"]
        cohort_excel = serializer.validated_data.get("cohort_file")

        try:
            importer = ExcelImporter(main_excel, cohort_excel)
            importer.validate_and_import()
            return Response({"message": "Excel imported successfully"})
        except ExcelImportError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# -------------------------
# Basic CRUD ViewSets
# -------------------------

class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.all().order_by("number")
    serializer_class = SemesterSerializer


class StudentCapacityViewSet(viewsets.ModelViewSet):
    queryset = StudentCapacity.objects.select_related("semester").all()
    serializer_class = StudentCapacitySerializer


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.select_related("semester").all()
    serializer_class = SectionSerializer


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class SectionSubjectViewSet(viewsets.ModelViewSet):
    queryset = SectionSubject.objects.select_related("section", "subject").all()
    serializer_class = SectionSubjectSerializer


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.all().order_by("day", "start_time")
    serializer_class = TimeSlotSerializer


class TimetableSlotViewSet(viewsets.ModelViewSet):
    queryset = TimetableSlot.objects.select_related("section", "subject", "room", "timeslot").all()
    serializer_class = TimetableSlotSerializer


class ElectiveConfigViewSet(viewsets.ModelViewSet):
    queryset = ElectiveConfig.objects.select_related("subject").all()
    serializer_class = ElectiveConfigSerializer


class ElectiveSlotViewSet(viewsets.ModelViewSet):
    queryset = ElectiveSlot.objects.select_related("elective", "room", "timeslot").all()
    serializer_class = ElectiveSlotSerializer


class SpecialLabViewSet(viewsets.ModelViewSet):
    queryset = SpecialLab.objects.select_related("subject", "room").all()
    serializer_class = SpecialLabSerializer


# -------------------------
# Scheduling endpoints
# -------------------------

class RunScheduleView(APIView):
    def post(self, request):
        serializer = RunScheduleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = run_main_schedule(
            selected_semesters=data.get("selected_semesters"),
            section_size=data.get("section_size", 50),
            program_code=data.get("program_code", "A"),
            enable_cohort=data.get("enable_cohort", False),
            clear_existing=data.get("clear_existing", True),
            constraints=data.get("constraints"),
        )
        status_code = status.HTTP_200_OK if result.get("status") in ("ok", "no-change") else status.HTTP_409_CONFLICT
        return Response(result, status=status_code)


class RunElectivesView(APIView):
    def post(self, request):
        serializer = RunElectivesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = run_electives(
            theory_needed=data.get("theory_needed", 2),
            lab_needed=data.get("lab_needed", 1),
            clear_existing=data.get("clear_existing", True),
        )
        status_code = status.HTTP_200_OK if result.get("status") in ("ok", "no-change") else status.HTTP_409_CONFLICT
        return Response(result, status=status_code)


class ExportTimetableView(APIView):
    def get(self, request):
        content = export_timetable_xlsx()
        resp = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = 'attachment; filename="timetable.xlsx"'
        return resp


class PlanSummaryView(APIView):
    """Compute required vs available slot summary akin to Streamlit app.
    Optional query params:
      - selected_semesters: comma-separated list of ints
      - enable_cohort: bool
      - include_existing: bool (default true) whether to consider current allocations
    """
    def get(self, request):
        from math import ceil
        from .services.scheduler_runner import _build_slot_mappings, _build_semester_courses_map

        # Params
        sel = request.query_params.get("selected_semesters")
        enable_cohort = request.query_params.get("enable_cohort", "false").lower() in ("1", "true", "yes")
        include_existing = request.query_params.get("include_existing", "true").lower() in ("1", "true", "yes")

        if sel:
            try:
                selected_semesters = [int(x) for x in sel.split(",") if x.strip()]
            except Exception:
                return Response({"error": "Invalid selected_semesters parameter"}, status=400)
        else:
            selected_semesters = list(Semester.objects.values_list("number", flat=True).order_by("number"))

        # Rooms
        theory_rooms = list(Room.objects.filter(room_type="theory").values_list("name", flat=True))
        lab_rooms = list(Room.objects.filter(room_type="lab").values_list("name", flat=True))

        # Special labs mapping
        special_map = {}
        for sp in SpecialLab.objects.select_related("subject", "room"):
            special_map.setdefault(sp.subject.code, []).append(sp.room.name)

        # Canonical slot counts
        theory_canonical, lab_canonical, theory_index_map, lab_index_map, *_rest = _build_slot_mappings()
        days_count = 6
        theory_slots_per_room = len(theory_canonical) * days_count
        lab_slots_per_room = len(lab_canonical) * days_count

        # Usage counts
        def init_usage_dict(rnames):
            return {r: 0 for r in rnames}

        used_theory = init_usage_dict(theory_rooms)
        used_lab = init_usage_dict(lab_rooms)

        if include_existing:
            for tt in TimetableSlot.objects.select_related("room", "timeslot"):
                if tt.room.name in used_theory and tt.room.room_type == "theory":
                    used_theory[tt.room.name] += 1
                elif tt.room.name in used_lab and tt.room.room_type == "lab":
                    used_lab[tt.room.name] += 1
            for es in ElectiveSlot.objects.select_related("room", "timeslot"):
                if es.room.name in used_theory and es.room.room_type == "theory":
                    used_theory[es.room.name] += 1
                elif es.room.name in used_lab and es.room.room_type == "lab":
                    used_lab[es.room.name] += 1

        free_theory_per_room = {r: max(theory_slots_per_room - used_theory[r], 0) for r in theory_rooms}
        free_lab_per_room = {r: max(lab_slots_per_room - used_lab[r], 0) for r in lab_rooms}

        free_theory_cap = sum(free_theory_per_room.values())
        free_lab_cap_total = sum(free_lab_per_room.values())

        # Compute needs
        # section sizes and counts
        sizes = {sc.semester.number: sc.student_count for sc in StudentCapacity.objects.select_related("semester")}
        sec_count = {s: max(1, ceil((sizes.get(s, 50)) / 50)) for s in selected_semesters}

        # Courses map (by subjects linked to sections in sem)
        semester_courses_map = _build_semester_courses_map(selected_semesters)

        # Build cohort present set if enabled
        cohort_present = set()
        if enable_cohort:
            from .models import CohortCourse
            for cc in CohortCourse.objects.select_related("subject", "semester"):
                cohort_present.add((cc.semester.number, cc.subject.code))

        total_needed_theory_slots = 0
        total_needed_lab_slots = 0
        special_lab_needed = {}

        for sem in selected_semesters:
            for (code, name, is_lab, times_needed, _ch) in semester_courses_map.get(sem, []):
                if enable_cohort and (sem, code) in cohort_present:
                    continue
                if is_lab:
                    if code in special_map:
                        special_lab_needed[code] = special_lab_needed.get(code, 0) + (times_needed * sec_count[sem])
                    else:
                        total_needed_lab_slots += times_needed * sec_count[sem]
                else:
                    total_needed_theory_slots += times_needed * sec_count[sem]

        # Normal lab capacity excludes special lab rooms
        special_lab_room_names = {rn for rooms in special_map.values() for rn in rooms}
        normal_lab_rooms = [r for r in lab_rooms if r not in special_lab_room_names]
        free_lab_cap = sum(free_lab_per_room.get(r, 0) for r in normal_lab_rooms)

        # Special lab capacity per course
        special_lab_capacities = {}
        total_special_lab_cap = 0
        for code, rooms in special_map.items():
            cap = sum(free_lab_per_room.get(r, 0) for r in rooms)
            special_lab_capacities[code] = cap
            total_special_lab_cap += cap

        # Minimum room suggestions (simple division by per-room capacity)
        def safe_div(num, denom):
            return ceil(num / denom) if denom > 0 else 0
        min_theory_rooms = safe_div(total_needed_theory_slots, theory_slots_per_room)
        min_lab_rooms = safe_div(total_needed_lab_slots + sum(special_lab_needed.values()), lab_slots_per_room)

        payload = {
            "selected_semesters": selected_semesters,
            "theory_rooms": theory_rooms,
            "lab_rooms": lab_rooms,
            "special_lab_rooms": special_map,
            "free_theory_per_room": free_theory_per_room,
            "free_lab_per_room": free_lab_per_room,
            "free_theory_cap": free_theory_cap,
            "free_lab_cap": free_lab_cap,
            "special_lab_capacities": special_lab_capacities,
            "total_special_lab_cap": total_special_lab_cap,
            "needed": {
                "theory": total_needed_theory_slots,
                "lab": total_needed_lab_slots,
                "special_lab": special_lab_needed,
            },
            "per_room_capacity": {
                "theory": theory_slots_per_room,
                "lab": lab_slots_per_room,
            },
            "min_rooms_suggestion": {
                "theory": min_theory_rooms,
                "lab": min_lab_rooms,
            },
        }
        return Response(payload)


# -------------------------
# Teacher Management
# -------------------------

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer


class TeacherPreferenceViewSet(viewsets.ModelViewSet):
    queryset = TeacherPreference.objects.select_related('teacher').all()
    serializer_class = TeacherPreferenceSerializer


class UploadTeachersView(APIView):
    """Upload teacher preferences from Excel file"""
    def post(self, request):
        serializer = TeacherUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        teacher_file = serializer.validated_data['teacher_file']
        clear_existing = serializer.validated_data.get('clear_existing', True)

        try:
            from .services.teacher_assigner import import_teachers_from_excel, TeacherAssignmentError
            result = import_teachers_from_excel(teacher_file, clear_existing)
            return Response(result)
        except TeacherAssignmentError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class AssignTeachersView(APIView):
    """Assign uploaded teachers to timetable slots"""
    def post(self, request):
        serializer = AssignTeachersRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        clear_existing = serializer.validated_data.get('clear_existing', False)

        try:
            from .services.teacher_assigner import TeacherAssigner, TeacherAssignmentError
            assigner = TeacherAssigner()
            result = assigner.assign_teachers(clear_existing)
            
            status_code = status.HTTP_200_OK
            if result['status'] in ['no-slots', 'no-preferences']:
                status_code = status.HTTP_400_BAD_REQUEST
                
            return Response(result, status=status_code)
        except TeacherAssignmentError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
