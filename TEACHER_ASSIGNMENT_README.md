# Teacher Assignment Feature

## Overview
This feature allows you to assign teachers to generated timetable slots using an Excel file with flexible assignment rules.

## How It Works

### Workflow
1. **Generate Timetable**: First, run the main scheduler to generate course schedules
2. **Upload Teacher Preferences**: Upload an Excel file with teacher preferences
3. **Assign Teachers**: Click "Assign Teachers" to automatically map teachers to slots
4. **Export**: Download the complete timetable with teacher assignments

### Assignment Priority
Teachers are assigned based on specificity (most specific first):
1. **Specific Course + Specific Type** (e.g., CS201 + Theory)
2. **Specific Course + Any Type** (e.g., CS201 + *)
3. **Any Course + Specific Type** (e.g., * + Theory)
4. **Any Course + Any Type** (e.g., * + *)

## Excel Format

### Required Columns
| Teacher Name | Course Code | Sections Count | Type   |
|--------------|-------------|----------------|--------|
| Dr. Ahmed    | CS201       | 2              | Theory |
| Prof. Sara   | *           | 1              | Lab    |
| Dr. Ali      | CS302       | 3              | *      |

### Column Definitions

#### Teacher Name
- **Required**: Yes
- **Type**: Text
- **Description**: Full name of the teacher
- **Example**: `Dr. Ahmed Khan`, `Prof. Sara Ali`

#### Course Code
- **Required**: Yes
- **Type**: Text
- **Values**: 
  - Specific course code (e.g., `CS201`, `CS302`)
  - `*` for any course (wildcard)
- **Example**: `CS201` (only CS201), `*` (any course)

#### Sections Count
- **Required**: Yes
- **Type**: Integer (positive)
- **Description**: Number of sections to assign
- **Meaning**: 
  - For **Theory**: Each section = 2 time slots/week (2 sessions per section)
  - For **Lab**: Each section = 1 time slot/week (single lab block)
- **Example**: 
  - `Sections Count = 2` for Theory → 4 time slots total
  - `Sections Count = 1` for Lab → 1 time slot total

#### Type
- **Required**: Yes
- **Type**: Text
- **Values**:
  - `Theory` or `T`: Can only teach theory sessions
  - `Lab` or `L`: Can only teach lab sessions
  - `*` or `Both` or `Any`: Can teach both theory and lab
- **Example**: `Theory`, `Lab`, `*`

## Examples

### Example 1: Specific Assignments
```
Teacher Name,Course Code,Sections Count,Type
Dr. Ahmed,CS201,2,Theory
```
**Result**: Dr. Ahmed teaches CS201 theory to 2 sections (4 time slots/week)

### Example 2: Flexible Lab Instructor
```
Teacher Name,Course Code,Sections Count,Type
Prof. Sara,*,3,Lab
```
**Result**: Prof. Sara teaches lab sessions for any 3 sections (3 lab slots/week)

### Example 3: Fully Flexible Teacher
```
Teacher Name,Course Code,Sections Count,Type
Dr. Ali,*,2,*
```
**Result**: Dr. Ali teaches any course, any type, to 2 sections (auto-assigned)

### Example 4: Course-Specific, Type-Flexible
```
Teacher Name,Course Code,Sections Count,Type
Dr. Hassan,CS302,3,*
```
**Result**: Dr. Hassan teaches CS302 (both theory and lab) to 3 sections

## Assignment Rules & Constraints

### 1. No Teacher Conflicts
- A teacher cannot be assigned to two slots at the same time
- System automatically checks for time conflicts

### 2. Section-Based Assignment
- Each section typically has:
  - **Theory courses**: 2 sessions per week
  - **Lab courses**: 1 session per week
- "Sections Count" refers to complete sections, not individual time slots

### 3. Priority-Based Assignment
- Specific assignments are made first
- Wildcard assignments fill remaining gaps
- Ensures best possible matching

### 4. Partial Assignments
- If no matching teacher exists for a slot, it remains unassigned
- System reports unassigned slots after assignment

## API Endpoints

### Upload Teachers
**POST** `/api/upload-teachers/`

**Request**:
- Content-Type: `multipart/form-data`
- Body: 
  - `teacher_file`: Excel file
  - `clear_existing`: boolean (default: true)

**Response**:
```json
{
  "status": "ok",
  "teachers_created": 5,
  "preferences_created": 7,
  "total_rows": 7
}
```

### Assign Teachers
**POST** `/api/assign-teachers/`

**Request**:
```json
{
  "clear_existing": false
}
```

**Response**:
```json
{
  "status": "ok",
  "assigned": 45,
  "unassigned": 3,
  "total_slots": 48,
  "teacher_workloads": {
    "1": 12,
    "2": 8,
    "3": 15
  },
  "warnings": [
    "Dr. Ahmed: 12 slots assigned",
    "3 slots remain unassigned (no matching teachers)"
  ]
}
```

## Frontend Usage

### Schedule Management Page
1. Navigate to **Schedule** page in the app
2. Scroll to **Teacher Assignment** card
3. **Step 1**: Click "Choose File" and select your Excel file
4. Click "Upload" to import teacher preferences
5. **Step 2**: Click "Assign Teachers" to auto-assign

### View Assignments
- Go to **Timetable** page
- Teacher names appear in brackets after room names
- Example: `CS201 @ R101 [Dr. Ahmed]`

### Export with Teachers
- Click **Export** button on Timetable page
- Downloaded Excel includes "Teacher" column
- Pivot view shows teachers inline

## Troubleshooting

### Issue: "No unassigned timetable slots found"
**Solution**: Generate the main timetable first before assigning teachers

### Issue: "No teacher preferences uploaded"
**Solution**: Upload the teacher Excel file in Step 1 first

### Issue: "X slots remain unassigned"
**Cause**: No matching teacher found for those slots
**Solution**: 
- Add more teachers with wildcard (`*`) preferences
- Check if Type restrictions are too strict
- Verify course codes match exactly

### Issue: "Upload failed: Invalid Type value"
**Cause**: Type column has invalid value
**Solution**: Use only `Theory`, `Lab`, or `*` (case-insensitive)

### Issue: Teacher conflicts
**Cause**: Same teacher assigned to overlapping time slots
**Solution**: System automatically prevents this - shouldn't occur

## Database Schema

### Teacher Model
```python
class Teacher(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
```

### TeacherPreference Model
```python
class TeacherPreference(models.Model):
    teacher = models.ForeignKey(Teacher)
    course_code = models.CharField(max_length=20)  # or '*'
    sections_count = models.PositiveIntegerField()
    can_theory = models.BooleanField(default=True)
    can_lab = models.BooleanField(default=True)
```

### TimetableSlot (Updated)
```python
class TimetableSlot(models.Model):
    section = models.ForeignKey(Section)
    subject = models.ForeignKey(Subject)
    room = models.ForeignKey(Room)
    timeslot = models.ForeignKey(TimeSlot)
    teacher = models.ForeignKey(Teacher, null=True, blank=True)  # NEW
```

## Files Modified/Created

### Backend
- `backend/scheduler/models.py` - Added Teacher, TeacherPreference models
- `backend/scheduler/services/teacher_assigner.py` - NEW: Assignment logic
- `backend/scheduler/serializers.py` - Added teacher serializers
- `backend/scheduler/views.py` - Added teacher views
- `backend/scheduler/urls.py` - Added teacher endpoints
- `backend/scheduler/services/exporter.py` - Updated to include teachers
- `backend/scheduler/migrations/0002_teacher_*.py` - NEW: Database migration

### Frontend
- `frontend/src/components/TeacherAssignment.tsx` - Already existed
- `frontend/src/components/TimetableViewer.tsx` - Already supports teachers
- `frontend/src/pages/SchedulePage.tsx` - Already includes component

## Future Enhancements (Optional)

1. **Teacher Availability**: Add preferred days/times per teacher
2. **Max Workload**: Set maximum hours per teacher per week
3. **Manual Assignment**: UI to manually assign/reassign specific slots
4. **Teacher Schedule Report**: Dedicated view showing weekly schedule per teacher
5. **Conflict Resolution**: Smart suggestions when conflicts occur
6. **Multi-Teacher Courses**: Support co-teaching (multiple teachers per slot)

## Migration Commands

```bash
# Create migration
python manage.py makemigrations scheduler

# Apply migration
python manage.py migrate scheduler
```

## Sample Template

See `backend/teacher_assignment_template.csv` for a sample Excel template.

Convert to `.xlsx` format before uploading (Excel can open .csv and save as .xlsx).
