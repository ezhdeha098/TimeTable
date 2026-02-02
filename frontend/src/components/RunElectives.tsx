import React, { useState } from 'react';
import api from '../api/client';
import { toast } from '../utils/toast';
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import Stack from '@mui/material/Stack'

const RunElectives: React.FC = () => {
  const [theoryNeeded, setTheoryNeeded] = useState<number>(2);
  const [labNeeded, setLabNeeded] = useState<number>(1);
  const [message, setMessage] = useState<string>("");

  const run = async () => {
    setMessage("");
    try {
      const res = await api.post('/run-electives/', {
        theory_needed: theoryNeeded,
        lab_needed: labNeeded,
        clear_existing: true
      });
      toast.success('Electives scheduled', { description: 'Electives allocation succeeded.' })
      setMessage('OK: ' + JSON.stringify(res.data));
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message || 'Electives failed';
      toast.error('Electives failed', { description: msg })
      setMessage('ERROR: ' + msg);
    }
  };

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Run Electives</Typography>} />
      <CardContent>
        <Stack spacing={2}>
          <TextField type="number" label="Theory needed" inputProps={{ min: 0 }} value={theoryNeeded}
            onChange={(e)=>setTheoryNeeded(Number((e.target as HTMLInputElement).value || 0))} sx={{ maxWidth: 320 }} />
          <TextField type="number" label="Lab needed" inputProps={{ min: 0 }} value={labNeeded}
            onChange={(e)=>setLabNeeded(Number((e.target as HTMLInputElement).value || 0))} sx={{ maxWidth: 320 }} />
          <Button onClick={run} variant="contained" size="large">Run Electives</Button>
          {message && <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{message}</Typography>}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default RunElectives;
