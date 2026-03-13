import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Mail, Shield, ArrowLeft, CheckCircle } from 'lucide-react';

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [capid, setCapid] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!email || !capid) {
      toast.error('Please enter both email and CAPID');
      return;
    }

    setLoading(true);
    try {
      const result = await forgotPassword(email, capid);
      setSubmitted(true);
      toast.success('If the information matches, you will receive a reset email.');
      
      // For testing when SendGrid is not configured
      if (result.debug_token) {
        console.log('Debug reset token:', result.debug_token);
        toast.info('Email service not configured. Check console for debug token.', { duration: 10000 });
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process request');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-sm border border-slate-200 p-8 text-center">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-emerald-600" />
            </div>
            <h2 className="text-xl font-bold text-[#00205B] mb-2">Check Your Email</h2>
            <p className="text-slate-600 mb-6">
              If an account exists with that email and the CAPID matches, we've sent you a password reset link.
            </p>
            <p className="text-sm text-slate-500 mb-6">
              The link will expire in 1 hour.
            </p>
            <Link to="/login">
              <Button className="w-full bg-[#00205B] hover:bg-[#001540]">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Login
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Shield className="w-10 h-10 text-[#00205B]" />
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Reset Password
          </h1>
          <p className="text-slate-500 mt-2">
            Enter your email and CAPID to verify your identity
          </p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-sm border border-slate-200 p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Email Address</Label>
              <div className="relative mt-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  className="pl-10 rounded-sm"
                  required
                  data-testid="forgot-email-input"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">CAPID (Security Verification)</Label>
              <Input
                type="text"
                value={capid}
                onChange={(e) => setCapid(e.target.value)}
                placeholder="Enter your CAPID"
                className="mt-1 rounded-sm"
                required
                data-testid="forgot-capid-input"
              />
              <p className="text-xs text-slate-400 mt-1">
                Your 6-digit CAP ID number for identity verification
              </p>
            </div>

            <Button 
              type="submit" 
              className="w-full bg-[#00205B] hover:bg-[#001540] rounded-sm"
              disabled={loading}
              data-testid="forgot-submit-btn"
            >
              {loading ? 'Processing...' : 'Send Reset Link'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <Link 
              to="/login" 
              className="text-sm text-[#00205B] hover:underline flex items-center justify-center gap-1"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Login
            </Link>
          </div>
        </div>

        {/* Help Text */}
        <p className="text-center text-xs text-slate-400 mt-4">
          Don't know your CAPID? Contact your unit commander for assistance.
        </p>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
