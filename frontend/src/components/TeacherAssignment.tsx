import React, { useState } from 'react';
import api from '../api/client';
import { toast } from '../utils/toast';
import Card from '@mui/material/Card';
import CardHeader from '@mui/material/CardHeader';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';

const TeacherAssignment: React.FC = () => {
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [assignResult, setAssignResult] = useState<any>(null);
  const [clearExisting, setClearExisting] = useState(true);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0]);
      setUploadResult(null);
      setAssignResult(null);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) {
      toast.error('No file selected', { description: 'Please select an Excel file first.' });
      return;
    }

    setUploading(true);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('teacher_file', uploadFile);
      formData.append('clear_existing', clearExisting.toString());

      const res = await api.post('/upload-teachers/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setUploadResult(res.data);
      toast.success('Teachers uploaded', {
        description: `${res.data.preferences_created} preferences created for ${res.data.teachers_created} teachers.`,
      });
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message || 'Upload failed';
      toast.error('Upload failed', { description: msg });
      setUploadResult({ error: msg });
    } finally {
      setUploading(false);
    }
  };

  const handleAssign = async () => {
    setAssigning(true);
    setAssignResult(null);

    try {
      const res = await api.post('/assign-teachers/', {
        clear_existing: false, // Don't clear existing, just fill unassigned slots
      });

      setAssignResult(res.data);
      
      if (res.data.status === 'ok') {
        toast.success('Teachers assigned', {
          description: `${res.data.assigned} slots assigned, ${res.data.unassigned} remain unassigned.`,
        });
      } else {
        toast.warning('Assignment incomplete', {
          description: res.data.message || 'Some slots could not be assigned.',
        });
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message || 'Assignment failed';
      toast.error('Assignment failed', { description: msg });
      setAssignResult({ error: msg });
    } finally {
      setAssigning(false);
    }
  };

  return (
    <Card elevation={2}>
      <CardHeader
        title={<Typography variant="subtitle1" fontWeight={700}>Teacher Assignment</Typography>}
      />
      <CardContent>
        <Stack spacing={3}>
          {/* Upload Section */}
          <Box>
            <Typography variant="body2" sx={{ mb: 2 }}>
              <strong>Step 1:</strong> Upload teacher preferences Excel file
            </Typography>
            <Typography variant="caption" sx={{ mb: 2, display: 'block', color: 'text.secondary' }}>
              Expected columns: Teacher Name, Course Code, Sections Count, Type
              <br />
              Course Code can be '*' for any course. Type can be 'Theory', 'Lab', or '*' for both.
            </Typography>
            
            <Stack direction="row" spacing={2} alignItems="center">
              <Button variant="outlined" component="label">
                Choose File
                <input type="file" accept=".xlsx,.xls" hidden onChange={handleFileChange} />
              </Button>
              {uploadFile && (
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {uploadFile.name}
                </Typography>
              )}
            </Stack>

            <FormControlLabel
              control={
                <Checkbox
                  checked={clearExisting}
                  onChange={(e) => setClearExisting(e.target.checked)}
                />
              }
              label="Clear existing teacher data"
              sx={{ mt: 1 }}
            />

            <Box sx={{ mt: 2 }}>
              <Button
                onClick={handleUpload}
                variant="contained"
                disabled={!uploadFile || uploading}
                fullWidth
              >
                {uploading ? 'Uploading...' : 'Upload Teachers'}
              </Button>
              {uploading && <LinearProgress sx={{ mt: 1 }} />}
            </Box>
          </Box>

          {/* Upload Result */}
          {uploadResult && (
            <Alert severity={uploadResult.error ? 'error' : 'success'}>
              <AlertTitle>{uploadResult.error ? 'Upload Error' : 'Upload Success'}</AlertTitle>
              {uploadResult.error ? (
                uploadResult.error
              ) : (
                <>
                  Teachers created: {uploadResult.teachers_created}
                  <br />
                  Preferences created: {uploadResult.preferences_created}
                </>
              )}
            </Alert>
          )}

          {/* Assign Section */}
          <Box>
            <Typography variant="body2" sx={{ mb: 2 }}>
              <strong>Step 2:</strong> Assign teachers to timetable slots
            </Typography>
            <Typography variant="caption" sx={{ mb: 2, display: 'block', color: 'text.secondary' }}>
              This will automatically assign uploaded teachers to available timetable slots based on their preferences.
            </Typography>
            
            <Button
              onClick={handleAssign}
              variant="contained"
              color="secondary"
              disabled={assigning}
              fullWidth
            >
              {assigning ? 'Assigning...' : 'Assign Teachers'}
            </Button>
            {assigning && <LinearProgress sx={{ mt: 1 }} />}
          </Box>

          {/* Assign Result */}
          {assignResult && (
            <Alert severity={assignResult.error ? 'error' : assignResult.status === 'ok' ? 'success' : 'warning'}>
              <AlertTitle>
                {assignResult.error ? 'Assignment Error' : assignResult.status === 'ok' ? 'Assignment Complete' : 'Assignment Status'}
              </AlertTitle>
              {assignResult.error ? (
                assignResult.error
              ) : (
                <>
                  {assignResult.message && <div>{assignResult.message}</div>}
                  {assignResult.assigned !== undefined && (
                    <>
                      Assigned: {assignResult.assigned} / {assignResult.total_slots}
                      <br />
                      Unassigned: {assignResult.unassigned}
                      {assignResult.warnings && assignResult.warnings.length > 0 && (
                        <>
                          <br />
                          <br />
                          <strong>Warnings:</strong>
                          <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                            {assignResult.warnings.map((w: string, i: number) => (
                              <li key={i}>{w}</li>
                            ))}
                          </ul>
                        </>
                      )}
                    </>
                  )}
                </>
              )}
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default TeacherAssignment;
