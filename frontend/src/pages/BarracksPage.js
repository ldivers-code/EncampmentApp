import React, { useState, useEffect, useCallback } from 'react';
import {
  getBarracks, getBarracksDetail, assignBunk, unassignBunk, getUnassignedParticipants
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Home, Users, Search, RefreshCw, ArrowLeft, ChevronUp, ChevronDown,
  X, UserPlus, BedDouble, Building2
} from 'lucide-react';

// Bunk bed visual component
const BunkBed = ({ bunk, onAssign, onUnassign, isHighlighted }) => {
  const topOccupied = bunk.top.occupied;
  const bottomOccupied = bunk.bottom.occupied;

  const BunkSlot = ({ position, data, bunkNum }) => {
    const occupied = data.occupied;
    return (
      <div
        className={`relative flex items-center justify-between px-2 py-1.5 border rounded-sm text-xs cursor-pointer transition-all group ${
          occupied
            ? 'bg-blue-50 border-blue-300 hover:bg-blue-100'
            : 'bg-slate-50 border-dashed border-slate-300 hover:bg-emerald-50 hover:border-emerald-300'
        } ${isHighlighted ? 'ring-2 ring-amber-400' : ''}`}
        onClick={() => occupied ? null : onAssign(bunkNum, position)}
        data-testid={`bunk-${bunkNum}-${position}`}
      >
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {position === 'top' ? (
            <ChevronUp className="w-3 h-3 text-slate-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="w-3 h-3 text-slate-400 flex-shrink-0" />
          )}
          {occupied ? (
            <div className="min-w-0">
              <p className="font-medium text-[#00205B] truncate text-[11px] leading-tight">{data.participant_name}</p>
              <p className="text-[9px] text-slate-400 capitalize">{(data.participant_type || '').replace(/_/g, ' ')}{data.flight ? ` | ${data.flight}` : ''}</p>
            </div>
          ) : (
            <span className="text-slate-400 italic">Empty</span>
          )}
        </div>
        {occupied && (
          <button
            onClick={(e) => { e.stopPropagation(); onUnassign(bunkNum, position); }}
            className="opacity-0 group-hover:opacity-100 w-4 h-4 bg-red-500 text-white rounded-full flex items-center justify-center flex-shrink-0 ml-1"
            title="Remove"
            data-testid={`remove-${bunkNum}-${position}`}
          >
            <X className="w-2.5 h-2.5" />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-0.5 w-full" data-testid={`bunk-bed-${bunk.bunk_number}`}>
      <div className="text-[9px] text-center text-slate-400 font-mono">#{bunk.bunk_number}</div>
      <BunkSlot position="top" data={bunk.top} bunkNum={bunk.bunk_number} />
      <BunkSlot position="bottom" data={bunk.bottom} bunkNum={bunk.bunk_number} />
    </div>
  );
};

// Open Bay Layout
const OpenBayLayout = ({ barracks, onAssign, onUnassign }) => {
  if (!barracks?.bunks) return null;

  const leftBunks = barracks.bunks.filter(b => b.wall === 'left');
  const rightBunks = barracks.bunks.filter(b => b.wall === 'right');

  return (
    <div className="bg-white border-2 border-slate-300 rounded-sm p-4" data-testid="open-bay-layout">
      {/* Bay header */}
      <div className="text-center mb-4">
        <div className="inline-block px-3 py-1 bg-slate-100 rounded text-xs text-slate-500 font-mono">ENTRANCE</div>
      </div>

      <div className="flex gap-6">
        {/* Left Wall */}
        <div className="flex-1">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-2 text-center">Left Wall</div>
          <div className="space-y-2">
            {leftBunks.map(bunk => (
              <BunkBed
                key={bunk.bunk_number}
                bunk={bunk}
                onAssign={onAssign}
                onUnassign={onUnassign}
              />
            ))}
          </div>
        </div>

        {/* Center Aisle */}
        <div className="w-8 flex-shrink-0 flex flex-col items-center justify-center">
          <div className="w-px h-full bg-slate-200 relative">
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 bg-white px-1 text-[8px] text-slate-300 rotate-90 whitespace-nowrap">
              AISLE
            </div>
          </div>
        </div>

        {/* Right Wall */}
        <div className="flex-1">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-2 text-center">Right Wall</div>
          <div className="space-y-2">
            {rightBunks.map(bunk => (
              <BunkBed
                key={bunk.bunk_number}
                bunk={bunk}
                onAssign={onAssign}
                onUnassign={onUnassign}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Bay footer */}
      <div className="text-center mt-4">
        <div className="inline-block px-3 py-1 bg-slate-100 rounded text-xs text-slate-500 font-mono">REAR WALL</div>
      </div>
    </div>
  );
};

// Participant picker dialog
const ParticipantPicker = ({ isOpen, onClose, onSelect, participants, loading }) => {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all');

  const filtered = participants.filter(p => {
    if (search) {
      const q = search.toLowerCase();
      if (!p.name.toLowerCase().includes(q) && !p.capid?.toLowerCase().includes(q)) return false;
    }
    if (filterType === 'student' && p.category !== 'student') return false;
    if (filterType === 'cadre' && p.category !== 'cadre') return false;
    return true;
  });

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[80vh]" data-testid="participant-picker">
        <DialogHeader>
          <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Assign to Bunk
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Search name or CAPID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 rounded-sm text-sm"
                data-testid="picker-search"
              />
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-28 rounded-sm text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="student">Students</SelectItem>
                <SelectItem value="cadre">Cadre</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <p className="text-xs text-slate-500">{filtered.length} unassigned participants</p>
          <div className="max-h-[400px] overflow-y-auto space-y-1">
            {loading ? (
              <div className="text-center py-8 text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                Loading...
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-center py-8 text-slate-400">No unassigned participants match</p>
            ) : (
              filtered.map(p => (
                <button
                  key={p.participant_id}
                  onClick={() => onSelect(p.participant_id)}
                  className="w-full flex items-center justify-between p-2.5 border border-slate-200 rounded-sm hover:bg-blue-50 hover:border-blue-300 transition-colors text-left"
                  data-testid={`pick-${p.capid || p.participant_id}`}
                >
                  <div>
                    <p className="font-medium text-sm text-[#00205B]">{p.name}</p>
                    <p className="text-[10px] text-slate-500">
                      {p.capid && `CAPID: ${p.capid} | `}
                      <span className="capitalize">{p.category}</span>
                      {p.flight && ` | ${p.flight}`}
                      {p.gender && ` | ${p.gender}`}
                    </p>
                  </div>
                  <UserPlus className="w-4 h-4 text-slate-400" />
                </button>
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Main Barracks Page
const BarracksPage = () => {
  const [barracks, setBarracks] = useState([]);
  const [selectedBarracks, setSelectedBarracks] = useState(null);
  const [barracksDetail, setBarracksDetail] = useState(null);
  const [unassigned, setUnassigned] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pendingAssign, setPendingAssign] = useState(null); // {bunkNumber, position}
  const [unassignedLoading, setUnassignedLoading] = useState(false);

  const loadBarracks = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getBarracks();
      setBarracks(data);
    } catch (error) {
      toast.error('Failed to load barracks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBarracks();
  }, [loadBarracks]);

  const selectBarracks = async (barracksId) => {
    try {
      setDetailLoading(true);
      setSelectedBarracks(barracksId);
      const data = await getBarracksDetail(barracksId);
      setBarracksDetail(data);
    } catch (error) {
      toast.error('Failed to load barracks detail');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleAssignClick = async (bunkNumber, position) => {
    setPendingAssign({ bunkNumber, position });
    setUnassignedLoading(true);
    try {
      const data = await getUnassignedParticipants();
      setUnassigned(data);
    } catch (error) {
      toast.error('Failed to load participants');
    } finally {
      setUnassignedLoading(false);
    }
    setPickerOpen(true);
  };

  const handleSelectParticipant = async (participantId) => {
    if (!pendingAssign || !selectedBarracks) return;
    try {
      await assignBunk(selectedBarracks, participantId, pendingAssign.bunkNumber, pendingAssign.position);
      toast.success('Bunk assigned');
      setPickerOpen(false);
      setPendingAssign(null);
      // Reload
      const [detail, list] = await Promise.all([
        getBarracksDetail(selectedBarracks),
        getBarracks()
      ]);
      setBarracksDetail(detail);
      setBarracks(list);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Assignment failed');
    }
  };

  const handleUnassign = async (bunkNumber, position) => {
    if (!selectedBarracks) return;
    try {
      await unassignBunk(selectedBarracks, bunkNumber, position);
      toast.success('Bunk cleared');
      const [detail, list] = await Promise.all([
        getBarracksDetail(selectedBarracks),
        getBarracks()
      ]);
      setBarracksDetail(detail);
      setBarracks(list);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove assignment');
    }
  };

  // Overview: barracks cards
  if (!selectedBarracks) {
    return (
      <div className="p-4 sm:p-6 max-w-full" data-testid="barracks-page">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-3">
          <div>
            <h1 className="text-2xl font-black text-[#00205B] uppercase tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Barracks & Bunk Assignment
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">VTS Catoosa Cantonment Area - Open Bay Barracks</p>
          </div>
          <Button variant="outline" size="sm" onClick={loadBarracks} className="rounded-sm">
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </Button>
        </div>

        {/* Total stats */}
        {!loading && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="bg-white border border-slate-200 rounded-sm p-3 text-center">
              <p className="text-2xl font-bold text-[#00205B]">{barracks.reduce((s, b) => s + b.capacity, 0)}</p>
              <p className="text-[10px] uppercase tracking-wide text-slate-500">Total Capacity</p>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-3 text-center">
              <p className="text-2xl font-bold text-emerald-700">{barracks.reduce((s, b) => s + b.assigned, 0)}</p>
              <p className="text-[10px] uppercase tracking-wide text-emerald-600">Assigned</p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-sm p-3 text-center">
              <p className="text-2xl font-bold text-amber-700">{barracks.reduce((s, b) => s + b.available, 0)}</p>
              <p className="text-[10px] uppercase tracking-wide text-amber-600">Available</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-5 h-5 animate-spin text-slate-400 mr-2" />
            <span className="text-slate-500">Loading barracks...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {barracks.map(b => {
              const pct = b.capacity > 0 ? (b.assigned / b.capacity) * 100 : 0;
              return (
                <button
                  key={b.barracks_id}
                  onClick={() => selectBarracks(b.barracks_id)}
                  className="bg-white border border-slate-200 rounded-sm p-5 text-left hover:border-[#00205B] hover:shadow-md transition-all group"
                  data-testid={`barracks-card-${b.barracks_id}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-5 h-5 text-[#00205B]" />
                        <h3 className="text-lg font-bold text-[#00205B]">{b.name}</h3>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{b.description}</p>
                    </div>
                    <BedDouble className="w-5 h-5 text-slate-300 group-hover:text-[#00205B] transition-colors" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-500">{b.assigned} / {b.capacity} assigned</span>
                      <span className="font-bold">{Math.round(pct)}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          pct > 90 ? 'bg-red-500' : pct > 60 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-400">
                      <span>{b.total_bunks} bunks ({b.left_wall_bunks}L + {b.right_wall_bunks}R)</span>
                      <span>{b.available} spots open</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Detail view: Open Bay layout
  return (
    <div className="p-4 sm:p-6 max-w-full" data-testid="barracks-detail-page">
      <div className="flex items-center gap-3 mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { setSelectedBarracks(null); setBarracksDetail(null); }}
          className="rounded-sm"
          data-testid="back-to-barracks"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-black text-[#00205B] uppercase tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {barracksDetail?.name || selectedBarracks}
          </h1>
          <p className="text-sm text-slate-500">
            {barracksDetail?.description} — {barracksDetail?.assigned || 0}/{barracksDetail?.capacity || 50} assigned, {barracksDetail?.available || 50} open
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => selectBarracks(selectedBarracks)} className="rounded-sm">
          <RefreshCw className="w-4 h-4 mr-1" /> Refresh
        </Button>
      </div>

      {detailLoading ? (
        <div className="flex items-center justify-center py-16">
          <RefreshCw className="w-5 h-5 animate-spin text-slate-400 mr-2" />
          <span className="text-slate-500">Loading layout...</span>
        </div>
      ) : (
        <div className="max-w-2xl mx-auto">
          <OpenBayLayout
            barracks={barracksDetail}
            onAssign={handleAssignClick}
            onUnassign={handleUnassign}
          />
        </div>
      )}

      {/* Participant Picker */}
      <ParticipantPicker
        isOpen={pickerOpen}
        onClose={() => { setPickerOpen(false); setPendingAssign(null); }}
        onSelect={handleSelectParticipant}
        participants={unassigned}
        loading={unassignedLoading}
      />
    </div>
  );
};

export default BarracksPage;
