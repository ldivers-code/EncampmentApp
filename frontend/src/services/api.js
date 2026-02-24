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

export const removeParticipantFromEncampment = async (participantId, removalReason) => {
  const response = await axios.post(
    `${API}/participants/${participantId}/remove`,
    { removal_reason: removalReason },
    { headers: getAuthHeaders() }
  );
  return response.data;
};

export const reinstateParticipant = async (participantId) => {
  const response = await axios.post(
    `${API}/participants/${participantId}/reinstate`,
    {},
    { headers: getAuthHeaders() }
  );
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

export const getParticipantStats = async () => {
  const response = await axios.get(`${API}/participants/stats`, { headers: getAuthHeaders() });
  return response.data;
};

export const getDetailedAnalytics = async () => {
  const response = await axios.get(`${API}/participants/analytics/detailed`, { headers: getAuthHeaders() });
  return response.data;
};

export const getPendingPayments = async () => {
  const response = await axios.get(`${API}/participants/pending-payments`, { headers: getAuthHeaders() });
  return response.data;
};

export const exportAnalytics = async (format = 'csv') => {
  const response = await axios.get(`${API}/participants/analytics/export?format=${format}`, {
    headers: getAuthHeaders(),
    responseType: 'blob'
  });
  return response;
};

export const exportAnalyticsSummary = async () => {
  const response = await axios.get(`${API}/participants/analytics/summary-export`, {
    headers: getAuthHeaders(),
    responseType: 'blob'
  });
  return response;
};

export const syncRosterToBudget = async () => {
  const response = await axios.post(`${API}/participants/sync-to-budget`, {}, { headers: getAuthHeaders() });
  return response.data;
};

// Push Notifications
export const getVapidKey = async () => {
  const response = await axios.get(`${API}/notifications/vapid-key`);
  return response.data;
};

export const subscribeToNotifications = async (subscription) => {
  const response = await axios.post(`${API}/notifications/subscribe`, subscription, { headers: getAuthHeaders() });
  return response.data;
};

export const unsubscribeFromNotifications = async () => {
  const response = await axios.delete(`${API}/notifications/unsubscribe`, { headers: getAuthHeaders() });
  return response.data;
};

export const getNotificationStatus = async () => {
  const response = await axios.get(`${API}/notifications/status`, { headers: getAuthHeaders() });
  return response.data;
};

export const sendNotification = async (title, body, targetGroups = ['all'], url = '/schedule') => {
  const response = await axios.post(`${API}/notifications/send`, {
    title,
    body,
    target_groups: targetGroups,
    url
  }, { headers: getAuthHeaders() });
  return response.data;
};

export const getNotificationHistory = async () => {
  const response = await axios.get(`${API}/notifications/history`, { headers: getAuthHeaders() });
  return response.data;
};

// Schedule
export const getSchedule = async () => {
  const response = await axios.get(`${API}/schedule`, { headers: getAuthHeaders() });
  return response.data;
};

export const getScheduleSettings = async () => {
  const response = await axios.get(`${API}/schedule/settings`, { headers: getAuthHeaders() });
  return response.data;
};

export const publishSchedule = async () => {
  const response = await axios.post(`${API}/schedule/publish`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const unpublishSchedule = async () => {
  const response = await axios.post(`${API}/schedule/unpublish`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const importSchedule = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API}/schedule/import`, formData, {
    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const clearSchedule = async () => {
  const response = await axios.delete(`${API}/schedule/clear`, { headers: getAuthHeaders() });
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

// Quick update for actual value only
export const updateBudgetActual = async (id, actual, paymentStatus = null) => {
  const data = { actual };
  if (paymentStatus) {
    data.payment_status = paymentStatus;
    if (paymentStatus === 'paid') {
      data.payment_date = new Date().toISOString().split('T')[0];
    }
  }
  const response = await axios.patch(`${API}/budget/${id}/actual`, data, { headers: getAuthHeaders() });
  return response.data;
};

// Mark item as paid (sets actual = estimated if no actual, and status = paid)
export const markBudgetItemPaid = async (id) => {
  const response = await axios.post(`${API}/budget/${id}/mark-paid`, {}, { headers: getAuthHeaders() });
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

// Food Expense Settings
export const getFoodExpenseSettings = async () => {
  const response = await axios.get(`${API}/budget/food-settings`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateFoodExpenseSettings = async (data) => {
  const response = await axios.put(`${API}/budget/food-settings`, data, { headers: getAuthHeaders() });
  return response.data;
};

// Receipt Upload
export const uploadReceipt = async (itemId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API}/budget/${itemId}/receipt`, formData, {
    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const deleteReceipt = async (itemId) => {
  const response = await axios.delete(`${API}/budget/${itemId}/receipt`, { headers: getAuthHeaders() });
  return response.data;
};

// Seed TNWG Budget Template
export const seedTNWGBudgetTemplate = async () => {
  const response = await axios.post(`${API}/budget/seed-tnwg-template`, {}, { headers: getAuthHeaders() });
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

export const assignUserUnit = async (userId, squadron, flight) => {
  const response = await axios.put(`${API}/users/${userId}/unit`, { squadron, flight }, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteUser = async (userId) => {
  const response = await axios.delete(`${API}/users/${userId}`, { headers: getAuthHeaders() });
  return response.data;
};

// Profile
export const getProfile = async () => {
  const response = await axios.get(`${API}/profile`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateProfile = async (data) => {
  const response = await axios.put(`${API}/profile`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const uploadProfilePhoto = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API}/profile/photo`, formData, {
    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const deleteProfilePhoto = async () => {
  const response = await axios.delete(`${API}/profile/photo`, { headers: getAuthHeaders() });
  return response.data;
};

// User Approval
export const getPendingUsers = async () => {
  const response = await axios.get(`${API}/users/pending`, { headers: getAuthHeaders() });
  return response.data;
};

export const approveUser = async (userId) => {
  const response = await axios.post(`${API}/users/${userId}/approve`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const linkUserToParticipant = async (userId, participantId, autoPopulate = true) => {
  const response = await axios.post(
    `${API}/users/${userId}/link-participant?participant_id=${participantId}&auto_populate=${autoPopulate}`,
    {},
    { headers: getAuthHeaders() }
  );
  return response.data;
};

export const findMatchingParticipants = async (userId) => {
  const response = await axios.get(`${API}/users/${userId}/match-participants`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateUserPermissions = async (userId, permissions) => {
  const response = await axios.put(`${API}/users/${userId}/permissions`, permissions, { headers: getAuthHeaders() });
  return response.data;
};

export const resetUserPermissions = async (userId) => {
  const response = await axios.post(`${API}/users/${userId}/reset-permissions`, {}, { headers: getAuthHeaders() });
  return response.data;
};

// Org Chart
export const getOrgChartRoles = async () => {
  const response = await axios.get(`${API}/org-chart/roles`, { headers: getAuthHeaders() });
  return response.data;
};

export const getOrgChartRole = async (roleId) => {
  const response = await axios.get(`${API}/org-chart/roles/${roleId}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createOrgChartRole = async (data) => {
  const response = await axios.post(`${API}/org-chart/roles`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateOrgChartRole = async (roleId, data) => {
  const response = await axios.put(`${API}/org-chart/roles/${roleId}`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const assignOrgChartRole = async (roleId, participantId) => {
  const response = await axios.put(
    `${API}/org-chart/roles/${roleId}/assign${participantId ? `?participant_id=${participantId}` : ''}`, 
    {}, 
    { headers: getAuthHeaders() }
  );
  return response.data;
};

export const deleteOrgChartRole = async (roleId) => {
  const response = await axios.delete(`${API}/org-chart/roles/${roleId}`, { headers: getAuthHeaders() });
  return response.data;
};

export const seedDefaultOrgChart = async () => {
  const response = await axios.post(`${API}/org-chart/seed-defaults`, {}, { headers: getAuthHeaders() });
  return response.data;
};

