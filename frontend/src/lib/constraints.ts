export type Constraints = {
  maxHoursPerDay: number
  maxLabsPerDay: number
  minGapMinutes: number
  earliestStartHour: number
  noClassesAfterHour: number
  workingDaysPerWeek: number
  allowConsecutiveLabs: boolean
  allowSameSubjectTwicePerDay: boolean
  // optional extended fields for backward compat
  maxConsecutiveHours?: number
}

export const CONSTRAINTS_KEY = 'scheduler_constraints_v1'

export const DEFAULT_CONSTRAINTS: Constraints = {
  maxHoursPerDay: 8,
  maxLabsPerDay: 1,
  minGapMinutes: 0,
  earliestStartHour: 8,
  noClassesAfterHour: 18,
  workingDaysPerWeek: 5,
  allowConsecutiveLabs: true,
  allowSameSubjectTwicePerDay: false,
}

export function getConstraints(): Constraints {
  try {
    const raw = localStorage.getItem(CONSTRAINTS_KEY)
    if (!raw) return DEFAULT_CONSTRAINTS
    const parsed = JSON.parse(raw)
    // Backward compatibility mapping
    const mapped: Partial<Constraints> = {}
    if (parsed.minBreakMinutes != null) mapped.minGapMinutes = parsed.minBreakMinutes
    if (parsed.dayStartHour != null) mapped.earliestStartHour = parsed.dayStartHour
    if (parsed.dayEndHour != null) mapped.noClassesAfterHour = parsed.dayEndHour
    if (parsed.workingDays != null) mapped.workingDaysPerWeek = parsed.workingDays
    if (parsed.allowSaturday === true && mapped.workingDaysPerWeek == null) mapped.workingDaysPerWeek = 6
    if (parsed.maxConsecutiveHours != null) mapped.maxConsecutiveHours = parsed.maxConsecutiveHours
    return { ...DEFAULT_CONSTRAINTS, ...parsed, ...mapped }
  } catch {
    return DEFAULT_CONSTRAINTS
  }
}

export function saveConstraints(c: Constraints) {
  localStorage.setItem(CONSTRAINTS_KEY, JSON.stringify(c))
}
