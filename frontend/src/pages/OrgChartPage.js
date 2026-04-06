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

// Color mapping based on role type - matching flight/squadron colors
const getRoleColor = (roleId) => {
  // Executive Cadre & All Staff = #008651 (Emerald Green)
  if (['enc-commander', 'cadet-commander', 'deputy-support', 'commandant', 'sm-superintendent', 
       'deputy-commander', 'dean-academics', 'chief-instructor', 'finance', 'chaplain-cdi', 
       'health-services', 'safety', 'word', 'public-affairs', 'logistics', 'plans-programs', 'comms'].includes(roleId)) {
    return 'bg-[#008651] text-white border-[#006b41]';
  }
  
  // Support Cadre = Silver (Support Squadron Commander and all support staff)
  if (roleId === 'support-sq-cc' || roleId.startsWith('support-') || 
      roleId.includes('-super')) {
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

  // Render visual org chart matching the reference structure
  const renderOrgChart = () => {
    if (roles.length === 0) return null;

    return (
      <div className="org-chart-visual p-4 overflow-x-auto">
        <div className="min-w-[1800px]">
          
          {/* === TOP SECTION === */}
          {/* ROW 1: Encampment Commander */}
          <div className="flex justify-center mb-2">
            <div className="flex flex-col items-center">
              {getRole('enc-commander') && (
                <RoleBox role={getRole('enc-commander')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'enc-commander'} size="large" />
              )}
              <Connector type="vertical" />
              {getRole('cadet-commander') && (
                <RoleBox role={getRole('cadet-commander')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'cadet-commander'} />
              )}
            </div>
          </div>
          
          <Connector type="vertical" className="h-4" />
          
          {/* ROW 2: Three Main Branches */}
          <div className="flex justify-center gap-16 mb-4">
            {/* LEFT BRANCH: SM Position / Dean of Academics */}
            <div className="flex flex-col items-center">
              <div className="text-[10px] uppercase text-slate-400 mb-1">SM Position</div>
              {getRole('dean-academics') && (
                <RoleBox role={getRole('dean-academics')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'dean-academics'} />
              )}
            </div>
            
            {/* CENTER BRANCH: Superintendent */}
            <div className="flex flex-col items-center">
              {getRole('sm-superintendent') && (
                <RoleBox role={getRole('sm-superintendent')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sm-superintendent'} />
              )}
            </div>
            
            {/* RIGHT BRANCH: Deputy Commander of Support */}
            <div className="flex flex-col items-center">
              {getRole('deputy-support') && (
                <RoleBox role={getRole('deputy-support')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'deputy-support'} />
              )}
              <Connector type="vertical" />
              
              {/* Staff positions under Deputy Support */}
              <div className="flex gap-2 mb-2">
                {getRole('finance') && <RoleBox role={getRole('finance')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'finance'} size="small" />}
                {getRole('chaplain-cdi') && <RoleBox role={getRole('chaplain-cdi')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chaplain-cdi'} size="small" />}
              </div>
              <div className="flex gap-2">
                {getRole('safety') && <RoleBox role={getRole('safety')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'safety'} size="small" />}
                {getRole('plans-programs') && <RoleBox role={getRole('plans-programs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'plans-programs'} size="small" />}
              </div>
            </div>
          </div>
          
          {/* === COMMANDANT SECTION === */}
          <div className="flex justify-center mb-2">
            <div className="flex flex-col items-center">
              {getRole('commandant') && (
                <RoleBox role={getRole('commandant')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'commandant'} />
              )}
              <Connector type="vertical" />
              {getRole('deputy-commander') && (
                <RoleBox role={getRole('deputy-commander')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'deputy-commander'} size="small" />
              )}
            </div>
          </div>
          
          <Connector type="vertical" className="h-4" />
          
          {/* Chief Instructor & Chief Training Officer */}
          <div className="flex justify-center gap-4 mb-4">
            {getRole('chief-instructor') && (
              <RoleBox role={getRole('chief-instructor')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chief-instructor'} />
            )}
            {getRole('chief-training-officer') && (
              <RoleBox role={getRole('chief-training-officer')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'chief-training-officer'} />
            )}
          </div>
          
          <Connector type="vertical" className="h-6" />
          
          {/* === SQUADRON SECTION === */}
          {/* Squadron Commanders Row */}
          <div className="flex justify-center gap-12 mb-2">
            {/* 6th CTS Squadron */}
            <div className="flex flex-col items-center min-w-[280px]">
              {getRole('sq1-cc') && (
                <RoleBox role={getRole('sq1-cc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sq1-cc'} />
              )}
              <Connector type="vertical" />
              
              {/* Training Officer & Superintendent */}
              <div className="flex gap-2 mb-2">
                {getRole('to-sq1') && <RoleBox role={getRole('to-sq1')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'to-sq1'} size="small" />}
                {getRole('sq1-super') && <RoleBox role={getRole('sq1-super')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sq1-super'} size="small" />}
              </div>
              
              {/* Flight Labels */}
              <div className="flex justify-center gap-1 mb-1">
                <div className="text-[10px] font-bold text-sky-600 w-[100px] text-center">A</div>
                <div className="text-[10px] font-bold text-sky-600 w-[100px] text-center">B</div>
              </div>
              
              {/* Flight Commanders */}
              <div className="flex gap-2 mb-1">
                {getRole('alpha-fc') && <RoleBox role={getRole('alpha-fc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'alpha-fc'} size="small" />}
                {getRole('bravo-fc') && <RoleBox role={getRole('bravo-fc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'bravo-fc'} size="small" />}
              </div>
              
              {/* Flight Sergeants */}
              <div className="flex gap-2 mb-1">
                {getRole('alpha-fs') && <RoleBox role={getRole('alpha-fs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'alpha-fs'} size="small" />}
                {getRole('bravo-fs') && <RoleBox role={getRole('bravo-fs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'bravo-fs'} size="small" />}
              </div>
              
              {/* Flight Training Officers */}
              <div className="flex gap-2">
                {getRole('ato-alpha') && <RoleBox role={getRole('ato-alpha')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'ato-alpha'} size="small" />}
                {getRole('ato-bravo') && <RoleBox role={getRole('ato-bravo')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'ato-bravo'} size="small" />}
              </div>
            </div>
            
            {/* 21st CTS Squadron */}
            <div className="flex flex-col items-center min-w-[280px]">
              {getRole('sq2-cc') && (
                <RoleBox role={getRole('sq2-cc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sq2-cc'} />
              )}
              <Connector type="vertical" />
              
              {/* Training Officer & Superintendent */}
              <div className="flex gap-2 mb-2">
                {getRole('to-sq2') && <RoleBox role={getRole('to-sq2')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'to-sq2'} size="small" />}
                {getRole('sq2-super') && <RoleBox role={getRole('sq2-super')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sq2-super'} size="small" />}
              </div>
              
              {/* Flight Labels */}
              <div className="flex justify-center gap-1 mb-1">
                <div className="text-[10px] font-bold text-red-700 w-[100px] text-center">C</div>
                <div className="text-[10px] font-bold text-red-700 w-[100px] text-center">D</div>
              </div>
              
              {/* Flight Commanders */}
              <div className="flex gap-2 mb-1">
                {getRole('charlie-fc') && <RoleBox role={getRole('charlie-fc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'charlie-fc'} size="small" />}
                {getRole('delta-fc') && <RoleBox role={getRole('delta-fc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'delta-fc'} size="small" />}
              </div>
              
              {/* Flight Sergeants */}
              <div className="flex gap-2 mb-1">
                {getRole('charlie-fs') && <RoleBox role={getRole('charlie-fs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'charlie-fs'} size="small" />}
                {getRole('delta-fs') && <RoleBox role={getRole('delta-fs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'delta-fs'} size="small" />}
              </div>
              
              {/* Flight Training Officers */}
              <div className="flex gap-2">
                {getRole('ato-charlie') && <RoleBox role={getRole('ato-charlie')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'ato-charlie'} size="small" />}
                {getRole('ato-delta') && <RoleBox role={getRole('ato-delta')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'ato-delta'} size="small" />}
              </div>
            </div>
            
            {/* 22nd CTS Squadron */}
            <div className="flex flex-col items-center min-w-[280px]">
              {getRole('sq3-cc') && (
                <RoleBox role={getRole('sq3-cc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sq3-cc'} />
              )}
              <Connector type="vertical" />
              
              {/* Training Officer & Superintendent */}
              <div className="flex gap-2 mb-2">
                {getRole('to-sq3') && <RoleBox role={getRole('to-sq3')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'to-sq3'} size="small" />}
                {getRole('sq3-super') && <RoleBox role={getRole('sq3-super')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'sq3-super'} size="small" />}
              </div>
              
              {/* Flight Labels */}
              <div className="flex justify-center gap-1 mb-1">
                <div className="text-[10px] font-bold text-indigo-800 w-[100px] text-center">E</div>
                <div className="text-[10px] font-bold text-indigo-800 w-[100px] text-center">F</div>
              </div>
              
              {/* Flight Commanders */}
              <div className="flex gap-2 mb-1">
                {getRole('echo-fc') && <RoleBox role={getRole('echo-fc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'echo-fc'} size="small" />}
                {getRole('foxtrot-fc') && <RoleBox role={getRole('foxtrot-fc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'foxtrot-fc'} size="small" />}
              </div>
              
              {/* Flight Sergeants */}
              <div className="flex gap-2 mb-1">
                {getRole('echo-fs') && <RoleBox role={getRole('echo-fs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'echo-fs'} size="small" />}
                {getRole('foxtrot-fs') && <RoleBox role={getRole('foxtrot-fs')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'foxtrot-fs'} size="small" />}
              </div>
              
              {/* Flight Training Officers */}
              <div className="flex gap-2">
                {getRole('ato-echo') && <RoleBox role={getRole('ato-echo')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'ato-echo'} size="small" />}
                {getRole('ato-foxtrot') && <RoleBox role={getRole('ato-foxtrot')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'ato-foxtrot'} size="small" />}
              </div>
            </div>
            
            {/* Support Squadron - Full Hierarchical Structure */}
            <div className="flex flex-col items-center min-w-[560px]" data-testid="support-squadron-section">
              {getRole('support-sq-cc') && (
                <RoleBox role={getRole('support-sq-cc')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-sq-cc'} />
              )}
              <Connector type="vertical" />
              
              {/* 5 Functional Sections side-by-side */}
              <div className="flex gap-3 mt-1">
                {/* Logistics Section */}
                <div className="flex flex-col items-center gap-1" data-testid="support-logistics-section">
                  <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Logistics</div>
                  {getRole('support-logistics-oic') && <RoleBox role={getRole('support-logistics-oic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-logistics-oic'} size="small" />}
                  {getRole('support-logistics-aoic') && <RoleBox role={getRole('support-logistics-aoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-logistics-aoic'} size="small" />}
                  {getRole('support-logistics-ncoic') && <RoleBox role={getRole('support-logistics-ncoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-logistics-ncoic'} size="small" />}
                  {getRole('support-logistics-cadre') && <RoleBox role={getRole('support-logistics-cadre')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-logistics-cadre'} size="small" />}
                </div>
                
                {/* Communications Section */}
                <div className="flex flex-col items-center gap-1" data-testid="support-comms-section">
                  <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Comms</div>
                  {getRole('support-comms-oic') && <RoleBox role={getRole('support-comms-oic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-comms-oic'} size="small" />}
                  {getRole('support-comms-aoic') && <RoleBox role={getRole('support-comms-aoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-comms-aoic'} size="small" />}
                  {getRole('support-comms-ncoic') && <RoleBox role={getRole('support-comms-ncoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-comms-ncoic'} size="small" />}
                  {getRole('support-comms-cadre') && <RoleBox role={getRole('support-comms-cadre')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-comms-cadre'} size="small" />}
                </div>
                
                {/* Public Affairs Section */}
                <div className="flex flex-col items-center gap-1" data-testid="support-pa-section">
                  <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Public Affairs</div>
                  {getRole('support-pa-oic') && <RoleBox role={getRole('support-pa-oic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-pa-oic'} size="small" />}
                  {getRole('support-pa-aoic') && <RoleBox role={getRole('support-pa-aoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-pa-aoic'} size="small" />}
                  {getRole('support-pa-ncoic') && <RoleBox role={getRole('support-pa-ncoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-pa-ncoic'} size="small" />}
                  {getRole('support-pa-cadre') && <RoleBox role={getRole('support-pa-cadre')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-pa-cadre'} size="small" />}
                </div>
                
                {/* Dining Services Section */}
                <div className="flex flex-col items-center gap-1" data-testid="support-dining-section">
                  <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Dining</div>
                  {getRole('support-dining-oic') && <RoleBox role={getRole('support-dining-oic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-dining-oic'} size="small" />}
                  {getRole('support-dining-aoic') && <RoleBox role={getRole('support-dining-aoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-dining-aoic'} size="small" />}
                  {getRole('support-dining-ncoic') && <RoleBox role={getRole('support-dining-ncoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-dining-ncoic'} size="small" />}
                  {getRole('support-dining-cadre') && <RoleBox role={getRole('support-dining-cadre')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-dining-cadre'} size="small" />}
                </div>
                
                {/* Health Services Section */}
                <div className="flex flex-col items-center gap-1" data-testid="support-health-section">
                  <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Health Svc</div>
                  {getRole('support-health-oic') && <RoleBox role={getRole('support-health-oic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-health-oic'} size="small" />}
                  {getRole('support-health-aoic') && <RoleBox role={getRole('support-health-aoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-health-aoic'} size="small" />}
                  {getRole('support-health-ncoic') && <RoleBox role={getRole('support-health-ncoic')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-health-ncoic'} size="small" />}
                  {getRole('support-health-cadre') && <RoleBox role={getRole('support-health-cadre')} onClick={handleRoleClick} isSelected={selectedRole?.role_id === 'support-health-cadre'} size="small" />}
                </div>
              </div>
            </div>
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
