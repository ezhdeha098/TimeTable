import axios from 'axios';

// Use relative /api path which nginx will proxy to Django backend
const baseURL = '/api';

const api = axios.create({ baseURL });

export default api;
