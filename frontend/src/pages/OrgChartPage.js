import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  getOrgChartRoles,
  getOrgChartRole,
  updateOrgChartRole,
  createOrgChartRole,
  deleteOrgChartRole,
  seedDefaultOrgChart,
  seedOrgChart,
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
  Network,
  ChevronRight,
  ChevronDown,
  User,
  Users,
  Layers,
  X,
  Edit2,
  Trash2,
  Plus,
  RefreshCw,
} from 'lucide-react';

// Category color map matching the spreadsheet color key
const CATEGORY_COLORS = {
  senior_member:   { bg: '#1a1a1a', text: '#fff', border: '#333', label: 'Senior Member' },
  executive_cadre: { bg: '#b0b0b0', text: '#1a1a1a', border: '#999', label: 'Executive Cadre' },
  training_cadre:  { bg: '#c27ba0', text: '#fff', border: '#a85d88', label: 'Training Cadre' },
  support_cadre:   { bg: '#f6b26b', text: '#1a1a1a', border: '#e09550', label: 'Support Cadre' },
  operations_cadre:{ bg: '#b6d7a8', text: '#1a1a1a', border: '#8fbc7a', label: 'Operations Cadre' },
  female_cadre:    { bg: '#c9daf8', text: '#1a1a1a', border: '#a4bde8', label: 'Female Cadre' },
  out_of_tnwg:     { bg: '#fff2cc', text: '#1a1a1a', border: '#e6d9a0', label: 'Out of TNWG Cadre' },
};

const getCatStyle = (cat) => CATEGORY_COLORS[cat] || { bg: '#e2e8f0', text: '#334155', border: '#cbd5e1', label: cat || 'Unknown' };

// ─── Tree Node Component ───────────────────────────
const TreeNode = ({ nodeData, childrenMap, depth, onSelect, selectedId, expandedSet, toggleExpand }) => {
  const children = childrenMap[nodeData.role_id] || [];
  const hasChildren = children.length > 0;
  const isExpanded = expandedSet.has(nodeData.role_id);
  const isSelected = selectedId === nodeData.role_id;
  const cat = getCatStyle(nodeData.role_category);
  const isVacant = !nodeData.assigned_name;

  return (
    <div className="tree-node" data-testid={`org-node-${nodeData.role_id}`}>
      <div
        className={`
          flex items-center gap-1.5 rounded-md cursor-pointer select-none
          transition-all duration-150 group
          ${isSelected ? 'ring-2 ring-[#00205B] ring-offset-1' : ''}
        `}
        style={{
          marginLeft: depth > 0 ? `${Math.min(depth, 6) * 20}px` : '0',
        }}
      >
        {/* Expand/collapse toggle */}
        <button
          onClick={(e) => { e.stopPropagation(); if (hasChildren) toggleExpand(nodeData.role_id); }}
          className={`w-5 h-5 flex items-center justify-center flex-shrink-0 rounded
            ${hasChildren ? 'text-slate-500 hover:bg-slate-200' : 'text-transparent'}`}
          data-testid={`toggle-${nodeData.role_id}`}
        >
          {hasChildren && (isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />)}
        </button>

        {/* Node chip */}
        <div
          onClick={() => onSelect(nodeData)}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border transition-shadow hover:shadow-md flex-1 min-w-0"
          style={{ backgroundColor: cat.bg, color: cat.text, borderColor: cat.border }}
        >
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-xs font-bold leading-tight truncate">
              {nodeData.position_title}
            </span>
            <span className={`text-[10px] leading-tight truncate ${isVacant ? 'italic opacity-60' : 'opacity-90'}`}>
              {nodeData.assigned_name || 'Vacant'}
            </span>
          </div>
          {nodeData.display_label && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-black/10 whitespace-nowrap flex-shrink-0">
              {nodeData.display_label}
            </span>
          )}
          {hasChildren && (
            <span className="text-[9px] px-1 py-0.5 rounded bg-black/10 flex-shrink-0 font-mono">
              {children.length}
            </span>
          )}
        </div>
      </div>

      {/* Children (rendered when expanded) */}
      {hasChildren && isExpanded && (
        <div className="mt-0.5">
          {children.map(child => (
            <TreeNode
              key={child.role_id}
              nodeData={child}
              childrenMap={childrenMap}
              depth={depth + 1}
              onSelect={onSelect}
              selectedId={selectedId}
              expandedSet={expandedSet}
              toggleExpand={toggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Color Key Legend ───────────────────────────────
const ColorKeyLegend = () => (
  <div className="flex flex-wrap gap-2 px-4 py-3 bg-slate-50 border-b border-slate-200">
    {Object.entries(CATEGORY_COLORS).map(([key, val]) => (
      <div key={key} className="flex items-center gap-1.5">
        <div className="w-3 h-3 rounded-sm border" style={{ backgroundColor: val.bg, borderColor: val.border }} />
        <span className="text-[10px] text-slate-600">{val.label}</span>
      </div>
    ))}
  </div>
);

// ─── Main Page ─────────────────────────────────────
const OrgChartPage = () => {
  const { canEdit, user } = useAuth();
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [expandedSet, setExpandedSet] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newRole, setNewRole] = useState({
    role_id: '', position_title: '', assigned_name: '', reports_to: '',
    role_category: '', order: 0, display_label: '',
  });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const data = await getOrgChartRoles();
      setRoles(data);
      // Auto-expand root + level 1
      const root = data.find(r => !r.reports_to);
      if (root) {
        const level1Ids = data.filter(r => r.reports_to === root.role_id).map(r => r.role_id);
        setExpandedSet(new Set([root.role_id, ...level1Ids]));
      }
    } catch (err) {
      console.error('Failed to load org chart:', err);
    } finally {
      setLoading(false);
    }
  };

  // Build children map
  const childrenMap = useMemo(() => {
    const map = {};
    roles.forEach(r => {
      const parent = r.reports_to || '__root__';
      if (!map[parent]) map[parent] = [];
      map[parent].push(r);
    });
    // Sort each group by order
    Object.values(map).forEach(arr => arr.sort((a, b) => (a.order || 0) - (b.order || 0)));
    return map;
  }, [roles]);

  const rootNodes = childrenMap['__root__'] || [];

  // Filter roles by search
  const matchesSearch = useCallback((node) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (node.position_title || '').toLowerCase().includes(term) ||
      (node.assigned_name || '').toLowerCase().includes(term) ||
      (node.role_category || '').toLowerCase().includes(term)
    );
  }, [searchTerm]);

  // Get all ancestor IDs for a given node
  const getAncestors = useCallback((roleId) => {
    const ancestors = [];
    const roleMap = {};
    roles.forEach(r => { roleMap[r.role_id] = r; });
    let current = roleMap[roleId];
    while (current && current.reports_to) {
      ancestors.push(current.reports_to);
      current = roleMap[current.reports_to];
    }
    return ancestors;
  }, [roles]);

  // Filtered + expanded for search
  const filteredExpandedSet = useMemo(() => {
    if (!searchTerm) return expandedSet;
    const set = new Set(expandedSet);
    roles.forEach(r => {
      if (matchesSearch(r)) {
        getAncestors(r.role_id).forEach(a => set.add(a));
      }
    });
    return set;
  }, [searchTerm, expandedSet, roles, matchesSearch, getAncestors]);

  const toggleExpand = useCallback((roleId) => {
    setExpandedSet(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  }, []);

  const expandAll = () => {
    setExpandedSet(new Set(roles.map(r => r.role_id)));
  };

  const collapseAll = () => {
    const root = roles.find(r => !r.reports_to);
    setExpandedSet(root ? new Set([root.role_id]) : new Set());
  };

  const handleSelect = useCallback(async (node) => {
    try {
      const full = await getOrgChartRole(node.role_id);
      setSelectedRole(full);
      setEditForm({
        position_title: full.position_title || '',
        assigned_name: full.assigned_name || '',
        job_description: full.job_description || '',
        responsible_for: full.responsible_for || '',
        supervises: full.supervises || '',
        display_label: full.display_label || '',
        role_category: full.role_category || '',
      });
      setSheetOpen(true);
      setEditing(false);
    } catch {
      toast.error('Failed to load position details');
    }
  }, []);

  const handleSave = async () => {
    if (!selectedRole) return;
    try {
      await updateOrgChartRole(selectedRole.role_id, editForm);
      toast.success('Position updated');
      setEditing(false);
      loadData();
      const updated = await getOrgChartRole(selectedRole.role_id);
      setSelectedRole(updated);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    }
  };

  const handleDelete = async (roleId) => {
    if (!window.confirm('Delete this position?')) return;
    try {
      await deleteOrgChartRole(roleId);
      toast.success('Position deleted');
      setSheetOpen(false);
      setSelectedRole(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleCreate = async () => {
    try {
      await createOrgChartRole(newRole);
      toast.success('Position created');
      setAddModalOpen(false);
      setNewRole({ role_id: '', position_title: '', assigned_name: '', reports_to: '', role_category: '', order: 0, display_label: '' });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create');
    }
  };

  const handleReseed = async () => {
    if (!window.confirm('This will wipe and reseed the entire org chart from the spreadsheet data. Continue?')) return;
    try {
      await seedOrgChart();
      toast.success('Org chart reseeded from spreadsheet');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reseed');
    }
  };

  const handleSeedDefaults = async () => {
    try {
      await seedDefaultOrgChart();
      toast.success('Org chart seeded');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to seed');
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

  // Get parent title for detail panel
  const getParentTitle = (parentId) => {
    const parent = roles.find(r => r.role_id === parentId);
    return parent ? parent.position_title : null;
  };

  return (
    <div className="p-4 lg:p-8 animate-fade-in" data-testid="org-chart-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-3">
            <Network className="w-7 h-7 text-[#00205B]" />
            <h1 className="text-xl lg:text-2xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Encampment 2026 Org Chart
            </h1>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            {roles.length} positions &middot; Click any node to view details
          </p>
        </div>
        {canEdit() && (
          <div className="flex items-center gap-2 flex-wrap">
            {roles.length === 0 && (
              <Button variant="outline" className="rounded-sm border-[#00205B] text-[#00205B]" onClick={handleSeedDefaults} data-testid="seed-org-chart-btn">
                <Layers className="w-4 h-4 mr-2" /> Load Structure
              </Button>
            )}
            {roles.length > 0 && ['commander', 'executive_staff', 'dcp'].includes(user?.role) && (
              <Button variant="outline" className="rounded-sm border-slate-300 text-slate-600" onClick={handleReseed} data-testid="reseed-orgchart-btn">
                <RefreshCw className="w-4 h-4 mr-2" /> Reseed
              </Button>
            )}
            <Dialog open={addModalOpen} onOpenChange={setAddModalOpen}>
              <DialogTrigger asChild>
                <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-role-btn">
                  <Plus className="w-4 h-4 mr-2" /> Add Position
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>Add New Position</DialogTitle>
                </DialogHeader>
                <div className="space-y-3 mt-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs uppercase text-slate-600">Role ID *</Label>
                      <Input value={newRole.role_id} onChange={(e) => setNewRole({ ...newRole, role_id: e.target.value.toLowerCase().replace(/\s+/g, '-') })} placeholder="my-position-id" className="mt-1 rounded-sm font-mono text-sm" />
                    </div>
                    <div>
                      <Label className="text-xs uppercase text-slate-600">Position Title *</Label>
                      <Input value={newRole.position_title} onChange={(e) => setNewRole({ ...newRole, position_title: e.target.value })} placeholder="Flight Commander" className="mt-1 rounded-sm" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs uppercase text-slate-600">Assigned Name</Label>
                      <Input value={newRole.assigned_name} onChange={(e) => setNewRole({ ...newRole, assigned_name: e.target.value })} placeholder="C/SSgt Smith, J" className="mt-1 rounded-sm" />
                    </div>
                    <div>
                      <Label className="text-xs uppercase text-slate-600">Category</Label>
                      <Select value={newRole.role_category || 'none'} onValueChange={(v) => setNewRole({ ...newRole, role_category: v === 'none' ? '' : v })}>
                        <SelectTrigger className="mt-1 rounded-sm"><SelectValue placeholder="Category" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          {Object.entries(CATEGORY_COLORS).map(([k, v]) => (
                            <SelectItem key={k} value={k}>{v.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs uppercase text-slate-600">Reports To</Label>
                    <Select value={newRole.reports_to || 'none'} onValueChange={(v) => setNewRole({ ...newRole, reports_to: v === 'none' ? '' : v })}>
                      <SelectTrigger className="mt-1 rounded-sm"><SelectValue placeholder="Parent" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None (Root)</SelectItem>
                        {roles.map(r => (<SelectItem key={r.role_id} value={r.role_id}>{r.position_title} {r.assigned_name ? `(${r.assigned_name})` : ''}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex justify-end gap-2 pt-3">
                    <Button variant="outline" onClick={() => setAddModalOpen(false)} className="rounded-sm">Cancel</Button>
                    <Button onClick={handleCreate} className="bg-[#00205B] hover:bg-[#001540] rounded-sm" disabled={!newRole.role_id || !newRole.position_title}>Create</Button>
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
          <h3 className="text-lg font-semibold text-slate-700 mb-2">No Org Chart</h3>
          <p className="text-slate-500 mb-4">The org chart has not been loaded yet.</p>
          {canEdit() && (
            <Button onClick={handleSeedDefaults} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">
              <Layers className="w-4 h-4 mr-2" /> Load Encampment Structure
            </Button>
          )}
        </div>
      )}

      {/* Org Chart Tree */}
      {roles.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
          {/* Title bar */}
          <div className="bg-[#00205B] text-white px-4 py-3 flex items-center justify-between">
            <h2 className="text-base font-bold uppercase tracking-wide" style={{ fontFamily: 'Chivo, sans-serif' }}>
              TNWG Encampment 2026 Structure
            </h2>
            <span className="text-xs opacity-70">{roles.length} positions</span>
          </div>

          {/* Color Key */}
          <ColorKeyLegend />

          {/* Controls bar */}
          <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-200 bg-white">
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search positions or names..."
              className="rounded-sm h-8 text-sm max-w-xs"
              data-testid="org-chart-search"
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm('')} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            )}
            <div className="ml-auto flex gap-1">
              <Button variant="ghost" size="sm" onClick={expandAll} className="text-xs h-7 px-2" data-testid="expand-all-btn">Expand All</Button>
              <Button variant="ghost" size="sm" onClick={collapseAll} className="text-xs h-7 px-2" data-testid="collapse-all-btn">Collapse</Button>
            </div>
          </div>

          {/* Tree */}
          <div className="p-4 overflow-x-auto" data-testid="org-chart-tree">
            <div className="min-w-[320px] space-y-0.5">
              {rootNodes.map(root => (
                <TreeNode
                  key={root.role_id}
                  nodeData={root}
                  childrenMap={childrenMap}
                  depth={0}
                  onSelect={handleSelect}
                  selectedId={selectedRole?.role_id}
                  expandedSet={filteredExpandedSet}
                  toggleExpand={toggleExpand}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Detail Panel (Sheet) */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
              <User className="w-5 h-5" /> Position Details
            </SheetTitle>
          </SheetHeader>

          {selectedRole && (
            <div className="mt-5 space-y-5">
              {/* Category badge */}
              {selectedRole.role_category && (
                <div className="flex items-center gap-2">
                  <div
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
                    style={{
                      backgroundColor: getCatStyle(selectedRole.role_category).bg,
                      color: getCatStyle(selectedRole.role_category).text,
                      borderColor: getCatStyle(selectedRole.role_category).border,
                    }}
                    data-testid="detail-category-badge"
                  >
                    {getCatStyle(selectedRole.role_category).label}
                  </div>
                  {selectedRole.display_label && (
                    <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">{selectedRole.display_label}</span>
                  )}
                </div>
              )}

              {/* Position Title */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Position Title</Label>
                {editing ? (
                  <Input value={editForm.position_title} onChange={(e) => setEditForm({ ...editForm, position_title: e.target.value })} className="mt-1 rounded-sm" />
                ) : (
                  <p className="text-lg font-bold text-[#00205B] mt-1" data-testid="detail-position-title">{selectedRole.position_title}</p>
                )}
              </div>

              {/* Assigned Name */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Assigned Name</Label>
                {editing ? (
                  <Input value={editForm.assigned_name} onChange={(e) => setEditForm({ ...editForm, assigned_name: e.target.value })} className="mt-1 rounded-sm" placeholder="Name or leave blank for Vacant" />
                ) : (
                  <div className={`mt-1 p-3 rounded-sm border ${selectedRole.assigned_name ? 'bg-slate-50 border-slate-200' : 'bg-amber-50 border-amber-200'}`}>
                    <div className="flex items-center gap-2">
                      <User className={`w-4 h-4 ${selectedRole.assigned_name ? 'text-[#00205B]' : 'text-amber-600'}`} />
                      <span className={selectedRole.assigned_name ? 'font-medium' : 'text-amber-600 italic'} data-testid="detail-assigned-name">
                        {selectedRole.assigned_name || 'Vacant'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Display Label */}
              {editing && (
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-500">Display Label</Label>
                  <Input value={editForm.display_label} onChange={(e) => setEditForm({ ...editForm, display_label: e.target.value })} className="mt-1 rounded-sm" placeholder="e.g. SM Level" />
                </div>
              )}

              {/* Job Description */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Job Description</Label>
                {editing ? (
                  <Textarea value={editForm.job_description} onChange={(e) => setEditForm({ ...editForm, job_description: e.target.value })} className="mt-1 rounded-sm" rows={3} placeholder="Describe the position..." />
                ) : (
                  <p className="mt-1 text-sm text-slate-700" data-testid="detail-job-description">
                    {selectedRole.job_description || <span className="text-slate-400 italic">Not defined</span>}
                  </p>
                )}
              </div>

              {/* Responsible For */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Responsible For</Label>
                {editing ? (
                  <Textarea value={editForm.responsible_for} onChange={(e) => setEditForm({ ...editForm, responsible_for: e.target.value })} className="mt-1 rounded-sm" rows={2} />
                ) : (
                  <p className="mt-1 text-sm text-slate-700" data-testid="detail-responsible-for">
                    {selectedRole.responsible_for || <span className="text-slate-400 italic">Not defined</span>}
                  </p>
                )}
              </div>

              {/* Supervises */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Supervises</Label>
                {editing ? (
                  <Textarea value={editForm.supervises} onChange={(e) => setEditForm({ ...editForm, supervises: e.target.value })} className="mt-1 rounded-sm" rows={2} />
                ) : (
                  <p className="mt-1 text-sm text-slate-700" data-testid="detail-supervises">
                    {selectedRole.supervises || <span className="text-slate-400 italic">Not defined</span>}
                  </p>
                )}
              </div>

              {/* Reports To */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Reports To</Label>
                <div className="mt-1 p-3 bg-slate-50 rounded-sm border border-slate-200">
                  {selectedRole.reports_to ? (
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-[#00205B]" />
                      <span className="font-medium text-sm" data-testid="detail-reports-to">
                        {getParentTitle(selectedRole.reports_to) || selectedRole.reports_to}
                      </span>
                    </div>
                  ) : (
                    <span className="text-slate-500 text-sm">Top Level Position</span>
                  )}
                </div>
              </div>

              {/* Direct Reports */}
              {selectedRole.children && selectedRole.children.length > 0 && (
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-500">Direct Reports ({selectedRole.children.length})</Label>
                  <div className="mt-1 space-y-1.5 max-h-48 overflow-y-auto">
                    {selectedRole.children.map(childId => {
                      const child = roles.find(r => r.role_id === childId);
                      if (!child) return null;
                      return (
                        <div
                          key={childId}
                          className="p-2 bg-slate-50 rounded-sm border border-slate-200 flex items-center gap-2 cursor-pointer hover:bg-slate-100 transition-colors"
                          onClick={() => handleSelect(child)}
                        >
                          <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: getCatStyle(child.role_category).bg }} />
                          <span className="text-xs font-medium">{child.position_title}</span>
                          {child.assigned_name && <span className="text-[10px] text-slate-500">- {child.assigned_name}</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Category (editing) */}
              {editing && (
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-500">Category</Label>
                  <Select value={editForm.role_category || 'none'} onValueChange={(v) => setEditForm({ ...editForm, role_category: v === 'none' ? '' : v })}>
                    <SelectTrigger className="mt-1 rounded-sm"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {Object.entries(CATEGORY_COLORS).map(([k, v]) => (<SelectItem key={k} value={k}>{v.label}</SelectItem>))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Actions */}
              {canEdit() && (
                <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
                  {editing ? (
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => setEditing(false)} className="rounded-sm">Cancel</Button>
                      <Button onClick={handleSave} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">Save</Button>
                    </div>
                  ) : (
                    <Button onClick={() => setEditing(true)} className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="edit-position-btn">
                      <Edit2 className="w-4 h-4 mr-2" /> Edit
                    </Button>
                  )}
                  {!editing && (
                    <Button variant="ghost" onClick={() => handleDelete(selectedRole.role_id)} className="text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50" data-testid="delete-position-btn">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
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
