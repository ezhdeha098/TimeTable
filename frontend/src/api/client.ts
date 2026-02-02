import axios from 'axios';

// Prefer Vite proxy in dev; fall back to VITE_API_BASE for production builds
const baseURL = import.meta.env.VITE_API_BASE || '/api';

const api = axios.create({ baseURL });

export default api;
