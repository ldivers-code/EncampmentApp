import React, { useState, useEffect, useCallback } from 'react';
import { 
  getOrgChartRoles, 
  getOrgChartRole, 
  updateOrgChartRole, 
  assignOrgChartRole,
  createOrgChartRole,
  deleteOrgChartRole,
  seedDefaultOrgChart,
  getParticipants 
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  Users, 
  User,
  UserCircle,
  Edit2,
  Plus,
  Trash2,
  Network,
  Layers,
  AlertCircle,
  Check
} from 'lucide-react';

// Color mapping based on role type - matching flight/squadron colors
const getRoleColor = (roleId) => {
  // Executive Cadre & All Staff = #008651 (Emerald Green)
  if (['enc-commander', 'cadet-commander', 'deputy-support', 'commandant', 'sm-superintendent', 
       'deputy-commander', 'dean-academics', 'chief-instructor', 'finance', 'chaplain-cdi', 
       'health-services', 'safety', 'word', 'public-affairs', 'logistics', 'plans-programs', 'comms'].includes(roleId)) {
    return 'bg-[#008651] text-white border-[#006b41]';
  }
  
  // Support Cadre = Silver (Support Squadron Commander and support staff)
  if (roleId === 'support-sq-cc' || roleId === 'support-squadron-commander' || 
      roleId.includes('support-sq') || roleId.includes('-super') || roleId.includes('-oic') || 
      roleId.includes('ncoic') || roleId === 'dfac') {
    return 'bg-slate-400 text-slate-900 border-slate-500';
  }
  
  // 6th CTS (Alpha, Bravo) - Sky Blue - including squadron commander, training officers, flight roles
  if (roleId.includes('6th') || roleId.includes('1sq') || 
      roleId === 'alpha-fc' || roleId === 'alpha-fs' || roleId === 'bravo-fc' || roleId === 'bravo-fs' || 
      roleId === 'ato-alpha' || roleId === 'ato-bravo' ||
      roleId.includes('6th-cts') || roleId.includes('6thcts') || roleId.includes('sq1')) {
    return 'bg-sky-500 text-white border-sky-600';
  }
  
  // 21st CTS (Charlie, Delta) - Dark Red - including squadron commander, training officers, flight roles
  if (roleId.includes('21st') || roleId.includes('2sq') || 
      roleId === 'charlie-fc' || roleId === 'charlie-fs' || roleId === 'delta-fc' || roleId === 'delta-fs' || 
      roleId === 'ato-charlie' || roleId === 'ato-delta' ||
      roleId.includes('21st-cts') || roleId.includes('21stcts') || roleId.includes('sq2')) {
    return 'bg-red-700 text-white border-red-800';
  }
  
  // 22nd CTS (Echo, Foxtrot) - Indigo/Dark Blue - including squadron commander, training officers, flight roles
  if (roleId.includes('22nd') || roleId.includes('3sq') || 
      roleId === 'echo-fc' || roleId === 'echo-fs' || roleId === 'foxtrot-fc' || roleId === 'foxtrot-fs' || 
      roleId === 'ato-echo' || roleId === 'ato-foxtrot' ||
      roleId.includes('22nd-cts') || roleId.includes('22ndcts') || roleId.includes('sq3')) {
    return 'bg-indigo-800 text-white border-indigo-900';
  }
  
  // Chief Training Officer - Orange (neutral, oversees all squadrons)
  if (roleId === 'chief-training-officer') {
    return 'bg-amber-500 text-white border-amber-600';
  }
  
  // Default - light gray
  return 'bg-slate-100 text-slate-800 border-slate-300';
};

// Role Box Component
const RoleBox = ({ role, onClick, isSelected, size = 'normal' }) => {
  const colorClass = getRoleColor(role.role_id);
  const isVacant = !role.assigned_member_name;
  
  const sizeClasses = {
    small: 'px-2 py-1 min-w-[100px]',
    normal: 'px-3 py-2 min-w-[140px]',
    large: 'px-4 py-3 min-w-[180px]'
  };
  
  return (
    <div
      onClick={() => onClick(role)}
      className={`
        ${colorClass} ${sizeClasses[size]}
        border-2 rounded cursor-pointer
        transition-all duration-150 hover:shadow-lg hover:scale-105
        ${isSelected ? 'ring-2 ring-offset-2 ring-[#00205B]' : ''}
        text-center
      `}
      data-testid={`org-node-${role.role_id}`}
    >
      <div className="font-bold text-xs leading-tight">{role.title}</div>
      <div className={`text-[10px] mt-0.5 ${isVacant ? 'italic opacity-75' : ''}`}>
        {role.assigned_member_name || 'Vacant'}
      </div>
    </div>
  );
};

// Connector line component
const Connector = ({ type = 'vertical', className = '' }) => {
  if (type === 'vertical') {
    return <div className={`w-0.5 h-4 bg-slate-400 mx-auto ${className}`} />;
  }
  if (type === 'horizontal') {
    return <div className={`h-0.5 bg-slate-400 flex-1 ${className}`} />;
  }
  return null;
};

const OrgChartPage = () => {
  const { canEdit, user } = useAuth();
  const [roles, setRoles] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editFormData, setEditFormData] = useState({});
  const [newRoleData, setNewRoleData] = useState({
    role_id: '',
    title: '',
    summary: '',
    responsibilities: '',
    reports_to: '',
    level: 0,
    order: 0
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [rolesData, participantsData] = await Promise.all([
        getOrgChartRoles(),
        getParticipants()
      ]);
      setRoles(rolesData);
      setParticipants(participantsData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Helper to get role by ID
  const getRole = (roleId) => roles.find(r => r.role_id === roleId);

  const handleRoleClick = useCallback(async (role) => {
    try {
      const fullRole = await getOrgChartRole(role.role_id);
      setSelectedRole(fullRole);
      setEditFormData({
        title: fullRole.title,
        summary: fullRole.summary || '',
        responsibilities: fullRole.responsibilities || ''
      });
      setIsSheetOpen(true);
      setIsEditing(false);
    } catch (error) {
      toast.error('Failed to load role details');
    }
  }, []);

  const handleSaveEdit = async () => {
    if (!selectedRole) return;
    try {
      await updateOrgChartRole(selectedRole.role_id, editFormData);
      toast.success('Role updated successfully');
      setIsEditing(false);
      loadData();
      const updated = await getOrgChartRole(selectedRole.role_id);
      setSelectedRole(updated);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleAssign = async (participantId) => {
    if (!selectedRole) return;
    try {
      await assignOrgChartRole(selectedRole.role_id, participantId || null);
      toast.success(participantId ? 'Member assigned' : 'Assignment removed');
      loadData();
      const updated = await getOrgChartRole(selectedRole.role_id);
      setSelectedRole(updated);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update assignment');
    }
  };

  const handleSeedDefaults = async () => {
    try {
      await seedDefaultOrgChart();
      toast.success('Default org chart created');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to seed org chart');
    }
  };

  const handleCreateRole = async () => {
    try {
      await createOrgChartRole(newRoleData);
      toast.success('Role created');
      setIsAddModalOpen(false);
      setNewRoleData({ role_id: '', title: '', summary: '', responsibilities: '', reports_to: '', level: 0, order: 0 });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create role');
    }
  };

  const handleDeleteRole = async (roleId) => {
    if (!window.confirm('Are you sure you want to delete this role?')) return;
    try {
      await deleteOrgChartRole(roleId);
      toast.success('Role deleted');
      setIsSheetOpen(false);
      setSelectedRole(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete role');
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading org chart...</div>
        </div>
      </div>
    );
  }

  // Render visual org chart matching the reference image
  const renderOrgChart = () => {
    if (roles.length === 0) return null;

    return (
      <div className="org-chart-visual p-4 overflow-x-auto">
        <div className="min-w-[1200px]">
          
          {/* ROW 1: Top Leadership */}
          <div className="flex items-start justify-center gap-2 mb-2">
            {/* SM Superintendent - Left */}
            <div className="flex flex-col items-center">
              {getRole('sm-superintendent') && (
                <RoleBox role={getRole('sm-superintendent')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sm-superintendent'} />
              )}
            </div>
            
            {/* Connector */}
            <div className="flex items-center h-12">
              <div className="w-8 h-0.5 bg-slate-400 border-dashed border-t-2 border-slate-400"></div>
            </div>
            
            {/* Encampment Commander - Center */}
            <div className="flex flex-col items-center">
              {getRole('enc-commander') && (
                <RoleBox role={getRole('enc-commander')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'enc-commander'} size="large" />
              )}
            </div>
            
            {/* Connector to right staff */}
            <div className="flex items-center h-12">
              <div className="w-8 h-0.5 border-dashed border-t-2 border-slate-400"></div>
            </div>
            
            {/* Right Staff - Finance, Chaplain, Health, Safety */}
            <div className="flex flex-col gap-1">
              <div className="flex gap-1">
                {getRole('finance') && <RoleBox role={getRole('finance')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'finance'} size="small" />}
                {getRole('chaplain-cdi') && <RoleBox role={getRole('chaplain-cdi')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chaplain-cdi'} size="small" />}
              </div>
              <div className="flex gap-1">
                {getRole('health-services') && <RoleBox role={getRole('health-services')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'health-services'} size="small" />}
                {getRole('safety') && <RoleBox role={getRole('safety')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'safety'} size="small" />}
              </div>
            </div>
          </div>
          
          <Connector type="vertical" className="h-6" />
          
          {/* ROW 2: Commandant, Cadet Commander, Deputy Support */}
          <div className="flex items-start justify-center gap-8 mb-2">
            {/* Commandant Branch */}
            <div className="flex flex-col items-center">
              {getRole('commandant') && (
                <RoleBox role={getRole('commandant')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'commandant'} />
              )}
            </div>
            
            {/* Cadet Commander Branch */}
            <div className="flex flex-col items-center">
              {getRole('cadet-commander') && (
                <RoleBox role={getRole('cadet-commander')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'cadet-commander'} />
              )}
              <Connector type="vertical" />
              <div className="flex gap-2">
                {getRole('dean-academics') && <RoleBox role={getRole('dean-academics')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'dean-academics'} size="small" />}
                {getRole('deputy-commander') && <RoleBox role={getRole('deputy-commander')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'deputy-commander'} size="small" />}
              </div>
            </div>
            
            {/* Deputy Support Branch */}
            <div className="flex flex-col items-center">
              {getRole('deputy-support') && (
                <RoleBox role={getRole('deputy-support')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'deputy-support'} />
              )}
              <Connector type="vertical" />
              <div className="flex flex-col gap-1">
                <div className="flex gap-1">
                  {getRole('word') && <RoleBox role={getRole('word')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'word'} size="small" />}
                  {getRole('public-affairs') && <RoleBox role={getRole('public-affairs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'public-affairs'} size="small" />}
                </div>
                <div className="flex gap-1">
                  {getRole('logistics') && <RoleBox role={getRole('logistics')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'logistics'} size="small" />}
                  {getRole('plans-programs') && <RoleBox role={getRole('plans-programs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'plans-programs'} size="small" />}
                </div>
                {getRole('comms') && <RoleBox role={getRole('comms')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'comms'} size="small" />}
              </div>
            </div>
          </div>
          
          {/* ROW 3: Under Commandant - Chief Instructor, Chief Training Officer */}
          <div className="flex justify-start ml-[100px] gap-4 mb-2">
            <div className="flex flex-col items-center">
              {getRole('chief-instructor') && (
                <RoleBox role={getRole('chief-instructor')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chief-instructor'} size="small" />
              )}
            </div>
            <div className="flex flex-col items-center">
              {getRole('chief-training-officer') && (
                <RoleBox role={getRole('chief-training-officer')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chief-training-officer'} />
              )}
            </div>
          </div>
          
          <Connector type="vertical" className="h-4 ml-[250px]" />
          
          {/* ROW 4: Training Officers */}
          <div className="flex justify-center gap-16 mb-2">
            {['to-sq1', 'to-sq2', 'to-sq3'].map(id => getRole(id) && (
              <div key={id} className="flex flex-col items-center">
                <RoleBox role={getRole(id)} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} size="small" />
              </div>
            ))}
          </div>
          
          <Connector type="vertical" className="h-4" />
          
          {/* ROW 5: Assistant Training Officers */}
          <div className="flex justify-center gap-16 mb-2">
            {['ato-sq1', 'ato-sq2', 'ato-sq3'].map(id => getRole(id) && (
              <div key={id} className="flex flex-col items-center">
                <RoleBox role={getRole(id)} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} size="small" />
              </div>
            ))}
          </div>
          
          <Connector type="vertical" className="h-4" />
          
          {/* ROW 6: Squadron Commanders + Support Squadron */}
          <div className="flex justify-center gap-8 mb-2">
            {['sq1-cc', 'sq2-cc', 'sq3-cc'].map(id => getRole(id) && (
              <div key={id} className="flex flex-col items-center">
                <RoleBox role={getRole(id)} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} />
                <Connector type="vertical" />
                <div className="flex flex-col gap-1">
                  {/* Squadron staff */}
                  {getRole(id.replace('-cc', '-super')) && (
                    <RoleBox role={getRole(id.replace('-cc', '-super').replace('sq', 'sq').replace('-cc', '-super'))} onClick={handleRoleClick} size="small" />
                  )}
                </div>
              </div>
            ))}
            
            {/* Support Squadron */}
            <div className="flex flex-col items-center">
              {getRole('support-sq-cc') && (
                <RoleBox role={getRole('support-sq-cc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-sq-cc'} />
              )}
              <Connector type="vertical" />
              <div className="flex flex-col gap-1">
                {['logistics-oic', 'word-oic', 'pa-ncoic', 'xp-oic', 'dfac'].map(id => getRole(id) && (
                  <RoleBox key={id} role={getRole(id)} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} size="small" />
                ))}
              </div>
            </div>
          </div>
          
          <Connector type="vertical" className="h-4" />
          
          {/* ROW 7: Flight Commanders */}
          <div className="flex justify-center gap-4 mb-2">
            {['alpha-fc', 'bravo-fc', 'charlie-fc', 'delta-fc', 'echo-fc', 'foxtrot-fc'].map(id => getRole(id) && (
              <div key={id} className="flex flex-col items-center">
                <RoleBox role={getRole(id)} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} size="small" />
              </div>
            ))}
          </div>
          
          <Connector type="vertical" className="h-4" />
          
          {/* ROW 8: Flight Sergeants */}
          <div className="flex justify-center gap-4 mb-2">
            {['alpha-fs', 'bravo-fs', 'charlie-fs', 'delta-fs', 'echo-fs', 'foxtrot-fs'].map(id => getRole(id) && (
              <div key={id} className="flex flex-col items-center">
                <RoleBox role={getRole(id)} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} size="small" />
              </div>
            ))}
          </div>
          
          {/* Flight Labels */}
          <div className="flex justify-center gap-4 mt-2">
            {['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot'].map(flight => (
              <div key={flight} className="bg-red-600 text-white text-xs px-3 py-1 rounded text-center min-w-[100px]">
                <div className="font-bold">{flight}</div>
                <div className="text-[10px]">3 elements of 5</div>
              </div>
            ))}
          </div>
          
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <Network className="w-8 h-8 text-[#00205B]" />
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Encampment 2026 Structure
            </h1>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            {roles.length} positions defined - Click any role for details
          </p>
        </div>

        {canEdit() && (
          <div className="flex items-center gap-2">
            {roles.length === 0 && ['commander', 'executive_staff'].includes(user?.role) && (
              <Button 
                variant="outline" 
                className="rounded-sm border-[#00205B] text-[#00205B]"
                onClick={handleSeedDefaults}
                data-testid="seed-org-chart-btn"
              >
                <Layers className="w-4 h-4 mr-2" />
                Load Default Structure
              </Button>
            )}
            
            <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
              <DialogTrigger asChild>
                <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-role-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Role
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                    Add New Role
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Role ID *</Label>
                      <Input
                        value={newRoleData.role_id}
                        onChange={(e) => setNewRoleData({ ...newRoleData, role_id: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                        placeholder="flight-1-commander"
                        className="mt-1 rounded-sm font-mono"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                      <Input
                        value={newRoleData.title}
                        onChange={(e) => setNewRoleData({ ...newRoleData, title: e.target.value })}
                        placeholder="Flight 1 Commander"
                        className="mt-1 rounded-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Reports To</Label>
                    <Select
                      value={newRoleData.reports_to || 'none'}
                      onValueChange={(value) => setNewRoleData({ ...newRoleData, reports_to: value === 'none' ? '' : value })}
                    >
                      <SelectTrigger className="mt-1 rounded-sm">
                        <SelectValue placeholder="Select supervisor" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None (Top Level)</SelectItem>
                        {roles.map(r => (
                          <SelectItem key={r.role_id} value={r.role_id}>{r.title}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Summary</Label>
                    <Input
                      value={newRoleData.summary}
                      onChange={(e) => setNewRoleData({ ...newRoleData, summary: e.target.value })}
                      placeholder="Brief role description"
                      className="mt-1 rounded-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Responsibilities</Label>
                    <Textarea
                      value={newRoleData.responsibilities}
                      onChange={(e) => setNewRoleData({ ...newRoleData, responsibilities: e.target.value })}
                      placeholder="- Responsibility 1&#10;- Responsibility 2"
                      className="mt-1 rounded-sm font-mono text-sm"
                      rows={4}
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button variant="outline" onClick={() => setIsAddModalOpen(false)} className="rounded-sm">Cancel</Button>
                    <Button 
                      onClick={handleCreateRole} 
                      className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
                      disabled={!newRoleData.role_id || !newRoleData.title}
                    >
                      Create Role
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {/* Empty State */}
      {roles.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <Network className="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700 mb-2">No Org Chart Defined</h3>
          <p className="text-slate-500 mb-4">
            {canEdit() 
              ? "Create roles to build your encampment's organizational structure."
              : "The org chart has not been set up yet."}
          </p>
          {canEdit() && ['commander', 'executive_staff'].includes(user?.role) && (
            <Button onClick={handleSeedDefaults} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">
              <Layers className="w-4 h-4 mr-2" />
              Load Default Encampment Structure
            </Button>
          )}
        </div>
      )}

      {/* Visual Org Chart */}
      {roles.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
          <div className="bg-[#00205B] text-white p-4 text-center">
            <h2 className="text-xl font-bold uppercase tracking-wide" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Encampment 2026 Encampment Structure
            </h2>
          </div>
          {renderOrgChart()}
        </div>
      )}

      {/* Role Details Sheet */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
              <UserCircle className="w-5 h-5" />
              Role Details
            </SheetTitle>
          </SheetHeader>

          {selectedRole && (
            <div className="mt-6 space-y-6">
              {/* Role Title */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Role Title</Label>
                {isEditing ? (
                  <Input
                    value={editFormData.title}
                    onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                    className="mt-1 rounded-sm"
                  />
                ) : (
                  <p className="text-lg font-bold text-[#00205B] mt-1">{selectedRole.title}</p>
                )}
              </div>

              {/* Assigned Member */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Assigned Member</Label>
                {canEdit() ? (
                  <Select
                    value={selectedRole.assigned_participant_id || 'vacant'}
                    onValueChange={(value) => handleAssign(value === 'vacant' ? null : value)}
                  >
                    <SelectTrigger className="mt-1 rounded-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vacant"><span className="text-amber-600 italic">Vacant</span></SelectItem>
                      {participants.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.rank} {p.first_name} {p.last_name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className={`mt-1 p-3 rounded-sm border ${selectedRole.assigned_member_name ? 'bg-slate-50 border-slate-200' : 'bg-amber-50 border-amber-200'}`}>
                    <div className="flex items-center gap-2">
                      <User className={`w-4 h-4 ${selectedRole.assigned_member_name ? 'text-[#00205B]' : 'text-amber-600'}`} />
                      <span className={selectedRole.assigned_member_name ? 'font-medium' : 'text-amber-600 italic'}>
                        {selectedRole.assigned_member_name || 'Vacant'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Role Summary */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Role Summary</Label>
                {isEditing ? (
                  <Textarea
                    value={editFormData.summary}
                    onChange={(e) => setEditFormData({ ...editFormData, summary: e.target.value })}
                    className="mt-1 rounded-sm"
                    rows={2}
                  />
                ) : (
                  <p className="mt-1 text-slate-700">
                    {selectedRole.summary || <span className="text-slate-400 italic">No summary provided</span>}
                  </p>
                )}
              </div>

              {/* Responsibilities */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Responsibilities</Label>
                {isEditing ? (
                  <Textarea
                    value={editFormData.responsibilities}
                    onChange={(e) => setEditFormData({ ...editFormData, responsibilities: e.target.value })}
                    className="mt-1 rounded-sm font-mono text-sm"
                    rows={6}
                    placeholder="- Responsibility 1&#10;- Responsibility 2"
                  />
                ) : (
                  <div className="mt-1 p-3 bg-slate-50 rounded-sm border border-slate-200">
                    {selectedRole.responsibilities ? (
                      <div className="prose prose-sm prose-slate max-w-none">
                        {selectedRole.responsibilities.split('\n').map((line, i) => (
                          <p key={i} className="my-1">
                            {line.startsWith('- ') ? (
                              <span className="flex items-start gap-2">
                                <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                                <span>{line.substring(2)}</span>
                              </span>
                            ) : line}
                          </p>
                        ))}
                      </div>
                    ) : (
                      <p className="text-slate-400 italic">No responsibilities defined</p>
                    )}
                  </div>
                )}
              </div>

              {/* Reports To */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Reports To</Label>
                <div className="mt-1 p-3 bg-slate-50 rounded-sm border border-slate-200">
                  {selectedRole.reports_to ? (
                    <div className="flex items-center gap-2">
                      <UserCircle className="w-4 h-4 text-[#00205B]" />
                      <span className="font-medium">
                        {roles.find(r => r.role_id === selectedRole.reports_to)?.title || selectedRole.reports_to}
                      </span>
                    </div>
                  ) : (
                    <span className="text-slate-500">Top Level Position</span>
                  )}
                </div>
              </div>

              {/* Direct Subordinates */}
              {selectedRole.direct_subordinates && selectedRole.direct_subordinates.length > 0 && (
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-500">Direct Subordinates</Label>
                  <div className="mt-1 space-y-2">
                    {selectedRole.direct_subordinates.map(subId => {
                      const subRole = roles.find(r => r.role_id === subId);
                      return subRole ? (
                        <div 
                          key={subId}
                          className="p-2 bg-slate-50 rounded-sm border border-slate-200 flex items-center gap-2 cursor-pointer hover:bg-slate-100"
                          onClick={() => handleRoleClick(subRole)}
                        >
                          <Users className="w-4 h-4 text-slate-500" />
                          <span className="text-sm">{subRole.title}</span>
                          {subRole.assigned_member_name && (
                            <span className="text-xs text-slate-500">- {subRole.assigned_member_name}</span>
                          )}
                        </div>
                      ) : null;
                    })}
                  </div>
                </div>
              )}

              {/* Actions */}
              {canEdit() && (
                <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
                  {isEditing ? (
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => setIsEditing(false)} className="rounded-sm">Cancel</Button>
                      <Button onClick={handleSaveEdit} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">Save Changes</Button>
                    </div>
                  ) : (
                    <Button onClick={() => setIsEditing(true)} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">
                      <Edit2 className="w-4 h-4 mr-2" />
                      Edit Role
                    </Button>
                  )}
                  {!isEditing && (
                    <Button variant="ghost" onClick={() => handleDeleteRole(selectedRole.role_id)} className="text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              )}

              {!canEdit() && (
                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <AlertCircle className="w-4 h-4" />
                    <span>You have view-only access to role details</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default OrgChartPage;
