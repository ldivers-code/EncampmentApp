import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const IncidentFormDialog = ({ open, onClose, onSubmit, referenceLists, medications }) => {
  const now = new Date();
  const [formData, setFormData] = useState({
    incident_date: now.toISOString().split('T')[0],
    incident_time: now.toTimeString().slice(0, 5).replace(':', ''),
    incident_type: 'other',
    related_medication: '',
    description: '',
    parent_contacted: false,
    parent_contact_time: '',
    command_notified: false
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[#00205B] uppercase font-bold">Log Health Incident</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Date *</Label>
              <Input 
                type="date"
                value={formData.incident_date}
                onChange={(e) => setFormData({...formData, incident_date: e.target.value})}
                required
                className="rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Time *</Label>
              <Input 
                value={formData.incident_time}
                onChange={(e) => setFormData({...formData, incident_time: e.target.value})}
                placeholder="HHMM"
                required
                className="rounded-sm"
              />
            </div>
          </div>
          <div>
            <Label className="text-xs">Incident Type *</Label>
            <Select value={formData.incident_type} onValueChange={(v) => setFormData({...formData, incident_type: v})}>
              <SelectTrigger className="rounded-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {referenceLists?.incident_types?.map(t => (
                  <SelectItem key={t} value={t}>{t.replace('_', ' ')}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {medications?.length > 0 && (
            <div>
              <Label className="text-xs">Related Medication</Label>
              <Select value={formData.related_medication} onValueChange={(v) => setFormData({...formData, related_medication: v})}>
                <SelectTrigger className="rounded-sm">
                  <SelectValue placeholder="Select if applicable" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {medications.map(m => (
                    <SelectItem key={m.med_profile_id} value={m.medication_name}>{m.medication_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div>
            <Label className="text-xs">Description *</Label>
            <Textarea 
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              required
              className="rounded-sm"
              rows={3}
            />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input 
                type="checkbox"
                checked={formData.parent_contacted}
                onChange={(e) => setFormData({...formData, parent_contacted: e.target.checked})}
              />
              Parent Contacted
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input 
                type="checkbox"
                checked={formData.command_notified}
                onChange={(e) => setFormData({...formData, command_notified: e.target.checked})}
              />
              Command Notified
            </label>
          </div>
          {formData.parent_contacted && (
            <div>
              <Label className="text-xs">Contact Time</Label>
              <Input 
                value={formData.parent_contact_time}
                onChange={(e) => setFormData({...formData, parent_contact_time: e.target.value})}
                placeholder="HHMM"
                className="rounded-sm"
              />
            </div>
          )}
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="bg-[#00205B]">Log Incident</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default IncidentFormDialog;
