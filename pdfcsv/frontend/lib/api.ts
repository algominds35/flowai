import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  console.log('API Request:', config.method?.toUpperCase(), config.url, token ? 'with token' : 'NO TOKEN');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (redirect to login)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: async (email: string, password: string, fullName?: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },

  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    const { access_token } = response.data;
    console.log('Login successful, saving token:', access_token ? 'YES' : 'NO');
    localStorage.setItem('access_token', access_token);
    console.log('Token saved to localStorage');
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// Documents API
export const documentsApi = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async (skip = 0, limit = 50) => {
    const response = await api.get('/documents/', {
      params: { skip, limit },
    });
    return response.data;
  },

  get: async (documentId: number) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  delete: async (documentId: number) => {
    await api.delete(`/documents/${documentId}`);
  },
};

// Transactions API
export const transactionsApi = {
  get: async (transactionId: number) => {
    const response = await api.get(`/transactions/${transactionId}`);
    return response.data;
  },

  update: async (transactionId: number, data: any) => {
    const response = await api.patch(`/transactions/${transactionId}`, data);
    return response.data;
  },

  delete: async (transactionId: number) => {
    await api.delete(`/transactions/${transactionId}`);
  },

  bulkUpdate: async (transactionIds: number[], updates: any) => {
    const response = await api.post('/transactions/bulk-update', {
      transaction_ids: transactionIds,
      ...updates,
    });
    return response.data;
  },
};
