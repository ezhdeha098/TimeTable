import React, { useState } from 'react';
import api from '../api/client';
import type { AxiosProgressEvent } from 'axios';
import { toast } from '../utils/toast';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Box,
  Stack,
  Button,
  LinearProgress,
} from '@mui/material'
import UploadIcon from '@mui/icons-material/Upload'
import DescriptionIcon from '@mui/icons-material/Description'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import { getConstraints } from '../lib/constraints'

const UploadExcel: React.FC = () => {
  const [mainFile, setMainFile] = useState<File | null>(null);
  const [cohortFile, setCohortFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>("");
  const [uploading, setUploading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    setProgress(0);
    if (!mainFile) { 
      toast.error('No file selected', { description: 'Please select a main Excel file.' })
      setMessage('Please select a main Excel file.'); 
      return; 
    }
    setUploading(true);
    const fd = new FormData();
    fd.append('main_file', mainFile);
    if (cohortFile) fd.append('cohort_file', cohortFile);
    try {
      const res = await api.post('/upload-excel/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (evt: AxiosProgressEvent) => {
          if (evt.total) setProgress(Math.round(((evt.loaded || 0) / evt.total) * 100));
        }
      });
  const okMsg = res.data?.message || 'Upload succeeded.'
  toast.success(okMsg, { description: 'Upload complete' })
      setMessage(okMsg + ' Running scheduler…');
      // Auto-run main scheduler with DB-derived inputs
      const constraints = getConstraints();
    try {
        const runRes = await api.post('/run-schedule/', { clear_existing: true, constraints });
  toast.success('Schedule started', { description: 'The scheduler ran successfully.' })
        setMessage((prev: string) => (prev ? prev + "\n" : "") + 'Schedule: ' + JSON.stringify(runRes.data));
      } catch (e: any) {
  const errMsg = e?.response?.data?.error || e.message
  toast.error('Schedule failed', { description: errMsg })
        setMessage((prev: string) => (prev ? prev + "\n" : "") + 'Schedule ERROR: ' + errMsg);
      }
    } catch (err: any) {
  const msg = err?.response?.data?.error || err.message || 'Upload failed';
  toast.error('Upload failed', { description: msg })
      setMessage('ERROR: ' + msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card elevation={2}>
      <CardHeader
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'primary.main', color: '#fff', display: 'inline-flex' }}>
              <UploadIcon fontSize="small" />
            </Box>
            <Typography variant="subtitle1" fontWeight={700}>Upload Excel Files</Typography>
          </Box>
        }
        subheader={<Typography variant="caption" color="text.secondary">Import your timetable data to begin scheduling</Typography>}
      />
      <CardContent>
        <Box component="form" onSubmit={onSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Stack spacing={1}>
            <Typography variant="body2" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DescriptionIcon fontSize="small" color="primary" /> Main Excel File
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Button variant="outlined" component="label" startIcon={<UploadIcon />} disabled={uploading}>
                Choose file
                <input hidden type="file" accept=".xlsx,.xls" onChange={(e) => setMainFile(e.target.files?.[0] ?? null)} />
              </Button>
              {mainFile && (
                <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }} color="text.secondary">
                  <CheckCircleIcon color="success" fontSize="small" /> {mainFile.name} ({(mainFile.size / 1024).toFixed(1)} KB)
                </Typography>
              )}
            </Box>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="body2" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DescriptionIcon fontSize="small" color="disabled" /> Cohort Excel File <Typography component="span" variant="caption" color="text.secondary">(optional)</Typography>
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Button variant="outlined" component="label" startIcon={<UploadIcon />} disabled={uploading}>
                Choose file
                <input hidden type="file" accept=".xlsx,.xls" onChange={(e) => setCohortFile(e.target.files?.[0] ?? null)} />
              </Button>
              {cohortFile && (
                <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }} color="text.secondary">
                  <CheckCircleIcon color="success" fontSize="small" /> {cohortFile.name} ({(cohortFile.size / 1024).toFixed(1)} KB)
                </Typography>
              )}
            </Box>
          </Stack>

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, pt: 1 }}>
            <Button type="submit" disabled={!mainFile || uploading} variant="contained" size="large" startIcon={<UploadIcon />}>
              {uploading ? 'Uploading...' : 'Upload & Process'}
            </Button>
            {progress > 0 && progress < 100 && (
              <Box sx={{ flex: 1, minWidth: 220, maxWidth: 360 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" color="primary" fontWeight={700}>Uploading…</Typography>
                  <Typography variant="caption" color="primary" fontWeight={700}>{progress}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 5 }} />
              </Box>
            )}
          </Box>
        </Box>
        {message && (
          <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap', mt: 2 }}>{message}</Typography>
        )}
      </CardContent>
    </Card>
  );
}

export default UploadExcel;
