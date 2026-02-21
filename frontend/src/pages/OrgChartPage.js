import React, { useState, useEffect, useMemo } from 'react';
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
  ChevronDown, 
  ChevronRight,
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
      if (error.response?.status !== 404) {
        toast.error('Failed to load org chart data');
      }
    } finally {
      setLoading(false);
    }
  };

  // Build hierarchical structure
  const orgChartTree = useMemo(() => {
    const roleMap = new Map(roles.map(r => [r.role_id, r]));
    const rootRoles = roles.filter(r => !r.reports_to);
    
    const buildTree = (role) => {
      const children = roles
        .filter(r => r.reports_to === role.role_id)
        .sort((a, b) => a.order - b.order);
      return {
        ...role,
        children: children.map(buildTree)
      };
    };
    
    return rootRoles.sort((a, b) => a.order - b.order).map(buildTree);
  }, [roles]);

  const handleRoleClick = async (role) => {
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
  };

  const handleSaveEdit = async () => {
    if (!selectedRole) return;
    try {
      await updateOrgChartRole(selectedRole.role_id, editFormData);
      toast.success('Role updated successfully');
      setIsEditing(false);
      loadData();
      // Refresh selected role
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
      setNewRoleData({
        role_id: '',
        title: '',
        summary: '',
        responsibilities: '',
        reports_to: '',
        level: 0,
        order: 0
      });
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

  // Render org chart node
  const OrgNode = ({ role, depth = 0 }) => {
    const [expanded, setExpanded] = useState(true);
    const hasChildren = role.children && role.children.length > 0;
    const isVacant = !role.assigned_member_name;

    return (
      <div className="org-node-container">
        <div 
          className={`
            org-node bg-white border-2 rounded-sm p-3 cursor-pointer
            transition-all duration-150 hover:shadow-md
            ${isVacant ? 'border-amber-300 border-dashed' : 'border-[#00205B]'}
            ${selectedRole?.role_id === role.role_id ? 'ring-2 ring-[#00205B] ring-offset-2' : ''}
          `}
          onClick={() => handleRoleClick(role)}
          data-testid={`org-node-${role.role_id}`}
        >
          <div className="flex items-start gap-2">
            <div className={`p-1.5 rounded-sm ${isVacant ? 'bg-amber-50' : 'bg-[#00205B]/10'}`}>
              <UserCircle className={`w-5 h-5 ${isVacant ? 'text-amber-600' : 'text-[#00205B]'}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-bold text-sm text-[#00205B] leading-tight">{role.title}</h4>
              <p className={`text-xs mt-1 truncate ${isVacant ? 'text-amber-600 italic' : 'text-slate-600'}`}>
                {role.assigned_member_name || 'Vacant'}
              </p>
            </div>
            {hasChildren && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="p-1 hover:bg-slate-100 rounded"
              >
                {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
        
        {hasChildren && expanded && (
          <div className="org-children mt-4 pl-8 border-l-2 border-slate-200 ml-4 space-y-3">
            {role.children.map(child => (
              <OrgNode key={child.role_id} role={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
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

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <Network className="w-8 h-8 text-[#00205B]" />
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Org Chart
            </h1>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            {roles.length} positions defined • Click any role for details
          </p>
        </div>

        {canEdit() && (
          <div className="flex items-center gap-2">
            {roles.length === 0 && user?.role === 'commander' && (
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
                        data-testid="new-role-id-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                      <Input
                        value={newRoleData.title}
                        onChange={(e) => setNewRoleData({ ...newRoleData, title: e.target.value })}
                        placeholder="Flight 1 Commander"
                        className="mt-1 rounded-sm"
                        data-testid="new-role-title-input"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Reports To</Label>
                    <Select
                      value={newRoleData.reports_to}
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
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Level</Label>
                      <Input
                        type="number"
                        value={newRoleData.level}
                        onChange={(e) => setNewRoleData({ ...newRoleData, level: parseInt(e.target.value) || 0 })}
                        className="mt-1 rounded-sm"
                        min="0"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Order</Label>
                      <Input
                        type="number"
                        value={newRoleData.order}
                        onChange={(e) => setNewRoleData({ ...newRoleData, order: parseInt(e.target.value) || 0 })}
                        className="mt-1 rounded-sm"
                        min="0"
                      />
                    </div>
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
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Responsibilities (Markdown)</Label>
                    <Textarea
                      value={newRoleData.responsibilities}
                      onChange={(e) => setNewRoleData({ ...newRoleData, responsibilities: e.target.value })}
                      placeholder="- Responsibility 1&#10;- Responsibility 2"
                      className="mt-1 rounded-sm font-mono text-sm"
                      rows={4}
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button variant="outline" onClick={() => setIsAddModalOpen(false)} className="rounded-sm">
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleCreateRole} 
                      className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
                      disabled={!newRoleData.role_id || !newRoleData.title}
                      data-testid="save-new-role-btn"
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
              : "The org chart has not been set up yet. Please check back later."}
          </p>
          {canEdit() && user?.role === 'commander' && (
            <Button 
              onClick={handleSeedDefaults}
              className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
            >
              <Layers className="w-4 h-4 mr-2" />
              Load Default Encampment Structure
            </Button>
          )}
        </div>
      )}

      {/* Org Chart Tree */}
      {roles.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm p-6 overflow-x-auto">
          <div className="min-w-[600px] space-y-4">
            {orgChartTree.map(role => (
              <OrgNode key={role.role_id} role={role} />
            ))}
          </div>
        </div>
      )}

      {/* Role Details Sheet (Side Drawer) */}
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
                    data-testid="edit-role-title"
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
                      <SelectItem value="vacant">
                        <span className="text-amber-600 italic">Vacant</span>
                      </SelectItem>
                      {participants.map(p => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.rank} {p.first_name} {p.last_name}
                        </SelectItem>
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
                    data-testid="edit-role-summary"
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
                    data-testid="edit-role-responsibilities"
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
                            <span className="text-xs text-slate-500">— {subRole.assigned_member_name}</span>
                          )}
                        </div>
                      ) : null;
                    })}
                  </div>
                </div>
              )}

              {/* Edit/Save/Delete Actions */}
              {canEdit() && (
                <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
                  {isEditing ? (
                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        onClick={() => setIsEditing(false)}
                        className="rounded-sm"
                      >
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleSaveEdit}
                        className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
                        data-testid="save-role-edit-btn"
                      >
                        Save Changes
                      </Button>
                    </div>
                  ) : (
                    <Button 
                      onClick={() => setIsEditing(true)}
                      className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
                      data-testid="edit-role-btn"
                    >
                      <Edit2 className="w-4 h-4 mr-2" />
                      Edit Role
                    </Button>
                  )}
                  
                  {!isEditing && (
                    <Button 
                      variant="ghost"
                      onClick={() => handleDeleteRole(selectedRole.role_id)}
                      className="text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                      data-testid="delete-role-btn"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              )}

              {/* Read-only notice for non-editors */}
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
