import React, { useMemo } from 'react';
import { Edit2, Trash2, MapPin, Shirt, Users } from 'lucide-react';

const SQUADRONS = [
  {
    id: '6th_cts',
    label: '6th CTS',
    color: 'bg-blue-600',
    headerBg: 'bg-blue-600',
    headerText: 'text-white',
    cellBg: 'bg-blue-50',
    cellBorder: 'border-blue-200',
    flights: [
      { id: 'alpha', label: 'A' },
      { id: 'bravo', label: 'B' }
    ]
  },
  {
    id: '21st_cts',
    label: '21st CTS',
    color: 'bg-red-600',
    headerBg: 'bg-red-600',
    headerText: 'text-white',
    cellBg: 'bg-red-50',
    cellBorder: 'border-red-200',
    flights: [
      { id: 'charlie', label: 'C' },
      { id: 'delta', label: 'D' }
    ]
  },
  {
    id: '22nd_cts',
    label: '22nd CTS',
    color: 'bg-emerald-600',
    headerBg: 'bg-emerald-600',
    headerText: 'text-white',
    cellBg: 'bg-emerald-50',
    cellBorder: 'border-emerald-200',
    flights: [
      { id: 'echo', label: 'E' },
      { id: 'foxtrot', label: 'F' }
    ]
  },
  {
    id: '16th_cts',
    label: '16th OPS SUP',
    color: 'bg-slate-500',
    headerBg: 'bg-slate-400',
    headerText: 'text-white',
    cellBg: 'bg-slate-50',
    cellBorder: 'border-slate-200',
    flights: []
  }
];

// All flight columns in order
const ALL_COLUMNS = SQUADRONS.flatMap(sq =>
  sq.flights.length > 0
    ? sq.flights.map(f => ({ ...f, squadronId: sq.id, squadronLabel: sq.label, cellBg: sq.cellBg, cellBorder: sq.cellBorder }))
    : [{ id: sq.id, label: sq.label.replace('OPS SUP', 'OPS'), squadronId: sq.id, squadronLabel: sq.label, cellBg: sq.cellBg, cellBorder: sq.cellBorder, isSingleCol: true }]
);

const TOTAL_COLS = ALL_COLUMNS.length; // 7 columns: A, B, C, D, E, F, 16th

function eventMatchesColumn(event, column) {
  const groups = event.target_groups || ['all'];
  if (groups.includes('all')) return true;
  // Direct flight match
  if (groups.includes(column.id)) return true;
  // Squadron-level match (show in all flights of that squadron)
  if (groups.includes(column.squadronId)) return true;
  // For single-col squadrons (16th), match if event targets that squadron
  if (column.isSingleCol && groups.includes(column.id)) return true;
  return false;
}

function getEventTypeColor(eventType) {
  const colors = {
    general: { bg: 'bg-slate-100', border: 'border-slate-300', text: 'text-slate-700' },
    training: { bg: 'bg-blue-100', border: 'border-blue-300', text: 'text-blue-800' },
    ceremony: { bg: 'bg-purple-100', border: 'border-purple-300', text: 'text-purple-800' },
    meal: { bg: 'bg-amber-100', border: 'border-amber-300', text: 'text-amber-800' },
    recreation: { bg: 'bg-emerald-100', border: 'border-emerald-300', text: 'text-emerald-800' },
    pt: { bg: 'bg-red-100', border: 'border-red-300', text: 'text-red-800' },
    admin: { bg: 'bg-slate-100', border: 'border-slate-400', text: 'text-slate-700' },
    leadership: { bg: 'bg-indigo-100', border: 'border-indigo-300', text: 'text-indigo-800' },
    academics: { bg: 'bg-teal-100', border: 'border-teal-300', text: 'text-teal-800' },
    aerospace: { bg: 'bg-sky-100', border: 'border-sky-300', text: 'text-sky-800' },
    character: { bg: 'bg-rose-100', border: 'border-rose-300', text: 'text-rose-800' }
  };
  return colors[eventType] || colors.general;
}

const SquadronScheduleView = ({ events, timeSlots, canEdit, onEdit, onDelete, onTimeSlotClick }) => {
  // Build a map: timeSlot -> column -> events
  const gridData = useMemo(() => {
    const data = {};
    timeSlots.forEach(slot => {
      data[slot] = {};
      ALL_COLUMNS.forEach(col => {
        data[slot][col.id] = [];
      });
    });

    events.forEach(event => {
      const startSlot = event.start_time.substring(0, 5);
      const endSlot = event.end_time.substring(0, 5);

      ALL_COLUMNS.forEach(col => {
        if (!eventMatchesColumn(event, col)) return;
        // Place event at its start time slot only (we'll span visually)
        timeSlots.forEach(slot => {
          if (slot >= startSlot && slot < endSlot) {
            data[slot][col.id].push(event);
          }
        });
      });
    });
    return data;
  }, [events, timeSlots]);

  // Determine which events START at a given slot for rendering
  const eventStartMap = useMemo(() => {
    const starts = {};
    events.forEach(e => {
      const key = e.start_time.substring(0, 5);
      if (!starts[key]) starts[key] = [];
      if (!starts[key].find(x => x.id === e.id)) starts[key].push(e);
    });
    return starts;
  }, [events]);

  // Calculate span (in 30-min slots) for an event
  const getEventSpan = (event) => {
    const [sh, sm] = event.start_time.split(':').map(Number);
    const [eh, em] = event.end_time.split(':').map(Number);
    const startMins = sh * 60 + sm;
    const endMins = eh * 60 + em;
    return Math.max(1, Math.round((endMins - startMins) / 30));
  };

  // Track which cells are "occupied" by a spanning event to skip rendering
  const occupiedCells = useMemo(() => {
    const occupied = new Set();
    events.forEach(event => {
      const startSlot = event.start_time.substring(0, 5);
      const span = getEventSpan(event);
      const startIdx = timeSlots.indexOf(startSlot);
      if (startIdx === -1) return;

      ALL_COLUMNS.forEach(col => {
        if (!eventMatchesColumn(event, col)) return;
        for (let i = 1; i < span && (startIdx + i) < timeSlots.length; i++) {
          occupied.add(`${timeSlots[startIdx + i]}-${col.id}`);
        }
      });
    });
    return occupied;
  }, [events, timeSlots]);

  return (
    <div className="bg-white border border-slate-200 rounded-sm overflow-hidden" data-testid="squadron-schedule-view">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse min-w-[900px]">
          {/* Header Row 1: Squadron Names */}
          <thead>
            <tr>
              <th className="bg-[#00205B] text-white text-[10px] uppercase font-bold tracking-wider p-2 border-r border-white/20 w-[60px] sticky left-0 z-10">
                Time
              </th>
              {SQUADRONS.map(sq => {
                const colSpan = sq.flights.length > 0 ? sq.flights.length : 1;
                return (
                  <th
                    key={sq.id}
                    colSpan={colSpan}
                    className={`${sq.headerBg} ${sq.headerText} text-xs sm:text-sm font-black uppercase tracking-tight p-2 border-r border-white/20 text-center`}
                    style={{ fontFamily: 'Chivo, sans-serif' }}
                    data-testid={`squadron-header-${sq.id}`}
                  >
                    {sq.label}
                  </th>
                );
              })}
            </tr>
            {/* Header Row 2: Flight Letters */}
            <tr>
              <th className="bg-[#00205B]/90 text-white text-[10px] p-1 border-r border-white/20 sticky left-0 z-10"></th>
              {ALL_COLUMNS.map(col => {
                const sq = SQUADRONS.find(s => s.id === col.squadronId);
                return (
                  <th
                    key={col.id}
                    className={`${sq.headerBg}/80 ${sq.headerText} text-xs sm:text-sm font-bold p-1.5 border-r border-white/20 text-center`}
                    data-testid={`flight-header-${col.id}`}
                  >
                    {col.isSingleCol ? '' : col.label}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {timeSlots.map((slot, slotIdx) => {
              const isHour = slot.endsWith(':00');
              const startEvents = eventStartMap[slot] || [];

              return (
                <tr key={slot} className={isHour ? 'border-t border-slate-300' : 'border-t border-slate-100'}>
                  {/* Time label */}
                  <td className={`text-[10px] text-slate-500 font-mono p-1 text-center border-r border-slate-200 sticky left-0 z-10 ${isHour ? 'bg-slate-100 font-bold text-slate-700' : 'bg-white'}`}>
                    {isHour ? slot : ''}
                  </td>
                  {/* Data cells */}
                  {ALL_COLUMNS.map(col => {
                    const cellKey = `${slot}-${col.id}`;

                    // Skip occupied cells (spanned by previous event)
                    if (occupiedCells.has(cellKey)) return null;

                    // Find events starting at this slot for this column
                    const cellStartEvents = startEvents.filter(e => eventMatchesColumn(e, col));
                    const cellActiveEvents = gridData[slot]?.[col.id] || [];

                    // If no events start here but a slot IS occupied by an earlier-starting event, skip
                    if (cellStartEvents.length === 0 && cellActiveEvents.length > 0) {
                      // This slot is covered by a spanning event - skip
                      return null;
                    }

                    if (cellStartEvents.length > 0) {
                      // Render the first event that starts here (with rowSpan)
                      const event = cellStartEvents[0];
                      const span = getEventSpan(event);
                      const typeColor = getEventTypeColor(event.event_type);

                      return (
                        <td
                          key={cellKey}
                          rowSpan={span}
                          className={`p-0.5 border-r border-slate-200 align-top`}
                        >
                          <div
                            className={`h-full rounded-sm p-1 ${typeColor.bg} ${typeColor.border} border ${typeColor.text} group relative cursor-pointer`}
                            onClick={() => canEdit && onEdit(event)}
                            data-testid={`squadron-event-${event.id}`}
                          >
                            <div className="text-[10px] font-bold leading-tight truncate">{event.title}</div>
                            <div className="text-[9px] opacity-70">{event.start_time.substring(0,5)}-{event.end_time.substring(0,5)}</div>
                            {event.location && (
                              <div className="text-[9px] opacity-60 flex items-center gap-0.5 mt-0.5">
                                <MapPin className="w-2 h-2 flex-shrink-0" /><span className="truncate">{event.location}</span>
                              </div>
                            )}
                            {event.uniform && event.uniform !== 'default' && (
                              <div className="text-[9px] opacity-60 flex items-center gap-0.5">
                                <Shirt className="w-2 h-2 flex-shrink-0" />{event.uniform}
                              </div>
                            )}
                            {canEdit && (
                              <div className="absolute top-0.5 right-0.5 hidden group-hover:flex gap-0.5">
                                <button onClick={(e) => { e.stopPropagation(); onEdit(event); }} className="p-0.5 rounded bg-white/80 hover:bg-white">
                                  <Edit2 className="w-2.5 h-2.5" />
                                </button>
                                <button onClick={(e) => { e.stopPropagation(); onDelete(event.id); }} className="p-0.5 rounded bg-white/80 hover:bg-white text-red-600">
                                  <Trash2 className="w-2.5 h-2.5" />
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      );
                    }

                    // Empty cell
                    return (
                      <td
                        key={cellKey}
                        className={`p-0 border-r border-slate-200 ${isHour ? 'bg-slate-50/50' : ''}`}
                        onClick={() => canEdit && onTimeSlotClick(slot)}
                        style={{ cursor: canEdit ? 'pointer' : 'default', height: '24px' }}
                      />
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SquadronScheduleView;
