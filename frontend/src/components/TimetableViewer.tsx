import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import TextField from '@mui/material/TextField'
import InputAdornment from '@mui/material/InputAdornment'
import SearchIcon from '@mui/icons-material/Search'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Grid from '@mui/material/GridLegacy'
import Button from '@mui/material/Button'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import FormGroup from '@mui/material/FormGroup'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import Autocomplete from '@mui/material/Autocomplete'
import Chip from '@mui/material/Chip'
import DownloadIcon from '@mui/icons-material/Download'

// Types reflecting backend minimal fields we need
interface ApiList<T> {
  count?: number
  next?: string | null
  previous?: string | null
  results?: T[]
}

interface Semester { id: number; name?: string; number?: number }
interface Section { id: number; name: string; semester: number }
interface Subject { id: number; code?: string; name?: string }
interface Room { id: number; name: string; is_lab?: boolean }
interface TimeSlot { id: number; day: number; start_time: string; end_time: string }
interface Teacher { id: number; name: string }
interface TimetableSlot { id: number; section: number; subject: number; room: number; timeslot: number; teacher?: number }

const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

async function fetchAll<T>(url: string): Promise<T[]> {
  // Fetches all pages if the API is paginated; otherwise returns the array directly
  const pageSizeParam = url.includes('?') ? '&page_size=100000' : '?page_size=100000'
  let next: string | null = url + pageSizeParam
  const acc: T[] = []
  while (next) {
    const res = await axios.get(next)
    const data = res.data as ApiList<T> | T[]
    if (Array.isArray(data)) {
      // Non-paginated
      acc.push(...data)
      break
    }
    const list = (data.results ?? []) as T[]
    acc.push(...list)
    next = data.next ?? null
  }
  return acc
}

function csvEscape(val: string) {
  if (val == null) return ''
  if (/[",\n]/.test(val)) return '"' + val.replace(/"/g, '""') + '"'
  return val
}

export default function TimetableViewer() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [semesters, setSemesters] = useState<Semester[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [timeslots, setTimeslots] = useState<TimeSlot[]>([])
  const [teachers, setTeachers] = useState<Teacher[]>([])
  const [timetable, setTimetable] = useState<TimetableSlot[]>([])

  const [selectedSemester, setSelectedSemester] = useState<number | 'all'>('all')
  const [sectionFilter, setSectionFilter] = useState('')
  const [selectedDays, setSelectedDays] = useState<number[]>([0,1,2,3,4,5])
  const [timeStartIdx, setTimeStartIdx] = useState<number>(0)
  const [timeEndIdx, setTimeEndIdx] = useState<number>(0)
  // New: control which sections to display (all / single / multi)
  const [viewMode, setViewMode] = useState<'all' | 'single' | 'multi'>('single')
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null)
  const [selectedSectionIds, setSelectedSectionIds] = useState<number[]>([])

  useEffect(() => {
    let alive = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const base = '/api'
        const [sem, sec, sub, rm, ts, teach, tt] = await Promise.all([
          fetchAll<Semester>(`${base}/semesters/`),
          fetchAll<Section>(`${base}/sections/`),
          fetchAll<Subject>(`${base}/subjects/`),
          fetchAll<Room>(`${base}/rooms/`),
          fetchAll<TimeSlot>(`${base}/timeslots/`),
          fetchAll<Teacher>(`${base}/teachers/`),
          fetchAll<TimetableSlot>(`${base}/timetable/`),
        ])
        if (!alive) return
        setSemesters(sem)
        setSections(sec)
        setSubjects(sub)
        setRooms(rm)
        setTimeslots(ts)
        setTeachers(teach)
        setTimetable(tt)
      } catch (e: any) {
        console.error(e)
        setError(e?.message ?? 'Failed to load timetable')
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => { alive = false }
  }, [])

  const maps = useMemo(() => {
    const secMap = new Map(sections.map(s => [s.id, s]))
    const subMap = new Map(subjects.map(s => [s.id, s]))
    const roomMap = new Map(rooms.map(r => [r.id, r]))
    const tsMap = new Map(timeslots.map(t => [t.id, t]))
    const semMap = new Map(semesters.map(s => [s.id, s]))
    const teacherMap = new Map(teachers.map(t => [t.id, t]))
    return { secMap, subMap, roomMap, tsMap, semMap, teacherMap }
  }, [sections, subjects, rooms, timeslots, semesters, teachers])

  const filteredSections = useMemo(() => {
    let list = sections
    if (selectedSemester !== 'all') {
      list = list.filter(s => s.semester === selectedSemester)
    }
    if (sectionFilter.trim()) {
      const q = sectionFilter.trim().toLowerCase()
      list = list.filter(s => s.name.toLowerCase().includes(q))
    }
    return list.sort((a, b) => a.name.localeCompare(b.name))
  }, [sections, selectedSemester, sectionFilter])

  // Keep single/multi selections in sync with current filtered list
  useEffect(() => {
    if (viewMode === 'single') {
      // Default to the first filtered section if none selected or selection not in list
      if (!selectedSectionId || !filteredSections.some(s => s.id === selectedSectionId)) {
        setSelectedSectionId(filteredSections[0]?.id ?? null)
      }
    } else if (viewMode === 'multi') {
      // Drop any ids not present in filtered list
      const ids = new Set(filteredSections.map(s => s.id))
      setSelectedSectionIds(prev => prev.filter(id => ids.has(id)))
    }
  }, [filteredSections, viewMode])

  // Build pivot per section
  type Cell = string
  type RowKey = string // time label

  const timeLabels = useMemo(() => {
    // Unique sorted time windows across all timeslots
    const label = (t: TimeSlot) => `${t.start_time.slice(0,5)}–${t.end_time.slice(0,5)}`
    const set = new Set<string>()
    timeslots.forEach(t => set.add(label(t)))
    return Array.from(set).sort()
  }, [timeslots])

  // Initialize end index when time labels change
  useEffect(() => {
    if (timeLabels.length && (timeEndIdx === 0 || timeEndIdx > timeLabels.length - 1)) {
      setTimeEndIdx(timeLabels.length - 1)
    }
    if (timeStartIdx > timeEndIdx) {
      setTimeStartIdx(0)
    }
  }, [timeLabels])

  const sectionPivots = useMemo(() => {
    // For each section, build rows keyed by time label, columns by day
    const label = (t: TimeSlot) => `${t.start_time.slice(0,5)}–${t.end_time.slice(0,5)}`

    const ttBySection = new Map<number, TimetableSlot[]>()
    for (const slot of timetable) {
      const list = ttBySection.get(slot.section) ?? []
      list.push(slot)
      ttBySection.set(slot.section, list)
    }

    const pivots = new Map<number, Record<RowKey, Cell[]>>()
    for (const sec of filteredSections) {
      const rows: Record<RowKey, Cell[]> = {}
      for (const time of timeLabels) rows[time] = Array(dayLabels.length).fill('')

      const items = ttBySection.get(sec.id) ?? []
      for (const item of items) {
        const ts = maps.tsMap.get(item.timeslot)
        if (!ts) continue
        const rIdx = timeLabels.indexOf(label(ts))
        if (rIdx < 0) continue
        const cIdx = ts.day
        const sub = maps.subMap.get(item.subject)
        const room = maps.roomMap.get(item.room)
        const teacher = item.teacher ? maps.teacherMap.get(item.teacher) : null
        const subLabel = sub?.code || sub?.name || `SUB#${item.subject}`
        const roomLabel = room?.name || `ROOM#${item.room}`
        const isLab = room?.is_lab ? ' (LAB)' : ''
        const teacherLabel = teacher ? ` [${teacher.name}]` : ''
        const val = `${subLabel} @ ${roomLabel}${isLab}${teacherLabel}`
        rows[timeLabels[rIdx]][cIdx] = val
      }
      pivots.set(sec.id, rows)
    }
    return pivots
  }, [filteredSections, timetable, maps, timeLabels])

  // Sections to actually display based on viewMode
  const displayedSections = useMemo(() => {
    if (viewMode === 'all') return filteredSections
    if (viewMode === 'single') {
      const s = filteredSections.find(x => x.id === selectedSectionId)
      return s ? [s] : []
    }
    // multi
    return filteredSections.filter(x => selectedSectionIds.includes(x.id))
  }, [filteredSections, viewMode, selectedSectionId, selectedSectionIds])

  const semesterOptions = useMemo(() => {
    const opts: { value: number | 'all'; label: string }[] = [
      { value: 'all', label: 'All semesters' },
    ]
    const rest = semesters
      .slice()
      .sort((a, b) => (a.number ?? 0) - (b.number ?? 0))
      .map(s => ({ value: s.id as number, label: s.name ?? `Semester ${s.number ?? s.id}` }))
    return [...opts, ...rest]
  }, [semesters])

  function onExportSection(sec: Section) {
    const rows = sectionPivots.get(sec.id)
    if (!rows) return
    const header = ['Time', ...dayLabels.filter((_, i) => selectedDays.includes(i))]
    const lines = [header.map(csvEscape).join(',')]
    const slice = timeLabels.slice(timeStartIdx, Math.max(timeStartIdx, timeEndIdx) + 1)
    for (const time of slice) {
      const cols = rows[time] ?? Array(dayLabels.length).fill('')
      const filtered = cols.filter((_, i) => selectedDays.includes(i))
      lines.push([csvEscape(time), ...filtered.map(c => csvEscape(c || ''))].join(','))
    }
    const csv = lines.join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${sec.name}_pivot.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function onExportAll() {
    const lines: string[] = []
    const slice = timeLabels.slice(timeStartIdx, Math.max(timeStartIdx, timeEndIdx) + 1)
    for (const sec of displayedSections) {
      const rows = sectionPivots.get(sec.id)
      if (!rows) continue
      lines.push(`# Section: ${sec.name}`)
      const header = ['Time', ...dayLabels.filter((_, i) => selectedDays.includes(i))]
      lines.push(header.map(csvEscape).join(','))
      for (const time of slice) {
        const cols = rows[time] ?? Array(dayLabels.length).fill('')
        const filtered = cols.filter((_, i) => selectedDays.includes(i))
        lines.push([csvEscape(time), ...filtered.map(c => csvEscape(c || ''))].join(','))
      }
      lines.push('')
    }
    const csv = lines.join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `timetable_all.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <Card elevation={2}>
        <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Timetable Viewer</Typography>} />
        <CardContent>
          <Typography variant="body2" color="text.secondary">Loading…</Typography>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card elevation={2}>
        <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Timetable Viewer</Typography>} />
        <CardContent>
          <Typography variant="body2" color="error">{error}</Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Timetable Viewer (Pivot)</Typography>} />
      <CardContent>
          <Box sx={{ width: '100%', mb: 1 }}>
            <Grid container spacing={2} alignItems="flex-end">
              <Grid item xs={12} sm={6} md={'auto' as any}>
                <FormControl>
                  <InputLabel id="sem-label">Semester</InputLabel>
                  <Select
                    labelId="sem-label"
                    label="Semester"
                    value={String(selectedSemester)}
                    onChange={(e)=>{
                      const val = e.target.value as string
                      setSelectedSemester(val === 'all' ? 'all' : Number(val))
                    }}
                    sx={{ minWidth: 220 }}
                  >
                    {semesterOptions.map(o => (
                      <MenuItem key={String(o.value)} value={String(o.value)}>{o.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={6}>
                <TextField
                  label="Filter sections"
                  placeholder="Type to filter…"
                  value={sectionFilter}
                  onChange={(e)=>setSectionFilter(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ minWidth: 240 }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={'auto' as any}>
                <FormControl>
                  <InputLabel id="view-label">View</InputLabel>
                  <Select
                    labelId="view-label"
                    label="View"
                    value={viewMode}
                    onChange={(e) => setViewMode(e.target.value as 'all'|'single'|'multi')}
                    sx={{ minWidth: 200 }}
                  >
                    <MenuItem value="all">All sections</MenuItem>
                    <MenuItem value="single">Single section</MenuItem>
                    <MenuItem value="multi">Multi-select</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              {viewMode === 'single' ? (
                <Grid item xs={12} sm={6} md={6}>
                  <FormControl>
                    <InputLabel id="sec-label">Section</InputLabel>
                    <Select
                      labelId="sec-label"
                      label="Section"
                      value={selectedSectionId ?? ''}
                      onChange={(e)=> setSelectedSectionId(Number(e.target.value))}
                      disabled={filteredSections.length === 0}
                      sx={{ minWidth: 220 }}
                    >
                      {filteredSections.map(s => (
                        <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              ) : null}
              {viewMode === 'multi' ? (
                <Grid item xs={12}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                    <Box component="span" sx={{ fontSize: 12, fontWeight: 600, color: 'text.secondary', mr: 1 }}>Sections</Box>
                    <Button size="small" variant="outlined" onClick={() => setSelectedSectionIds(filteredSections.map(s=>s.id))}>Select all</Button>
                    <Button size="small" variant="outlined" onClick={() => setSelectedSectionIds([])}>Clear</Button>
                  </Stack>
                  <Autocomplete
                    multiple
                    options={filteredSections}
                    value={filteredSections.filter(s => selectedSectionIds.includes(s.id))}
                    onChange={(_, vals)=> setSelectedSectionIds(vals.map(v=>v.id))}
                    getOptionLabel={(s)=>s.name}
                    renderTags={(value, getTagProps) =>
                      value.map((option, index) => (
                        <Chip variant="outlined" label={option.name} {...getTagProps({ index })} />
                      ))
                    }
                    renderInput={(params) => (
                      <TextField {...params} label="Sections" placeholder="Select sections" />
                    )}
                    sx={{ maxWidth: 560 }}
                  />
                </Grid>
              ) : null}
              <Grid item xs={12} sm={6} md={'auto' as any}>
                <Box component="div" sx={{ fontSize: 12, fontWeight: 600, color: 'text.secondary', mb: 0.5 }}>Days</Box>
                <FormGroup row>
                  {dayLabels.map((d, i) => (
                    <FormControlLabel key={d}
                      control={<Checkbox size="small" checked={selectedDays.includes(i)} onChange={(e)=>{
                        setSelectedDays(prev => e.target.checked ? Array.from(new Set([...prev, i])) : prev.filter(x=>x!==i))
                      }} />}
                      label={d}
                    />
                  ))}
                </FormGroup>
              </Grid>
              <Grid item xs={12} sm={6} md={'auto' as any}>
                <Box component="div" sx={{ fontSize: 12, fontWeight: 600, color: 'text.secondary', mb: 0.5 }}>Time range</Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <FormControl>
                    <InputLabel id="start-label">Start</InputLabel>
                    <Select labelId="start-label" label="Start" value={timeStartIdx}
                      onChange={(e)=>{
                        const v = Number(e.target.value)
                        setTimeStartIdx(v)
                        if (v > timeEndIdx) setTimeEndIdx(v)
                      }}
                      sx={{ minWidth: 160 }}
                    >
                      {timeLabels.map((t, i) => (<MenuItem key={t} value={i}>{t}</MenuItem>))}
                    </Select>
                  </FormControl>
                  <Box component="span" sx={{ fontSize: 12, color: 'text.secondary' }}>to</Box>
                  <FormControl>
                    <InputLabel id="end-label">End</InputLabel>
                    <Select labelId="end-label" label="End" value={timeEndIdx}
                      onChange={(e)=>{
                        const v = Number(e.target.value)
                        if (v < timeStartIdx) setTimeStartIdx(v)
                        setTimeEndIdx(v)
                      }}
                      sx={{ minWidth: 160 }}
                    >
                      {timeLabels.map((t, i) => (<MenuItem key={t} value={i}>{t}</MenuItem>))}
                    </Select>
                  </FormControl>
                </Stack>
              </Grid>
              <Grid item xs={12} md={'auto' as any}>
                <Button variant="contained" startIcon={<DownloadIcon />} onClick={onExportAll}>Export All CSV</Button>
              </Grid>
            </Grid>
          </Box>
        {displayedSections.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>No sections match the current filters.</Typography>
        ) : null}

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2, mt: 2 }}>
          {displayedSections.map(sec => {
            const rows = sectionPivots.get(sec.id)
            const sem = maps.semMap.get(sec.semester)
            const subtitle = sem?.name ?? `Semester ${sem?.number ?? sec.semester}`
            return (
              <Card key={sec.id} variant="outlined">
                <CardHeader title={
                  <Box sx={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap: 2 }}>
                    <Box>
                      <Typography variant="subtitle2" fontWeight={700}>{sec.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
                    </Box>
                    <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => onExportSection(sec)}>
                      Export CSV
                    </Button>
                  </Box>
                } />
                <CardContent>
                  <Box sx={{ overflow: 'auto' }}>
                    <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                      <Box component="thead" sx={{ position: 'sticky', top: 0, bgcolor: 'background.paper' }}>
                        <Box component="tr">
                          <Box component="th" sx={{ textAlign: 'left', fontWeight: 700, border: '1px solid', borderColor: 'divider', position: 'sticky', left: 0, bgcolor: 'background.paper', zIndex: 1, px: 1, py: 0.5 }}>Time</Box>
                          {dayLabels.map((d, idx) => (
                            selectedDays.includes(idx) ? (
                              <Box key={d} component="th" sx={{ textAlign: 'left', fontWeight: 700, border: '1px solid', borderColor: 'divider', px: 1, py: 0.5 }}>{d}</Box>
                            ) : null
                          ))}
                        </Box>
                      </Box>
                      <Box component="tbody">
                        {timeLabels.slice(timeStartIdx, Math.max(timeStartIdx, timeEndIdx) + 1).map(time => (
                          <Box component="tr" key={time}>
                            <Box component="td" sx={{ border: '1px solid', borderColor: 'divider', fontWeight: 700, position: 'sticky', left: 0, bgcolor: 'background.paper', zIndex: 1, px: 1, py: 0.5 }}>{time}</Box>
                            {dayLabels.map((_, idx) => (
                              selectedDays.includes(idx) ? (
                                <Box key={idx} component="td" sx={{ border: '1px solid', borderColor: 'divider', minWidth: 140, px: 1, py: 0.5, bgcolor: rows && rows[time]?.[idx]?.includes('(LAB)') ? 'success.light' : 'transparent' }}>
                                  {rows ? rows[time]?.[idx] || '' : ''}
                                </Box>
                              ) : null
                            ))}
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            )
          })}
        </Box>
      </CardContent>
    </Card>
  )
}

// Inline styles removed in favor of Tailwind utility classes and sticky headers
