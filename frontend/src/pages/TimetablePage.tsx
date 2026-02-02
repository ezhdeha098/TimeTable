import React from 'react'
import TimetableViewer from '../components/TimetableViewer'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

export default function TimetablePage() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="h4" fontWeight={700}>Timetable Viewer</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>View and export generated timetables</Typography>
      </Box>
      <TimetableViewer />
    </Box>
  )
}
