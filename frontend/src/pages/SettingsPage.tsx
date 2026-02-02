import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Grid from '@mui/material/Grid'
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import StorageIcon from '@mui/icons-material/Storage'
import PeopleIcon from '@mui/icons-material/People'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import PaletteIcon from '@mui/icons-material/Palette'

export default function SettingsPage() {
  const tiles = [
    { icon: <StorageIcon fontSize="small" color="primary" />, title: 'Database', subtitle: 'Active' },
    { icon: <PeopleIcon fontSize="small" color="success" />, title: 'Users', subtitle: 'Manage access' },
    { icon: <AccessTimeIcon fontSize="small" color="secondary" />, title: 'Schedule', subtitle: 'Time config' },
    { icon: <PaletteIcon fontSize="small" color="warning" />, title: 'Theme', subtitle: 'Appearance' },
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="h4" fontWeight={700}>Settings</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Configure system preferences and manage resources</Typography>
      </Box>

      <Grid container spacing={2} alignItems="stretch">
        {tiles.map((t) => (
          <Grid size={{ xs: 12, md: 6, lg: 3 }} key={t.title}>
            <Card elevation={2} sx={{ minHeight: 120 }}>
              <CardHeader
                sx={{ py: 2 }}
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.75 }}>
                    <Box sx={{ p: 1.25, borderRadius: 2, bgcolor: 'action.hover', display: 'inline-flex' }}>
                      {t.icon}
                    </Box>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="subtitle1" fontWeight={700} sx={{ lineHeight: 1.2 }}>{t.title}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25, whiteSpace: 'normal' }}>{t.subtitle}</Typography>
                    </Box>
                  </Box>
                }
              />
            </Card>
          </Grid>
        ))}
      </Grid>
  {/* Constraints moved to Schedule page */}
    </Box>
  )
}
