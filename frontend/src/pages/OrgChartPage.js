import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import RichTextEditor, { RichTextDisplay, plainTextToHtml } from '../components/RichTextEditor';
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
  Check,
  Printer
} from 'lucide-react';

// Color mapping based on role type
const getRoleColor = (roleId) => {
  if (!roleId) return 'bg-slate-100 text-slate-800 border-slate-300';
  
  // Senior Member roles (SM indicator in summary or known SM positions)
  const smRoles = ['enc-commander', 'dep-commander', 'chaplain', 'safety-cadre', 'chief-training-officer',
    'dep-commander-support', 'academics-superintendent', 'health-services-word',
    'support-ops-cadre'];
  if (smRoles.includes(roleId) || roleId.endsWith('-training-officer')) {
    return 'bg-[#1a1a1a] text-white border-[#333]';
  }
  
  // Cadet Commander & Group Superintendent — Gold
  if (['cadet-commander', 'group-superintendent'].includes(roleId)) {
    return 'bg-amber-500 text-white border-amber-600';
  }

  // Chief Training Officer branch — Orange
  if (roleId === 'chief-training-officer' || roleId.startsWith('training-') || roleId.startsWith('media-') || roleId.startsWith('health-') || roleId === 'word-lead') {
    return 'bg-orange-500 text-white border-orange-600';
  }

  // Deputy Commander Support branch — Emerald
  if (roleId.startsWith('dep-commander-support') || roleId.startsWith('support-') || roleId.startsWith('comms-') ||
      roleId.startsWith('finance-') || roleId.startsWith('pa-') || roleId.startsWith('dfac-') ||
      roleId.startsWith('logistics-') || roleId.startsWith('pp-')) {
    return 'bg-[#008651] text-white border-[#006b41]';
  }

  // Academics
  if (roleId.startsWith('dean-') || roleId.startsWith('dep-commander-cadets') || roleId === 'academics-superintendent') {
    return 'bg-purple-600 text-white border-purple-700';
  }

  // 6th CTS — Sky Blue
  if (roleId.startsWith('6th-cts')) {
    return 'bg-sky-500 text-white border-sky-600';
  }
  
  // 21st CTS — Dark Red
  if (roleId.startsWith('21st-cts')) {
    return 'bg-red-700 text-white border-red-800';
  }
  
  // 22nd CTS — Indigo
  if (roleId.startsWith('22nd-cts')) {
    return 'bg-indigo-800 text-white border-indigo-900';
  }
  
  // 16th OSS — Silver
  if (roleId.startsWith('16th-oss')) {
    return 'bg-slate-500 text-white border-slate-600';
  }
  
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

// CAP rank ordering for sorting (higher rank = lower index = sorts first)
const SENIOR_RANK_ORDER = [
  'Col', 'Lt Col', 'Maj', 'Capt', '1st Lt', '2nd Lt', '2dLt',
  'CMSgt', 'SMSgt', 'MSgt', 'TSgt', 'SSgt', 'SrA', 'A1C', 'Amn', 'AB',
  'SM'
];

const CADET_RANK_ORDER = [
  'C/Col', 'C/Lt Col', 'C/Maj', 'C/Capt',
  'C/1stLt', 'C/1st Lt', 'C/2dLt', 'C/2nd Lt',
  'C/CMSgt', 'C/SMSgt', 'C/MSgt', 'C/TSgt', 'C/SSgt',
  'C/SrA', 'C/A1C', 'C/Amn', 'C/AB'
];

const getRankIndex = (rank, isSenior) => {
  const orderList = isSenior ? SENIOR_RANK_ORDER : CADET_RANK_ORDER;
  const idx = orderList.findIndex(r => r === rank);
  return idx === -1 ? orderList.length : idx;
};

const sortParticipantsByRankThenName = (list, isSenior) => {
  return [...list].sort((a, b) => {
    const rankDiff = getRankIndex(a.rank, isSenior) - getRankIndex(b.rank, isSenior);
    if (rankDiff !== 0) return rankDiff;
    return (a.last_name || '').localeCompare(b.last_name || '');
  });
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
  const orgChartScrollRef = useRef(null);
  const [newRoleData, setNewRoleData] = useState({
    role_id: '',
    title: '',
    summary: '',
    responsibilities: '',
    reports_to: '',
    level: 0,
    order: 0
  });

  // Auto-scroll org chart to center on mobile
  useEffect(() => {
    if (!loading && roles.length > 0 && orgChartScrollRef.current) {
      const scrollEl = orgChartScrollRef.current.querySelector('.org-chart-visual');
      if (scrollEl && window.innerWidth < 1024) {
        const scrollTarget = (scrollEl.scrollWidth - scrollEl.clientWidth) / 2;
        scrollEl.scrollLeft = scrollTarget;
      }
    }
  }, [loading, roles]);

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

  // Build lookup maps for data-driven rendering
  const roleMap = {};
  const childrenMap = {};
  roles.forEach(r => {
    roleMap[r.role_id] = r;
    const parent = r.reports_to || '__root__';
    if (!childrenMap[parent]) childrenMap[parent] = [];
    childrenMap[parent].push(r);
  });
  Object.values(childrenMap).forEach(arr => arr.sort((a, b) => (a.order || 0) - (b.order || 0)));
  const getChildren = (parentId) => childrenMap[parentId] || [];

  const StaffBranch = ({ roleId, label }) => {
    const r = roleMap[roleId];
    if (!r) return null;
    const kids = getChildren(roleId);
    return (
      <div className="flex flex-col items-center border border-slate-100 rounded-lg p-2 bg-white/30 min-w-[110px]">
        {label && <div className="text-[9px] uppercase text-slate-400 font-bold mb-0.5">{label}</div>}
        <RoleBox role={r} onClick={handleRoleClick} isSelected={selectedRole?.role_id === roleId} size="small" />
        {kids.length > 0 && (
          <div className="flex flex-col items-center gap-0.5 mt-1">
            {kids.map(kid => {
              const grandkids = getChildren(kid.role_id);
              return (
                <div key={kid.role_id} className="flex flex-col items-center">
                  <RoleBox role={kid} onClick={handleRoleClick} isSelected={selectedRole?.role_id === kid.role_id} size="small" />
                  {grandkids.length > 0 && (
                    <div className="flex gap-0.5 mt-0.5 flex-wrap justify-center">
                      {grandkids.map(gk => <RoleBox key={gk.role_id} role={gk} onClick={handleRoleClick} isSelected={selectedRole?.role_id === gk.role_id} size="small" />)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const SquadronBlock = ({ prefix, label }) => {
    const cmdr = roleMap[`${prefix}-commander`];
    const to = roleMap[`${prefix}-training-officer`];
    const sup = roleMap[`${prefix}-superintendent`];
    const fs = roleMap[`${prefix}-first-sergeant`];
    const flights = ['a', 'b', 'c', 'd', 'e', 'f'];
    const supportIds = [`${prefix}-logistics`, `${prefix}-public-affairs`, `${prefix}-communications`, `${prefix}-dining-facility`, `${prefix}-training-officer-sq`, `${prefix}-word`];
    return (
      <div className="flex flex-col items-center min-w-[260px] border border-slate-200 rounded-lg p-3 bg-white/50">
        <div className="text-[10px] uppercase text-slate-400 font-bold mb-1 tracking-wider">{label}</div>
        {cmdr && <RoleBox role={cmdr} onClick={handleRoleClick} isSelected={selectedRole?.role_id === cmdr.role_id} size="normal" />}
        <Connector type="vertical" />
        <div className="flex gap-1 mb-2 flex-wrap justify-center">
          {to && <RoleBox role={to} onClick={handleRoleClick} isSelected={selectedRole?.role_id === to.role_id} size="small" />}
          {sup && <RoleBox role={sup} onClick={handleRoleClick} isSelected={selectedRole?.role_id === sup.role_id} size="small" />}
          {fs && <RoleBox role={fs} onClick={handleRoleClick} isSelected={selectedRole?.role_id === fs.role_id} size="small" />}
        </div>
        <div className="flex gap-1 mb-0.5">{flights.map(l => <div key={l} className="text-[10px] font-bold text-center w-[90px] uppercase">{l}</div>)}</div>
        <div className="flex gap-1 mb-0.5">
          {flights.map(l => { const fc = roleMap[`${prefix}-flt-${l}-commander`]; return fc ? <RoleBox key={l} role={fc} onClick={handleRoleClick} isSelected={selectedRole?.role_id === fc.role_id} size="small" /> : <div key={l} className="w-[90px]" />; })}
        </div>
        <div className="flex gap-1 mb-2">
          {flights.map(l => { const fsg = roleMap[`${prefix}-flt-${l}-sergeant`]; return fsg ? <RoleBox key={l} role={fsg} onClick={handleRoleClick} isSelected={selectedRole?.role_id === fsg.role_id} size="small" /> : <div key={l} className="w-[90px]" />; })}
        </div>
        <div className="flex gap-1 flex-wrap justify-center">
          {supportIds.map(sid => { const sr = roleMap[sid]; return sr ? <RoleBox key={sid} role={sr} onClick={handleRoleClick} isSelected={selectedRole?.role_id === sr.role_id} size="small" /> : null; })}
        </div>
      </div>
    );
  };

  const renderOrgChart = () => {
    if (roles.length === 0) return null;
    return (
      <div className="org-chart-visual p-4 overflow-x-auto">
        <div className="min-w-[2400px]">
          <div className="flex justify-center mb-3">
            {roleMap['enc-commander'] && <RoleBox role={roleMap['enc-commander']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'enc-commander'} size="large" />}
          </div>
          <Connector type="vertical" className="h-4" />
          <div className="flex justify-center gap-4 mb-3">
            {['dep-commander', 'cadet-commander', 'chaplain', 'safety-cadre', 'female-cadre'].map(id => {
              const r = roleMap[id]; if (!r) return null;
              const kids = id === 'cadet-commander' ? getChildren(id) : [];
              return (<div key={id} className="flex flex-col items-center">
                <RoleBox role={r} onClick={handleRoleClick} isSelected={selectedRole?.role_id === id} size="normal" />
                {kids.length > 0 && <><Connector type="vertical" /><div className="flex gap-1">{kids.map(k => <RoleBox key={k.role_id} role={k} onClick={handleRoleClick} isSelected={selectedRole?.role_id === k.role_id} size="small" />)}</div></>}
              </div>);
            })}
          </div>
          <Connector type="vertical" className="h-4" />
          <div className="flex justify-center gap-6 mb-3">
            <div className="flex flex-col items-center">
              {roleMap['academics-superintendent'] && <RoleBox role={roleMap['academics-superintendent']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'academics-superintendent'} size="normal" />}
              <Connector type="vertical" />
              {roleMap['dean-academics'] && <RoleBox role={roleMap['dean-academics']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'dean-academics'} size="small" />}
              {roleMap['dep-commander-cadets'] && <RoleBox role={roleMap['dep-commander-cadets']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'dep-commander-cadets'} size="small" />}
            </div>
            <div className="flex flex-col items-center">
              {roleMap['chief-training-officer'] && <RoleBox role={roleMap['chief-training-officer']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chief-training-officer'} size="normal" />}
              <Connector type="vertical" />
              <div className="flex gap-2 flex-wrap justify-center">
                <StaffBranch roleId="training-oic" label="Training OIC" />
                <StaffBranch roleId="training-aoic" label="Training AOIC" />
                <StaffBranch roleId="training-cadets-lead" label="Cadets/SM" />
                <StaffBranch roleId="media-publishing" label="Media" />
                <StaffBranch roleId="health-services-word" label="Health/WORD" />
              </div>
            </div>
            <div className="flex flex-col items-center">
              {roleMap['dep-commander-support'] && <RoleBox role={roleMap['dep-commander-support']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'dep-commander-support'} size="normal" />}
              <Connector type="vertical" />
              <div className="flex gap-1 mb-2">{roleMap['support-ops-cadre'] && <RoleBox role={roleMap['support-ops-cadre']} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-ops-cadre'} size="small" />}</div>
              <div className="flex gap-2 flex-wrap justify-center">
                <StaffBranch roleId="support-communications" label="Comms" />
                <StaffBranch roleId="support-finance" label="Finance" />
                <StaffBranch roleId="support-public-affairs" label="PA" />
                <StaffBranch roleId="support-dining-facility" label="DFAC" />
                <StaffBranch roleId="support-logistics" label="Logistics" />
                <StaffBranch roleId="support-plans-programs" label="Plans" />
              </div>
            </div>
          </div>
          <Connector type="vertical" className="h-6" />
          <div className="flex justify-center gap-4">
            <SquadronBlock prefix="6th-cts" label="6th CTS" />
            <SquadronBlock prefix="21st-cts" label="21st CTS" />
            <SquadronBlock prefix="22nd-cts" label="22nd CTS" />
            <SquadronBlock prefix="16th-oss" label="16th OPS SUP SQ" />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 lg:p-8 animate-fade-in print-container">
      {/* Print-only header */}
      <div className="print-header">
        <h1>Tennessee Wing CAP Encampment — Org Chart</h1>
        <div className="print-meta">
          <div>Printed {new Date().toLocaleDateString()}</div>
          <div>{roles.length} positions</div>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 no-print">
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
            <Button
              variant="outline"
              className="rounded-sm border-slate-300 text-slate-700 hover:bg-slate-50"
              onClick={() => window.print()}
              data-testid="print-orgchart-btn"
            >
              <Printer className="w-4 h-4 mr-2" />
              Print
            </Button>
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
                    <div className="mt-1">
                      <RichTextEditor
                        value={newRoleData.responsibilities}
                        onChange={(val) => setNewRoleData({ ...newRoleData, responsibilities: val })}
                        placeholder="Enter responsibilities..."
                      />
                    </div>
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
          {/* Mobile scroll hint */}
          <div className="lg:hidden bg-blue-50 border-b border-blue-100 px-4 py-2 flex items-center justify-center gap-2 text-xs text-blue-600">
            <svg className="w-4 h-4 animate-bounce-x" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
            Swipe to scroll through the org chart
          </div>
          <div ref={orgChartScrollRef}>
            {renderOrgChart()}
          </div>
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
                    <SelectTrigger className="mt-1 rounded-sm" data-testid="assign-member-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vacant"><span className="text-amber-600 italic">Vacant</span></SelectItem>
                      {(() => {
                        const seniors = sortParticipantsByRankThenName(
                          participants.filter(p => p.member_type === 'SENIOR'),
                          true
                        );
                        const cadets = sortParticipantsByRankThenName(
                          participants.filter(p => p.member_type !== 'SENIOR'),
                          false
                        );
                        return (
                          <>
                            {seniors.length > 0 && (
                              <>
                                <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-50 sticky">Senior Members</div>
                                {seniors.map(p => (
                                  <SelectItem key={p.id} value={p.id}>
                                    <span className="font-medium">{p.rank}</span> {p.last_name}, {p.first_name}
                                  </SelectItem>
                                ))}
                              </>
                            )}
                            {cadets.length > 0 && (
                              <>
                                <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-50 sticky mt-1">Cadets</div>
                                {cadets.map(p => (
                                  <SelectItem key={p.id} value={p.id}>
                                    <span className="font-medium">{p.rank}</span> {p.last_name}, {p.first_name}
                                  </SelectItem>
                                ))}
                              </>
                            )}
                          </>
                        );
                      })()}
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
                  <div className="mt-1">
                    <RichTextEditor
                      value={plainTextToHtml(editFormData.responsibilities)}
                      onChange={(val) => setEditFormData({ ...editFormData, responsibilities: val })}
                      placeholder="Enter responsibilities..."
                    />
                  </div>
                ) : (
                  <div className="mt-1 p-3 bg-slate-50 rounded-sm border border-slate-200">
                    {selectedRole.responsibilities ? (
                      <RichTextDisplay html={plainTextToHtml(selectedRole.responsibilities)} />
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
