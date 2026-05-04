import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
  getLogisticsDashboard, getInventory, createInventoryItem, updateInventoryItem, deleteInventoryItem,
  getLostFound, createLostFound, updateLostFound,
  getRadios, checkoutRadio, checkinRadio, updateRadio, resetRadioAvailable,
  getCommsLog, createCommsEntry,
  getCallSigns, createCallSign, updateCallSign, deleteCallSign,
  getVehicles, createVehicleAssignment, returnVehicle, updateVehicle,
  getVehicleLog, createVehicleLogEntry,
  getFacilities, createFacility, updateFacility,
  getSupplyRequests, createSupplyRequest, approveSupplyRequest, issueSupplyRequest, completeSupplyRequest
} from '../services/api';
import {
  Package, Radio, Car, MapPin, Clipboard, Phone, Truck, Building2, ShoppingCart,
  Search, Plus, RefreshCw, AlertTriangle, Clock, CheckCircle, XCircle, ArrowLeft,
  ChevronRight, Eye, RotateCcw, Edit2
} from 'lucide-react';

const ADMIN_ROLES = ['commander', 'executive_staff', 'logistics'];
const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: Package },
  { id: 'inventory', label: 'Inventory', icon: Clipboard },
  { id: 'lost-found', label: 'Lost & Found', icon: Search },
  { id: 'radios', label: 'Radios', icon: Radio },
  { id: 'comms-log', label: 'Comms Log', icon: Phone },
  { id: 'callsigns', label: 'Call Signs', icon: Phone },
  { id: 'vehicles', label: 'Vehicles', icon: Car },
  { id: 'vehicle-log', label: 'Vehicle Log', icon: Truck },
  { id: 'facilities', label: 'Facilities', icon: Building2 },
  { id: 'supply', label: 'Supply Requests', icon: ShoppingCart },
];
const INV_CATS = ['communications', 'training_equipment', 'office_supplies', 'pt_equipment', 'facilities', 'admin_supplies', 'miscellaneous'];
const PRIORITIES = ['routine', 'important', 'urgent'];
const STAFF_CATS = ['command_staff', 'senior_staff', 'cadre', 'support_staff', 'training_staff'];

const Badge = ({ children, className = '' }) => (
  <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-medium ${className}`}>{children}</span>
);
const StatusBadge = ({ status }) => {
  const colors = {
    available: 'bg-emerald-100 text-emerald-700', checked_out: 'bg-blue-100 text-blue-700',
    returned: 'bg-slate-100 text-slate-600', overdue: 'bg-red-200 text-red-800 font-bold',
    maintenance_needed: 'bg-amber-100 text-amber-700', in_use: 'bg-blue-100 text-blue-700',
    pending: 'bg-amber-100 text-amber-700', approved: 'bg-blue-100 text-blue-700',
    denied: 'bg-red-100 text-red-700', issued: 'bg-emerald-100 text-emerald-700',
    completed: 'bg-slate-100 text-slate-500', unclaimed: 'bg-amber-100 text-amber-700',
    claimed: 'bg-blue-100 text-blue-700', disposed: 'bg-slate-100 text-slate-400',
    ready: 'bg-emerald-100 text-emerald-700', needs_attention: 'bg-amber-100 text-amber-700',
    out_of_service: 'bg-red-100 text-red-700', active: 'bg-emerald-100 text-emerald-700',
    backup: 'bg-blue-100 text-blue-700', unassigned: 'bg-slate-100 text-slate-500',
  };
  return <Badge className={colors[status] || 'bg-slate-100 text-slate-600'}>{(status || '').replace(/_/g, ' ')}</Badge>;
};
const Card = ({ label, value, icon: Icon, color = 'text-slate-700', alert = false }) => (
  <div className={`bg-white border rounded-sm p-3 ${alert ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}>
    <div className="flex items-center justify-between">
      <div>
        <p className="text-[10px] uppercase tracking-wide text-slate-400">{label}</p>
        <p className={`text-xl font-bold ${alert ? 'text-red-700' : color}`}>{value}</p>
      </div>
      <Icon className={`w-5 h-5 ${alert ? 'text-red-500' : color} opacity-50`} />
    </div>
  </div>
);
const Empty = ({ text }) => (
  <div className="text-center py-8 text-slate-400 bg-white border border-slate-200 rounded-sm">
    <p className="text-sm">{text}</p>
  </div>
);

// Static select options (extracted to avoid inline re-creation on every render)
const CONDITION_OPTIONS = [{v:'good',l:'Good'},{v:'fair',l:'Fair'},{v:'poor',l:'Poor'}];
const CONDITION_IN_OPTIONS = [{v:'good',l:'Good'},{v:'fair',l:'Fair'},{v:'needs_maintenance',l:'Needs Maintenance'}];
const CALLSIGN_STATUS_OPTIONS = [{v:'active',l:'Active'},{v:'backup',l:'Backup'},{v:'unassigned',l:'Unassigned'},{v:'out_of_service',l:'Out of Service'}];
const VEHICLE_FUEL_OPTIONS = [{v:'full',l:'Full'},{v:'3/4',l:'3/4'},{v:'1/2',l:'1/2'},{v:'1/4',l:'1/4'},{v:'empty',l:'Empty'}];

const FACILITY_STATUS_OPTIONS = [{v:'ready',l:'Ready'},{v:'in_use',l:'In Use'},{v:'needs_attention',l:'Needs Attention'},{v:'out_of_service',l:'Out of Service'}];
const PRIORITY_OPTIONS = [{v:'low',l:'Low'},{v:'normal',l:'Normal'},{v:'high',l:'High'},{v:'urgent',l:'Urgent'}];

const LogisticsPage = () => {
  const { user } = useAuth();
  const isAdmin = ADMIN_ROLES.includes(user?.role);
  const [tab, setTab] = useState('dashboard');
  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(true);

  // Section data
  const [inventory, setInventory] = useState([]);
  const [lostFound, setLostFound] = useState([]);
  const [radios, setRadios] = useState([]);
  const [commsLog, setCommsLog] = useState([]);
  const [callSigns, setCallSigns] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [vehicleLog, setVehicleLog] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [supplyReqs, setSupplyReqs] = useState([]);

  // Modals
  const [modal, setModal] = useState(null); // { type: 'inventory'|'radio_out'|... }
  const [form, setForm] = useState({});
  const [searchQ, setSearchQ] = useState('');

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const d = await getLogisticsDashboard();
      setDash(d);
    } catch { toast.error('Failed to load dashboard'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const loadTab = useCallback(async (t) => {
    try {
      if (t === 'inventory') setInventory(await getInventory(searchQ ? { search: searchQ } : {}));
      else if (t === 'lost-found') setLostFound(await getLostFound());
      else if (t === 'radios') setRadios(await getRadios());
      else if (t === 'comms-log') setCommsLog(await getCommsLog());
      else if (t === 'callsigns') setCallSigns(await getCallSigns());
      else if (t === 'vehicles') setVehicles(await getVehicles());
      else if (t === 'vehicle-log') setVehicleLog(await getVehicleLog());
      else if (t === 'facilities') setFacilities(await getFacilities());
      else if (t === 'supply') setSupplyReqs(await getSupplyRequests());
    } catch (error) { console.error(`Failed to load ${t}:`, error); }
  }, [searchQ]);

  useEffect(() => { if (tab !== 'dashboard') loadTab(tab); }, [tab, loadTab]);

  const openModal = (type, defaults = {}) => { setForm(defaults); setModal(type); };
  const closeModal = () => { setModal(null); setForm({}); };
  const f = (key, val) => setForm(p => ({ ...p, [key]: val }));

  const submitForm = async () => {
    try {
      if (modal === 'inventory') { await createInventoryItem(form); toast.success('Item added'); }
      else if (modal === 'lost-found') { await createLostFound(form); toast.success('Item logged'); }
      else if (modal === 'radio-out') { await checkoutRadio(form); toast.success('Radio checked out'); }
      else if (modal === 'radio-in') { await checkinRadio(form._radio_id, form); toast.success('Radio checked in'); }
      else if (modal === 'comms') { await createCommsEntry(form); toast.success('Entry logged'); }
      else if (modal === 'callsign') { await createCallSign(form); toast.success('Call sign created'); }
      else if (modal === 'vehicle-assign') { await createVehicleAssignment(form); toast.success('Vehicle assigned'); }
      else if (modal === 'vehicle-return') { await returnVehicle(form._vehicle_id, form); toast.success('Vehicle returned'); }
      else if (modal === 'vehicle-log') { await createVehicleLogEntry(form); toast.success('Log entry created'); }
      else if (modal === 'facility') { await createFacility(form); toast.success('Facility added'); }
      else if (modal === 'supply') { await createSupplyRequest(form); toast.success('Request submitted'); }
      closeModal();
      loadTab(tab);
      loadDashboard();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };

  const switchTab = (t) => { setTab(t); setSearchQ(''); };

  // ========== RENDER ==========
  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-[#00205B]" data-testid="logistics-title">Logistics</h1>
          <p className="text-xs text-slate-500">Encampment Logistics Operations Center</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { loadDashboard(); loadTab(tab); }} className="rounded-sm">
          <RefreshCw className="w-4 h-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Tab Navigation - scrollable on mobile */}
      <div className="flex gap-1 overflow-x-auto pb-2 mb-4 border-b border-slate-200 -mx-4 px-4 md:mx-0 md:px-0">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => switchTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-sm whitespace-nowrap transition-colors
              ${tab === t.id ? 'bg-[#00205B] text-white' : 'text-slate-600 hover:bg-slate-100'}`}
            data-testid={`tab-${t.id}`}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* ===== DASHBOARD ===== */}
      {tab === 'dashboard' && dash && (
        <div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
            <Card label="Inventory Items" value={dash.inventory_total} icon={Package} color="text-blue-600" />
            <Card label="Items Issued" value={dash.inventory_issued} icon={Clipboard} color="text-indigo-600" />
            <Card label="Low Stock Alerts" value={dash.inventory_low_stock} icon={AlertTriangle} color="text-amber-600" alert={dash.inventory_low_stock > 0} />
            <Card label="Radios Out" value={dash.radios_checked_out} icon={Radio} color="text-teal-600" />
            <Card label="Radios Available" value={dash.radios_available} icon={Radio} color="text-emerald-600" />
            <Card label="Radios Overdue" value={dash.radios_overdue} icon={Clock} color="text-red-600" alert={dash.radios_overdue > 0} />
            <Card label="Vehicles In Use" value={dash.vehicles_in_use} icon={Car} color="text-blue-600" />
            <Card label="Vehicles Available" value={dash.vehicles_available} icon={Car} color="text-emerald-600" />
            <Card label="Vehicles Overdue" value={dash.vehicles_overdue} icon={Clock} color="text-red-600" alert={dash.vehicles_overdue > 0} />
            <Card label="Open Supply Requests" value={dash.supply_requests_open} icon={ShoppingCart} color="text-amber-600" />
            <Card label="Lost & Found Unclaimed" value={dash.lost_found_unclaimed} icon={Search} color="text-purple-600" />
          </div>

          {/* Overdue Alerts */}
          {(dash.overdue_radios?.length > 0 || dash.overdue_vehicles?.length > 0) && (
            <div className="bg-red-50 border border-red-300 rounded-sm p-4 mb-6" data-testid="overdue-alerts">
              <h3 className="text-sm font-bold text-red-800 uppercase mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Overdue Equipment
              </h3>
              {dash.overdue_radios?.map(r => (
                <div key={r.id} className="flex items-center justify-between py-2 border-b border-red-200 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-red-900">Radio {r.radio_number}</p>
                    <p className="text-xs text-red-700">{r.assigned_to} &middot; {r.call_sign} &middot; Ch {r.channel}</p>
                  </div>
                  <Badge className="bg-red-200 text-red-800">OVERDUE{r.overdue_minutes ? ` ${r.overdue_minutes}min` : ''}</Badge>
                </div>
              ))}
              {dash.overdue_vehicles?.map(v => (
                <div key={v.id} className="flex items-center justify-between py-2 border-b border-red-200 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-red-900">{v.vehicle_name}</p>
                    <p className="text-xs text-red-700">Driver: {v.driver}</p>
                  </div>
                  <Badge className="bg-red-200 text-red-800">OVERDUE{v.overdue_minutes ? ` ${v.overdue_minutes}min` : ''}</Badge>
                </div>
              ))}
            </div>
          )}

          {/* Quick Actions */}
          {isAdmin && (
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="text-xs font-bold uppercase text-slate-400 mb-3">Quick Actions</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { label: 'Add Inventory', onClick: () => { switchTab('inventory'); setTimeout(() => openModal('inventory'), 100); } },
                  { label: 'Check Out Radio', onClick: () => { switchTab('radios'); setTimeout(() => openModal('radio-out'), 100); } },
                  { label: 'Check In Radio', onClick: () => switchTab('radios') },
                  { label: 'Assign Vehicle', onClick: () => { switchTab('vehicles'); setTimeout(() => openModal('vehicle-assign'), 100); } },
                  { label: 'Log Vehicle Trip', onClick: () => { switchTab('vehicle-log'); setTimeout(() => openModal('vehicle-log'), 100); } },
                  { label: 'Lost & Found', onClick: () => { switchTab('lost-found'); setTimeout(() => openModal('lost-found'), 100); } },
                  { label: 'Supply Requests', onClick: () => switchTab('supply') },
                ].map(a => (
                  <Button key={a.label} variant="outline" size="sm" className="justify-start text-xs rounded-sm" onClick={a.onClick}>
                    <ChevronRight className="w-3 h-3 mr-1" /> {a.label}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== INVENTORY ===== */}
      {tab === 'inventory' && (
        <Section title="Inventory" onAdd={isAdmin ? () => openModal('inventory') : null} addLabel="Add Item"
          search={searchQ} onSearch={setSearchQ} onSearchSubmit={() => loadTab('inventory')}>
          {inventory.length === 0 ? <Empty text="No inventory items" /> : (
            <div className="space-y-2">
              {inventory.map(item => (
                <div key={item.id} className={`bg-white border rounded-sm p-3 ${item.quantity_available <= (item.reorder_threshold || 0) ? 'border-amber-300 bg-amber-50' : 'border-slate-200'}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{item.item_name}</p>
                      <p className="text-xs text-slate-500">{item.category?.replace(/_/g, ' ')} {item.item_id && `· #${item.item_id}`}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs"><span className="font-bold text-emerald-700">{item.quantity_available}</span> avail / <span className="text-amber-600">{item.quantity_issued}</span> issued</p>
                      <p className="text-[10px] text-slate-400">{item.storage_location}</p>
                    </div>
                  </div>
                  {item.assigned_to && <p className="text-xs text-slate-600 mt-1">Assigned: {item.assigned_to}</p>}
                  {item.quantity_available <= (item.reorder_threshold || 0) && (
                    <p className="text-xs text-amber-700 font-medium mt-1">LOW STOCK (threshold: {item.reorder_threshold})</p>
                  )}
                  {item.notes && <p className="text-xs text-slate-500 mt-1">{item.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== LOST & FOUND ===== */}
      {tab === 'lost-found' && (
        <Section title="Lost & Found" onAdd={isAdmin ? () => openModal('lost-found') : null} addLabel="Add Item">
          {lostFound.length === 0 ? <Empty text="No lost & found items" /> : (
            <div className="space-y-2">
              {lostFound.map(item => (
                <div key={item.id} className="bg-white border border-slate-200 rounded-sm p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{item.item_description}</p>
                      <p className="text-xs text-slate-500">{item.location_found} · {item.date_found} {item.time_found}</p>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                  {item.found_by && <p className="text-xs text-slate-600 mt-1">Found by: {item.found_by}</p>}
                  {item.claimed_by && <p className="text-xs text-emerald-700 mt-1">Claimed by: {item.claimed_by}</p>}
                  {isAdmin && item.status === 'unclaimed' && (
                    <div className="flex gap-1 mt-2">
                      <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={async () => {
                        const name = prompt('Claimed by:');
                        if (name) { await updateLostFound(item.id, { claimed_by: name, status: 'claimed' }); loadTab('lost-found'); }
                      }}>Mark Claimed</Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== RADIOS ===== */}
      {tab === 'radios' && (
        <Section title="Radio Check Out / Check In"
          onAdd={isAdmin ? () => openModal('radio-out') : null} addLabel="Check Out Radio">
          {radios.length === 0 ? <Empty text="No radios tracked" /> : (
            <div className="space-y-2">
              {radios.map(r => (
                <div key={r.id} className={`bg-white border rounded-sm p-3 ${r.status === 'overdue' ? 'border-red-400 bg-red-50' : 'border-slate-200'}`} data-testid={`radio-${r.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">Radio {r.radio_number}</p>
                      {r.assigned_to && <p className="text-xs text-slate-600">{r.assigned_to} · {r.position}</p>}
                      {r.call_sign && <p className="text-xs text-slate-500">Call Sign: {r.call_sign} · Ch {r.channel}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={r.status} />
                      {r.overdue_minutes && <Badge className="bg-red-200 text-red-800">{r.overdue_minutes}min overdue</Badge>}
                    </div>
                  </div>
                  {r.time_out && <p className="text-xs text-slate-500 mt-1">Out: {new Date(r.time_out).toLocaleString()}</p>}
                  {r.expected_return && <p className="text-xs text-slate-500">Expected: {new Date(r.expected_return).toLocaleString()}</p>}
                  {r.battery_issued && <Badge className="bg-slate-100 text-slate-600 mr-1">Battery</Badge>}
                  {r.spare_battery_issued && <Badge className="bg-slate-100 text-slate-600">Spare</Badge>}
                  {isAdmin && (r.status === 'checked_out' || r.status === 'overdue') && (
                    <div className="flex gap-1 mt-2">
                      <Button variant="outline" size="sm" className="h-6 text-[10px]" onClick={() => openModal('radio-in', { _radio_id: r.id, condition_in: 'good' })}>
                        <RotateCcw className="w-3 h-3 mr-1" /> Check In
                      </Button>
                      <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={async () => {
                        const newTime = prompt('New expected return (YYYY-MM-DDTHH:MM):');
                        if (newTime) { await updateRadio(r.id, { expected_return: newTime, status: 'checked_out' }); loadTab('radios'); toast.success('Extended'); }
                      }}>Extend</Button>
                    </div>
                  )}
                  {isAdmin && (r.status === 'returned' || r.status === 'maintenance_needed') && (
                    <Button variant="ghost" size="sm" className="h-6 text-[10px] mt-2" onClick={async () => { await resetRadioAvailable({ id: r.id }); loadTab('radios'); toast.success('Reset'); }}>
                      Reset Available
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== COMMS LOG ===== */}
      {tab === 'comms-log' && (
        <Section title="Communications Log" onAdd={isAdmin ? () => openModal('comms') : null} addLabel="Log Entry">
          {commsLog.length === 0 ? <Empty text="No communications logged" /> : (
            <div className="space-y-2">
              {commsLog.map(e => (
                <div key={e.id} className={`bg-white border rounded-sm p-3 ${e.priority === 'urgent' ? 'border-red-300' : e.priority === 'important' ? 'border-amber-300' : 'border-slate-200'}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-slate-500">{new Date(e.time).toLocaleString()}</p>
                      <p className="font-medium text-sm mt-0.5">{e.message_summary}</p>
                    </div>
                    <Badge className={e.priority === 'urgent' ? 'bg-red-100 text-red-700' : e.priority === 'important' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}>{e.priority}</Badge>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">Call Sign: {e.call_sign} · Operator: {e.operator}</p>
                  {e.notes && <p className="text-xs text-slate-500 mt-0.5">{e.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== CALL SIGNS ===== */}
      {tab === 'callsigns' && (
        <Section title="Call Sign Directory" onAdd={isAdmin ? () => openModal('callsign') : null} addLabel="Add Call Sign">
          {callSigns.length === 0 ? <Empty text="No call signs assigned" /> : (
            <div className="space-y-2">
              {callSigns.map(cs => (
                <div key={cs.id} className="bg-white border border-slate-200 rounded-sm p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-sm text-[#00205B]">{cs.call_sign}</p>
                      <p className="text-xs text-slate-700">{cs.assigned_member} · {cs.assigned_role}</p>
                      <p className="text-xs text-slate-500">{cs.staff_category?.replace(/_/g, ' ')} · Radio {cs.radio_number} · Ch {cs.channel}</p>
                    </div>
                    <StatusBadge status={cs.status} />
                  </div>
                  {cs.alternate_member && <p className="text-xs text-slate-500 mt-1">Alt: {cs.alternate_member} ({cs.alternate_role})</p>}
                  {cs.notes && <p className="text-xs text-slate-500 mt-0.5">{cs.notes}</p>}
                  {isAdmin && (
                    <div className="flex gap-1 mt-2">
                      <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => openModal('callsign-edit', { ...cs })}>
                        <Edit2 className="w-3 h-3 mr-1" /> Edit
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== VEHICLES ===== */}
      {tab === 'vehicles' && (
        <Section title="Vehicle Assignments" onAdd={isAdmin ? () => openModal('vehicle-assign') : null} addLabel="Assign Vehicle">
          {vehicles.length === 0 ? <Empty text="No vehicles tracked" /> : (
            <div className="space-y-2">
              {vehicles.map(v => (
                <div key={v.id} className={`bg-white border rounded-sm p-3 ${v.status === 'overdue' ? 'border-red-400 bg-red-50' : 'border-slate-200'}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{v.vehicle_name}</p>
                      <p className="text-xs text-slate-600">Driver: {v.driver}</p>
                      <p className="text-xs text-slate-500">{v.purpose}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={v.status} />
                      {v.overdue_minutes && <Badge className="bg-red-200 text-red-800">{v.overdue_minutes}min overdue</Badge>}
                    </div>
                  </div>
                  {v.departure_time && <p className="text-xs text-slate-500 mt-1">Departed: {new Date(v.departure_time).toLocaleString()}</p>}
                  {v.expected_return && <p className="text-xs text-slate-500">Expected: {new Date(v.expected_return).toLocaleString()}</p>}
                  {v.fuel_level_out && <p className="text-xs text-slate-500">Fuel out: {v.fuel_level_out}</p>}
                  {isAdmin && (v.status === 'in_use' || v.status === 'overdue') && (
                    <div className="flex gap-1 mt-2">
                      <Button variant="outline" size="sm" className="h-6 text-[10px]" onClick={() => openModal('vehicle-return', { _vehicle_id: v.id, fuel_level_in: '' })}>
                        <RotateCcw className="w-3 h-3 mr-1" /> Return
                      </Button>
                      <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={async () => {
                        const newTime = prompt('New expected return (YYYY-MM-DDTHH:MM):');
                        if (newTime) { await updateVehicle(v.id, { expected_return: newTime, status: 'in_use' }); loadTab('vehicles'); toast.success('Extended'); }
                      }}>Extend</Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== VEHICLE LOG ===== */}
      {tab === 'vehicle-log' && (
        <Section title="Vehicle Log" onAdd={isAdmin ? () => openModal('vehicle-log') : null} addLabel="Log Trip">
          {vehicleLog.length === 0 ? <Empty text="No vehicle log entries" /> : (
            <div className="space-y-2">
              {vehicleLog.map(l => (
                <div key={l.id} className="bg-white border border-slate-200 rounded-sm p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{l.vehicle_name}</p>
                      <p className="text-xs text-slate-600">Driver: {l.driver} · {l.date}</p>
                    </div>
                    <p className="text-sm font-bold text-[#00205B]">{l.total_miles} mi</p>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Start: {l.start_mileage} · End: {l.end_mileage}</p>
                  {l.purpose && <p className="text-xs text-slate-600">{l.purpose}</p>}
                  {l.fuel_purchased && <p className="text-xs text-emerald-700">Fuel: {l.fuel_purchased}</p>}
                  {l.maintenance_issue && <p className="text-xs text-amber-700">Maintenance: {l.maintenance_issue}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== FACILITIES ===== */}
      {tab === 'facilities' && (
        <Section title="Facilities & Equipment" onAdd={isAdmin ? () => openModal('facility') : null} addLabel="Add Item">
          {facilities.length === 0 ? <Empty text="No facilities tracked" /> : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {facilities.map(fc => (
                <div key={fc.id} className={`bg-white border rounded-sm p-3 ${fc.status === 'needs_attention' ? 'border-amber-300' : fc.status === 'out_of_service' ? 'border-red-300' : 'border-slate-200'}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{fc.item_name}</p>
                      <p className="text-xs text-slate-500">{fc.location}</p>
                    </div>
                    <StatusBadge status={fc.status} />
                  </div>
                  {fc.responsible_staff && <p className="text-xs text-slate-600 mt-1">Staff: {fc.responsible_staff}</p>}
                  {fc.notes && <p className="text-xs text-slate-500 mt-0.5">{fc.notes}</p>}
                  {isAdmin && (
                    <div className="flex gap-1 mt-2">
                      {['ready', 'in_use', 'needs_attention', 'out_of_service'].map(s => (
                        s !== fc.status && <Button key={s} variant="ghost" size="sm" className="h-6 text-[10px]" onClick={async () => { await updateFacility(fc.id, { status: s }); loadTab('facilities'); }}>{s.replace(/_/g, ' ')}</Button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ===== SUPPLY REQUESTS ===== */}
      {tab === 'supply' && (
        <Section title="Supply Requests" onAdd={() => openModal('supply')} addLabel="Submit Request">
          {supplyReqs.length === 0 ? <Empty text="No supply requests" /> : (
            <div className="space-y-2">
              {supplyReqs.map(req => (
                <div key={req.id} className="bg-white border border-slate-200 rounded-sm p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{req.item_requested} <span className="text-slate-400">x{req.quantity}</span></p>
                      <p className="text-xs text-slate-600">{req.requestor} ({req.requestor_role})</p>
                      <p className="text-xs text-slate-500">{req.purpose}</p>
                    </div>
                    <div className="text-right">
                      <StatusBadge status={req.status} />
                      <Badge className={req.priority === 'urgent' ? 'bg-red-100 text-red-700 ml-1' : req.priority === 'high' ? 'bg-amber-100 text-amber-700 ml-1' : 'bg-slate-100 text-slate-600 ml-1'}>{req.priority}</Badge>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Requested: {req.date_requested} {req.needed_by && `· Needed by: ${req.needed_by}`}</p>
                  {req.approved_by && <p className="text-xs text-emerald-700">Approved by: {req.approved_by}</p>}
                  {req.issued_by && <p className="text-xs text-blue-700">Issued by: {req.issued_by}</p>}
                  {isAdmin && req.status === 'pending' && (
                    <div className="flex gap-1 mt-2">
                      <Button variant="outline" size="sm" className="h-6 text-[10px] text-emerald-700" onClick={async () => { await approveSupplyRequest(req.id, { status: 'approved' }); loadTab('supply'); toast.success('Approved'); }}>
                        <CheckCircle className="w-3 h-3 mr-1" /> Approve
                      </Button>
                      <Button variant="ghost" size="sm" className="h-6 text-[10px] text-red-600" onClick={async () => { await approveSupplyRequest(req.id, { status: 'denied' }); loadTab('supply'); toast.success('Denied'); }}>
                        <XCircle className="w-3 h-3 mr-1" /> Deny
                      </Button>
                    </div>
                  )}
                  {isAdmin && req.status === 'approved' && (
                    <Button variant="outline" size="sm" className="h-6 text-[10px] mt-2" onClick={async () => { await issueSupplyRequest(req.id); loadTab('supply'); toast.success('Issued'); }}>Issue</Button>
                  )}
                  {isAdmin && req.status === 'issued' && (
                    <Button variant="outline" size="sm" className="h-6 text-[10px] mt-2" onClick={async () => { await completeSupplyRequest(req.id); loadTab('supply'); toast.success('Completed'); }}>Complete</Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ==================== MODALS ==================== */}

      {/* Inventory Modal */}
      <FormModal open={modal === 'inventory'} onClose={closeModal} title="Add Inventory Item" onSubmit={submitForm}>
        <Row2>
          <Field label="Item Name *"><Input value={form.item_name || ''} onChange={e => f('item_name', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="inv-item-name" /></Field>
          <Field label="Category"><Sel value={form.category || 'miscellaneous'} onChange={v => f('category', v)} options={INV_CATS.map(c => ({ v: c, l: c.replace(/_/g, ' ') }))} /></Field>
        </Row2>
        <Row2>
          <Field label="Item ID / Serial"><Input value={form.item_id || ''} onChange={e => f('item_id', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Storage Location"><Input value={form.storage_location || ''} onChange={e => f('storage_location', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Row3>
          <Field label="Qty Available"><Input type="number" value={form.quantity_available || 0} onChange={e => f('quantity_available', parseInt(e.target.value) || 0)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Qty Issued"><Input type="number" value={form.quantity_issued || 0} onChange={e => f('quantity_issued', parseInt(e.target.value) || 0)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Reorder At"><Input type="number" value={form.reorder_threshold || 0} onChange={e => f('reorder_threshold', parseInt(e.target.value) || 0)} className="h-8 text-sm rounded-sm" /></Field>
        </Row3>
        <Row2>
          <Field label="Condition"><Sel value={form.condition || 'good'} onChange={v => f('condition', v)} options={CONDITION_OPTIONS} /></Field>
          <Field label="Assigned To"><Input value={form.assigned_to || ''} onChange={e => f('assigned_to', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Lost & Found Modal */}
      <FormModal open={modal === 'lost-found'} onClose={closeModal} title="Log Lost & Found Item" onSubmit={submitForm}>
        <Field label="Item Description *"><Input value={form.item_description || ''} onChange={e => f('item_description', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="lf-description" /></Field>
        <Row3>
          <Field label="Date Found"><Input type="date" value={form.date_found || new Date().toISOString().split('T')[0]} onChange={e => f('date_found', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Time Found"><Input type="time" value={form.time_found || ''} onChange={e => f('time_found', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Location"><Input value={form.location_found || ''} onChange={e => f('location_found', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row3>
        <Row2>
          <Field label="Found By"><Input value={form.found_by || ''} onChange={e => f('found_by', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Storage Location"><Input value={form.storage_location || ''} onChange={e => f('storage_location', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Radio Checkout Modal */}
      <FormModal open={modal === 'radio-out'} onClose={closeModal} title="Check Out Radio" onSubmit={submitForm}>
        <Row2>
          <Field label="Radio Number *"><Input value={form.radio_number || ''} onChange={e => f('radio_number', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="radio-number" /></Field>
          <Field label="Assigned To *"><Input value={form.assigned_to || ''} onChange={e => f('assigned_to', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Row3>
          <Field label="Position"><Input value={form.position || ''} onChange={e => f('position', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Call Sign"><Input value={form.call_sign || ''} onChange={e => f('call_sign', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Channel"><Input value={form.channel || ''} onChange={e => f('channel', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row3>
        <Row2>
          <Field label="Expected Return"><Input type="datetime-local" value={form.expected_return || ''} onChange={e => f('expected_return', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Condition"><Sel value={form.condition_out || 'good'} onChange={v => f('condition_out', v)} options={CONDITION_OPTIONS} /></Field>
        </Row2>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.battery_issued || false} onChange={e => f('battery_issued', e.target.checked)} className="rounded" /> Battery</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.spare_battery_issued || false} onChange={e => f('spare_battery_issued', e.target.checked)} className="rounded" /> Spare Battery</label>
        </div>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Radio Check-In Modal */}
      <FormModal open={modal === 'radio-in'} onClose={closeModal} title="Check In Radio" onSubmit={submitForm}>
        <Field label="Condition"><Sel value={form.condition_in || 'good'} onChange={v => f('condition_in', v)} options={CONDITION_IN_OPTIONS} /></Field>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Comms Log Modal */}
      <FormModal open={modal === 'comms'} onClose={closeModal} title="Log Communication" onSubmit={submitForm}>
        <Row3>
          <Field label="Call Sign"><Input value={form.call_sign || ''} onChange={e => f('call_sign', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="comms-callsign" /></Field>
          <Field label="Operator"><Input value={form.operator || ''} onChange={e => f('operator', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Priority"><Sel value={form.priority || 'routine'} onChange={v => f('priority', v)} options={PRIORITIES.map(p => ({ v: p, l: p }))} /></Field>
        </Row3>
        <Field label="Message Summary *"><Textarea value={form.message_summary || ''} onChange={e => f('message_summary', e.target.value)} rows={3} className="text-sm rounded-sm" /></Field>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Call Sign Modal */}
      <FormModal open={modal === 'callsign' || modal === 'callsign-edit'} onClose={closeModal} title={modal === 'callsign-edit' ? 'Edit Call Sign' : 'Add Call Sign'}
        onSubmit={async () => {
          if (modal === 'callsign-edit' && form.id) { await updateCallSign(form.id, form); toast.success('Updated'); }
          else { await createCallSign(form); toast.success('Created'); }
          closeModal(); loadTab('callsigns');
        }}>
        <Row2>
          <Field label="Call Sign *"><Input value={form.call_sign || ''} onChange={e => f('call_sign', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="cs-callsign" /></Field>
          <Field label="Status"><Sel value={form.status || 'active'} onChange={v => f('status', v)} options={CALLSIGN_STATUS_OPTIONS} /></Field>
        </Row2>
        <Row2>
          <Field label="Assigned Member"><Input value={form.assigned_member || ''} onChange={e => f('assigned_member', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Assigned Role"><Input value={form.assigned_role || ''} onChange={e => f('assigned_role', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Row3>
          <Field label="Staff Category"><Sel value={form.staff_category || 'none'} onChange={v => f('staff_category', v === 'none' ? '' : v)} options={[{v:'none',l:'Select'},...STAFF_CATS.map(c => ({v:c,l:c.replace(/_/g,' ')}))]} /></Field>
          <Field label="Radio #"><Input value={form.radio_number || ''} onChange={e => f('radio_number', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Channel"><Input value={form.channel || ''} onChange={e => f('channel', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row3>
        <Row2>
          <Field label="Alternate Member"><Input value={form.alternate_member || ''} onChange={e => f('alternate_member', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Alternate Role"><Input value={form.alternate_role || ''} onChange={e => f('alternate_role', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Vehicle Assignment Modal */}
      <FormModal open={modal === 'vehicle-assign'} onClose={closeModal} title="Assign Vehicle" onSubmit={submitForm}>
        <Row2>
          <Field label="Vehicle Name/Number *"><Input value={form.vehicle_name || ''} onChange={e => f('vehicle_name', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="vehicle-name" /></Field>
          <Field label="Driver *"><Input value={form.driver || ''} onChange={e => f('driver', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Purpose"><Input value={form.purpose || ''} onChange={e => f('purpose', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        <Row3>
          <Field label="Expected Return"><Input type="datetime-local" value={form.expected_return || ''} onChange={e => f('expected_return', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Passengers"><Input type="number" value={form.passenger_count || 0} onChange={e => f('passenger_count', parseInt(e.target.value) || 0)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Fuel Level Out"><Input value={form.fuel_level_out || ''} onChange={e => f('fuel_level_out', e.target.value)} className="h-8 text-sm rounded-sm" placeholder="e.g. 3/4" /></Field>
        </Row3>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Vehicle Return Modal */}
      <FormModal open={modal === 'vehicle-return'} onClose={closeModal} title="Return Vehicle" onSubmit={submitForm}>
        <Field label="Fuel Level In"><Input value={form.fuel_level_in || ''} onChange={e => f('fuel_level_in', e.target.value)} className="h-8 text-sm rounded-sm" placeholder="e.g. 1/2" /></Field>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Vehicle Log Modal */}
      <FormModal open={modal === 'vehicle-log'} onClose={closeModal} title="Log Vehicle Trip" onSubmit={submitForm}>
        <Row2>
          <Field label="Vehicle *"><Input value={form.vehicle_name || ''} onChange={e => f('vehicle_name', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="vlog-vehicle" /></Field>
          <Field label="Driver *"><Input value={form.driver || ''} onChange={e => f('driver', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Row3>
          <Field label="Date"><Input type="date" value={form.date || new Date().toISOString().split('T')[0]} onChange={e => f('date', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Start Mileage"><Input type="number" value={form.start_mileage || ''} onChange={e => f('start_mileage', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="End Mileage"><Input type="number" value={form.end_mileage || ''} onChange={e => f('end_mileage', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row3>
        <Row2>
          <Field label="Purpose"><Input value={form.purpose || ''} onChange={e => f('purpose', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Fuel Purchased"><Input value={form.fuel_purchased || ''} onChange={e => f('fuel_purchased', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Maintenance Issue"><Textarea value={form.maintenance_issue || ''} onChange={e => f('maintenance_issue', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Facility Modal */}
      <FormModal open={modal === 'facility'} onClose={closeModal} title="Add Facility/Equipment" onSubmit={submitForm}>
        <Row2>
          <Field label="Item/Area Name *"><Input value={form.item_name || ''} onChange={e => f('item_name', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="facility-name" /></Field>
          <Field label="Location"><Input value={form.location || ''} onChange={e => f('location', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Row2>
          <Field label="Responsible Staff"><Input value={form.responsible_staff || ''} onChange={e => f('responsible_staff', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
          <Field label="Status"><Sel value={form.status || 'ready'} onChange={v => f('status', v)} options={FACILITY_STATUS_OPTIONS} /></Field>
        </Row2>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>

      {/* Supply Request Modal */}
      <FormModal open={modal === 'supply'} onClose={closeModal} title="Submit Supply Request" onSubmit={submitForm}>
        <Row2>
          <Field label="Item Requested *"><Input value={form.item_requested || ''} onChange={e => f('item_requested', e.target.value)} className="h-8 text-sm rounded-sm" data-testid="supply-item" /></Field>
          <Field label="Quantity"><Input type="number" value={form.quantity || 1} onChange={e => f('quantity', parseInt(e.target.value) || 1)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Purpose"><Input value={form.purpose || ''} onChange={e => f('purpose', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        <Row2>
          <Field label="Priority"><Sel value={form.priority || 'normal'} onChange={v => f('priority', v)} options={PRIORITY_OPTIONS} /></Field>
          <Field label="Needed By"><Input type="date" value={form.needed_by || ''} onChange={e => f('needed_by', e.target.value)} className="h-8 text-sm rounded-sm" /></Field>
        </Row2>
        <Field label="Notes"><Textarea value={form.notes || ''} onChange={e => f('notes', e.target.value)} rows={2} className="text-sm rounded-sm" /></Field>
      </FormModal>
    </div>
  );
};

// ========== Helper Components ==========

const Section = ({ title, onAdd, addLabel, children, search, onSearch, onSearchSubmit }) => (
  <div>
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-sm font-bold uppercase text-[#00205B]">{title}</h3>
      <div className="flex items-center gap-2">
        {onSearch && (
          <div className="flex gap-1">
            <Input value={search} onChange={e => onSearch(e.target.value)} placeholder="Search..." className="h-8 w-40 text-sm rounded-sm"
              onKeyDown={e => e.key === 'Enter' && onSearchSubmit()} />
            <Button variant="outline" size="sm" className="h-8 rounded-sm" onClick={onSearchSubmit}><Search className="w-3.5 h-3.5" /></Button>
          </div>
        )}
        {onAdd && (
          <Button size="sm" onClick={onAdd} className="bg-[#00205B] rounded-sm" data-testid={`add-${title.toLowerCase().replace(/[^a-z]/g, '-')}`}>
            <Plus className="w-4 h-4 mr-1" /> {addLabel}
          </Button>
        )}
      </div>
    </div>
    {children}
  </div>
);

const FormModal = ({ open, onClose, title, onSubmit, children }) => (
  <Dialog open={open} onOpenChange={v => !v && onClose()}>
    <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
      <DialogHeader><DialogTitle className="text-[#00205B] uppercase font-bold text-sm">{title}</DialogTitle></DialogHeader>
      <div className="space-y-3 mt-2">
        {children}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} className="bg-[#00205B]" data-testid="modal-submit">Submit</Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
);

const Field = ({ label, children }) => (<div><Label className="text-xs">{label}</Label>{children}</div>);
const Row2 = ({ children }) => <div className="grid grid-cols-2 gap-3">{children}</div>;
const Row3 = ({ children }) => <div className="grid grid-cols-3 gap-3">{children}</div>;
const Sel = ({ value, onChange, options }) => (
  <Select value={value} onValueChange={onChange}>
    <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
    <SelectContent>{options.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
  </Select>
);

export default LogisticsPage;
