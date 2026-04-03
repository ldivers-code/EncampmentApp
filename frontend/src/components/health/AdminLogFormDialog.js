import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const AdminLogFormDialog = ({ open, onClose, onSubmit, medication, referenceLists }) => {
  const now = new Date();
  const [formData, setFormData] = useState({
    date: now.toISOString().split('T')[0],
    time_due: '',
    time_taken: now.toTimeString().slice(0, 5).replace(':', ''),
    result: 'taken',
    observer_initials: '',
    cadet_initials: '',
    notes: ''
  });

  useEffect(() => {
    if (medication) {
      const dueTimes = medication.due_times?.split(',') || [];
      setFormData(prev => ({
        ...prev,
        time_due: dueTimes[0] || ''
      }));
    }
  }, [medication]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  if (!medication) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[#00205B] uppercase font-bold">Log Administration</DialogTitle>
        </DialogHeader>
        <div className="bg-blue-50 p-3 rounded-sm mb-4">
          <p className="font-medium">{medication.medication_name}</p>
          <p className="text-sm text-slate-600">{medication.dose} - {medication.route}</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Date *</Label>
              <Input 
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({...formData, date: e.target.value})}
                required
                className="rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Time Due *</Label>
              <Select value={formData.time_due} onValueChange={(v) => setFormData({...formData, time_due: v})}>
                <SelectTrigger className="rounded-sm">
                  <SelectValue placeholder="Select time" />
                </SelectTrigger>
                <SelectContent>
                  {medication.due_times?.split(',').map(t => (
                    <SelectItem key={t.trim()} value={t.trim()}>{t.trim().slice(0,2)}:{t.trim().slice(2)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Time Taken</Label>
              <Input 
                value={formData.time_taken}
                onChange={(e) => setFormData({...formData, time_taken: e.target.value})}
                placeholder="HHMM"
                className="rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Result *</Label>
              <Select value={formData.result} onValueChange={(v) => setFormData({...formData, result: v})}>
                <SelectTrigger className="rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {referenceLists?.result_types?.map(r => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Observer Initials *</Label>
              <Input 
                value={formData.observer_initials}
                onChange={(e) => setFormData({...formData, observer_initials: e.target.value.toUpperCase()})}
                maxLength={4}
                required
                className="rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Cadet Initials</Label>
              <Input 
                value={formData.cadet_initials}
                onChange={(e) => setFormData({...formData, cadet_initials: e.target.value.toUpperCase()})}
                maxLength={4}
                className="rounded-sm"
              />
            </div>
          </div>
          <div>
            <Label className="text-xs">Notes</Label>
            <Textarea 
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              className="rounded-sm"
              rows={2}
            />
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="bg-[#00205B]">Log Administration</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default AdminLogFormDialog;
