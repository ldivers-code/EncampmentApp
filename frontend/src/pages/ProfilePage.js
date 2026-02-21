import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { getProfile, updateProfile, uploadProfilePhoto, deleteProfilePhoto } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  User, 
  Mail, 
  Phone, 
  MapPin, 
  Shield, 
  Camera,
  Save,
  X,
  AlertTriangle,
  CheckCircle,
  Clock,
  Building,
  Users,
  Heart
} from 'lucide-react';

const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({});
  const fileInputRef = useRef(null);

  const ranks = [
    // Cadet ranks
    'C/AB', 'C/Amn', 'C/A1C', 'C/SrA', 'C/SSgt', 'C/TSgt', 'C/MSgt', 'C/SMSgt', 'C/CMSgt',
    'C/2dLt', 'C/1stLt', 'C/Capt', 'C/Maj', 'C/LtCol', 'C/Col',
    // Senior ranks
    'SM', '2d Lt', '1st Lt', 'Capt', 'Maj', 'Lt Col', 'Col', 'Brig Gen', 'Maj Gen'
  ];

  const shirtSizes = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL'];

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await getProfile();
      setProfile(data);
      setFormData(data);
    } catch (error) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value === 'none' ? null : value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateProfile(formData);
      setProfile(updated);
      setEditMode(false);
      toast.success('Profile updated successfully');
      if (refreshUser) refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setFormData(profile);
    setEditMode(false);
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be less than 5MB');
      return;
    }

    try {
      const result = await uploadProfilePhoto(file);
      setProfile(prev => ({ ...prev, photo_url: result.photo_url }));
      setFormData(prev => ({ ...prev, photo_url: result.photo_url }));
      toast.success('Photo uploaded successfully');
    } catch (error) {
      toast.error('Failed to upload photo');
    }
  };

  const handlePhotoDelete = async () => {
    if (!window.confirm('Remove your profile photo?')) return;
    
    try {
      await deleteProfilePhoto();
      setProfile(prev => ({ ...prev, photo_url: null }));
      setFormData(prev => ({ ...prev, photo_url: null }));
      toast.success('Photo removed');
    } catch (error) {
      toast.error('Failed to remove photo');
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading profile...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          {/* Profile Photo */}
          <div className="relative group">
            <div className="w-20 h-20 rounded-full bg-slate-200 border-4 border-white shadow-lg overflow-hidden">
              {profile?.photo_url ? (
                <img src={profile.photo_url} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-[#00205B] text-white text-2xl font-bold">
                  {profile?.name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
              )}
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="absolute bottom-0 right-0 w-8 h-8 bg-[#00205B] rounded-full flex items-center justify-center text-white shadow-lg hover:bg-[#001540] transition-colors"
              data-testid="upload-photo-btn"
            >
              <Camera className="w-4 h-4" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handlePhotoUpload}
              className="hidden"
            />
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              {profile?.name || 'My Profile'}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                profile?.role === 'commander' ? 'bg-[#00205B] text-white' :
                profile?.role === 'staff' ? 'bg-amber-100 text-amber-800' :
                profile?.role === 'finance' ? 'bg-emerald-100 text-emerald-800' :
                'bg-slate-100 text-slate-800'
              }`}>
                {profile?.role}
              </span>
              {profile?.is_approved ? (
                <span className="text-xs text-emerald-600 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Approved
                </span>
              ) : (
                <span className="text-xs text-amber-600 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Pending Approval
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {editMode ? (
            <>
              <Button
                variant="outline"
                onClick={handleCancel}
                className="rounded-sm"
                data-testid="cancel-edit-btn"
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
                className="rounded-sm bg-[#00205B] hover:bg-[#001540]"
                data-testid="save-profile-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </>
          ) : (
            <Button
              onClick={() => setEditMode(true)}
              className="rounded-sm bg-[#00205B] hover:bg-[#001540]"
              data-testid="edit-profile-btn"
            >
              Edit Profile
            </Button>
          )}
        </div>
      </div>

      {/* Photo Actions */}
      {profile?.photo_url && (
        <div className="mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={handlePhotoDelete}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            Remove Photo
          </Button>
        </div>
      )}

      {/* Profile Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Basic Information */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4 flex items-center gap-2">
            <User className="w-5 h-5 text-[#00205B]" />
            <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Basic Information</h2>
          </div>
          <div className="p-4 space-y-4">
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Full Name</Label>
              {editMode ? (
                <Input
                  name="name"
                  value={formData.name || ''}
                  onChange={handleChange}
                  className="mt-1 rounded-sm"
                  data-testid="profile-name-input"
                />
              ) : (
                <p className="mt-1 font-medium">{profile?.name || '-'}</p>
              )}
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Email</Label>
              {editMode ? (
                <Input
                  name="email"
                  type="email"
                  value={formData.email || ''}
                  onChange={handleChange}
                  className="mt-1 rounded-sm"
                  data-testid="profile-email-input"
                />
              ) : (
                <p className="mt-1 font-medium flex items-center gap-2">
                  <Mail className="w-4 h-4 text-slate-400" />
                  {profile?.email || '-'}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Phone</Label>
                {editMode ? (
                  <Input
                    name="phone"
                    value={formData.phone || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="(555) 123-4567"
                    data-testid="profile-phone-input"
                  />
                ) : (
                  <p className="mt-1 font-medium flex items-center gap-2">
                    <Phone className="w-4 h-4 text-slate-400" />
                    {profile?.phone || '-'}
                  </p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Cell Phone</Label>
                {editMode ? (
                  <Input
                    name="cell_phone"
                    value={formData.cell_phone || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="(555) 123-4567"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.cell_phone || '-'}</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Gender</Label>
                {editMode ? (
                  <Select
                    value={formData.gender || 'none'}
                    onValueChange={(v) => handleSelectChange('gender', v)}
                  >
                    <SelectTrigger className="mt-1 rounded-sm">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Not specified</SelectItem>
                      <SelectItem value="M">Male</SelectItem>
                      <SelectItem value="F">Female</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="mt-1 font-medium">
                    {profile?.gender === 'M' ? 'Male' : profile?.gender === 'F' ? 'Female' : '-'}
                  </p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Shirt Size</Label>
                {editMode ? (
                  <Select
                    value={formData.shirt_size || 'none'}
                    onValueChange={(v) => handleSelectChange('shirt_size', v)}
                  >
                    <SelectTrigger className="mt-1 rounded-sm">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Not specified</SelectItem>
                      {shirtSizes.map(size => (
                        <SelectItem key={size} value={size}>{size}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="mt-1 font-medium">{profile?.shirt_size || '-'}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* CAP Information */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-[#00205B]" />
            <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">CAP Information</h2>
          </div>
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">CAPID</Label>
                {editMode ? (
                  <Input
                    name="capid"
                    value={formData.capid || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm font-mono"
                    placeholder="123456"
                    data-testid="profile-capid-input"
                  />
                ) : (
                  <p className="mt-1 font-mono font-bold text-[#00205B]">{profile?.capid || '-'}</p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Rank</Label>
                {editMode ? (
                  <Select
                    value={formData.rank || 'none'}
                    onValueChange={(v) => handleSelectChange('rank', v)}
                  >
                    <SelectTrigger className="mt-1 rounded-sm">
                      <SelectValue placeholder="Select rank" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Not specified</SelectItem>
                      {ranks.map(rank => (
                        <SelectItem key={rank} value={rank}>{rank}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="mt-1 font-medium">{profile?.rank || '-'}</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Unit</Label>
                {editMode ? (
                  <Input
                    name="unit"
                    value={formData.unit || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="TN-001"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.unit || '-'}</p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Wing</Label>
                {editMode ? (
                  <Input
                    name="wing"
                    value={formData.wing || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="TN"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.wing || '-'}</p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">Region</Label>
                {editMode ? (
                  <Input
                    name="region"
                    value={formData.region || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="SER"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.region || '-'}</p>
                )}
              </div>
            </div>
            {/* Squadron/Flight (read-only, set by admin) */}
            {(profile?.squadron || profile?.flight) && (
              <div className="pt-2 border-t border-slate-100">
                <Label className="text-xs uppercase tracking-wide text-slate-500">Encampment Assignment</Label>
                <p className="mt-1 font-medium flex items-center gap-2">
                  <Users className="w-4 h-4 text-slate-400" />
                  {profile?.squadron && <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">{profile.squadron.toUpperCase()}</span>}
                  {profile?.flight && <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs">{profile.flight.toUpperCase()}</span>}
                </p>
                <p className="text-xs text-slate-400 mt-1">Set by encampment administration</p>
              </div>
            )}
          </div>
        </div>

        {/* Address */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-[#00205B]" />
            <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Address</h2>
          </div>
          <div className="p-4 space-y-4">
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Street Address</Label>
              {editMode ? (
                <Input
                  name="address"
                  value={formData.address || ''}
                  onChange={handleChange}
                  className="mt-1 rounded-sm"
                  placeholder="123 Main Street"
                />
              ) : (
                <p className="mt-1 font-medium">{profile?.address || '-'}</p>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">City</Label>
                {editMode ? (
                  <Input
                    name="city"
                    value={formData.city || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.city || '-'}</p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">State</Label>
                {editMode ? (
                  <Input
                    name="state"
                    value={formData.state || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="TN"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.state || '-'}</p>
                )}
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-500">ZIP Code</Label>
                {editMode ? (
                  <Input
                    name="zip_code"
                    value={formData.zip_code || ''}
                    onChange={handleChange}
                    className="mt-1 rounded-sm"
                    placeholder="37000"
                  />
                ) : (
                  <p className="mt-1 font-medium">{profile?.zip_code || '-'}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4 flex items-center gap-2">
            <Heart className="w-5 h-5 text-[#BF0D3E]" />
            <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Emergency Contact</h2>
          </div>
          <div className="p-4 space-y-4">
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Contact Name</Label>
              {editMode ? (
                <Input
                  name="emergency_contact"
                  value={formData.emergency_contact || ''}
                  onChange={handleChange}
                  className="mt-1 rounded-sm"
                  placeholder="Jane Doe"
                />
              ) : (
                <p className="mt-1 font-medium">{profile?.emergency_contact || '-'}</p>
              )}
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Contact Phone</Label>
              {editMode ? (
                <Input
                  name="emergency_phone"
                  value={formData.emergency_phone || ''}
                  onChange={handleChange}
                  className="mt-1 rounded-sm"
                  placeholder="(555) 123-4567"
                />
              ) : (
                <p className="mt-1 font-medium flex items-center gap-2">
                  <Phone className="w-4 h-4 text-slate-400" />
                  {profile?.emergency_phone || '-'}
                </p>
              )}
            </div>

            {/* Parent/Guardian Info (for cadets) */}
            {(profile?.role === 'cadet' || formData.cadet_parent_name || formData.cadet_parent_phone || formData.cadet_parent_email) && (
              <>
                <div className="pt-2 border-t border-slate-100">
                  <Label className="text-xs uppercase tracking-wide text-slate-500 mb-2 block">Parent/Guardian</Label>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-500">Parent Name</Label>
                  {editMode ? (
                    <Input
                      name="cadet_parent_name"
                      value={formData.cadet_parent_name || ''}
                      onChange={handleChange}
                      className="mt-1 rounded-sm"
                    />
                  ) : (
                    <p className="mt-1 font-medium">{profile?.cadet_parent_name || '-'}</p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-500">Parent Phone</Label>
                    {editMode ? (
                      <Input
                        name="cadet_parent_phone"
                        value={formData.cadet_parent_phone || ''}
                        onChange={handleChange}
                        className="mt-1 rounded-sm"
                      />
                    ) : (
                      <p className="mt-1 font-medium">{profile?.cadet_parent_phone || '-'}</p>
                    )}
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-500">Parent Email</Label>
                    {editMode ? (
                      <Input
                        name="cadet_parent_email"
                        type="email"
                        value={formData.cadet_parent_email || ''}
                        onChange={handleChange}
                        className="mt-1 rounded-sm"
                      />
                    ) : (
                      <p className="mt-1 font-medium">{profile?.cadet_parent_email || '-'}</p>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Approval Notice */}
      {!profile?.is_approved && (
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800">
            <p className="font-semibold">Account Pending Approval</p>
            <p className="mt-1">
              Your account is awaiting approval from an encampment commander. You can still update your profile information while waiting.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
