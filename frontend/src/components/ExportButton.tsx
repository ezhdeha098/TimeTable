import React from 'react';
import api from '../api/client';
import { toast } from '../utils/toast';
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import DownloadIcon from '@mui/icons-material/Download'
import Typography from '@mui/material/Typography'

const ExportButton: React.FC = () => {
  const download = async () => {
    try {
      toast.message('Exporting…', { description: 'Preparing Excel download' })
      const res = await api.get('/export-timetable/', { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'timetable.xlsx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message || 'Export failed'
      toast.error('Export failed', { description: msg })
    }
  };

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Export Timetable</Typography>} />
      <CardContent>
        <Button onClick={download} variant="contained" size="large" startIcon={<DownloadIcon />}>
          Download Excel
        </Button>
      </CardContent>
    </Card>
  );
};

export default ExportButton;
