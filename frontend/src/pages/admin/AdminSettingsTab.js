import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import {
  Shield, UserCog, DollarSign, Users, Plane,
  Cloud, CheckCircle, AlertTriangle, RefreshCw, Clock,
  FileSpreadsheet, ExternalLink, XCircle, Calendar, Plus, Trash2
} from 'lucide-react';
import { getHonorAgreementStatus, sendHonorAgreementReminders } from '../../services/api';

// Phase 8: accept a full Google Sheets URL OR a raw spreadsheet id.
const parseSheetField = (input) => {
  if (!input) return { spreadsheet_id: '', gid: '' };
  const trimmed = input.trim();
  if (!trimmed.includes('/')) return { spreadsheet_id: trimmed, gid: '' };
  const idMatch = trimmed.match(/\/d\/([a-zA-Z0-9_-]+)/);
  const gidMatch = trimmed.match(/[?&#]gid=(\d+)/);
  return {
    spreadsheet_id: idMatch ? idMatch[1] : trimmed,
    gid: gidMatch ? gidMatch[1] : '',
  };
};

const AdminSettingsTab = ({
  gsheetSettings,
  setGsheetSettings,
  syncStatus,
  syncingNow,
  savingGsheetSettings,
  handleSaveGsheetSettings,
  handleManualSync,
  handleSyncSchedule,
  syncingParticipants,
  handleSyncUsersToRoster
}) => {
  // Phase 8: per-schedule helpers.
  const schedules = gsheetSettings.schedules || [];

  const updateScheduleField = (index, field, value) => {
    setGsheetSettings((prev) => {
      const next = [...(prev.schedules || [])];
      next[index] = { ...next[index], [field]: value };
      return { ...prev, schedules: next };
    });
  };

  const updateScheduleUrl = (index, urlValue) => {
    const parsed = parseSheetField(urlValue);
    setGsheetSettings((prev) => {
      const next = [...(prev.schedules || [])];
      next[index] = {
        ...next[index],
        spreadsheet_id: parsed.spreadsheet_id,
        gid: parsed.gid || next[index].gid || '',
      };
      return { ...prev, schedules: next };
    });
  };

  const addSchedule = () => {
    setGsheetSettings((prev) => ({
      ...prev,
      schedules: [
        ...(prev.schedules || []),
        {
          id: `schedule_${(prev.schedules || []).length + 1}`,
          label: 'New Schedule',
          spreadsheet_id: '',
          gid: '',
          enabled: true,
        },
      ],
    }));
  };

  const removeSchedule = (index) => {
    setGsheetSettings((prev) => ({
      ...prev,
      schedules: (prev.schedules || []).filter((_, i) => i !== index),
    }));
  };

  return (
    <div className="space-y-6">
      {/* Role Permissions Info */}
      <div className="bg-white border border-slate-200 rounded-sm">
        <div className="border-b border-slate-100 p-4">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Role Permissions
          </h2>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-[#00205B]/5 rounded-sm border border-[#00205B]/20">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-5 h-5 text-[#00205B]" />
              <span className="font-bold text-[#00205B]">Commander</span>
            </div>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>Full access to all features</li>
              <li>Manage users and roles</li>
              <li>Approve new accounts</li>
              <li>Edit roster, schedule, budget</li>
            </ul>
          </div>
          <div className="p-4 bg-amber-50 rounded-sm border border-amber-200">
            <div className="flex items-center gap-2 mb-2">
              <UserCog className="w-5 h-5 text-amber-700" />
              <span className="font-bold text-amber-700">Staff</span>
            </div>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>Edit roster participants</li>
              <li>Manage schedule events</li>
              <li>Assign users to units</li>
              <li>Manage documents</li>
            </ul>
          </div>
          <div className="p-4 bg-emerald-50 rounded-sm border border-emerald-200">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-emerald-700" />
              <span className="font-bold text-emerald-700">Finance</span>
            </div>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>Full budget access</li>
              <li>Manage expenses & income</li>
              <li>Upload receipts</li>
              <li>Food expense planning</li>
            </ul>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-slate-200">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-5 h-5 text-slate-600" />
              <span className="font-bold text-slate-600">Cadet</span>
            </div>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>View roster</li>
              <li>View their unit's schedule</li>
              <li>Access documents</li>
              <li>No budget access</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Unit Structure Info */}
      <div className="bg-white border border-slate-200 rounded-sm">
        <div className="border-b border-slate-100 p-4">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Plane className="w-4 h-4" />
            Unit Structure
          </h2>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 bg-blue-50 rounded-sm border border-blue-200">
            <div className="flex items-center gap-3 mb-2">
              <img src="/patches/6th_cts.png" alt="6th CTS" className="w-12 h-12 object-contain rounded" />
              <div>
                <p className="font-bold text-blue-800">6th CTS</p>
                <p className="text-xs text-blue-600">6th Cadet Training Squadron</p>
              </div>
            </div>
            <div className="flex gap-2 mt-2">
              <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-medium">Alpha</span>
              <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-medium">Bravo</span>
            </div>
          </div>
          <div className="p-3 bg-red-50 rounded-sm border border-red-200">
            <div className="flex items-center gap-3 mb-2">
              <img src="/patches/21st_cts.png" alt="21st CTS" className="w-12 h-12 object-contain rounded" />
              <div>
                <p className="font-bold text-red-800">21st CTS</p>
                <p className="text-xs text-red-600">21st Cadet Training Squadron</p>
                <p className="text-xs text-red-500 italic">Scorpions</p>
              </div>
            </div>
            <div className="flex gap-2 mt-2">
              <span className="bg-red-100 text-red-700 px-2 py-1 rounded text-xs font-medium">Charlie</span>
              <span className="bg-red-100 text-red-700 px-2 py-1 rounded text-xs font-medium">Delta</span>
            </div>
          </div>
          <div className="p-3 bg-amber-50 rounded-sm border border-amber-200">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 bg-amber-100 rounded flex items-center justify-center">
                <Plane className="w-6 h-6 text-amber-700" />
              </div>
              <div>
                <p className="font-bold text-amber-800">22nd CTS</p>
                <p className="text-xs text-amber-600">22nd Cadet Training Squadron</p>
                <p className="text-xs text-amber-500 italic">Night Owls</p>
              </div>
            </div>
            <div className="flex gap-2 mt-2">
              <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded text-xs font-medium">Echo</span>
              <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded text-xs font-medium">Foxtrot</span>
            </div>
          </div>
        </div>
      </div>

      {/* Honor Agreement Tracker */}
      <HonorAgreementTracker />

      {/* Google Sheets Sync */}
      <div className="bg-white border border-slate-200 rounded-sm">
        <div className="border-b border-slate-100 p-4">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Cloud className="w-4 h-4" />
            Google Sheets Live Sync
          </h2>
          <p className="text-xs text-slate-500 mt-1">Connect Google Sheets to automatically update roster data</p>
        </div>
        <div className="p-4 space-y-6">
          {/* Sync Status */}
          {syncStatus && (
            <div className={`p-3 rounded-sm flex items-center justify-between ${
              syncStatus.last_sync_status === 'success' ? 'bg-emerald-50 border border-emerald-200' :
              syncStatus.last_sync_status === 'error' ? 'bg-red-50 border border-red-200' :
              syncStatus.last_sync_status === 'running' ? 'bg-blue-50 border border-blue-200' :
              'bg-slate-50 border border-slate-200'
            }`}>
              <div className="flex items-center gap-3">
                {syncStatus.last_sync_status === 'success' && <CheckCircle className="w-5 h-5 text-emerald-600" />}
                {syncStatus.last_sync_status === 'error' && <AlertTriangle className="w-5 h-5 text-red-600" />}
                {syncStatus.last_sync_status === 'running' && <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />}
                {!syncStatus.last_sync_status && <Clock className="w-5 h-5 text-slate-400" />}
                <div>
                  <p className="text-sm font-medium">
                    {syncStatus.last_sync_status === 'success' && 'Last sync successful'}
                    {syncStatus.last_sync_status === 'error' && 'Last sync failed'}
                    {syncStatus.last_sync_status === 'running' && 'Sync in progress...'}
                    {!syncStatus.last_sync_status && 'No sync performed yet'}
                  </p>
                  {syncStatus.last_sync_at && (
                    <p className="text-xs text-slate-500">
                      {new Date(syncStatus.last_sync_at).toLocaleString()}
                    </p>
                  )}
                  {syncStatus.last_sync_message && (
                    <p className="text-xs text-slate-600 mt-1">{syncStatus.last_sync_message}</p>
                  )}
                </div>
              </div>
              <Button
                onClick={handleManualSync}
                disabled={syncingNow || syncStatus.last_sync_status === 'running'}
                variant="outline"
                size="sm"
                className="rounded-sm"
                data-testid="sync-now-btn"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${syncingNow ? 'animate-spin' : ''}`} />
                Sync Now
              </Button>
            </div>
          )}

          {/* Schedules — Phase 8: multiple named schedules, each sync'd independently */}
          <div className="space-y-3" data-testid="schedules-config">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-600" />
                <Label className="text-sm font-bold uppercase text-slate-700">Schedules</Label>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addSchedule}
                className="rounded-sm"
                data-testid="add-schedule-btn"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Add Schedule
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              Each schedule syncs to its own Google Sheet. Events imported from one
              schedule are tagged separately, so syncing CAST does not touch
              Encampment events. Change a sheet link anytime (e.g. draft → final).
            </p>

            {schedules.length === 0 && (
              <div className="text-sm text-slate-400 italic py-3 px-2 border border-dashed border-slate-200 rounded-sm text-center">
                No schedules configured. Click "Add Schedule" to start.
              </div>
            )}

            {schedules.map((s, idx) => {
              const fullUrl = s.spreadsheet_id
                ? `https://docs.google.com/spreadsheets/d/${s.spreadsheet_id}/edit${s.gid ? `#gid=${s.gid}` : ''}`
                : '';
              return (
                <div
                  key={s.id || idx}
                  className="border border-slate-200 rounded-sm p-3 space-y-2 bg-slate-50/40"
                  data-testid={`schedule-row-${s.id || idx}`}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs text-slate-500 mb-1 block">Schedule Name</Label>
                      <Input
                        value={s.label || ''}
                        onChange={(e) => updateScheduleField(idx, 'label', e.target.value)}
                        placeholder="CAST Weekend (May 29-31)"
                        className="rounded-sm text-sm"
                        data-testid={`schedule-label-${idx}`}
                      />
                    </div>
                    <div>
                      <Label className="text-xs text-slate-500 mb-1 block">Sheet Tab (gid, optional)</Label>
                      <Input
                        value={s.gid || ''}
                        onChange={(e) => updateScheduleField(idx, 'gid', e.target.value)}
                        placeholder="(leave blank for first tab)"
                        className="rounded-sm text-sm font-mono"
                        data-testid={`schedule-gid-${idx}`}
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500 mb-1 block">
                      Google Sheet URL or Spreadsheet ID
                    </Label>
                    <Input
                      value={fullUrl || s.spreadsheet_id || ''}
                      onChange={(e) => updateScheduleUrl(idx, e.target.value)}
                      placeholder="https://docs.google.com/spreadsheets/d/{ID}/edit?usp=drive_link"
                      className="rounded-sm text-sm font-mono"
                      data-testid={`schedule-url-${idx}`}
                    />
                    <p className="text-[11px] text-slate-400 mt-1">
                      Paste a full Google Sheets URL — we'll extract the ID and tab automatically.
                    </p>
                  </div>

                  {/* Telemetry + per-row controls */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-200">
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={!!s.enabled}
                          onChange={(e) => updateScheduleField(idx, 'enabled', e.target.checked)}
                          className="rounded"
                          data-testid={`schedule-enabled-${idx}`}
                        />
                        <span>Auto-sync enabled</span>
                      </label>
                      {s.last_sync_status === 'success' && (
                        <span className="flex items-center gap-1 text-emerald-600">
                          <CheckCircle className="w-3 h-3" />
                          {s.last_event_count ?? '—'} events
                          {s.last_sync_at && ` · ${new Date(s.last_sync_at).toLocaleString()}`}
                        </span>
                      )}
                      {s.last_sync_status === 'error' && (
                        <span className="flex items-center gap-1 text-rose-600" title={s.last_sync_message || ''}>
                          <AlertTriangle className="w-3 h-3" />
                          {s.last_sync_message ? `Error: ${s.last_sync_message.slice(0, 80)}` : 'Sync failed'}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {fullUrl && (
                        <a
                          href={fullUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-slate-500 hover:text-[#00205B] flex items-center gap-1"
                          data-testid={`schedule-open-${idx}`}
                        >
                          <ExternalLink className="w-3 h-3" />
                          Open
                        </a>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleSyncSchedule(s.id)}
                        disabled={!s.id || !s.spreadsheet_id}
                        className="rounded-sm h-7 text-xs"
                        data-testid={`schedule-sync-now-${idx}`}
                      >
                        <RefreshCw className="w-3 h-3 mr-1" />
                        Sync now
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeSchedule(idx)}
                        className="rounded-sm h-7 text-xs text-rose-600 hover:bg-rose-50"
                        data-testid={`schedule-remove-${idx}`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}

            <div className="text-[11px] text-slate-500 leading-relaxed bg-slate-50 border border-slate-200 rounded-sm p-2.5 space-y-1.5">
              <p>
                <strong className="text-slate-700">Two sheet formats supported</strong> — the parser auto-detects which one your sheet uses:
              </p>
              <p>
                <strong>1. Flat table:</strong> one row per event with columns{' '}
                <code>Date</code>, <code>Start Time</code>, <code>End Time</code>,{' '}
                <code>Title</code> (optionally <code>Location</code>,{' '}
                <code>Event Type</code>, <code>Target Groups</code>,{' '}
                <code>Uniform</code>, <code>Notes</code>).
              </p>
              <p>
                <strong>2. Grid layout</strong> (CAST / Encampment day tabs): cell{' '}
                <code>A1</code> contains a Month + Day (e.g.{' '}
                <em>“Friday | Day 1 CADRE Arrival | May 29th”</em>), then a header row with{' '}
                <code>START</code>, <code>END</code>, one column per squadron (e.g.{' '}
                <code>6th CTS</code>, <code>21st CTS</code>) and an optional{' '}
                <code>Notes</code> column. Use one Schedule entry per day tab — paste the URL with{' '}
                <code>?gid=...</code> for the tab. Horizontally-merged cells apply to all squadrons in the block; vertically-merged cells extend the event end time automatically.
              </p>
            </div>
          </div>

          {/* Org Chart Sheet Config */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-blue-600" />
              <Label className="text-sm font-bold uppercase text-slate-700">Org Chart Sheet (Optional)</Label>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-slate-500 mb-1 block">Spreadsheet ID</Label>
                <Input
                  value={gsheetSettings.orgChartSpreadsheetId}
                  onChange={(e) => setGsheetSettings(prev => ({ ...prev, orgChartSpreadsheetId: e.target.value }))}
                  placeholder="1b9JpdOsUHT7p18fC2qykFvbuMNFidT5ydl161_lFFW8"
                  className="rounded-sm text-sm font-mono"
                  data-testid="orgchart-spreadsheet-id"
                />
              </div>
              <div>
                <Label className="text-xs text-slate-500 mb-1 block">Sheet Tab GIDs (comma-separated)</Label>
                <Input
                  value={gsheetSettings.orgChartGids}
                  onChange={(e) => setGsheetSettings(prev => ({ ...prev, orgChartGids: e.target.value }))}
                  placeholder="1271574678, 123456789"
                  className="rounded-sm text-sm font-mono"
                  data-testid="orgchart-gids"
                />
              </div>
            </div>
          </div>

          {/* Sync Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
            <div>
              <Label className="text-xs text-slate-500 mb-1 block">Sync Interval</Label>
              <Select 
                value={String(gsheetSettings.syncIntervalHours)}
                onValueChange={(v) => setGsheetSettings(prev => ({ ...prev, syncIntervalHours: parseInt(v) }))}
              >
                <SelectTrigger className="rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Every Hour</SelectItem>
                  <SelectItem value="2">Every 2 Hours</SelectItem>
                  <SelectItem value="4">Every 4 Hours</SelectItem>
                  <SelectItem value="6">Every 6 Hours</SelectItem>
                  <SelectItem value="12">Every 12 Hours</SelectItem>
                  <SelectItem value="24">Daily</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="autoSyncEnabled"
                checked={gsheetSettings.autoSyncEnabled}
                onChange={(e) => setGsheetSettings(prev => ({ ...prev, autoSyncEnabled: e.target.checked }))}
                className="rounded"
              />
              <Label htmlFor="autoSyncEnabled" className="text-sm">Enable automatic sync</Label>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4">
            <Button
              onClick={handleSaveGsheetSettings}
              disabled={savingGsheetSettings}
              className="bg-[#00205B] rounded-sm"
              data-testid="save-gsheet-settings-btn"
            >
              {savingGsheetSettings ? 'Saving...' : 'Save Google Sheets Settings'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const HonorAgreementTracker = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [tab, setTab] = useState('unsigned');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const result = await getHonorAgreementStatus();
      setData(result);
    } catch (err) {
      console.error('Failed to load honor agreement status:', err);
      toast.error('Failed to load agreement data');
    } finally {
      setLoading(false);
    }
  };

  const handleSendReminders = async () => {
    setSending(true);
    try {
      const result = await sendHonorAgreementReminders();
      alert(result.count === 0
        ? 'All cadre and staff have signed!'
        : `Sent reminders to ${result.count} user(s)`);
    } catch (err) {
      alert('Failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSending(false);
    }
  };

  const formatRole = (role) => role?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="bg-white border border-slate-200 rounded-sm" data-testid="honor-agreement-tracker">
      <div className="border-b border-slate-100 p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Shield className="w-4 h-4" />
            Honor Agreement Tracker
          </h2>
          {data && (
            <p className="text-xs text-slate-500 mt-1">
              {data.signed_count} of {data.total} signed ({data.unsigned_count} remaining)
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData} className="rounded-sm" data-testid="refresh-honor-status">
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
          </Button>
          <Button size="sm" onClick={handleSendReminders} disabled={sending} className="bg-amber-600 hover:bg-amber-700 rounded-sm" data-testid="send-honor-reminders-btn">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> {sending ? 'Sending...' : 'Send Reminders'}
          </Button>
        </div>
      </div>

      {/* Progress Bar */}
      {data && (
        <div className="px-4 pt-3">
          <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
            <div
              className="h-3 bg-emerald-500 rounded-full transition-all"
              style={{ width: `${data.total > 0 ? (data.signed_count / data.total * 100) : 0}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 mt-1">
            <span>{Math.round(data.total > 0 ? (data.signed_count / data.total * 100) : 0)}% complete</span>
            <span>{data.signed_count}/{data.total}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 mx-4 mt-3">
        <button
          onClick={() => setTab('unsigned')}
          className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px ${tab === 'unsigned' ? 'border-red-500 text-red-600' : 'border-transparent text-slate-400 hover:text-slate-600'}`}
          data-testid="honor-tab-unsigned"
        >
          <XCircle className="w-3 h-3 inline mr-1" />
          Not Signed ({data?.unsigned_count || 0})
        </button>
        <button
          onClick={() => setTab('signed')}
          className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px ${tab === 'signed' ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-slate-400 hover:text-slate-600'}`}
          data-testid="honor-tab-signed"
        >
          <CheckCircle className="w-3 h-3 inline mr-1" />
          Signed ({data?.signed_count || 0})
        </button>
      </div>

      {/* Table */}
      <div className="p-4">
        {loading ? (
          <p className="text-center text-sm text-slate-400 py-4">Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-2 text-xs uppercase text-slate-500 font-medium">Name</th>
                  <th className="text-left py-2 px-2 text-xs uppercase text-slate-500 font-medium">Email</th>
                  <th className="text-left py-2 px-2 text-xs uppercase text-slate-500 font-medium">Role</th>
                  <th className="text-left py-2 px-2 text-xs uppercase text-slate-500 font-medium">Type</th>
                  {tab === 'signed' && (
                    <>
                      <th className="text-left py-2 px-2 text-xs uppercase text-slate-500 font-medium">Signature</th>
                      <th className="text-left py-2 px-2 text-xs uppercase text-slate-500 font-medium">Signed At</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {(tab === 'unsigned' ? data?.unsigned : data?.signed)?.map(u => (
                  <tr key={u.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 px-2 font-medium">{u.name}</td>
                    <td className="py-2 px-2 text-slate-500">{u.email}</td>
                    <td className="py-2 px-2">
                      <span className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{formatRole(u.role)}</span>
                    </td>
                    <td className="py-2 px-2">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${u.agreement_type === 'cadre' ? 'bg-blue-100 text-blue-700' : 'bg-indigo-100 text-indigo-700'}`}>
                        {u.agreement_type === 'cadre' ? 'Cadre' : 'Staff'}
                      </span>
                    </td>
                    {tab === 'signed' && (
                      <>
                        <td className="py-2 px-2 italic text-slate-600" style={{ fontFamily: 'cursive, serif' }}>{u.signature_name}</td>
                        <td className="py-2 px-2 text-slate-400 text-xs">{u.signed_at ? new Date(u.signed_at).toLocaleString() : '-'}</td>
                      </>
                    )}
                  </tr>
                ))}
                {(tab === 'unsigned' ? data?.unsigned : data?.signed)?.length === 0 && (
                  <tr>
                    <td colSpan={tab === 'signed' ? 6 : 4} className="text-center py-6 text-slate-400">
                      {tab === 'unsigned' ? 'Everyone has signed!' : 'No signatures yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminSettingsTab;
