import React, { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { updateParticipantAssignment } from '../services/api';
import { toast } from 'sonner';
import { GripVertical, Search, User, Users, X } from 'lucide-react';
import { Input } from '../components/ui/input';

const FLIGHTS = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot'];
const FLIGHT_COLORS = {
  Alpha: { bg: 'bg-blue-600', light: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', ring: 'ring-blue-400' },
  Bravo: { bg: 'bg-emerald-600', light: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', ring: 'ring-emerald-400' },
  Charlie: { bg: 'bg-amber-600', light: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', ring: 'ring-amber-400' },
  Delta: { bg: 'bg-purple-600', light: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', ring: 'ring-purple-400' },
  Echo: { bg: 'bg-rose-600', light: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', ring: 'ring-rose-400' },
  Foxtrot: { bg: 'bg-teal-600', light: 'bg-teal-50', border: 'border-teal-200', text: 'text-teal-700', ring: 'ring-teal-400' },
  Unassigned: { bg: 'bg-slate-500', light: 'bg-slate-50', border: 'border-slate-300', text: 'text-slate-700', ring: 'ring-slate-400' },
};

const SQUADRON_MAP = {
  alpha: '6th_cts', bravo: '6th_cts',
  charlie: '21st_cts', delta: '21st_cts',
  echo: '22nd_cts', foxtrot: '22nd_cts',
};

// ─── Draggable Participant Card ───
const DraggableCard = ({ participant, flightColor }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: participant.id,
    data: { participant, type: 'participant' },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const pType = participant.participant_type;
  const isCadre = pType === 'cadre' || pType === 'exec_cadre';

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 px-2.5 py-1.5 rounded border bg-white hover:shadow-sm transition-shadow cursor-grab active:cursor-grabbing group ${
        isDragging ? 'shadow-lg ring-2 ' + (flightColor?.ring || 'ring-slate-400') : 'border-slate-200'
      }`}
      data-testid={`drag-card-${participant.id}`}
      {...attributes}
      {...listeners}
    >
      <GripVertical className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-900 truncate">
          {participant.last_name}, {participant.first_name}
        </p>
        <p className="text-[10px] text-slate-500 truncate">
          {participant.rank || ''} {participant.capid ? `• ${participant.capid}` : ''} {participant.unit ? `• ${participant.unit}` : ''}
        </p>
      </div>
      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold flex-shrink-0 ${
        isCadre ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
      }`}>
        {isCadre ? 'CADRE' : 'STU'}
      </span>
    </div>
  );
};

// ─── Flight Column ───
const FlightColumn = ({ flightName, participants, color, searchTerm }) => {
  const filteredParticipants = useMemo(() => {
    if (!searchTerm) return participants;
    const term = searchTerm.toLowerCase();
    return participants.filter(p =>
      (p.last_name || '').toLowerCase().includes(term) ||
      (p.first_name || '').toLowerCase().includes(term) ||
      (p.capid || '').toLowerCase().includes(term)
    );
  }, [participants, searchTerm]);

  const studentCount = participants.filter(p => p.participant_type === 'basic_student' || p.participant_type === 'student').length;
  const cadreCount = participants.filter(p => p.participant_type === 'cadre' || p.participant_type === 'exec_cadre').length;

  return (
    <div
      className={`flex flex-col rounded-sm border ${color.border} overflow-hidden h-full`}
      data-testid={`flight-column-${flightName.toLowerCase()}`}
    >
      {/* Column Header */}
      <div className={`${color.bg} px-3 py-2 flex items-center justify-between`}>
        <div>
          <h3 className="text-white font-bold text-sm uppercase tracking-wide">{flightName}</h3>
          <p className="text-white/70 text-[10px]">{studentCount} stu • {cadreCount} cadre</p>
        </div>
        <div className="bg-white/20 rounded px-2 py-0.5">
          <span className="text-white font-bold text-sm">{participants.length}</span>
        </div>
      </div>

      {/* Droppable Area */}
      <SortableContext
        items={filteredParticipants.map(p => p.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className={`flex-1 ${color.light} p-1.5 space-y-1 overflow-y-auto min-h-[120px]`}
          style={{ maxHeight: 'calc(100vh - 300px)' }}>
          {filteredParticipants.length === 0 ? (
            <div className="flex items-center justify-center h-20 text-slate-400">
              <p className="text-xs italic">
                {searchTerm ? 'No matches' : 'Drop here'}
              </p>
            </div>
          ) : (
            filteredParticipants.map((p) => (
              <DraggableCard key={p.id} participant={p} flightColor={color} />
            ))
          )}
        </div>
      </SortableContext>
    </div>
  );
};

// ─── Drag Overlay Card (follows cursor) ───
const DragOverlayCard = ({ participant }) => {
  if (!participant) return null;
  const isCadre = participant.participant_type === 'cadre' || participant.participant_type === 'exec_cadre';
  return (
    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded border border-[#00205B] bg-white shadow-xl ring-2 ring-[#00205B]/30 w-[220px]">
      <GripVertical className="w-3.5 h-3.5 text-[#00205B] flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-bold text-[#00205B] truncate">{participant.last_name}, {participant.first_name}</p>
        <p className="text-[10px] text-slate-500">{participant.rank} • {participant.capid}</p>
      </div>
      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${isCadre ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}>
        {isCadre ? 'CADRE' : 'STU'}
      </span>
    </div>
  );
};

// ─── Main Flight Manager Component ───
const FlightManager = ({ participants, onUpdate }) => {
  const [activeParticipant, setActiveParticipant] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [updating, setUpdating] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  // Only students and cadre are manageable
  const manageable = useMemo(() =>
    participants.filter(p =>
      ['basic_student', 'student', 'cadre', 'exec_cadre'].includes(p.participant_type)
    ),
    [participants]
  );

  // Group by flight
  const flightGroups = useMemo(() => {
    const groups = {};
    FLIGHTS.forEach(f => { groups[f] = []; });
    groups['Unassigned'] = [];

    manageable.forEach(p => {
      const flight = (p.flight || '').charAt(0).toUpperCase() + (p.flight || '').slice(1).toLowerCase();
      if (FLIGHTS.includes(flight)) {
        groups[flight].push(p);
      } else {
        groups['Unassigned'].push(p);
      }
    });

    // Sort each group by last name
    Object.keys(groups).forEach(key => {
      groups[key].sort((a, b) => (a.last_name || '').localeCompare(b.last_name || ''));
    });

    return groups;
  }, [manageable]);

  const findFlightForParticipant = (participantId) => {
    for (const [flight, members] of Object.entries(flightGroups)) {
      if (members.some(m => m.id === participantId)) return flight;
    }
    return null;
  };

  const handleDragStart = (event) => {
    const { active } = event;
    const participant = manageable.find(p => p.id === active.id);
    setActiveParticipant(participant || null);
  };

  const handleDragOver = () => {};

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveParticipant(null);

    if (!over || !active) return;

    const activeId = active.id;
    const overId = over.id;

    // Determine source and target flights
    const sourceFlight = findFlightForParticipant(activeId);

    let targetFlight = null;

    // Check if dropped over a flight column container
    const overElement = over.data?.current;
    if (overElement?.participant) {
      targetFlight = findFlightForParticipant(overId);
    }

    // If dropped on another participant, get their flight
    if (!targetFlight) {
      targetFlight = findFlightForParticipant(overId);
    }

    // If no target flight found or same flight, do nothing
    if (!targetFlight || targetFlight === sourceFlight) return;

    // Perform the reassignment
    setUpdating(true);
    try {
      const newFlight = targetFlight === 'Unassigned' ? '' : targetFlight.toLowerCase();
      const newSquadron = SQUADRON_MAP[newFlight] || '';

      await updateParticipantAssignment(activeId, {
        flight: newFlight,
        squadron: newSquadron,
      });

      const participant = manageable.find(p => p.id === activeId);
      toast.success(
        `${participant?.last_name}, ${participant?.first_name} moved to ${targetFlight}`,
        { duration: 2000 }
      );
      onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reassign flight');
    } finally {
      setUpdating(false);
    }
  };

  const totalManageable = manageable.length;
  const assignedCount = manageable.filter(p => p.flight && FLIGHTS.map(f => f.toLowerCase()).includes((p.flight || '').toLowerCase())).length;

  return (
    <div data-testid="flight-manager">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-[#00205B]" />
          <div>
            <p className="text-sm font-bold text-[#00205B]">{assignedCount}/{totalManageable} assigned to flights</p>
            <p className="text-xs text-slate-500">Drag and drop participants between flights to reassign</p>
          </div>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by name or CAPID..."
            className="pl-9 rounded-sm text-sm h-9"
            data-testid="flight-manager-search"
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1/2 -translate-y-1/2">
              <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
            </button>
          )}
        </div>
      </div>

      {updating && (
        <div className="mb-3 px-3 py-2 bg-[#00205B]/5 border border-[#00205B]/20 rounded-sm text-sm text-[#00205B] font-medium animate-pulse">
          Updating assignment...
        </div>
      )}

      {/* Flight Columns Grid */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {FLIGHTS.map(flight => (
            <FlightColumn
              key={flight}
              flightName={flight}
              participants={flightGroups[flight] || []}
              color={FLIGHT_COLORS[flight]}
              searchTerm={searchTerm}
            />
          ))}
          <FlightColumn
            flightName="Unassigned"
            participants={flightGroups['Unassigned'] || []}
            color={FLIGHT_COLORS['Unassigned']}
            searchTerm={searchTerm}
          />
        </div>

        <DragOverlay>
          <DragOverlayCard participant={activeParticipant} />
        </DragOverlay>
      </DndContext>
    </div>
  );
};

export default FlightManager;
