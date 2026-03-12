import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem('cap_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Presence / Active Users
export const sendHeartbeat = async () => {
  const response = await axios.post(`${API}/presence/heartbeat`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const getActiveUsers = async () => {
  const response = await axios.get(`${API}/presence/active-users`, { headers: getAuthHeaders() });
  return response.data;
};

export const goOffline = async () => {
  const response = await axios.post(`${API}/presence/offline`, {}, { headers: getAuthHeaders() });
  return response.data;
};

// Notification Badges
export const getNotificationBadges = async () => {
  const response = await axios.get(`${API}/notification-badges`, { headers: getAuthHeaders() });
  return response.data;
};

// Password Reset
export const forgotPassword = async (email, capid) => {
  const params = new URLSearchParams({ email, capid });
  const response = await axios.post(`${API}/auth/forgot-password?${params}`);
  return response.data;
};

export const verifyResetToken = async (token) => {
  const response = await axios.post(`${API}/auth/verify-reset-token?token=${token}`);
  return response.data;
};

export const resetPassword = async (token, newPassword) => {
  const params = new URLSearchParams({ token, new_password: newPassword });
  const response = await axios.post(`${API}/auth/reset-password?${params}`);
  return response.data;
};

export const adminResetPassword = async (userId, newPassword) => {
  const params = new URLSearchParams({ new_password: newPassword });
  const response = await axios.post(`${API}/users/${userId}/reset-password?${params}`, {}, { headers: getAuthHeaders() });
  return response.data;
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

// Point Tracking
export const getScoreCategories = async () => {
  const response = await axios.get(`${API}/points/categories`, { headers: getAuthHeaders() });
  return response.data;
};

export const createScoreCategory = async (data) => {
  const response = await axios.post(`${API}/points/categories`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const seedDefaultCategories = async () => {
  const response = await axios.post(`${API}/points/categories/seed-defaults`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const recordScore = async (data) => {
  const response = await axios.post(`${API}/points/scores`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const getScores = async (params = {}) => {
  const queryParams = new URLSearchParams(params).toString();
  const response = await axios.get(`${API}/points/scores${queryParams ? `?${queryParams}` : ''}`, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteScore = async (scoreId) => {
  const response = await axios.delete(`${API}/points/scores/${scoreId}`, { headers: getAuthHeaders() });
  return response.data;
};

export const recordMeritDemerit = async (data) => {
  const response = await axios.post(`${API}/points/merits`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const getMeritDemerits = async (params = {}) => {
  const queryParams = new URLSearchParams(params).toString();
  const response = await axios.get(`${API}/points/merits${queryParams ? `?${queryParams}` : ''}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getFlightLeaderboard = async (date = null) => {
  const response = await axios.get(`${API}/points/leaderboard/flights${date ? `?date=${date}` : ''}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getSquadronLeaderboard = async (date = null) => {
  const response = await axios.get(`${API}/points/leaderboard/squadrons${date ? `?date=${date}` : ''}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getIndividualLeaderboard = async (participantType = null, date = null, limit = 20) => {
  const params = new URLSearchParams();
  if (participantType) params.append('participant_type', participantType);
  if (date) params.append('date', date);
  params.append('limit', limit);
  const response = await axios.get(`${API}/points/leaderboard/individuals?${params}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getDailyWinners = async (date) => {
  const response = await axios.get(`${API}/points/daily-winners?date=${date}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getCumulativeStandings = async () => {
  const response = await axios.get(`${API}/points/cumulative-standings`, { headers: getAuthHeaders() });
  return response.data;
};

export const getPointsSummary = async () => {
  const response = await axios.get(`${API}/points/summary`, { headers: getAuthHeaders() });
  return response.data;
};

// Honor Awards
export const getAwardTypes = async () => {
  const response = await axios.get(`${API}/points/awards/types`, { headers: getAuthHeaders() });
  return response.data;
};

export const getHonorAwards = async (params = {}) => {
  const queryParams = new URLSearchParams(params).toString();
  const response = await axios.get(`${API}/points/awards${queryParams ? `?${queryParams}` : ''}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getAwardsByDate = async (date) => {
  const response = await axios.get(`${API}/points/awards/by-date/${date}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createHonorAward = async (awardType, recipientId, date, notes = null) => {
  const params = new URLSearchParams({
    award_type: awardType,
    recipient_id: recipientId,
    date: date
  });
  if (notes) params.append('notes', notes);
  const response = await axios.post(`${API}/points/awards?${params}`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteHonorAward = async (awardId) => {
  const response = await axios.delete(`${API}/points/awards/${awardId}`, { headers: getAuthHeaders() });
  return response.data;
};

export const autoAssignDailyAwards = async (date) => {
  const response = await axios.post(`${API}/points/awards/auto-assign/${date}`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const getAwardRecipientsSummary = async () => {
  const response = await axios.get(`${API}/points/awards/recipients-summary`, { headers: getAuthHeaders() });
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

// Flight/Squadron API
export const getFlights = async () => {
  const response = await axios.get(`${API}/flights`, { headers: getAuthHeaders() });
  return response.data;
};

export const getSquadrons = async () => {
  const response = await axios.get(`${API}/squadrons`, { headers: getAuthHeaders() });
  return response.data;
};

export const getFlightRoster = async (flight) => {
  const response = await axios.get(`${API}/flights/${flight}/roster`, { headers: getAuthHeaders() });
  return response.data;
};

export const getSquadronRoster = async (squadron) => {
  const response = await axios.get(`${API}/squadrons/${squadron}/roster`, { headers: getAuthHeaders() });
  return response.data;
};

export const getMyFlightInfo = async () => {
  const response = await axios.get(`${API}/my-flight`, { headers: getAuthHeaders() });
  return response.data;
};

export const getFlightLeadership = async (flight) => {
  const response = await axios.get(`${API}/flights/${flight}/leadership`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateFlightLeadership = async (flight, leadership) => {
  const response = await axios.put(`${API}/flights/${flight}/leadership`, leadership, { headers: getAuthHeaders() });
  return response.data;
};


export const getFlightDocuments = async (flight) => {
  const response = await axios.get(`${API}/documents/by-flight/${flight}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getSquadronDocuments = async (squadron) => {
  const response = await axios.get(`${API}/documents/by-squadron/${squadron}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getDocumentCategories = async () => {
  const response = await axios.get(`${API}/documents/categories`, { headers: getAuthHeaders() });
  return response.data;
};

// Google Sheets Sync
export const getGoogleSheetsSettings = async () => {
  const response = await axios.get(`${API}/google-sheets/settings`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateGoogleSheetsSettings = async (settings) => {
  const response = await axios.post(`${API}/google-sheets/settings`, settings, { headers: getAuthHeaders() });
  return response.data;
};

export const triggerGoogleSheetsSync = async () => {
  const response = await axios.post(`${API}/google-sheets/sync`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const getGoogleSheetsSyncStatus = async () => {
  const response = await axios.get(`${API}/google-sheets/sync-status`, { headers: getAuthHeaders() });
  return response.data;
};

// Daily Settings (Uniform & Weather Flag)
export const getDailySettings = async () => {
  const response = await axios.get(`${API}/daily-settings`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateUniformOfDay = async (uniform) => {
  const response = await axios.post(`${API}/daily-settings/uniform`, uniform, { headers: getAuthHeaders() });
  return response.data;
};

export const updateWeatherFlag = async (weather) => {
  const response = await axios.post(`${API}/daily-settings/weather-flag`, weather, { headers: getAuthHeaders() });
  return response.data;
};

export const getWeatherGuidelines = async () => {
  const response = await axios.get(`${API}/daily-settings/weather-guidelines`, { headers: getAuthHeaders() });
  return response.data;
};

// ================= FLIGHT REPORTS =================

export const getReportSettings = async () => {
  const response = await axios.get(`${API}/reports/settings`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateReportSettings = async (settings) => {
  const response = await axios.post(`${API}/reports/settings`, settings, { headers: getAuthHeaders() });
  return response.data;
};

export const createFlightReport = async (report) => {
  const response = await axios.post(`${API}/reports`, report, { headers: getAuthHeaders() });
  return response.data;
};

export const getFlightReports = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.flight) params.append('flight', filters.flight);
  if (filters.squadron) params.append('squadron', filters.squadron);
  if (filters.report_date) params.append('report_date', filters.report_date);
  if (filters.status) params.append('status', filters.status);
  const response = await axios.get(`${API}/reports?${params}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getFlightReport = async (reportId) => {
  const response = await axios.get(`${API}/reports/${reportId}`, { headers: getAuthHeaders() });
  return response.data;
};

export const reviewFlightReport = async (reportId, reviewNotes = null) => {
  const params = reviewNotes ? `?review_notes=${encodeURIComponent(reviewNotes)}` : '';
  const response = await axios.put(`${API}/reports/${reportId}/review${params}`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const escalateFlightReport = async (reportId, escalateTo, notes = null) => {
  const response = await axios.put(`${API}/reports/${reportId}/escalate`, 
    { escalate_to: escalateTo, notes }, 
    { headers: getAuthHeaders() }
  );
  return response.data;
};

export const resolveFlightReport = async (reportId, resolutionNotes = null) => {
  const params = resolutionNotes ? `?resolution_notes=${encodeURIComponent(resolutionNotes)}` : '';
  const response = await axios.put(`${API}/reports/${reportId}/resolve${params}`, {}, { headers: getAuthHeaders() });
  return response.data;
};

export const getMySubmittedReports = async () => {
  const response = await axios.get(`${API}/reports/my/submitted`, { headers: getAuthHeaders() });
  return response.data;
};

export const getCommanderIssues = async () => {
  const response = await axios.get(`${API}/reports/commander-issues`, { headers: getAuthHeaders() });
  return response.data;
};

export const deleteFlightReport = async (reportId) => {
  const response = await axios.delete(`${API}/reports/${reportId}`, { headers: getAuthHeaders() });
  return response.data;
};

// ================= HEALTH SERVICES API =================

// Health Settings
export const getHealthSettings = async () => {
  const response = await axios.get(`${API}/health/settings`, { headers: getAuthHeaders() });
  return response.data;
};

export const updateHealthSettings = async (settings) => {
  const response = await axios.post(`${API}/health/settings`, settings, { headers: getAuthHeaders() });
  return response.data;
};

// Reference Lists
export const getHealthReferenceLists = async () => {
  const response = await axios.get(`${API}/health/reference-lists`, { headers: getAuthHeaders() });
  return response.data;
};

// Cadet Health Summary
export const getCadetHealthSummary = async (cadetId) => {
  const response = await axios.get(`${API}/health/cadet/${cadetId}/summary`, { headers: getAuthHeaders() });
  return response.data;
};

export const getCadetHealthSummaryByCapid = async (capid) => {
  const response = await axios.get(`${API}/health/cadet/by-capid/${capid}/summary`, { headers: getAuthHeaders() });
  return response.data;
};

// Medication Profiles
export const getCadetMedications = async (cadetId) => {
  const response = await axios.get(`${API}/health/cadet/${cadetId}/medications`, { headers: getAuthHeaders() });
  return response.data;
};

export const createCadetMedication = async (cadetId, medication) => {
  const response = await axios.post(`${API}/health/cadet/${cadetId}/medications`, medication, { headers: getAuthHeaders() });
  return response.data;
};

export const updateMedicationProfile = async (medProfileId, updates) => {
  const response = await axios.put(`${API}/health/medications/${medProfileId}`, updates, { headers: getAuthHeaders() });
  return response.data;
};

export const deactivateMedication = async (medProfileId) => {
  const response = await axios.put(`${API}/health/medications/${medProfileId}/deactivate`, {}, { headers: getAuthHeaders() });
  return response.data;
};

// Medication Administration Log
export const getCadetMedicationLog = async (cadetId, limit = 100) => {
  const response = await axios.get(`${API}/health/cadet/${cadetId}/medication-log?limit=${limit}`, { headers: getAuthHeaders() });
  return response.data;
};

export const logMedicationAdministration = async (cadetId, entry) => {
  const response = await axios.post(`${API}/health/cadet/${cadetId}/medication-log`, entry, { headers: getAuthHeaders() });
  return response.data;
};

// Incident Log
export const getCadetIncidents = async (cadetId) => {
  const response = await axios.get(`${API}/health/cadet/${cadetId}/incidents`, { headers: getAuthHeaders() });
  return response.data;
};

export const logCadetIncident = async (cadetId, entry) => {
  const response = await axios.post(`${API}/health/cadet/${cadetId}/incidents`, entry, { headers: getAuthHeaders() });
  return response.data;
};

export const updateIncidentStatus = async (incidentId, status, notes = null) => {
  const response = await axios.put(`${API}/health/incidents/${incidentId}/status`, { status, notes }, { headers: getAuthHeaders() });
  return response.data;
};

// Custody Log
export const getCadetCustodyLog = async (cadetId) => {
  const response = await axios.get(`${API}/health/cadet/${cadetId}/custody-log`, { headers: getAuthHeaders() });
  return response.data;
};

export const logCustodyAction = async (cadetId, entry) => {
  const response = await axios.post(`${API}/health/cadet/${cadetId}/custody-log`, entry, { headers: getAuthHeaders() });
  return response.data;
};

// Cadet Health Status
export const updateCadetHealthStatus = async (cadetId, status, capid) => {
  const response = await axios.put(`${API}/health/cadet/${cadetId}/status`, { status, capid }, { headers: getAuthHeaders() });
  return response.data;
};

// Dashboard Endpoints
export const getMedsDue = async (windowMinutes = 30) => {
  const response = await axios.get(`${API}/health/dashboard/meds-due?window_minutes=${windowMinutes}`, { headers: getAuthHeaders() });
  return response.data;
};

export const getOverdueMeds = async () => {
  const response = await axios.get(`${API}/health/dashboard/overdue`, { headers: getAuthHeaders() });
  return response.data;
};

export const getOpenIncidents = async () => {
  const response = await axios.get(`${API}/health/dashboard/open-incidents`, { headers: getAuthHeaders() });
  return response.data;
};

export const getHealthDashboardSummary = async () => {
  const response = await axios.get(`${API}/health/dashboard/summary`, { headers: getAuthHeaders() });
  return response.data;
};

export const getHealthHistoricalReport = async (eventYear = null, squadron = null, cadetId = null) => {
  const params = new URLSearchParams();
  if (eventYear) params.append('event_year', eventYear);
  if (squadron) params.append('squadron', squadron);
  if (cadetId) params.append('cadet_id', cadetId);
  const response = await axios.get(`${API}/health/reports/historical?${params}`, { headers: getAuthHeaders() });
  return response.data;
};

// Search
export const searchHealthCadets = async (query = null, squadron = null, flight = null, hasMedication = null, hasIncident = null) => {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (squadron) params.append('squadron', squadron);
  if (flight) params.append('flight', flight);
  if (hasMedication !== null) params.append('has_medication', hasMedication);
  if (hasIncident !== null) params.append('has_incident', hasIncident);
  const response = await axios.get(`${API}/health/search/cadets?${params}`, { headers: getAuthHeaders() });
  return response.data;
};

// Audit Log
export const getHealthAuditLog = async (limit = 100, tableName = null, recordId = null) => {
  const params = new URLSearchParams();
  params.append('limit', limit);
  if (tableName) params.append('table_name', tableName);
  if (recordId) params.append('record_id', recordId);
  const response = await axios.get(`${API}/health/audit-log?${params}`, { headers: getAuthHeaders() });
  return response.data;
};

// Health Data Import
export const importMedicalData = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API}/health/import/medical-data`, formData, {
    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getImportSummary = async () => {
  const response = await axios.get(`${API}/health/import/summary`, { headers: getAuthHeaders() });
  return response.data;
};

// Cadet Allergies
export const getCadetAllergies = async (capid) => {
  const response = await axios.get(`${API}/health/cadet/${capid}/allergies`, { headers: getAuthHeaders() });
  return response.data;
};

// Cadet OTC Approvals
export const getCadetOtcApprovals = async (capid) => {
  const response = await axios.get(`${API}/health/cadet/${capid}/otc-approvals`, { headers: getAuthHeaders() });
  return response.data;
};


// ============ Training Officer ============

export const getTrainingSummary = async () => {
  const response = await axios.get(`${API}/training/summary`, { headers: getAuthHeaders() });
  return response.data;
};

// Blister Checks
export const getBisterChecks = async (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  const response = await axios.get(`${API}/training/blister-checks?${qs}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createBlisterCheck = async (data) => {
  const response = await axios.post(`${API}/training/blister-checks`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateBlisterCheck = async (id, data) => {
  const response = await axios.put(`${API}/training/blister-checks/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

// Counseling Logs
export const getCounselingLogs = async (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  const response = await axios.get(`${API}/training/counseling-logs?${qs}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createCounselingLog = async (data) => {
  const response = await axios.post(`${API}/training/counseling-logs`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateCounselingLog = async (id, data) => {
  const response = await axios.put(`${API}/training/counseling-logs/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

// Cadre Issues
export const getCadreIssues = async (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  const response = await axios.get(`${API}/training/cadre-issues?${qs}`, { headers: getAuthHeaders() });
  return response.data;
};

export const createCadreIssue = async (data) => {
  const response = await axios.post(`${API}/training/cadre-issues`, data, { headers: getAuthHeaders() });
  return response.data;
};

export const updateCadreIssue = async (id, data) => {
  const response = await axios.put(`${API}/training/cadre-issues/${id}`, data, { headers: getAuthHeaders() });
  return response.data;
};

// ============ Schedule Change Requests ============
export const getScheduleChangeRequests = async (params = {}) => {
  const r = await axios.get(`${API}/schedule-changes?${new URLSearchParams(params)}`, { headers: getAuthHeaders() }); return r.data;
};
export const submitScheduleChange = async (data) => {
  const r = await axios.post(`${API}/schedule-changes`, data, { headers: getAuthHeaders() }); return r.data;
};
export const reviewScheduleChange = async (id, data) => {
  const r = await axios.put(`${API}/schedule-changes/${id}/review`, data, { headers: getAuthHeaders() }); return r.data;
};
export const getPendingScheduleChangesCount = async () => {
  const r = await axios.get(`${API}/schedule-changes/pending-count`, { headers: getAuthHeaders() }); return r.data;
};



// ============ Logistics Module ============
const LOG = `${API}/logistics`;

export const getLogisticsDashboard = async () => {
  const r = await axios.get(`${LOG}/dashboard`, { headers: getAuthHeaders() }); return r.data;
};
// Inventory
export const getInventory = async (p = {}) => {
  const r = await axios.get(`${LOG}/inventory?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createInventoryItem = async (d) => {
  const r = await axios.post(`${LOG}/inventory`, d, { headers: getAuthHeaders() }); return r.data;
};
export const updateInventoryItem = async (id, d) => {
  const r = await axios.put(`${LOG}/inventory/${id}`, d, { headers: getAuthHeaders() }); return r.data;
};
export const deleteInventoryItem = async (id) => {
  const r = await axios.delete(`${LOG}/inventory/${id}`, { headers: getAuthHeaders() }); return r.data;
};
// Lost & Found
export const getLostFound = async (p = {}) => {
  const r = await axios.get(`${LOG}/lost-found?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createLostFound = async (d) => {
  const r = await axios.post(`${LOG}/lost-found`, d, { headers: getAuthHeaders() }); return r.data;
};
export const updateLostFound = async (id, d) => {
  const r = await axios.put(`${LOG}/lost-found/${id}`, d, { headers: getAuthHeaders() }); return r.data;
};
// Radios
export const getRadios = async (p = {}) => {
  const r = await axios.get(`${LOG}/radios?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const checkoutRadio = async (d) => {
  const r = await axios.post(`${LOG}/radios/checkout`, d, { headers: getAuthHeaders() }); return r.data;
};
export const checkinRadio = async (id, d) => {
  const r = await axios.put(`${LOG}/radios/${id}/checkin`, d, { headers: getAuthHeaders() }); return r.data;
};
export const updateRadio = async (id, d) => {
  const r = await axios.put(`${LOG}/radios/${id}`, d, { headers: getAuthHeaders() }); return r.data;
};
export const resetRadioAvailable = async (d) => {
  const r = await axios.post(`${LOG}/radios/reset-available`, d, { headers: getAuthHeaders() }); return r.data;
};
// Comms Log
export const getCommsLog = async (p = {}) => {
  const r = await axios.get(`${LOG}/comms-log?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createCommsEntry = async (d) => {
  const r = await axios.post(`${LOG}/comms-log`, d, { headers: getAuthHeaders() }); return r.data;
};
// Call Signs
export const getCallSigns = async (p = {}) => {
  const r = await axios.get(`${LOG}/callsigns?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createCallSign = async (d) => {
  const r = await axios.post(`${LOG}/callsigns`, d, { headers: getAuthHeaders() }); return r.data;
};
export const updateCallSign = async (id, d) => {
  const r = await axios.put(`${LOG}/callsigns/${id}`, d, { headers: getAuthHeaders() }); return r.data;
};
export const deleteCallSign = async (id) => {
  const r = await axios.delete(`${LOG}/callsigns/${id}`, { headers: getAuthHeaders() }); return r.data;
};
// Vehicles
export const getVehicles = async (p = {}) => {
  const r = await axios.get(`${LOG}/vehicles?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createVehicleAssignment = async (d) => {
  const r = await axios.post(`${LOG}/vehicles`, d, { headers: getAuthHeaders() }); return r.data;
};
export const returnVehicle = async (id, d) => {
  const r = await axios.put(`${LOG}/vehicles/${id}/return`, d, { headers: getAuthHeaders() }); return r.data;
};
export const updateVehicle = async (id, d) => {
  const r = await axios.put(`${LOG}/vehicles/${id}`, d, { headers: getAuthHeaders() }); return r.data;
};
// Vehicle Log
export const getVehicleLog = async (p = {}) => {
  const r = await axios.get(`${LOG}/vehicle-log?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createVehicleLogEntry = async (d) => {
  const r = await axios.post(`${LOG}/vehicle-log`, d, { headers: getAuthHeaders() }); return r.data;
};
// Facilities
export const getFacilities = async (p = {}) => {
  const r = await axios.get(`${LOG}/facilities?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createFacility = async (d) => {
  const r = await axios.post(`${LOG}/facilities`, d, { headers: getAuthHeaders() }); return r.data;
};
export const updateFacility = async (id, d) => {
  const r = await axios.put(`${LOG}/facilities/${id}`, d, { headers: getAuthHeaders() }); return r.data;
};
// Supply Requests
export const getSupplyRequests = async (p = {}) => {
  const r = await axios.get(`${LOG}/supply-requests?${new URLSearchParams(p)}`, { headers: getAuthHeaders() }); return r.data;
};
export const createSupplyRequest = async (d) => {
  const r = await axios.post(`${LOG}/supply-requests`, d, { headers: getAuthHeaders() }); return r.data;
};
export const approveSupplyRequest = async (id, d) => {
  const r = await axios.put(`${LOG}/supply-requests/${id}/approve`, d, { headers: getAuthHeaders() }); return r.data;
};
export const issueSupplyRequest = async (id) => {
  const r = await axios.put(`${LOG}/supply-requests/${id}/issue`, {}, { headers: getAuthHeaders() }); return r.data;
};
export const completeSupplyRequest = async (id) => {
  const r = await axios.put(`${LOG}/supply-requests/${id}/complete`, {}, { headers: getAuthHeaders() }); return r.data;
};

// ============ Health Alerts ============
export const getHealthAlerts = async (memberId) => {
  const r = await axios.get(`${API}/health-alerts/${memberId}`, { headers: getAuthHeaders() }); return r.data;
};
export const updateHealthAlerts = async (memberId, data) => {
  const r = await axios.put(`${API}/health-alerts/${memberId}`, data, { headers: getAuthHeaders() }); return r.data;
};
export const getMemberProfile = async (memberId) => {
  const r = await axios.get(`${API}/members/${memberId}/profile`, { headers: getAuthHeaders() }); return r.data;
};


// ============ Status Board ============
const SB = `${API}/statusboard`;

// Display (no auth needed for projector)
export const getSBDisplay = async () => { const r = await axios.get(`${SB}/display`); return r.data; };

// Flights
export const getSBFlights = async () => { const r = await axios.get(`${SB}/flights`, { headers: getAuthHeaders() }); return r.data; };
export const createSBFlight = async (d) => { const r = await axios.post(`${SB}/flights`, d, { headers: getAuthHeaders() }); return r.data; };
export const updateSBFlight = async (id, d) => { const r = await axios.put(`${SB}/flights/${id}`, d, { headers: getAuthHeaders() }); return r.data; };
export const deleteSBFlight = async (id) => { const r = await axios.delete(`${SB}/flights/${id}`, { headers: getAuthHeaders() }); return r.data; };

// Issues
export const getSBIssues = async () => { const r = await axios.get(`${SB}/issues`, { headers: getAuthHeaders() }); return r.data; };
export const createSBIssue = async (d) => { const r = await axios.post(`${SB}/issues`, d, { headers: getAuthHeaders() }); return r.data; };
export const updateSBIssue = async (id, d) => { const r = await axios.put(`${SB}/issues/${id}`, d, { headers: getAuthHeaders() }); return r.data; };

// Announcements
export const getSBAnnouncements = async () => { const r = await axios.get(`${SB}/announcements`, { headers: getAuthHeaders() }); return r.data; };
export const createSBAnnouncement = async (d) => { const r = await axios.post(`${SB}/announcements`, d, { headers: getAuthHeaders() }); return r.data; };
export const updateSBAnnouncement = async (id, d) => { const r = await axios.put(`${SB}/announcements/${id}`, d, { headers: getAuthHeaders() }); return r.data; };
export const deleteSBAnnouncement = async (id) => { const r = await axios.delete(`${SB}/announcements/${id}`, { headers: getAuthHeaders() }); return r.data; };

// Schedule
export const getSBSchedule = async () => { const r = await axios.get(`${SB}/schedule`, { headers: getAuthHeaders() }); return r.data; };
export const createSBScheduleEvent = async (d) => { const r = await axios.post(`${SB}/schedule`, d, { headers: getAuthHeaders() }); return r.data; };
export const updateSBScheduleEvent = async (id, d) => { const r = await axios.put(`${SB}/schedule/${id}`, d, { headers: getAuthHeaders() }); return r.data; };
export const deleteSBScheduleEvent = async (id) => { const r = await axios.delete(`${SB}/schedule/${id}`, { headers: getAuthHeaders() }); return r.data; };

// Resources
export const getSBResources = async () => { const r = await axios.get(`${SB}/resources`, { headers: getAuthHeaders() }); return r.data; };
export const createSBResource = async (d) => { const r = await axios.post(`${SB}/resources`, d, { headers: getAuthHeaders() }); return r.data; };
export const updateSBResource = async (id, d) => { const r = await axios.put(`${SB}/resources/${id}`, d, { headers: getAuthHeaders() }); return r.data; };

// Settings & Emergency
export const getSBSettings = async () => { const r = await axios.get(`${SB}/settings`, { headers: getAuthHeaders() }); return r.data; };
export const updateSBSettings = async (d) => { const r = await axios.put(`${SB}/settings`, d, { headers: getAuthHeaders() }); return r.data; };
export const updateSBEmergency = async (d) => { const r = await axios.put(`${SB}/emergency`, d, { headers: getAuthHeaders() }); return r.data; };

// Audit & Seed
export const getSBAudit = async () => { const r = await axios.get(`${SB}/audit`, { headers: getAuthHeaders() }); return r.data; };
export const seedSBData = async () => { const r = await axios.post(`${SB}/seed`, {}, { headers: getAuthHeaders() }); return r.data; };
