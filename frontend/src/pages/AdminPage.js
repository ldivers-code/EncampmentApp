import React, { useState, useEffect } from 'react';
import { getUsers, updateUserRole, deleteUser } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  Users, 
  Shield, 
  UserCog,
  Trash2,
  Settings,
  AlertTriangle
} from 'lucide-react';

const AdminPage = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const roles = [
    { value: 'commander', label: 'Commander', color: 'bg-[#00205B] text-white' },
    { value: 'staff', label: 'Staff', color: 'bg-amber-100 text-amber-800 border-amber-200' },
    { value: 'cadet', label: 'Cadet', color: 'bg-slate-100 text-slate-800 border-slate-200' }
  ];

  useEffect(() => {
    loadUsers();
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

  const handleRoleChange = async (userId, newRole) => {
    try {
      await updateUserRole(userId, newRole);
      toast.success('Role updated successfully');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
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
          Manage user roles and permissions
        </p>
      </div>

      {/* Role Permissions Info */}
      <div className="bg-white border border-slate-200 rounded-sm mb-6">
        <div className="border-b border-slate-100 p-4">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Role Permissions
          </h2>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-[#00205B]/5 rounded-sm border border-[#00205B]/20">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-5 h-5 text-[#00205B]" />
              <span className="font-bold text-[#00205B]">Commander</span>
            </div>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>• Full access to all features</li>
              <li>• Manage users and roles</li>
              <li>• Edit roster, schedule, budget</li>
              <li>• Manage documents</li>
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
              <li>• Update budget items</li>
              <li>• Manage documents</li>
            </ul>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-slate-200">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-5 h-5 text-slate-600" />
              <span className="font-bold text-slate-600">Cadet</span>
            </div>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>• View roster</li>
              <li>• View schedule</li>
              <li>• View budget</li>
              <li>• Access documents</li>
            </ul>
          </div>
        </div>
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
                <th className="text-left">CAP ID</th>
                <th className="text-left">Role</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-slate-400">
                    No users registered yet
                  </td>
                </tr>
              ) : (
                users.map(user => (
                  <tr key={user.id} className="hover:bg-slate-50" data-testid={`user-row-${user.id}`}>
                    <td className="font-medium">
                      {user.name}
                      {user.id === currentUser?.id && (
                        <span className="ml-2 text-xs text-slate-400">(You)</span>
                      )}
                    </td>
                    <td className="text-slate-600">{user.email}</td>
                    <td className="font-mono">{user.capid || '-'}</td>
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
          <p className="mt-1">Role changes take effect immediately. Users will need to refresh their browser to see updated permissions. Be careful when modifying Commander access.</p>
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
