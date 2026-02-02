import React, { useEffect, useMemo, useState } from 'react';
import api from '../api/client';
import RoomsManager from './RoomsManager';
import SpecialLabsManager from './SpecialLabsManager';
import Card from '@mui/material/Card'
import CardHeader from '@mui/material/CardHeader'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import Chip from '@mui/material/Chip'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import TextField from '@mui/material/TextField'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'

// Helper types
interface PlanSummary {
  selected_semesters: number[];
  theory_rooms: string[];
  lab_rooms: string[];
  special_lab_rooms: Record<string, string[]>;
  free_theory_per_room: Record<string, number>;
  free_lab_per_room: Record<string, number>;
  free_theory_cap: number;
  free_lab_cap: number;
  special_lab_capacities: Record<string, number>;
  total_special_lab_cap: number;
  needed: { theory: number; lab: number; special_lab: Record<string, number> };
  per_room_capacity: { theory: number; lab: number };
  min_rooms_suggestion: { theory: number; lab: number };
}

const Pill: React.FC<{ label: string; value?: string | number }> = ({ label, value }) => (
  <div style={{display:'inline-flex', alignItems:'center', padding:'6px 10px', border:'1px solid var(--mantine-color-gray-3)', borderRadius:20, marginRight:8, marginBottom:8, background:'var(--mantine-color-gray-0)'}}>
    <span style={{fontWeight:600, marginRight:6}}>{label}:</span>
    <span>{value}</span>
  </div>
);

const Planner: React.FC = () => {
  const [semesters, setSemesters] = useState<number[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [enableCohort, setEnableCohort] = useState<boolean>(false);
  const [includeExisting, setIncludeExisting] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [summary, setSummary] = useState<PlanSummary | null>(null);
  const [error, setError] = useState<string>('');
  const [presetName, setPresetName] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<string>('');

  type PlanPreset = { semesters: number[]; enableCohort: boolean; includeExisting: boolean };
  const PRESET_KEY = 'plan_presets_v1';
  function loadPresets(): Record<string, PlanPreset> {
    try { return JSON.parse(localStorage.getItem(PRESET_KEY) || '{}') } catch { return {} }
  }
  function savePresets(obj: Record<string, PlanPreset>) { localStorage.setItem(PRESET_KEY, JSON.stringify(obj)) }
  function savePreset() {
    const name = presetName.trim(); if (!name) return;
    const all = loadPresets();
    all[name] = { semesters: selected.slice(), enableCohort, includeExisting };
    savePresets(all); setSelectedPreset(name);
  }
  function applyPreset(name: string) {
    const all = loadPresets(); const p = all[name]; if (!p) return;
    setSelected(p.semesters); setEnableCohort(p.enableCohort); setIncludeExisting(p.includeExisting);
    fetchSummary();
  }
  function deletePreset(name: string) {
    const all = loadPresets(); if (!(name in all)) return;
    delete all[name]; savePresets(all); if (selectedPreset === name) setSelectedPreset('');
  }

  // Load semesters
  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/semesters/');
        const nums = (res.data as any[]).map((s: any) => s.number).sort((a:number,b:number)=>a-b);
        setSemesters(nums);
        setSelected(nums);
      } catch (e:any) {
        setError(e?.response?.data?.error || e.message);
      }
    })();
  }, []);

  const fetchSummary = async () => {
    setLoading(true); setError('');
    try {
      const qs = new URLSearchParams();
      if (selected.length) qs.set('selected_semesters', selected.join(','));
      if (enableCohort) qs.set('enable_cohort','true');
      if (!includeExisting) qs.set('include_existing','false');
      const res = await api.get(`/plan-summary/?${qs.toString()}`);
      setSummary(res.data as PlanSummary);
    } catch (e:any) {
      setError(e?.response?.data?.error || e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (semesters.length) { fetchSummary(); } }, [semesters]);

  const theoryRoomList = useMemo(() => Object.entries(summary?.free_theory_per_room || {}).sort((a,b)=>a[0].localeCompare(b[0])), [summary]);
  const labRoomList = useMemo(() => Object.entries(summary?.free_lab_per_room || {}).sort((a,b)=>a[0].localeCompare(b[0])), [summary]);

  return (
  <Card elevation={2}>
      <CardHeader title={<Typography variant="subtitle1" fontWeight={700}>Planning & Capacity</Typography>} />
      <CardContent>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
          <Box>
            <Stack spacing={1.5}>
              <FormControlLabel control={<Checkbox checked={enableCohort} onChange={(e)=>setEnableCohort(e.target.checked)} />} label="Include Cohort Courses" />
              <FormControlLabel control={<Checkbox checked={includeExisting} onChange={(e)=>setIncludeExisting(e.target.checked)} />} label="Use current allocations" />
              <Button variant="outlined" onClick={fetchSummary} disabled={loading}>Refresh Summary</Button>
              <Box>
                <Typography variant="subtitle2" fontWeight={700} gutterBottom>Presets</Typography>
                <Stack direction={{ xs:'column', sm:'row' }} spacing={2} alignItems="flex-end">
                  <TextField
                    label="Preset name"
                    placeholder="e.g., S1-4 Cohort"
                    value={presetName}
                    onChange={(e)=>setPresetName(e.target.value)}
                    sx={{ minWidth: 260 }}
                  />
                  <Button variant="contained" size="large" onClick={savePreset} disabled={!presetName.trim()}>Save</Button>
                </Stack>
                <Stack direction={{ xs:'column', sm:'row' }} spacing={2} alignItems="flex-end" sx={{ mt: 2 }}>
                  <FormControl sx={{ minWidth: 220 }} size="medium">
                    <InputLabel id="preset-select-label">Choose preset</InputLabel>
                    <Select
                      labelId="preset-select-label"
                      label="Choose preset"
                      value={selectedPreset}
                      onChange={(e)=>setSelectedPreset(e.target.value)}
                    >
                      <MenuItem value="">(none)</MenuItem>
                      {Object.keys(loadPresets()).map(name => (
                        <MenuItem key={name} value={name}>{name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Stack direction="row" spacing={1.5}>
                    <Button variant="outlined" size="large" onClick={()=>applyPreset(selectedPreset)} disabled={!selectedPreset}>Load</Button>
                    <Button variant="outlined" color="error" size="large" onClick={()=>{ deletePreset(selectedPreset); }} disabled={!selectedPreset}>Delete</Button>
                  </Stack>
                </Stack>
              </Box>
            </Stack>
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={700}>Semesters</Typography>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
              {semesters.map(s => {
                const checked = selected.includes(s)
                return (
                  <Chip
                    key={s}
                    label={`S${s}`}
                    color={checked ? 'primary' : 'default'}
                    variant={checked ? 'filled' : 'outlined'}
                    onClick={() => setSelected(prev => checked ? prev.filter(x=>x!==s) : Array.from(new Set([...prev, s])))}
                    clickable
                    sx={{ minWidth: 48 }}
                  />
                )
              })}
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ display:'block', mt: 1 }}>
              Selected: {selected.length ? selected.sort((a,b)=>a-b).map(s=>`S${s}`).join(', ') : 'None'}
            </Typography>
          </Box>
        </Box>

        {error && <Typography variant="body2" color="error" sx={{ mt: 1 }}>{error}</Typography>}
        {loading && <Typography variant="body2" sx={{ mt: 1 }}>Loading…</Typography>}

        {summary && (
          <Box sx={{ mt: 2 }}>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              <Pill label="Theory Needed" value={summary.needed.theory} />
              <Pill label="Lab Needed" value={summary.needed.lab} />
              <Pill label="Theory Free" value={summary.free_theory_cap} />
              <Pill label="Lab Free (normal)" value={summary.free_lab_cap} />
              <Pill label="Theory Capacity/Room" value={summary.per_room_capacity.theory} />
              <Pill label="Lab Capacity/Room" value={summary.per_room_capacity.lab} />
              <Pill label="Min Theory Rooms" value={summary.min_rooms_suggestion.theory} />
              <Pill label="Min Lab Rooms" value={summary.min_rooms_suggestion.lab} />
            </Stack>

            {Object.keys(summary.special_lab_rooms || {}).length > 0 && (
              <Box sx={{ mt: 1.5 }}>
                <Typography variant="subtitle2" fontWeight={700}>Special Lab Needs by Course</Typography>
                {Object.entries(summary.needed.special_lab).map(([code, need]) => (
                  <Typography key={code} variant="body2" sx={{ mb: 0.5 }}>
                    <strong>{code}</strong>: Needed {need}, Available {summary.special_lab_capacities[code] || 0}
                  </Typography>
                ))}
              </Box>
            )}

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2 }}>
              <Box>
                <Typography variant="subtitle2" fontWeight={700}>Theory Rooms (free slots)</Typography>
                <Box component="ul" sx={{ pl: 3, m: 0 }}>
                  {theoryRoomList.map(([name, free]) => (
                    <li key={name}><Typography variant="body2">{name}: {free}</Typography></li>
                  ))}
                </Box>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight={700}>Lab Rooms (free slots)</Typography>
                <Box component="ul" sx={{ pl: 3, m: 0 }}>
                  {labRoomList.map(([name, free]) => (
                    <li key={name}><Typography variant="body2">{name}: {free}</Typography></li>
                  ))}
                </Box>
              </Box>
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2 }}>
              <RoomsManager />
              <SpecialLabsManager />
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default Planner;
