import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  TextField,
  Box,
  Typography,
} from '@mui/material'

type Command = {
  id: string
  label: string
  action: () => Promise<void> | void
}

interface Props {
  open: boolean
  onClose: () => void
}

const routes = [
  { path: '/', label: 'Planner' },
  { path: '/schedule', label: 'Schedule' },
  { path: '/timetable', label: 'Timetable' },
  { path: '/export', label: 'Export' },
  { path: '/settings', label: 'Settings' },
]

export default function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (open) document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const commands: Command[] = useMemo(() => {
    const nav: Command[] = routes.map(({ path, label }) => ({
      id: `nav:${path}`,
      label: `Go to ${label}`,
      action: () => {
        navigate(path)
        onClose()
      }
    }))
    const actions: Command[] = [
      {
        id: 'action:run-schedule',
        label: 'Run Scheduler now',
        action: async () => { try { await api.post('/run-schedule/', { clear_existing: true }) } finally { onClose() } }
      },
      {
        id: 'action:run-electives',
        label: 'Run Electives now',
        action: async () => { try { await api.post('/run-electives/', { theory_needed: 2, lab_needed: 1, clear_existing: true }) } finally { onClose() } }
      },
      {
        id: 'action:export',
        label: 'Export Timetable (Excel)',
        action: async () => {
          try {
            const res = await api.get('/export-timetable/', { responseType: 'blob' })
            const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'timetable.xlsx'
            document.body.appendChild(a)
            a.click()
            a.remove()
            URL.revokeObjectURL(url)
          } finally { onClose() }
        }
      },
    ]
    return [...nav, ...actions]
  }, [onClose, navigate])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return commands
    return commands.filter(c => c.label.toLowerCase().includes(q))
  }, [query, commands])

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Command Palette</DialogTitle>
      <DialogContent dividers>
        <Box sx={{ mb: 2 }}>
          <TextField
            autoFocus
            fullWidth
            size="small"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command… (e.g., Go to Planner)"
          />
        </Box>
        {filtered.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No results</Typography>
        ) : (
          <List dense disablePadding>
            {filtered.map((cmd) => (
              <ListItemButton key={cmd.id} onClick={() => cmd.action()} sx={{ borderRadius: 1 }}>
                {cmd.label}
              </ListItemButton>
            ))}
          </List>
        )}
        <Box sx={{ pt: 1 }}>
          <Typography variant="caption" color="text.secondary">Esc to close • Enter to run • Ctrl/Cmd+K to open</Typography>
        </Box>
      </DialogContent>
    </Dialog>
  )
}
