import React from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  Shield, UserCog, DollarSign, Users, Plane, 
  Cloud, CheckCircle, AlertTriangle, RefreshCw, Clock,
  FileSpreadsheet, ExternalLink
} from 'lucide-react';

const AdminSettingsTab = ({
  gsheetSettings,
  setGsheetSettings,
  syncStatus,
  syncingNow,
  savingGsheetSettings,
  handleSaveGsheetSettings,
  handleManualSync,
  syncingParticipants,
  handleSyncUsersToRoster
}) => {
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

          {/* Roster Sheet Config */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <Label className="text-sm font-bold uppercase text-slate-700">Roster Sheet</Label>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-slate-500 mb-1 block">Spreadsheet ID</Label>
                <Input
                  value={gsheetSettings.rosterSpreadsheetId}
                  onChange={(e) => setGsheetSettings(prev => ({ ...prev, rosterSpreadsheetId: e.target.value }))}
                  placeholder="1-HbkFiABYG3fIsF41crkD-T5aCRJ-Zq7"
                  className="rounded-sm text-sm font-mono"
                  data-testid="roster-spreadsheet-id"
                />
              </div>
              <div>
                <Label className="text-xs text-slate-500 mb-1 block">Sheet Tab (gid)</Label>
                <Input
                  value={gsheetSettings.rosterGid}
                  onChange={(e) => setGsheetSettings(prev => ({ ...prev, rosterGid: e.target.value }))}
                  placeholder="345615746"
                  className="rounded-sm text-sm font-mono"
                  data-testid="roster-gid"
                />
              </div>
            </div>
            <p className="text-xs text-slate-400">
              Find these in your Google Sheets URL: docs.google.com/spreadsheets/d/<strong>[SPREADSHEET_ID]</strong>/edit?gid=<strong>[GID]</strong>
            </p>
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

export default AdminSettingsTab;
