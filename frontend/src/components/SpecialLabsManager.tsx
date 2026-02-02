import React, { useEffect, useMemo, useState } from 'react';
import api from '../api/client';
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'

interface SpecialLabItem { id: number; subject: number; room: number }
interface Subject { id: number; code: string; name: string }
interface Room { id: number; name: string; room_type: 'theory'|'lab' }

const SpecialLabsManager: React.FC = () => {
  const [items, setItems] = useState<SpecialLabItem[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [newCode, setNewCode] = useState('');
  const [newRooms, setNewRooms] = useState('');
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [sl, rs, ss] = await Promise.all([
        api.get('/special-labs/'),
        api.get('/rooms/'),
        api.get('/subjects/'),
      ]);
      setItems(sl.data as SpecialLabItem[]);
      setRooms(rs.data as Room[]);
      setSubjects(ss.data as Subject[]);
    } catch (e:any) { setError(e?.response?.data?.error || e.message); }
    finally { setLoading(false); }
  };
  useEffect(()=>{ load(); }, []);

  const byCode = useMemo(() => {
    const map: Record<string, {subjectId:number, roomIds:number[]}> = {};
    const subjById = Object.fromEntries(subjects.map(s=>[s.id, s]));
    items.forEach(it => {
      const subj = subjById[it.subject];
      if (!subj) return;
      if (!map[subj.code]) map[subj.code] = {subjectId: subj.id, roomIds: []};
      map[subj.code].roomIds.push(it.room);
    });
    return map;
  }, [items, subjects]);

  const removeSelected = async () => {
    setLoading(true); setError('');
    try {
      for (const code of selectedCodes) {
        const subj = subjects.find(s=>s.code===code);
        if (!subj) continue;
        for (const it of items) {
          if (it.subject === subj.id) {
            await api.delete(`/special-labs/${it.id}/`);
          }
        }
      }
      setSelectedCodes([]);
      await load();
    } catch (e:any) { setError(e?.response?.data?.error || e.message); }
    finally { setLoading(false); }
  };

  const ensureRoom = async (name: string) => {
    const exist = rooms.find(r=>r.name===name);
    if (exist) return exist;
    const res = await api.post('/rooms/', { name, room_type: 'lab', capacity: 30 });
    return res.data as Room;
  };

  const upsertSpecialLab = async () => {
    const code = newCode.trim();
    if (!code) return;
    const subj = subjects.find(s=>s.code===code);
    if (!subj) { setError(`Subject code '${code}' not found in backend.`); return; }
    setLoading(true); setError('');
    try {
      // delete old
      for (const it of items) {
        if (it.subject === subj.id) {
          await api.delete(`/special-labs/${it.id}/`);
        }
      }
      // create new for each room
      const roomsStr = newRooms.split(',').map(s=>s.trim()).filter(Boolean);
      for (const rn of roomsStr) {
        const room = await ensureRoom(rn);
        await api.post('/special-labs/', { subject: subj.id, room: room.id });
      }
      setNewCode(''); setNewRooms('');
      await load();
    } catch (e:any) { setError(e?.response?.data?.error || e.message); }
    finally { setLoading(false); }
  };

  return (
    <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle2" fontWeight={700}>Special Labs</Typography>} />
      <CardContent>
        <Stack spacing={2}>
          {error && <Typography variant="body2" color="error">{error}</Typography>}
          {loading && <Typography variant="body2">Working…</Typography>}
          <Box sx={{ maxHeight: 208, overflow: 'auto' }}>
            <Stack spacing={1}>
              {Object.entries(byCode).length===0 ? (
                <Typography variant="body2" color="text.secondary">No special labs configured.</Typography>
              ) : (
                Object.entries(byCode).map(([code, v]) => (
                  <Box key={code} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="body2"><strong>{code}</strong> → {v.roomIds.map(id => rooms.find(r=>r.id===id)?.name || id).filter(Boolean).join(', ')}</Typography>
                    <FormControlLabel control={<Checkbox checked={selectedCodes.includes(code)} onChange={(e)=>{
                      setSelectedCodes(prev => e.target.checked ? [...prev, code] : prev.filter(x=>x!==code));
                    }} />} label="" />
                  </Box>
                ))
              )}
            </Stack>
          </Box>
          <Box>
            <Button variant="outlined" onClick={removeSelected} disabled={!selectedCodes.length || loading}>Remove Selected</Button>
          </Box>
          <Stack direction="column" spacing={2} alignItems="stretch">
            <TextField
              label="Course code"
              placeholder="e.g., CS101"
              value={newCode}
              onChange={(e)=>setNewCode(e.target.value)}
              fullWidth
            />
            <TextField
              label="Rooms (comma separated)"
              placeholder="e.g., LAB-1, LAB-2"
              value={newRooms}
              onChange={(e)=>setNewRooms(e.target.value)}
              fullWidth
            />
            <Box>
              <Button
                variant="contained"
                size="large"
                onClick={upsertSpecialLab}
                disabled={loading}
                sx={{ whiteSpace: 'nowrap', flexShrink: 0, minWidth: 160 }}
              >
                Add/Update
              </Button>
            </Box>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default SpecialLabsManager;
