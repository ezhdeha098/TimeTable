import React, { useEffect, useState } from 'react'
import { toast } from '../utils/toast'
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import Grid from '@mui/material/Grid'
import { DEFAULT_CONSTRAINTS, getConstraints, saveConstraints, type Constraints } from '../lib/constraints'

const ConstraintsManager: React.FC = () => {
  const [c, setC] = useState<Constraints>(DEFAULT_CONSTRAINTS)

  useEffect(() => {
    setC(getConstraints())
  }, [])

  const onSave = () => {
    saveConstraints(c)
    toast.success('Constraints saved', { description: 'Scheduler will use these values.' })
  }

  const onReset = () => {
    setC(DEFAULT_CONSTRAINTS)
    saveConstraints(DEFAULT_CONSTRAINTS)
    toast.success('Constraints reset')
  }

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Scheduling Constraints</Typography>} />
      <CardContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Tune limits and rules the scheduler must respect. Values save locally and are sent when you run the scheduler.
        </Typography>
        <Grid container spacing={3} alignItems="flex-start">
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              type="number"
              label="Max hours per day"
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: 1, max: 12 }}
              value={c.maxHoursPerDay}
              onChange={(e) => setC(prev => ({ ...prev, maxHoursPerDay: Number((e.target as HTMLInputElement).value || 0) }))}
              helperText="1–12 hours"
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              type="number"
              label="Max labs per day"
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: 0, max: 4 }}
              value={c.maxLabsPerDay}
              onChange={(e) => setC(prev => ({ ...prev, maxLabsPerDay: Number((e.target as HTMLInputElement).value || 0) }))}
              helperText="0–4 labs"
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              type="number"
              label="Min gap (mins)"
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: 0, step: 5 }}
              value={c.minGapMinutes}
              onChange={(e) => setC(prev => ({ ...prev, minGapMinutes: Number((e.target as HTMLInputElement).value || 0) }))}
              helperText="Minutes between classes"
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              type="number"
              label="Working days/week"
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: 1, max: 7 }}
              value={c.workingDaysPerWeek}
              onChange={(e) => setC(prev => ({ ...prev, workingDaysPerWeek: Number((e.target as HTMLInputElement).value || 0) }))}
              helperText="1–7 days"
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              type="number"
              label="Earliest start (hour)"
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: 6, max: 12 }}
              value={c.earliestStartHour}
              onChange={(e) => setC(prev => ({ ...prev, earliestStartHour: Number((e.target as HTMLInputElement).value || 0) }))}
              helperText="24h, e.g., 8"
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              type="number"
              label="No classes after (hour)"
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: 12, max: 22 }}
              value={c.noClassesAfterHour}
              onChange={(e) => setC(prev => ({ ...prev, noClassesAfterHour: Number((e.target as HTMLInputElement).value || 0) }))}
              helperText="24h, e.g., 18"
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 6 }}>
            <FormControlLabel
              control={<Checkbox checked={c.allowConsecutiveLabs} onChange={(e) => setC(prev => ({ ...prev, allowConsecutiveLabs: e.target.checked }))} />}
              label={<Typography variant="body1">Allow consecutive labs</Typography>}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 6 }}>
            <FormControlLabel
              control={<Checkbox checked={c.allowSameSubjectTwicePerDay} onChange={(e) => setC(prev => ({ ...prev, allowSameSubjectTwicePerDay: e.target.checked }))} />}
              label={<Typography variant="body1">Allow same subject twice/day</Typography>}
            />
          </Grid>
        </Grid>
        <Box sx={{ display: 'flex', gap: 1.5, mt: 3, flexWrap: 'wrap' }}>
          <Button variant="contained" size="large" onClick={onSave}>Save Constraints</Button>
          <Button variant="outlined" color="inherit" onClick={onReset}>Reset</Button>
        </Box>
      </CardContent>
    </Card>
  )
}

export default ConstraintsManager
 
