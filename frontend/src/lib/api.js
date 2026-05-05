import axios from 'axios';

/** Dev uses Vite proxy (/api → backend). Production: set VITE_API_BASE_URL at build time. */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? '/api' : 'http://127.0.0.1:8000/api');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const medicineApi = {
  search: async (query) => {
    const response = await api.get(`/medicine/search?q=${encodeURIComponent(query)}`);
    return response.data;
  },
  
  scan: async (imageFile) => {
    const formData = new FormData();
    formData.append('file', imageFile);
    
    const response = await api.post('/medicine/scan', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  getDetails: async (drugId) => {
    const response = await api.get(`/medicine/${drugId}`);
    return response.data;
  },
  
  getAlternatives: async (drugId) => {
    const response = await api.get(`/medicine/${drugId}/alternatives`);
    return response.data;
  },
  
  checkInteractions: async (drugId1, drugId2) => {
    const response = await api.get(`/medicine/interactions/${drugId1}/${drugId2}`);
    return response.data;
  }
};

export const chatApi = {
  sendMessage: async (message, sessionId = null) => {
    const response = await api.post('/chat/message', {
      message,
      session_id: sessionId,
    });
    return response.data;
  },
  
  getHistory: async (sessionId) => {
    const response = await api.get(`/chat/history/${sessionId}`);
    return response.data;
  },
  
  getSessions: async () => {
    const response = await api.get('/chat/sessions');
    return response.data;
  }
};
