import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { Shield, Plane } from 'lucide-react';

const LoginPage = () => {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    capid: '',
    role: 'staff'  // Default to staff
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isLogin) {
        await login(formData.email, formData.password);
        toast.success('Welcome back!');
      } else {
        await register(formData);
        toast.success('Account created successfully!');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Hero image */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#00205B] relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#00205B] to-[#001540]"></div>
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `url('https://images.pexels.com/photos/32567920/pexels-photo-32567920.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')`,
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          }}
        ></div>
        <div className="relative z-10 flex flex-col justify-center items-center w-full p-12 text-white">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="w-12 h-12" />
            <Plane className="w-10 h-10" />
          </div>
          <h1 className="text-4xl font-black uppercase tracking-tight text-center mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Civil Air Patrol
          </h1>
          <h2 className="text-2xl font-bold uppercase tracking-wide text-center mb-2">
            Encampment Roster
          </h2>
          <p className="text-lg text-center text-slate-300 mt-4 max-w-md">
            Comprehensive management system for encampment operations, roster tracking, and financial oversight.
          </p>
          <div className="mt-12 flex items-center gap-2 text-sm text-slate-400">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
            <span>VOLUNTEERS SERVING AMERICA</span>
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <Shield className="w-10 h-10 text-[#00205B]" />
            <div>
              <h1 className="text-xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Civil Air Patrol
              </h1>
              <p className="text-xs text-slate-500 uppercase tracking-wide">Encampment Roster</p>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-sm p-8">
            <h2 className="text-2xl font-bold uppercase tracking-tight text-[#00205B] mb-6" style={{ fontFamily: 'Chivo, sans-serif' }}>
              {isLogin ? 'Sign In' : 'Create Account'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <>
                  <div>
                    <Label htmlFor="name" className="text-xs uppercase tracking-wide text-slate-600">Full Name</Label>
                    <Input
                      id="name"
                      name="name"
                      type="text"
                      value={formData.name}
                      onChange={handleChange}
                      required={!isLogin}
                      className="mt-1 rounded-sm"
                      placeholder="John Doe"
                      data-testid="register-name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="capid" className="text-xs uppercase tracking-wide text-slate-600">CAP ID (Optional)</Label>
                    <Input
                      id="capid"
                      name="capid"
                      type="text"
                      value={formData.capid}
                      onChange={handleChange}
                      className="mt-1 rounded-sm font-mono"
                      placeholder="123456"
                      data-testid="register-capid-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="role" className="text-xs uppercase tracking-wide text-slate-600">I am registering as</Label>
                    <Select
                      value={formData.role}
                      onValueChange={(value) => setFormData({ ...formData, role: value })}
                    >
                      <SelectTrigger className="mt-1 rounded-sm" data-testid="register-role-select">
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="staff">Staff / Senior Member</SelectItem>
                        <SelectItem value="cadre">Cadre</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-400 mt-1">Your role can be adjusted by encampment admin after approval</p>
                  </div>
                </>
              )}

              <div>
                <Label htmlFor="email" className="text-xs uppercase tracking-wide text-slate-600">Email Address</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="mt-1 rounded-sm"
                  placeholder="cadet@capunit.org"
                  data-testid="login-email-input"
                />
              </div>

              <div>
                <Label htmlFor="password" className="text-xs uppercase tracking-wide text-slate-600">Password</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="mt-1 rounded-sm"
                  placeholder="••••••••"
                  data-testid="login-password-input"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-[#00205B] hover:bg-[#001540] text-white font-bold uppercase tracking-wide rounded-sm py-5"
                data-testid="login-submit-btn"
              >
                {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Create Account')}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-sm text-[#00205B] hover:underline"
                data-testid="toggle-auth-mode"
              >
                {isLogin ? "Don't have an account? Register" : 'Already have an account? Sign In'}
              </button>
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-slate-400">
            Civil Air Patrol • United States Air Force Auxiliary
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
