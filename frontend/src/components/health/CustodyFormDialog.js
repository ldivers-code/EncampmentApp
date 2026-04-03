import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const CustodyFormDialog = ({ open, onClose, onSubmit, referenceLists, medications }) => {
  const [formData, setFormData] = useState({
    medication_name: '',
    action_type: 'check_in',
    quantity: '',
    notes: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[#00205B] uppercase font-bold">Log Custody Action</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div>
            <Label className="text-xs">Medication *</Label>
            {medications?.length > 0 ? (
              <Select value={formData.medication_name} onValueChange={(v) => setFormData({...formData, medication_name: v})}>
                <SelectTrigger className="rounded-sm">
                  <SelectValue placeholder="Select medication" />
                </SelectTrigger>
                <SelectContent>
                  {medications.map(m => (
                    <SelectItem key={m.med_profile_id} value={m.medication_name}>{m.medication_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input 
                value={formData.medication_name}
                onChange={(e) => setFormData({...formData, medication_name: e.target.value})}
                required
                className="rounded-sm"
              />
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Action Type *</Label>
              <Select value={formData.action_type} onValueChange={(v) => setFormData({...formData, action_type: v})}>
                <SelectTrigger className="rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {referenceLists?.custody_actions?.map(a => (
                    <SelectItem key={a} value={a}>{a.replace('_', ' ')}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Quantity</Label>
              <Input 
                value={formData.quantity}
                onChange={(e) => setFormData({...formData, quantity: e.target.value})}
                placeholder="e.g., 30 tablets"
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
            <Button type="submit" className="bg-[#00205B]">Log Action</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CustodyFormDialog;
