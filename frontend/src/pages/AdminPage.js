import React, { useState, useEffect } from 'react';
import { getUsers, updateUserRole, assignUserUnit, deleteUser, getPendingUsers, approveUser, findMatchingParticipants, linkUserToParticipant, updateUserPermissions, resetUserPermissions, adminResetPassword } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
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
  Key
} from 'lucide-react';
import NotificationManager from '../components/NotificationManager';

const AdminPage = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending'); // 'pending', 'users'
  const [matchingParticipants, setMatchingParticipants] = useState({});
  const [loadingMatches, setLoadingMatches] = useState({});
  const [editingPermissions, setEditingPermissions] = useState(null);
  const [permissionsForm, setPermissionsForm] = useState({});
  
  // Password reset state
  const [resetPasswordModal, setResetPasswordModal] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resettingPassword, setResettingPassword] = useState(false);

  const roles = [
    { value: 'commander', label: 'Commander', color: 'bg-[#00205B] text-white' },
    { value: 'finance', label: 'Finance', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
    { value: 'plans_programs', label: 'Plans & Programs', color: 'bg-blue-100 text-blue-800 border-blue-200' },
    { value: 'exec_cadre', label: 'Executive Cadre', color: 'bg-purple-100 text-purple-800 border-purple-200' },
    { value: 'staff', label: 'Staff', color: 'bg-amber-100 text-amber-800 border-amber-200' },
    { value: 'cadre', label: 'Cadre', color: 'bg-slate-100 text-slate-800 border-slate-200' }
  ];

  const squadrons = [
    { value: 'none', label: 'Not Assigned' },
    { value: 'staff', label: 'Staff' },
    { value: 'support_cadre', label: 'Support Cadre' },
    { value: 'exec_cadre', label: 'Exec Cadre' },
    { value: 'ops_cadre', label: 'Ops Cadre' },
    { value: 'sq1', label: 'Squadron 1' },
    { value: 'sq2', label: 'Squadron 2' },
    { value: 'sq3', label: 'Squadron 3' }
  ];

  const flights = [
    { value: 'none', label: 'Not Assigned' },
    { value: 'alpha', label: 'Alpha', squadron: 'sq1' },
    { value: 'bravo', label: 'Bravo', squadron: 'sq1' },
    { value: 'charlie', label: 'Charlie', squadron: 'sq2' },
    { value: 'delta', label: 'Delta', squadron: 'sq2' },
    { value: 'echo', label: 'Echo', squadron: 'sq3' },
    { value: 'foxtrot', label: 'Foxtrot', squadron: 'sq3' }
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
    admin_panel: 'Admin Panel'
  };

  useEffect(() => {
    loadUsers();
    loadPendingUsers();
  }, []);

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
      admin_panel: false
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

  const handleRoleChange = async (userId, newRole) => {
    try {
      await updateUserRole(userId, newRole);
      toast.success('Role updated successfully');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleUnitChange = async (userId, squadron, flight) => {
    try {
      await assignUserUnit(userId, squadron || null, flight || null);
      toast.success('Unit assignment updated');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update unit');
    }
  };

  const handleSquadronChange = (userId, squadron) => {
    const user = users.find(u => u.id === userId);
    const actualSquadron = squadron === 'none' ? null : squadron;
    // Clear flight if squadron changes and flight doesn't belong to new squadron
    const currentFlight = user?.flight;
    const flightInfo = flights.find(f => f.value === currentFlight);
    const newFlight = (flightInfo && flightInfo.squadron === actualSquadron) ? currentFlight : null;
    handleUnitChange(userId, actualSquadron, newFlight);
  };

  const handleFlightChange = (userId, flight) => {
    const actualFlight = flight === 'none' ? null : flight;
    const flightInfo = flights.find(f => f.value === actualFlight);
    const squadron = flightInfo?.squadron || null;
    handleUnitChange(userId, squadron, actualFlight);
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
  const unitRequiresFlight = (squadron) => {
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
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Settings className="w-8 h-8 text-[#00205B]" />
          <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Administration
          </h1>
        </div>
        <p className="text-slate-500">
          Manage user roles, permissions, and unit assignments
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('pending')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'pending'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="pending-users-tab"
        >
          <span className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Pending Approval
            {pendingUsers.length > 0 && (
              <span className="bg-amber-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {pendingUsers.length}
              </span>
            )}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'users'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="all-users-tab"
        >
          <span className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            All Users ({users.length})
          </span>
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'settings'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="settings-tab"
        >
          <span className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Settings
          </span>
        </button>
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
                            <div key={idx} className="flex items-center justify-between p-2 bg-white rounded border border-blue-100">
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
        <div className="space-y-6">
          {/* Push Notifications */}
          <div className="mb-6">
            <NotificationManager />
          </div>

          {/* Users Table */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="border-b border-slate-100 p-4 flex items-center justify-between">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Registered Users
          </h2>
          <span className="text-sm text-slate-500">{users.length} users</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full cap-table" data-testid="users-table">
            <thead>
              <tr>
                <th className="text-left">Name</th>
                <th className="text-left">Email</th>
                <th className="text-left">Role</th>
                <th className="text-left">Unit</th>
                <th className="text-left">Flight</th>
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
                users.map(user => (
                  <React.Fragment key={user.id}>
                  <tr className="hover:bg-slate-50" data-testid={`user-row-${user.id}`}>
                    <td className="font-medium">
                      {user.name}
                      {user.id === currentUser?.id && (
                        <span className="ml-2 text-xs text-slate-400">(You)</span>
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
                          className={`w-32 rounded-sm text-xs font-bold uppercase ${getRoleBadgeColor(user.role)}`}
                          data-testid={`role-select-${user.id}`}
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {roles.map(role => (
                            <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td>
                      <Select
                        value={user.squadron || 'none'}
                        onValueChange={(value) => handleSquadronChange(user.id, value)}
                      >
                        <SelectTrigger className="w-32 rounded-sm text-xs" data-testid={`squadron-select-${user.id}`}>
                          <SelectValue placeholder="Not Assigned" />
                        </SelectTrigger>
                        <SelectContent>
                          {squadrons.map(sq => (
                            <SelectItem key={sq.value} value={sq.value}>{sq.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td>
                      <Select
                        value={user.flight || 'none'}
                        onValueChange={(value) => handleFlightChange(user.id, value)}
                        disabled={!unitRequiresFlight(user.squadron)}
                      >
                        <SelectTrigger 
                          className="w-24 rounded-sm text-xs" 
                          data-testid={`flight-select-${user.id}`}
                          disabled={!unitRequiresFlight(user.squadron)}
                        >
                          <SelectValue placeholder="N/A" />
                        </SelectTrigger>
                        <SelectContent>
                          {getFlightsForSquadron(user.squadron).map(fl => (
                            <SelectItem key={fl.value} value={fl.value}>{fl.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td>
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
                    </td>
                    <td className="text-right">
                      {user.id !== currentUser?.id && (
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
                      <td colSpan={7} className="p-4">
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <h4 className="font-bold text-sm text-[#00205B] uppercase tracking-tight">
                              Edit Access Permissions for {user.name}
                            </h4>
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleResetPermissions(user.id)}
                                className="rounded-sm text-xs"
                              >
                                <RotateCcw className="w-3 h-3 mr-1" />
                                Reset to Role Defaults
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
                                Save Permissions
                              </Button>
                            </div>
                          </div>
                          <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
                            {Object.entries(permissionLabels).map(([key, label]) => (
                              <label key={key} className="flex items-center gap-2 p-2 bg-white rounded border cursor-pointer hover:bg-slate-50">
                                <input
                                  type="checkbox"
                                  checked={permissionsForm[key] || false}
                                  onChange={(e) => setPermissionsForm(prev => ({ ...prev, [key]: e.target.checked }))}
                                  className="w-4 h-4 rounded border-slate-300"
                                />
                                <span className="text-xs text-slate-700">{label}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Warning */}
      <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-sm flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-amber-800">
          <p className="font-semibold">Important</p>
          <p className="mt-1">
            Role and unit changes take effect immediately. Users will need to refresh their browser to see updated permissions and schedule filtering.
            Assigning a flight will automatically set the correct squadron.
          </p>
        </div>
      </div>
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          {/* Role Permissions Info */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4">
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Role Permissions
              </h2>
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 bg-[#00205B]/5 rounded-sm border border-[#00205B]/20">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-5 h-5 text-[#00205B]" />
                  <span className="font-bold text-[#00205B]">Commander</span>
                </div>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>• Full access to all features</li>
                  <li>• Manage users and roles</li>
                  <li>• Approve new accounts</li>
                  <li>• Edit roster, schedule, budget</li>
                </ul>
              </div>
              <div className="p-4 bg-amber-50 rounded-sm border border-amber-200">
                <div className="flex items-center gap-2 mb-2">
                  <UserCog className="w-5 h-5 text-amber-700" />
                  <span className="font-bold text-amber-700">Staff</span>
                </div>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>• Edit roster participants</li>
                  <li>• Manage schedule events</li>
                  <li>• Assign users to units</li>
                  <li>• Manage documents</li>
                </ul>
              </div>
              <div className="p-4 bg-emerald-50 rounded-sm border border-emerald-200">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-5 h-5 text-emerald-700" />
                  <span className="font-bold text-emerald-700">Finance</span>
                </div>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>• Full budget access</li>
                  <li>• Manage expenses & income</li>
                  <li>• Upload receipts</li>
                  <li>• Food expense planning</li>
                </ul>
              </div>
              <div className="p-4 bg-slate-50 rounded-sm border border-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-5 h-5 text-slate-600" />
                  <span className="font-bold text-slate-600">Cadet</span>
                </div>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>• View roster</li>
                  <li>• View their unit's schedule</li>
                  <li>• Access documents</li>
                  <li>• No budget access</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Unit Structure Info */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4">
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                <Plane className="w-4 h-4" />
                Unit Structure
              </h2>
            </div>
            <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 bg-blue-50 rounded-sm border border-blue-200">
                <p className="font-bold text-blue-800 mb-2">Squadron 1</p>
                <div className="flex gap-2">
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs">Alpha</span>
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs">Bravo</span>
                </div>
              </div>
              <div className="p-3 bg-emerald-50 rounded-sm border border-emerald-200">
                <p className="font-bold text-emerald-800 mb-2">Squadron 2</p>
                <div className="flex gap-2">
                  <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded text-xs">Charlie</span>
                  <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded text-xs">Delta</span>
                </div>
              </div>
              <div className="p-3 bg-purple-50 rounded-sm border border-purple-200">
                <p className="font-bold text-purple-800 mb-2">Squadron 3</p>
                <div className="flex gap-2">
                  <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs">Echo</span>
                  <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs">Foxtrot</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPage;
