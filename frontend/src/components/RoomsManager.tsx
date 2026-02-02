import React, { useEffect, useState } from 'react';
import api from '../api/client';
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import Checkbox from '@mui/material/Checkbox'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import Grid from '@mui/material/GridLegacy'

interface Room { id: number; name: string; room_type: 'theory'|'lab'; capacity: number }

const RoomsManager: React.FC = () => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState<'theory'|'lab'>('theory');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.get('/rooms/');
      setRooms(res.data as Room[]);
    } catch (e:any) { setError(e?.response?.data?.error || e.message); }
    finally { setLoading(false); }
  };
  useEffect(()=>{ load(); },[]);

  const removeSelected = async () => {
    setLoading(true); setError('');
    try {
      for (const id of selected) {
        await api.delete(`/rooms/${id}/`);
      }
      setSelected([]);
      await load();
    } catch (e:any) { setError(e?.response?.data?.error || e.message); }
    finally { setLoading(false); }
  };

  const addRoom = async () => {
    if (!newName.trim()) return;
    setLoading(true); setError('');
    try {
      await api.post('/rooms/', { name: newName.trim(), room_type: newType, capacity: 30 });
      setNewName('');
      await load();
    } catch (e:any) { setError(e?.response?.data?.error || e.message); }
    finally { setLoading(false); }
  };

  const theory = rooms.filter(r=>r.room_type==='theory').sort((a,b)=>a.name.localeCompare(b.name));
  const labs = rooms.filter(r=>r.room_type==='lab').sort((a,b)=>a.name.localeCompare(b.name));

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Manage Rooms</Typography>} />
      <CardContent>
        <Stack spacing={2}>
          {error && (
            <Typography variant="body2" color="error">{error}</Typography>
          )}

          <Grid container spacing={3} alignItems="flex-start">
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                Theory
              </Typography>
              <Box sx={{ maxHeight: 220, overflow: 'auto', pr: 1 }}>
                <List>
                  {theory.map((r) => {
                    const checked = selected.includes(r.id)
                    return (
                      <ListItem key={r.id} disableGutters secondaryAction={
                        <Checkbox edge="end" checked={checked} onChange={(e)=>{
                          setSelected(prev => e.target.checked ? [...prev, r.id] : prev.filter(x=>x!==r.id));
                        }} />
                      }>
                        <ListItemText primary={r.name} />
                      </ListItem>
                    )
                  })}
                </List>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                Lab
              </Typography>
              <Box sx={{ maxHeight: 220, overflow: 'auto', pr: 1 }}>
                <List>
                  {labs.map((r) => {
                    const checked = selected.includes(r.id)
                    return (
                      <ListItem key={r.id} disableGutters secondaryAction={
                        <Checkbox edge="end" checked={checked} onChange={(e)=>{
                          setSelected(prev => e.target.checked ? [...prev, r.id] : prev.filter(x=>x!==r.id));
                        }} />
                      }>
                        <ListItemText primary={r.name} />
                      </ListItem>
                    )
                  })}
                </List>
              </Box>
            </Grid>
          </Grid>

          <Box>
            <Button variant="outlined" size="large" onClick={removeSelected} disabled={!selected.length || loading}>
              Remove Selected
            </Button>
          </Box>

          <Grid container spacing={2} alignItems="flex-end">
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="New room name" placeholder="e.g., C-101" value={newName} onChange={(e)=>setNewName(e.target.value)} disabled={loading} />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth>
                <InputLabel id="room-type-label">Type</InputLabel>
                <Select
                  labelId="room-type-label"
                  label="Type"
                  value={newType}
                  onChange={(e)=>setNewType(e.target.value as 'theory'|'lab')}
                >
                  <MenuItem value="theory">Theory</MenuItem>
                  <MenuItem value="lab">Lab</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Button variant="contained" size="large" onClick={addRoom} disabled={loading}>Add Room</Button>
            </Grid>
          </Grid>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default RoomsManager;
