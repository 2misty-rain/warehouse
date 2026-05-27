import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Request interceptor - attach JWT token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// Response interceptor - handle auth errors
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      if (window.location.hash !== '#/login') {
        window.location.reload();
      }
    }
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ========== Auth ==========
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  getUsers: () => api.get('/auth/users'),
  changePassword: (data) => api.put('/auth/change-password', data),
  updateUser: (id, data) => api.put(`/auth/users/${id}`, data),
};

// ========== Inventory ==========
export const inventoryAPI = {
  getAll: (params = {}) => api.get('/inventory', { params }),
  getById: (id) => api.get(`/inventory/${id}`),
  getDetail: (id) => api.get(`/inventory/${id}/detail`),
  getTimeline: (id) => api.get(`/inventory/${id}/timeline`),
  create: (data) => api.post('/inventory', data),
  update: (id, data) => api.put(`/inventory/${id}`, data),
  delete: (id) => api.delete(`/inventory/${id}`),
  updateIoTCard: (deviceId, status) => api.put(`/inventory/${deviceId}/iot-card`, { device_id: deviceId, iot_card_status: status }),
  batchUpdateIoTCard: (deviceIds, status) => api.post('/inventory/batch/iot-card', { device_ids: deviceIds, iot_card_status: status }),
  getOwners: () => api.get('/inventory/owners'),
  importCSV: (formData) => api.post('/inventory/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  batchDelete: (deviceIds) => api.post('/inventory/batch/delete', { device_ids: deviceIds }),
  batchUpdate: (deviceIds, updateData) => api.post('/inventory/batch/update', { device_ids: deviceIds, ...updateData }),
  downloadTemplate: () => api.get('/inventory/import/template', { responseType: 'blob' }).then(r => r.data),
  exportCSV: (params = {}) => api.get('/inventory/export/stream', { params, responseType: 'blob' }).then(r => r.data),
};

// ========== Reminders ==========
export const reminderAPI = {
  getAll: (params = {}) => api.get('/reminders', { params }),
  create: (data) => api.post('/reminders', data),
  update: (id, isProcessed) => api.put(`/reminders/${id}?is_processed=${isProcessed}`),
  delete: (id) => api.delete(`/reminders/${id}`)
};

// ========== AI ==========
export const aiAPI = {
  chat: (data) => api.post('/ai/chat', data, { timeout: 60000 }),
  getSuggestions: () => api.get('/ai/suggestions'),
  clearHistory: () => api.post('/ai/clear-history'),
};

// ========== Dashboard ==========
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
  getSalesTrend: () => api.get('/dashboard/sales')
};

// ========== Borrow ==========
export const borrowAPI = {
  borrow: (data) => api.post('/borrow', data),
  getList: (params = {}) => api.get('/borrow', { params }),
  getById: (id) => api.get(`/borrow/${id}`),
  delete: (id) => api.delete(`/borrow/${id}`),
  return: (id, data) => api.post(`/borrow/${id}/return`, data),
  getOverdue: () => api.get('/borrow/overdue/list')
};

// ========== Reservation ==========
export const reservationAPI = {
  create: (data) => api.post('/reservation', data),
  getList: (params = {}) => api.get('/reservation', { params }),
  getById: (id) => api.get(`/reservation/${id}`),
  approve: (id, data) => api.post(`/reservation/${id}/approve`, data),
  reject: (id, data) => api.post(`/reservation/${id}/reject`, data),
  getPendingCount: () => api.get('/reservation/pending-count'),
};

// ========== Analysis ==========
export const analysisAPI = {
  getWeeklyReport: () => api.get('/analysis/weekly-report'),
  getMonthlyReport: () => api.get('/analysis/monthly-report'),
  getSalesAnalysis: () => api.get('/analysis/sales-analysis'),
  query: (data) => api.post('/analysis/query', data),
};

// ========== Operation Logs ==========
export const operationLogAPI = {
  getList: (params = {}) => api.get('/operation-logs', { params }),
};

export default api;
