import React, { useState } from 'react';
import api from '../api/client';
import { toast } from '../utils/toast';
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import Typography from '@mui/material/Typography'
import Stack from '@mui/material/Stack'
import { getConstraints } from '../lib/constraints'

const RunSchedule: React.FC = () => {
  const [enableCohort, setEnableCohort] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");

  const run = async () => {
    setMessage("");
    try {
      const constraints = getConstraints()
      const res = await api.post('/run-schedule/', {
        // Let backend derive semesters, section sizes, and program from Excel-imported DB
        enable_cohort: enableCohort,
        clear_existing: true,
        constraints,
      });
      toast.success('Scheduler ran', { description: 'Timetable generated successfully.' })
      setMessage('OK: ' + JSON.stringify(res.data));
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message || 'Schedule failed';
      toast.error('Scheduler failed', { description: msg })
      setMessage('ERROR: ' + msg);
    }
  };

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Generate Timetable</Typography>} />
      <CardContent>
        <Stack spacing={2}>
          <FormControlLabel control={<Checkbox checked={enableCohort} onChange={(e)=>setEnableCohort(e.target.checked)} />} label="Enable cohort" />
          <Button onClick={run} variant="contained" size="large">Run Scheduler</Button>
          {message && <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{message}</Typography>}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default RunSchedule;
