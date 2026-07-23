import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://10.104.1.89:5000',
  timeout: 5000
});

export default api;
