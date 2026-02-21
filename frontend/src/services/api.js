import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem('cap_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Dashboard Stats
export const getDashboardStats = async () => {
  const response = await axios.get(`${API}/stats/dashboard`, { headers: getAuthHeaders() });
  return response.data;
};

// Participants
export const getParticipants = async () => {
  const response = await axios.get(`${API}/participants`, { headers: getAuthHeaders() });
  return response.data;
};

export const getParticipant = async (id) => {
  const response = await axios.get(`${API}/participants/${id}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createParticipant = async (data) => {
  const response = await axios.post(`${API}/participants`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateParticipant = async (id, data) => {
  const response = await axios.put(`${API}/participants/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteParticipant = async (id) => {
  const response = await axios.delete(`${API}/participants/${id}`, { headers: getAuthHeaders() });
  return response.data;
};

export const importParticipants = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API}/participants/import`, formData, {
    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// Schedule
export const getSchedule = async () => {
  const response = await axios.get(`${API}/schedule`, { headers: getAuthHeaders() });
  return response.data;
};

export const createScheduleEvent = async (data) => {
  const response = await axios.post(`${API}/schedule`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateScheduleEvent = async (id, data) => {
  const response = await axios.put(`${API}/schedule/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteScheduleEvent = async (id) => {
  const response = await axios.delete(`${API}/schedule/${id}`, { headers: getAuthHeaders() });
  return response.data;
};

// Budget
export const getBudget = async () => {
  const response = await axios.get(`${API}/budget`, { headers: getAuthHeaders() });
  return response.data;
};

export const getBudgetSummary = async () => {
  const response = await axios.get(`${API}/budget/summary`, { headers: getAuthHeaders() });
  return response.data;
};

export const createBudgetItem = async (data) => {
  const response = await axios.post(`${API}/budget`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateBudgetItem = async (id, data) => {
  const response = await axios.put(`${API}/budget/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteBudgetItem = async (id) => {
  const response = await axios.delete(`${API}/budget/${id}`, { headers: getAuthHeaders() });
  return response.data;
};

export const importBudget = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API}/budget/import`, formData, {
    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// Documents
export const getDocuments = async () => {
  const response = await axios.get(`${API}/documents`, { headers: getAuthHeaders() });
  return response.data;
};

export const getDocument = async (id) => {
  const response = await axios.get(`${API}/documents/${id}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createDocument = async (data) => {
  const response = await axios.post(`${API}/documents`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateDocument = async (id, data) => {
  const response = await axios.put(`${API}/documents/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteDocument = async (id) => {
  const response = await axios.delete(`${API}/documents/${id}`, { headers: getAuthHeaders() });
  return response.data;
};

// Users
export const getUsers = async () => {
  const response = await axios.get(`${API}/users`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateUserRole = async (userId, role) => {
  const response = await axios.put(`${API}/users/${userId}/role?role=${role}`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteUser = async (userId) => {
  const response = await axios.delete(`${API}/users/${userId}`, { headers: getAuthHeaders() });
  return response.data;
};
