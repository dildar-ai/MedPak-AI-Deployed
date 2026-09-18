import axios from 'axios';

/** Dev uses the Vite proxy (/api → backend). Production builds default to
 *  same-origin /api so the self-hosted app works behind any host or tunnel;
 *  set VITE_API_BASE_URL only when the API lives on a different origin
 *  (e.g. Vercel frontend + hosted API). */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

// ── Auth storage ─────────────────────────────────────────────────────────────

const TOKEN_KEY = 'medpak_token';
const USER_KEY = 'medpak_user';

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser: () => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  },
  set: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

// ── Axios instance ───────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    // ngrok's free tier serves an interstitial warning page for browser
    // traffic unless requests carry this header — API calls through the
    // tunnel would otherwise receive HTML instead of JSON.
    'ngrok-skip-browser-warning': 'true',
  },
});

// Attach the JWT to every request when signed in
api.interceptors.request.use((config) => {
  const token = authStorage.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401 (expired/invalid token) — drop credentials and tell the app to show
// the login screen. A 401 from /auth/login itself means wrong credentials and
// must NOT trigger the logout flow.
// Also show user-friendly toast notifications for common error types.
import { toast } from '../components/Toast';

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';

    if (status === 401 && !url.startsWith('/auth/')) {
      authStorage.clear();
      window.dispatchEvent(new Event('medpak:unauthorized'));
    } else if (status === 429) {
      toast.error('Too many requests — please slow down and try again in a minute.');
    } else if (status >= 500) {
      toast.error('Server error — please try again in a moment.');
    } else if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      toast.error('Request timed out — the server may be busy. Try again.');
    } else if (!error.response) {
      toast.error('Network error — please check your internet connection.');
    }

    return Promise.reject(error);
  }
);

// ── Auth API ─────────────────────────────────────────────────────────────────

export const authApi = {
  register: async (email, username, password) => {
    const response = await api.post('/auth/register', { email, username, password });
    return response.data;
  },

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },

  me: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// ── Medicine API ─────────────────────────────────────────────────────────────

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
      timeout: 60000,
    });
    return response.data;
  },

  getDetails: async (drugId, brandName = null) => {
    const url = brandName
      ? `/medicine/${drugId}?brand=${encodeURIComponent(brandName)}`
      : `/medicine/${drugId}`;
    const response = await api.get(url);
    return response.data;
  },

  getAlternatives: async (drugId, brandName = null, form = null, strength = null) => {
    let url = `/medicine/${drugId}/alternatives`;
    const params = [];
    if (brandName) params.push(`brand=${encodeURIComponent(brandName)}`);
    if (form) params.push(`form=${encodeURIComponent(form)}`);
    if (strength) params.push(`strength=${encodeURIComponent(strength)}`);
    if (params.length) url += `?${params.join('&')}`;
    const response = await api.get(url);
    return response.data;
  },

  checkInteractions: async (drugId1, drugId2) => {
    const response = await api.get(`/medicine/interactions/${drugId1}/${drugId2}`);
    return response.data;
  },

  chat: async (message, drugId, sessionId = null) => {
    const response = await api.post('/medicine/chat', {
      message,
      drug_id: drugId,
      session_id: sessionId,
    }, { timeout: 60000 });
    return response.data;
  },

  getLivePrice: async (brand, strength = null, form = null) => {
    const response = await api.get('/medicine/live-price', {
      params: { brand, strength, form },
    });
    return response.data;
  },

  refreshPrices: async (brandName, strength = null) => {
    const response = await api.post('/medicine/prices/refresh', {
      brand: brandName,
      ...(strength ? { strength } : {}),
    });
    return response.data;
  },
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
