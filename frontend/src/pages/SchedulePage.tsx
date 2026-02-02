import React from 'react'
import RunSchedule from '../components/RunSchedule'
import RunElectives from '../components/RunElectives'
import ConstraintsManager from '../components/ConstraintsManager'
import TeacherAssignment from '../components/TeacherAssignment'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Stack from '@mui/material/Stack'

export default function SchedulePage() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="h4" fontWeight={700}>Schedule Management</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Generate and manage course schedules</Typography>
      </Box>
      <Stack spacing={3}>
        <ConstraintsManager />
        <RunSchedule />
        <RunElectives />
        <TeacherAssignment />
      </Stack>
    </Box>
  )
}
