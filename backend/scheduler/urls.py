from django.urls import path, include
from rest_framework import routers
from .views import (
    SectionViewSet,
    RoomViewSet,
    SubjectViewSet,
    SectionSubjectViewSet,
    TimetableSlotViewSet,
    UploadExcelView,
    RunScheduleView,
    RunElectivesView,
    SemesterViewSet,
    StudentCapacityViewSet,
    TimeSlotViewSet,
    ElectiveConfigViewSet,
    ElectiveSlotViewSet,
    ExportTimetableView,
    SpecialLabViewSet,
    PlanSummaryView,
    TeacherViewSet,
    TeacherPreferenceViewSet,
    UploadTeachersView,
    AssignTeachersView,
)


router = routers.DefaultRouter()
router.register(r'semesters', SemesterViewSet)
router.register(r'student-capacities', StudentCapacityViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'section-subjects', SectionSubjectViewSet)
router.register(r'timeslots', TimeSlotViewSet)
router.register(r'timetable', TimetableSlotViewSet)
router.register(r'elective-configs', ElectiveConfigViewSet)
router.register(r'elective-slots', ElectiveSlotViewSet)
router.register(r'special-labs', SpecialLabViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'teacher-preferences', TeacherPreferenceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload-excel/', UploadExcelView.as_view()),
    path('run-schedule/', RunScheduleView.as_view()),
    path('run-electives/', RunElectivesView.as_view()),
    path('export-timetable/', ExportTimetableView.as_view()),
    path('plan-summary/', PlanSummaryView.as_view()),
    path('upload-teachers/', UploadTeachersView.as_view()),
    path('assign-teachers/', AssignTeachersView.as_view()),
]
