import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const MedicationFormDialog = ({ open, onClose, onSubmit, referenceLists }) => {
  const [formData, setFormData] = useState({
    medication_name: '',
    dose: '',
    route: 'oral',
    schedule_text: '',
    due_times: '',
    special_instructions: '',
    refrigeration_required: false,
    rescue_med_flag: false
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[#00205B] uppercase font-bold">Add Medication Profile</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div>
            <Label className="text-xs">Medication Name *</Label>
            <Input 
              value={formData.medication_name}
              onChange={(e) => setFormData({...formData, medication_name: e.target.value})}
              required
              className="rounded-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Dose *</Label>
              <Input 
                value={formData.dose}
                onChange={(e) => setFormData({...formData, dose: e.target.value})}
                placeholder="e.g., 10mg"
                required
                className="rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Route</Label>
              <Select value={formData.route} onValueChange={(v) => setFormData({...formData, route: v})}>
                <SelectTrigger className="rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {referenceLists?.routes?.map(r => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label className="text-xs">Schedule Description</Label>
            <Input 
              value={formData.schedule_text}
              onChange={(e) => setFormData({...formData, schedule_text: e.target.value})}
              placeholder="e.g., Every 8 hours with meals"
              className="rounded-sm"
            />
          </div>
          <div>
            <Label className="text-xs">Due Times (24hr, comma-separated) *</Label>
            <Input 
              value={formData.due_times}
              onChange={(e) => setFormData({...formData, due_times: e.target.value})}
              placeholder="0800,1200,1800,2200"
              required
              className="rounded-sm"
            />
          </div>
          <div>
            <Label className="text-xs">Special Instructions</Label>
            <Textarea 
              value={formData.special_instructions}
              onChange={(e) => setFormData({...formData, special_instructions: e.target.value})}
              className="rounded-sm"
              rows={2}
            />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input 
                type="checkbox"
                checked={formData.refrigeration_required}
                onChange={(e) => setFormData({...formData, refrigeration_required: e.target.checked})}
              />
              Requires Refrigeration
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input 
                type="checkbox"
                checked={formData.rescue_med_flag}
                onChange={(e) => setFormData({...formData, rescue_med_flag: e.target.checked})}
              />
              Rescue Medication
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="bg-[#00205B]">Add Medication</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default MedicationFormDialog;
