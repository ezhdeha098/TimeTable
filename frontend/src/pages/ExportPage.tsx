import React from 'react'
import ExportButton from '../components/ExportButton'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Grid from '@mui/material/GridLegacy'
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import DescriptionIcon from '@mui/icons-material/Description'
import TableChartIcon from '@mui/icons-material/TableChart'
import DataObjectIcon from '@mui/icons-material/DataObject'

export default function ExportPage() {
  const tiles = [
    { icon: <TableChartIcon color="success" />, title: 'Excel Format', subtitle: 'Pivot table export' },
    { icon: <DescriptionIcon color="primary" />, title: 'CSV Format', subtitle: 'Raw data export' },
    { icon: <DataObjectIcon color="secondary" />, title: 'JSON Format', subtitle: 'API data export' },
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="h4" fontWeight={700}>Export Data</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Download timetables and schedules in various formats</Typography>
      </Box>

      <Grid container spacing={2}>
        {tiles.map(t => (
          <Grid item xs={12} md={4} key={t.title}>
            <Card elevation={2}>
              <CardHeader title={
                <Box sx={{ display:'flex', alignItems:'center', gap: 1.5 }}>
                  <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'action.hover', display: 'inline-flex' }}>{t.icon}</Box>
                  <Box>
                    <Typography variant="subtitle1" fontWeight={700}>{t.title}</Typography>
                    <Typography variant="caption" color="text.secondary">{t.subtitle}</Typography>
                  </Box>
                </Box>
              } />
            </Card>
          </Grid>
        ))}
      </Grid>

      <ExportButton />
    </Box>
  )
}
