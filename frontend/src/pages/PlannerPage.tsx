import React from 'react'
import Planner from '../components/Planner'
import UploadExcel from '../components/UploadExcel'
import { Box, Typography } from '@mui/material'
import Grid from '@mui/material/GridLegacy'

export default function PlannerPage() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="h4" fontWeight={700} gutterBottom>Subject Planner</Typography>
        <Typography variant="body2" color="text.secondary">Upload the latest data and adjust capacity in one place.</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={12}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <UploadExcel />
            <Planner />
          </Box>
        </Grid>
      </Grid>
    </Box>
  )
}
