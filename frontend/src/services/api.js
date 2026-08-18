import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://10.104.1.89:5000',
  timeout: 5000
});

export const getSecurityEvents = () => api.get('/api/security-events', {
  params: { limit: 50, offset: 0 },
});
export const getResponseActions = () => api.get('/api/response-actions', {
  params: { limit: 50, offset: 0 },
});
export const getHealth = () => api.get('/api/health');
export const getSystemStatus = () => api.get('/api/system/status');

export default api;
