import React, { useState, useEffect, useMemo } from 'react';
import { getUsers, updateUserRole, assignUserUnit, deleteUser, getPendingUsers, approveUser, findMatchingParticipants, linkUserToParticipant, updateUserPermissions, resetUserPermissions, adminResetPassword, getGoogleSheetsSettings, updateGoogleSheetsSettings, triggerGoogleSheetsSync, getGoogleSheetsSyncStatus, syncUsersToParticipants, previewBulkReset, executeBulkReset, clearAllParticipants, resetOrgChart } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { 
  Users, 
  Shield, 
  UserCog,
  Trash2,
  Settings,
  AlertTriangle,
  Plane,
  DollarSign,
  Clock,
  CheckCircle,
  Link,
  Search,
  UserPlus,
  Lock,
  Unlock,
  X,
  RotateCcw,
  Key,
  RefreshCw,
  FileSpreadsheet,
  Cloud,
  ExternalLink,
  AlertOctagon,
  Network
} from 'lucide-react';
import NotificationManager from '../components/NotificationManager';
import AdminSettingsTab from './admin/AdminSettingsTab';

// ─── Annual Reset Tab ───
const AnnualResetTab = ({ currentUser }) => {
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [orgChartConfirm, setOrgChartConfirm] = useState('');

  const TYPE_OPTIONS = [
    { value: 'cadre', label: 'Cadre', desc: 'All cadre members' },
    { value: 'staff', label: 'Senior Staff', desc: 'Staff role participants' },
    { value: 'senior_member', label: 'Senior Members', desc: 'Non-staff seniors' },
    { value: 'basic_student', label: 'Students', desc: 'All basic students' },
  ];

  const toggleType = (type) => {
    setSelectedTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
    setPreview(null);
    setConfirmText('');
  };

  const handlePreview = async () => {
    if (!selectedTypes.length) return;
    setLoading(true);
    try {
      const data = await previewBulkReset(selectedTypes);
      setPreview(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Preview failed');
    }
    setLoading(false);
  };

  const handleExecute = async () => {
    if (confirmText !== 'RESET') return;
    setLoading(true);
    try {
      const result = await executeBulkReset(selectedTypes);
      toast.success(result.message);
      setPreview(null);
      setSelectedTypes([]);
      setConfirmText('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reset failed');
    }
    setLoading(false);
  };

  const handleOrgChartReset = async () => {
    if (orgChartConfirm !== 'RESET') return;
    setLoading(true);
    try {
      const result = await resetOrgChart();
      toast.success(result.message);
      setOrgChartConfirm('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reset failed');
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6" data-testid="annual-reset-tab">
      <div className="bg-red-50 border border-red-200 rounded-sm p-4">
        <div className="flex items-start gap-3">
          <AlertOctagon className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-bold text-red-800 text-sm">Annual Encampment Reset</h3>
            <p className="text-red-700 text-xs mt-1">
              Use this to clear the roster and org chart between encampment years. This permanently deletes participant records,
              unlinks user accounts, and clears related data (med diary, supplements, contraband, check-in records).
              User accounts are preserved — only the roster link is removed.
            </p>
          </div>
        </div>
      </div>

      {/* Roster Reset */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
          <h4 className="text-sm font-bold text-[#00205B] flex items-center gap-2">
            <Users className="w-4 h-4" /> Roster Bulk Removal
          </h4>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <p className="text-xs text-slate-500 uppercase font-bold mb-2">Select participant types to remove</p>
            <div className="flex flex-wrap gap-2">
              {TYPE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => toggleType(opt.value)}
                  className={`px-3 py-2 rounded-sm border text-sm font-medium transition-colors ${
                    selectedTypes.includes(opt.value)
                      ? 'bg-red-600 text-white border-red-600'
                      : 'bg-white text-slate-700 border-slate-300 hover:border-red-300'
                  }`}
                  data-testid={`reset-type-${opt.value}`}
                >
                  {opt.label}
                  <span className="block text-[10px] font-normal opacity-75">{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {selectedTypes.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreview}
              disabled={loading}
              className="rounded-sm border-red-300 text-red-700 hover:bg-red-50"
              data-testid="preview-reset-btn"
            >
              <Search className="w-3.5 h-3.5 mr-1.5" />
              Preview ({selectedTypes.length} type{selectedTypes.length > 1 ? 's' : ''})
            </Button>
          )}

          {preview && (
            <div className="border border-red-200 rounded-sm overflow-hidden">
              <div className="bg-red-50 px-4 py-2 border-b border-red-200">
                <p className="text-sm font-bold text-red-800">
                  {preview.total_to_remove} participants will be permanently deleted
                </p>
                {preview.linked_accounts > 0 && (
                  <p className="text-xs text-red-600 mt-0.5">
                    {preview.linked_accounts} user account{preview.linked_accounts > 1 ? 's' : ''} will be unlinked (accounts preserved, roster link cleared)
                  </p>
                )}
              </div>
              {preview.sample.length > 0 && (
                <div className="max-h-48 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 sticky top-0">
                      <tr><th className="px-3 py-1.5 text-left">Name</th><th className="px-3 py-1.5 text-left">Type</th><th className="px-3 py-1.5 text-left">Flight</th><th className="px-3 py-1.5 text-left">Position</th></tr>
                    </thead>
                    <tbody>
                      {preview.sample.map(p => (
                        <tr key={p.id} className="border-t border-slate-100">
                          <td className="px-3 py-1.5">{p.rank} {p.last_name}, {p.first_name}</td>
                          <td className="px-3 py-1.5">{p.participant_type}</td>
                          <td className="px-3 py-1.5">{p.flight || '-'}</td>
                          <td className="px-3 py-1.5">{p.position || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {preview.total_to_remove > 20 && (
                    <p className="text-xs text-slate-500 px-3 py-1.5 bg-slate-50">...and {preview.total_to_remove - 20} more</p>
                  )}
                </div>
              )}
              <div className="p-3 bg-white border-t border-red-200 space-y-2">
                <p className="text-xs text-red-700 font-medium">Type RESET to confirm</p>
                <div className="flex gap-2">
                  <Input
                    value={confirmText}
                    onChange={e => setConfirmText(e.target.value)}
                    placeholder="RESET"
                    className="max-w-[150px] h-8 text-sm rounded-sm border-red-300"
                    data-testid="reset-confirm-input"
                  />
                  <Button
                    size="sm"
                    disabled={confirmText !== 'RESET' || loading}
                    onClick={handleExecute}
                    className="bg-red-600 hover:bg-red-700 text-white rounded-sm"
                    data-testid="execute-reset-btn"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                    Delete {preview.total_to_remove} Participants
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Org Chart Reset */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
          <h4 className="text-sm font-bold text-[#00205B] flex items-center gap-2">
            <Network className="w-4 h-4" /> Org Chart Reset
          </h4>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-xs text-slate-600">
            Clear all org chart positions. You can reseed from the spreadsheet after resetting.
          </p>
          <div className="flex items-center gap-2">
            <Input
              value={orgChartConfirm}
              onChange={e => setOrgChartConfirm(e.target.value)}
              placeholder="Type RESET to confirm"
              className="max-w-[200px] h-8 text-sm rounded-sm border-red-300"
              data-testid="orgchart-reset-input"
            />
            <Button
              size="sm"
              disabled={orgChartConfirm !== 'RESET' || loading}
              onClick={handleOrgChartReset}
              className="bg-red-600 hover:bg-red-700 text-white rounded-sm"
              data-testid="orgchart-reset-btn"
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Clear Org Chart
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const AdminPage = () => {
  const { user: currentUser } = useAuth();
  const isFullAdmin = ['dcp', 'commander', 'executive_staff'].includes(currentUser?.role);
  const [users, setUsers] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(isFullAdmin ? 'pending' : 'users');
  const [matchingParticipants, setMatchingParticipants] = useState({});
  const [loadingMatches, setLoadingMatches] = useState({});
  const [editingPermissions, setEditingPermissions] = useState(null);
  const [permissionsForm, setPermissionsForm] = useState({});
  
  // Password reset state
  const [resetPasswordModal, setResetPasswordModal] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resettingPassword, setResettingPassword] = useState(false);

  // User-Participant sync state
  const [syncingParticipants, setSyncingParticipants] = useState(false);

  // Google Sheets sync state
  const [gsheetSettings, setGsheetSettings] = useState({
    rosterSpreadsheetId: '',
    rosterGid: '',
    orgChartSpreadsheetId: '',
    orgChartGids: '',
    syncIntervalHours: 1,
    autoSyncEnabled: true
  });
  const [syncStatus, setSyncStatus] = useState(null);
  const [savingGsheetSettings, setSavingGsheetSettings] = useState(false);
  const [syncingNow, setSyncingNow] = useState(false);

  const roles = [
    // Senior Staff (adults)
    { value: 'dcp', label: 'Director of Cadet Programs', color: 'bg-yellow-100 text-yellow-900 border-yellow-300', group: 'staff' },
    { value: 'commander', label: 'Commander', color: 'bg-[#00205B] text-white', group: 'staff' },
    { value: 'executive_staff', label: 'Executive Staff', color: 'bg-[#00205B] text-white', group: 'staff' },
    { value: 'training_officer', label: 'Training Officer', color: 'bg-teal-100 text-teal-800 border-teal-200', group: 'staff' },
    { value: 'health_services', label: 'Health Services', color: 'bg-rose-100 text-rose-800 border-rose-200', group: 'staff' },
    { value: 'finance', label: 'Finance', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', group: 'staff' },
    { value: 'dining_facility', label: 'Dining Facility', color: 'bg-orange-100 text-orange-800 border-orange-200', group: 'staff' },
    { value: 'logistics', label: 'Logistics (Senior)', color: 'bg-cyan-100 text-cyan-800 border-cyan-200', group: 'staff' },
    { value: 'plans_programs', label: 'Plans & Programs (Senior)', color: 'bg-blue-100 text-blue-800 border-blue-200', group: 'staff' },
    { value: 'staff', label: 'Staff', color: 'bg-amber-100 text-amber-800 border-amber-200', group: 'staff' },
    // Cadre (cadets)
    { value: 'exec_cadre', label: 'Executive Cadre', color: 'bg-purple-100 text-purple-800 border-purple-200', group: 'cadre' },
    { value: 'cadre', label: 'Cadre', color: 'bg-slate-100 text-slate-800 border-slate-200', group: 'cadre' },
    // Parent
    { value: 'parent', label: 'Parent / Guardian', color: 'bg-sky-100 text-sky-800 border-sky-200', group: 'parent' }
  ];

  const cadreUnits = [
    { value: '', label: 'Not Assigned' },
    { value: 'ops', label: 'Operations' },
    { value: 'support', label: 'Support' }
  ];

  const opsPositions = [
    { value: '', label: 'Not Assigned' },
    { value: 'squadron_commander', label: 'Squadron Commander' },
    { value: 'squadron_superintendent', label: 'Squadron Superintendent' },
    { value: 'flight_commander', label: 'Flight Commander' },
    { value: 'flight_sergeant', label: 'Flight Sergeant' }
  ];

  const supportSections = [
    { value: '', label: 'Not Assigned' },
    { value: 'word', label: 'WORD' },
    { value: 'logistics', label: 'Logistics' },
    { value: 'public_affairs', label: 'Public Affairs' },
    { value: 'dfac', label: 'DFAC' },
    { value: 'plans_programs', label: 'Plans & Programs' }
  ];

  const squadrons = [
    { value: 'none', label: 'Not Assigned' },
    { value: '6th_cts', label: '6th CTS' },
    { value: '21st_cts', label: '21st CTS' },
    { value: '22nd_cts', label: '22nd CTS' }
  ];

  const flights = [
    { value: 'none', label: 'Not Assigned' },
    { value: 'alpha', label: 'Alpha', squadron: '6th_cts' },
    { value: 'bravo', label: 'Bravo', squadron: '6th_cts' },
    { value: 'charlie', label: 'Charlie', squadron: '21st_cts' },
    { value: 'delta', label: 'Delta', squadron: '21st_cts' },
    { value: 'echo', label: 'Echo', squadron: '22nd_cts' },
    { value: 'foxtrot', label: 'Foxtrot', squadron: '22nd_cts' }
  ];

  const permissionLabels = {
    dashboard: 'Dashboard',
    roster_view: 'Roster (View)',
    roster_edit: 'Roster (Edit)',
    schedule_view: 'Schedule (View)',
    schedule_edit: 'Schedule (Edit)',
    budget_view: 'Budget (View)',
    budget_edit: 'Budget (Edit)',
    analytics: 'Analytics',
    org_chart: 'Org Chart',
    handbooks: 'Handbooks',
    documents: 'Documents',
    admin_panel: 'Admin Panel',
    health_view: 'Health (View)',
    health_full: 'Health (Full)',
    check_in_view: 'Check-In (View)',
    check_in_edit: 'Check-In (Edit)',
    meal_plan_view: 'Meal Plan (View)',
    meal_plan_edit: 'Meal Plan (Edit)'
  };

  const pageVisibilityLabels = {
    page_health: 'Health Services',
    page_check_in: 'Check-In',
    page_barracks: 'Barracks',
    page_logistics: 'Logistics',
    page_meal_plan: 'Meal Plan',
    page_training: 'Training Officer',
    page_status_board: 'Status Board',
    page_parent_portal: 'Parent Portal'
  };

  // Memoize user groups to avoid re-computing on every render
  const userGroups = useMemo(() => {
    const staffRoles = ['dcp', 'commander', 'executive_staff', 'training_officer', 'logistics',
      'finance', 'plans_programs', 'health_services', 'dining_facility', 'staff'];
    const cadreRoles = ['exec_cadre', 'cadre'];
    const parentRoles = ['parent'];
    return [
      { label: 'SENIOR STAFF', users: users.filter(u => staffRoles.includes(u.role)).sort((a, b) => (a.name || '').localeCompare(b.name || '')) },
      { label: 'CADRE', users: users.filter(u => cadreRoles.includes(u.role)).sort((a, b) => (a.name || '').localeCompare(b.name || '')) },
      { label: 'PARENT', users: users.filter(u => parentRoles.includes(u.role)).sort((a, b) => (a.name || '').localeCompare(b.name || '')) },
    ].filter(g => g.users.length > 0);
  }, [users]);

  const staffRoleOptions = useMemo(() => roles.filter(r => r.group === 'staff'), []);
  const cadreRoleOptions = useMemo(() => roles.filter(r => r.group === 'cadre'), []);
  const parentRoleOptions = useMemo(() => roles.filter(r => r.group === 'parent'), []);

  useEffect(() => {
    loadUsers();
    if (isFullAdmin) {
      loadPendingUsers();
      loadGoogleSheetsSettings();
    }
  }, []);

  // Load Google Sheets settings
  const loadGoogleSheetsSettings = async () => {
    try {
      const settings = await getGoogleSheetsSettings();
      if (settings) {
        setGsheetSettings({
          rosterSpreadsheetId: settings.roster_sheet?.spreadsheet_id || '',
          rosterGid: settings.roster_sheet?.gid || '',
          orgChartSpreadsheetId: settings.org_chart_sheets?.[0]?.spreadsheet_id || '',
          orgChartGids: settings.org_chart_sheets?.map(s => s.gid).join(',') || '',
          syncIntervalHours: settings.sync_interval_hours || 1,
          autoSyncEnabled: settings.auto_sync_enabled !== false
        });
      }
      
      const status = await getGoogleSheetsSyncStatus();
      setSyncStatus(status);
    } catch (error) {
      console.error('Failed to load Google Sheets settings', error);
    }
  };

  // Save Google Sheets settings
  const handleSaveGsheetSettings = async () => {
    setSavingGsheetSettings(true);
    try {
      await updateGoogleSheetsSettings({
        roster_spreadsheet_id: gsheetSettings.rosterSpreadsheetId || null,
        roster_gid: gsheetSettings.rosterGid || null,
        org_chart_spreadsheet_id: gsheetSettings.orgChartSpreadsheetId || null,
        org_chart_gids: gsheetSettings.orgChartGids ? gsheetSettings.orgChartGids.split(',').map(g => g.trim()) : null,
        sync_interval_hours: gsheetSettings.syncIntervalHours,
        auto_sync_enabled: gsheetSettings.autoSyncEnabled
      });
      toast.success('Google Sheets settings saved');
      loadGoogleSheetsSettings();
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSavingGsheetSettings(false);
    }
  };

  // Trigger manual sync
  const handleManualSync = async () => {
    setSyncingNow(true);
    try {
      await triggerGoogleSheetsSync();
      toast.success('Sync started! This may take a moment.');
      // Poll for status updates
      setTimeout(loadGoogleSheetsSettings, 2000);
      setTimeout(loadGoogleSheetsSettings, 5000);
      setTimeout(loadGoogleSheetsSettings, 10000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start sync');
    } finally {
      setSyncingNow(false);
    }
  };

  // Helper to extract spreadsheet ID and gid from Google Sheets URL
  const parseGoogleSheetsUrl = (url) => {
    try {
      const spreadsheetIdMatch = url.match(/\/d\/([a-zA-Z0-9-_]+)/);
      const gidMatch = url.match(/gid=(\d+)/);
      return {
        spreadsheetId: spreadsheetIdMatch ? spreadsheetIdMatch[1] : '',
        gid: gidMatch ? gidMatch[1] : ''
      };
    } catch {
      return { spreadsheetId: '', gid: '' };
    }
  };

  const loadUsers = async () => {
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const loadPendingUsers = async () => {
    try {
      const data = await getPendingUsers();
      setPendingUsers(data);
    } catch (error) {
      console.error('Failed to load pending users', error);
    }
  };

  const handleApproveUser = async (userId) => {
    try {
      await approveUser(userId);
      toast.success('User approved successfully');
      loadPendingUsers();
      loadUsers();
    } catch (error) {
      toast.error('Failed to approve user');
    }
  };

  const handleFindMatches = async (userId) => {
    setLoadingMatches(prev => ({ ...prev, [userId]: true }));
    try {
      const data = await findMatchingParticipants(userId);
      setMatchingParticipants(prev => ({ ...prev, [userId]: data.matches }));
    } catch (error) {
      toast.error('Failed to find matches');
    } finally {
      setLoadingMatches(prev => ({ ...prev, [userId]: false }));
    }
  };

  const handleLinkParticipant = async (userId, participantId) => {
    try {
      await linkUserToParticipant(userId, participantId, true);
      toast.success('User linked and profile populated');
      loadPendingUsers();
      loadUsers();
      setMatchingParticipants(prev => ({ ...prev, [userId]: null }));
    } catch (error) {
      toast.error('Failed to link participant');
    }
  };

  const handleEditPermissions = (user) => {
    setEditingPermissions(user.id);
    setPermissionsForm(user.permissions || {
      dashboard: true,
      roster_view: true,
      roster_edit: false,
      schedule_view: true,
      schedule_edit: false,
      budget_view: false,
      budget_edit: false,
      analytics: false,
      org_chart: true,
      handbooks: true,
      documents: true,
      admin_panel: false,
      health_view: false,
      health_full: false,
      check_in_view: false,
      check_in_edit: false,
      meal_plan_view: false,
      meal_plan_edit: false,
      page_health: false,
      page_check_in: false,
      page_barracks: false,
      page_logistics: false,
      page_meal_plan: false,
      page_training: false,
      page_status_board: false,
      page_parent_portal: false
    });
  };

  const handleSavePermissions = async (userId) => {
    try {
      await updateUserPermissions(userId, permissionsForm);
      toast.success('Permissions updated successfully');
      setEditingPermissions(null);
      loadUsers();
    } catch (error) {
      toast.error('Failed to update permissions');
    }
  };

  const handleResetPermissions = async (userId) => {
    try {
      await resetUserPermissions(userId);
      toast.success('Permissions reset to role defaults');
      setEditingPermissions(null);
      loadUsers();
    } catch (error) {
      toast.error('Failed to reset permissions');
    }
  };

  const handleResetPassword = async () => {
    if (!resetPasswordModal) return;
    
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    setResettingPassword(true);
    try {
      await adminResetPassword(resetPasswordModal.id, newPassword);
      toast.success(`Password reset for ${resetPasswordModal.name}`);
      setResetPasswordModal(null);
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    } finally {
      setResettingPassword(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await updateUserRole(userId, newRole);
      toast.success('Role updated successfully');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleUnitChange = async (userId, squadron, flight, supportSection, cadreUnit, cadrePosition) => {
    try {
      await assignUserUnit(userId, squadron || null, flight || null, supportSection || null, cadreUnit || null, cadrePosition || null);
      toast.success('Assignment updated');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update assignment');
    }
  };

  const handleCadreUnitChange = (userId, newUnit) => {
    const user = users.find(u => u.id === userId);
    // Clear position/section/squadron/flight when switching unit
    handleUnitChange(userId, null, null, null, newUnit || null, null);
  };

  const handleCadrePositionChange = (userId, newPosition) => {
    const user = users.find(u => u.id === userId);
    // Clear squadron/flight when changing position
    handleUnitChange(userId, null, null, user?.support_section, user?.cadre_unit, newPosition || null);
  };

  const handleCadreSectionChange = (userId, newSection) => {
    const user = users.find(u => u.id === userId);
    handleUnitChange(userId, null, null, newSection || null, user?.cadre_unit, user?.cadre_position);
  };

  const handleSquadronChange = (userId, squadron) => {
    const user = users.find(u => u.id === userId);
    const actualSquadron = squadron === 'none' ? null : squadron;
    const currentFlight = user?.flight;
    const flightInfo = flights.find(f => f.value === currentFlight);
    const newFlight = (flightInfo && flightInfo.squadron === actualSquadron) ? currentFlight : null;
    handleUnitChange(userId, actualSquadron, newFlight, user?.support_section, user?.cadre_unit, user?.cadre_position);
  };

  const handleFlightChange = (userId, flight) => {
    const user = users.find(u => u.id === userId);
    const actualFlight = flight === 'none' ? null : flight;
    const flightInfo = flights.find(f => f.value === actualFlight);
    const squadron = flightInfo?.squadron || user?.squadron || null;
    handleUnitChange(userId, squadron, actualFlight, user?.support_section, user?.cadre_unit, user?.cadre_position);
  };

  const handleSupportSectionChange = (userId, section) => {
    const user = users.find(u => u.id === userId);
    const actualSection = section === 'none' ? null : section;
    handleUnitChange(userId, user?.squadron, user?.flight, actualSection, user?.cadre_unit, user?.cadre_position);
  };

  const handleDelete = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      try {
        await deleteUser(userId);
        toast.success('User deleted');
        loadUsers();
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Failed to delete user');
      }
    }
  };

  const handleSyncUsersToRoster = async () => {
    setSyncingParticipants(true);
    try {
      const result = await syncUsersToParticipants();
      toast.success(result.message);
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to sync users to roster');
    } finally {
      setSyncingParticipants(false);
    }
  };

  const getRoleBadgeColor = (role) => {
    return roles.find(r => r.value === role)?.color || roles[2].color;
  };

  const getFlightsForSquadron = (squadron) => {
    // Units that don't need flight assignment
    const noFlightUnits = ['staff', 'support_cadre', 'exec_cadre'];
    if (!squadron || noFlightUnits.includes(squadron)) return [{ value: 'none', label: 'N/A' }];
    // For ops_cadre and squadrons, show all flights or filter by squadron
    if (squadron === 'ops_cadre') return flights;
    return flights.filter(f => f.squadron === squadron || f.value === 'none');
  };

  // Check if unit requires flight assignment
  const unitRequiresFlight = (squadron, role) => {
    // Support cadre can optionally have flight sub-assignments
    if (role?.startsWith('support_') || role === 'squadron_commander') return true;
    const noFlightUnits = ['staff', 'support_cadre', 'exec_cadre', null, undefined, 'none'];
    return !noFlightUnits.includes(squadron);
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="mb-4 sm:mb-8">
        <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
          <Settings className="w-6 h-6 sm:w-8 sm:h-8 text-[#00205B]" />
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Administration
          </h1>
        </div>
        <p className="text-sm sm:text-base text-slate-500">
          Manage user roles, permissions, and unit assignments
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 sm:mb-6 border-b border-slate-200 overflow-x-auto">
        {isFullAdmin && (
        <button
          onClick={() => setActiveTab('pending')}
          className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap ${
            activeTab === 'pending'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="pending-users-tab"
        >
          <span className="flex items-center gap-1 sm:gap-2">
            <Clock className="w-3 h-3 sm:w-4 sm:h-4" />
            <span className="hidden sm:inline">Pending</span> Approval
            {pendingUsers.length > 0 && (
              <span className="bg-amber-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {pendingUsers.length}
              </span>
            )}
          </span>
        </button>
        )}
        <button
          onClick={() => setActiveTab('users')}
          className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap ${
            activeTab === 'users'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="all-users-tab"
        >
          <span className="flex items-center gap-1 sm:gap-2">
            <Users className="w-3 h-3 sm:w-4 sm:h-4" />
            All Users ({users.length})
          </span>
        </button>
        {isFullAdmin && (
        <button
          onClick={() => setActiveTab('settings')}
          className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap ${
            activeTab === 'settings'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="settings-tab"
        >
          <span className="flex items-center gap-1 sm:gap-2">
            <Settings className="w-3 h-3 sm:w-4 sm:h-4" />
            Settings
          </span>
        </button>
        )}
        {['dcp', 'commander'].includes(currentUser?.role) && (
        <button
          onClick={() => setActiveTab('reset')}
          className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap ${
            activeTab === 'reset'
              ? 'border-red-600 text-red-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="reset-tab"
        >
          <span className="flex items-center gap-1 sm:gap-2">
            <AlertOctagon className="w-3 h-3 sm:w-4 sm:h-4" />
            Annual Reset
          </span>
        </button>
        )}
      </div>

      {/* Pending Users Tab */}
      {activeTab === 'pending' && (
        <div className="space-y-6">
          {pendingUsers.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-sm p-8 text-center">
              <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <p className="text-slate-600 font-medium">No pending approvals</p>
              <p className="text-sm text-slate-400 mt-1">All user accounts have been approved</p>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-sm">
              <div className="border-b border-slate-100 p-4">
                <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                  Pending User Approvals ({pendingUsers.length})
                </h2>
              </div>
              <div className="divide-y divide-slate-100">
                {pendingUsers.map(pendingUser => (
                  <div key={pendingUser.id} className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 font-bold">
                          {pendingUser.name?.charAt(0)?.toUpperCase() || '?'}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900">{pendingUser.name}</p>
                          <p className="text-sm text-slate-500">{pendingUser.email}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`text-xs px-2 py-0.5 rounded border ${getRoleBadgeColor(pendingUser.role)}`}>
                              {pendingUser.role}
                            </span>
                            {pendingUser.capid && (
                              <span className="text-xs font-mono text-slate-500">CAPID: {pendingUser.capid}</span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400 mt-1">
                            Registered {new Date(pendingUser.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleFindMatches(pendingUser.id)}
                          disabled={loadingMatches[pendingUser.id]}
                          className="rounded-sm text-xs"
                          data-testid={`find-matches-${pendingUser.id}`}
                        >
                          <Search className="w-3 h-3 mr-1" />
                          {loadingMatches[pendingUser.id] ? 'Searching...' : 'Find Matches'}
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleApproveUser(pendingUser.id)}
                          className="rounded-sm bg-emerald-600 hover:bg-emerald-700 text-xs"
                          data-testid={`approve-user-${pendingUser.id}`}
                        >
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Approve
                        </Button>
                      </div>
                    </div>

                    {/* Matching Participants */}
                    {matchingParticipants[pendingUser.id] && matchingParticipants[pendingUser.id].length > 0 && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-sm">
                        <p className="text-sm font-medium text-blue-800 mb-2 flex items-center gap-1">
                          <Link className="w-4 h-4" />
                          Potential Roster Matches
                        </p>
                        <div className="space-y-2">
                          {matchingParticipants[pendingUser.id].map((match, idx) => (
                            <div key={match.participant?.capid || `match-${idx}`} className="flex items-center justify-between p-2 bg-white rounded border border-blue-100">
                              <div>
                                <p className="text-sm font-medium">
                                  {match.participant.rank} {match.participant.first_name} {match.participant.last_name}
                                </p>
                                <p className="text-xs text-slate-500">
                                  CAPID: {match.participant.capid} | {match.participant.unit} | {match.participant.wing}
                                </p>
                                <span className={`text-xs px-1.5 py-0.5 rounded ${
                                  match.confidence === 'high' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                                }`}>
                                  {match.match_type} match ({match.confidence})
                                </span>
                              </div>
                              <Button
                                size="sm"
                                onClick={() => handleLinkParticipant(pendingUser.id, match.participant.id || match.participant.capid)}
                                className="rounded-sm bg-blue-600 hover:bg-blue-700 text-xs"
                              >
                                <UserPlus className="w-3 h-3 mr-1" />
                                Link & Approve
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {matchingParticipants[pendingUser.id] && matchingParticipants[pendingUser.id].length === 0 && (
                      <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-sm">
                        <p className="text-sm text-slate-500">No matching participants found in the roster</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* All Users Tab */}
      {activeTab === 'users' && (
        <div className="space-y-4 sm:space-y-6">
          {/* Push Notifications */}
          <div className="mb-4 sm:mb-6">
            <NotificationManager compact={true} />
          </div>

          {/* Users Table */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="border-b border-slate-100 p-3 sm:p-4 flex items-center justify-between">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Registered Users
          </h2>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleSyncUsersToRoster}
              disabled={syncingParticipants}
              className="rounded-sm text-xs"
              data-testid="sync-users-to-roster-btn"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${syncingParticipants ? 'animate-spin' : ''}`} />
              {syncingParticipants ? 'Syncing...' : 'Sync Users to Roster'}
            </Button>
            <span className="text-xs sm:text-sm text-slate-500">{users.length} users</span>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full cap-table" data-testid="users-table">
            <thead>
              <tr>
                <th className="text-left">Name</th>
                <th className="text-left">Email</th>
                <th className="text-left">Role</th>
                <th className="text-left">Unit / Position</th>
                <th className="text-left">Assignment</th>
                <th className="text-left">Access</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-400">
                    No users registered yet
                  </td>
                </tr>
              ) : (
                (() => {
                  return userGroups.map(g => (
                    <React.Fragment key={g.label}>
                      <tr>
                        <td colSpan={7} className="bg-slate-100 py-1.5 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                          {g.label} ({g.users.length})
                        </td>
                      </tr>
                      {g.users.map(user => (
                  <React.Fragment key={user.id}>
                  <tr className="hover:bg-slate-50" data-testid={`user-row-${user.id}`}>
                    <td className="font-medium">
                      {user.name}
                      {user.id === currentUser?.id && (
                        <span className="ml-2 text-xs text-slate-400">(You)</span>
                      )}
                      {user.linked_participant_id ? (
                        <span className="ml-2 text-xs text-emerald-600" title="Linked to roster participant"><Link className="w-3 h-3 inline" /></span>
                      ) : (
                        <span className="ml-2 text-xs text-amber-500" title="Not linked to roster"><AlertTriangle className="w-3 h-3 inline" /></span>
                      )}
                    </td>
                    <td className="text-slate-600 text-sm">{user.email}</td>
                    <td>
                      <Select
                        value={user.role}
                        onValueChange={(value) => handleRoleChange(user.id, value)}
                        disabled={user.id === currentUser?.id}
                      >
                        <SelectTrigger 
                          className={`w-36 rounded-sm text-xs font-bold uppercase ${getRoleBadgeColor(user.role)}`}
                          data-testid={`role-select-${user.id}`}
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem disabled value="__staff_header" className="text-xs font-bold text-slate-400">--- Senior Staff ---</SelectItem>
                          {staffRoleOptions.map(role => (
                            <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                          ))}
                          <SelectItem disabled value="__cadre_header" className="text-xs font-bold text-slate-400">--- Cadre ---</SelectItem>
                          {cadreRoleOptions.map(role => (
                            <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                          ))}
                          <SelectItem disabled value="__parent_header" className="text-xs font-bold text-slate-400">--- Other ---</SelectItem>
                          {parentRoleOptions.map(role => (
                            <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    {/* Unit / Position column - only for cadre */}
                    <td>
                      {['cadre', 'exec_cadre'].includes(user.role) ? (
                        <div className="flex flex-col gap-1">
                          <Select
                            value={user.cadre_unit || ''}
                            onValueChange={(value) => handleCadreUnitChange(user.id, value)}
                          >
                            <SelectTrigger className="w-28 rounded-sm text-xs" data-testid={`cadre-unit-${user.id}`}>
                              <SelectValue placeholder="Unit..." />
                            </SelectTrigger>
                            <SelectContent>
                              {cadreUnits.map(u => (
                                <SelectItem key={u.value || 'none'} value={u.value || 'none'}>{u.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {user.cadre_unit === 'ops' && (
                            <Select
                              value={user.cadre_position || ''}
                              onValueChange={(value) => handleCadrePositionChange(user.id, value)}
                            >
                              <SelectTrigger className="w-28 rounded-sm text-xs" data-testid={`cadre-position-${user.id}`}>
                                <SelectValue placeholder="Position..." />
                              </SelectTrigger>
                              <SelectContent>
                                {opsPositions.map(p => (
                                  <SelectItem key={p.value || 'none'} value={p.value || 'none'}>{p.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                          {user.cadre_unit === 'support' && (
                            <Select
                              value={user.support_section || ''}
                              onValueChange={(value) => handleCadreSectionChange(user.id, value)}
                            >
                              <SelectTrigger className="w-28 rounded-sm text-xs" data-testid={`cadre-section-${user.id}`}>
                                <SelectValue placeholder="Section..." />
                              </SelectTrigger>
                              <SelectContent>
                                {supportSections.map(s => (
                                  <SelectItem key={s.value || 'none'} value={s.value || 'none'}>{s.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">-</span>
                      )}
                    </td>
                    {/* Assignment column - squadron/flight for ops cadre */}
                    <td>
                      {['cadre', 'exec_cadre'].includes(user.role) && user.cadre_unit === 'ops' && ['squadron_commander', 'squadron_superintendent'].includes(user.cadre_position) && (
                        <Select
                          value={user.squadron || 'none'}
                          onValueChange={(value) => handleSquadronChange(user.id, value)}
                        >
                          <SelectTrigger className="w-28 rounded-sm text-xs" data-testid={`squadron-select-${user.id}`}>
                            <SelectValue placeholder="Squadron" />
                          </SelectTrigger>
                          <SelectContent>
                            {squadrons.map(sq => (
                              <SelectItem key={sq.value} value={sq.value}>{sq.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                      {['cadre', 'exec_cadre'].includes(user.role) && user.cadre_unit === 'ops' && ['flight_commander', 'flight_sergeant'].includes(user.cadre_position) && (
                        <Select
                          value={user.flight || 'none'}
                          onValueChange={(value) => handleFlightChange(user.id, value)}
                        >
                          <SelectTrigger className="w-28 rounded-sm text-xs" data-testid={`flight-select-${user.id}`}>
                            <SelectValue placeholder="Flight" />
                          </SelectTrigger>
                          <SelectContent>
                            {flights.map(fl => (
                              <SelectItem key={fl.value} value={fl.value}>{fl.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                      {!(['cadre', 'exec_cadre'].includes(user.role) && user.cadre_unit === 'ops' && user.cadre_position) && (
                        <span className="text-xs text-slate-400">-</span>
                      )}
                    </td>
                    <td>
                      {isFullAdmin && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => editingPermissions === user.id ? setEditingPermissions(null) : handleEditPermissions(user)}
                        className={`rounded-sm text-xs ${editingPermissions === user.id ? 'bg-blue-50 border-blue-300' : ''}`}
                        data-testid={`edit-permissions-${user.id}`}
                      >
                        {editingPermissions === user.id ? <Unlock className="w-3 h-3 mr-1" /> : <Lock className="w-3 h-3 mr-1" />}
                        {editingPermissions === user.id ? 'Editing...' : 'Permissions'}
                      </Button>
                      )}
                    </td>
                    <td className="text-right flex items-center gap-1 justify-end">
                      {isFullAdmin && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setResetPasswordModal(user)}
                        className="h-8 px-2 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded-sm"
                        title="Reset Password"
                        data-testid={`reset-password-${user.id}`}
                      >
                        <Key className="w-4 h-4" />
                      </Button>
                      )}
                      {isFullAdmin && user.id !== currentUser?.id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(user.id)}
                          className="h-8 w-8 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                          data-testid={`delete-user-${user.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </td>
                  </tr>
                  {/* Permissions Edit Row */}
                  {editingPermissions === user.id && (
                    <tr className="bg-blue-50/50">
                      <td colSpan={8} className="p-4">
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <h4 className="font-bold text-sm text-[#00205B] uppercase tracking-tight">
                              Edit Access for {user.name}
                            </h4>
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleResetPermissions(user.id)}
                                className="rounded-sm text-xs"
                              >
                                <RotateCcw className="w-3 h-3 mr-1" />
                                Reset to Defaults
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setEditingPermissions(null)}
                                className="rounded-sm text-xs"
                              >
                                <X className="w-3 h-3 mr-1" />
                                Cancel
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleSavePermissions(user.id)}
                                className="rounded-sm text-xs bg-[#00205B] hover:bg-[#001540]"
                              >
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Save
                              </Button>
                            </div>
                          </div>
                          
                          {/* Access Level Toggles */}
                          <div>
                            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-2">Access Level</p>
                            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                              {Object.entries(permissionLabels).map(([key, label]) => (
                                <label key={key} className="flex items-center gap-2 p-2 bg-white rounded border cursor-pointer hover:bg-slate-50">
                                  <input
                                    type="checkbox"
                                    checked={permissionsForm[key] || false}
                                    onChange={(e) => setPermissionsForm(prev => ({ ...prev, [key]: e.target.checked }))}
                                    className="w-4 h-4 rounded border-slate-300"
                                    data-testid={`perm-${key}`}
                                  />
                                  <span className="text-xs text-slate-700">{label}</span>
                                </label>
                              ))}
                            </div>
                          </div>

                          {/* Page Visibility Toggles */}
                          <div>
                            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-2">Page Visibility</p>
                            <div className="grid grid-cols-3 md:grid-cols-7 gap-2">
                              {Object.entries(pageVisibilityLabels).map(([key, label]) => (
                                <label key={key} className="flex items-center gap-2 p-2 bg-white rounded border cursor-pointer hover:bg-slate-50">
                                  <input
                                    type="checkbox"
                                    checked={permissionsForm[key] || false}
                                    onChange={(e) => setPermissionsForm(prev => ({ ...prev, [key]: e.target.checked }))}
                                    className="w-4 h-4 rounded border-slate-300"
                                    data-testid={`page-${key}`}
                                  />
                                  <span className="text-xs text-slate-700">{label}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                  </React.Fragment>
                ))}
              </React.Fragment>
            ))
          })()
        )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Warning */}
      <div className="mt-4 sm:mt-6 p-3 sm:p-4 bg-amber-50 border border-amber-200 rounded-sm flex items-start gap-2 sm:gap-3">
        <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm text-amber-800">
          <p className="font-semibold">Important</p>
          <p className="mt-1">
            Role and unit changes take effect immediately. Users will need to refresh their browser to see updated permissions.
          </p>
        </div>
      </div>
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <AdminSettingsTab
          gsheetSettings={gsheetSettings}
          setGsheetSettings={setGsheetSettings}
          syncStatus={syncStatus}
          syncingNow={syncingNow}
          savingGsheetSettings={savingGsheetSettings}
          handleSaveGsheetSettings={handleSaveGsheetSettings}
          handleManualSync={handleManualSync}
          syncingParticipants={syncingParticipants}
          handleSyncUsersToRoster={handleSyncUsersToRoster}
        />
      )}

      {/* Annual Reset Tab */}
      {activeTab === 'reset' && (
        <AnnualResetTab currentUser={currentUser} />
      )}

      {/* Password Reset Modal */}
      <Dialog open={!!resetPasswordModal} onOpenChange={(open) => !open && setResetPasswordModal(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2">
              <Key className="w-5 h-5" />
              Reset Password
            </DialogTitle>
          </DialogHeader>
          {resetPasswordModal && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-slate-50 rounded-sm">
                <p className="text-sm text-slate-500">Resetting password for:</p>
                <p className="font-bold text-slate-900">{resetPasswordModal.name}</p>
                <p className="text-sm text-slate-500">{resetPasswordModal.email}</p>
              </div>
              
              <div>
                <label className="text-xs uppercase tracking-wide text-slate-600 block mb-1">New Password</label>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="rounded-sm"
                  data-testid="admin-reset-password-input"
                />
                <p className="text-xs text-slate-400 mt-1">Minimum 6 characters</p>
              </div>
              
              <div>
                <label className="text-xs uppercase tracking-wide text-slate-600 block mb-1">Confirm Password</label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  className="rounded-sm"
                  data-testid="admin-reset-confirm-input"
                />
              </div>
              
              <div className="flex justify-end gap-2 pt-2">
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setResetPasswordModal(null);
                    setNewPassword('');
                    setConfirmPassword('');
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleResetPassword}
                  disabled={resettingPassword || !newPassword || !confirmPassword}
                  className="bg-[#00205B]"
                  data-testid="admin-reset-submit-btn"
                >
                  {resettingPassword ? 'Resetting...' : 'Reset Password'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminPage;
