import React, { useState, useEffect, useCallback } from 'react';
import { 
  getVapidKey, 
  subscribeToNotifications, 
  unsubscribeFromNotifications, 
  getNotificationStatus,
  sendNotification,
  getNotificationHistory
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Bell, 
  BellOff, 
  Send, 
  History, 
  Users,
  CheckCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react';
import { format, parseISO } from 'date-fns';

// Convert base64 to Uint8Array for VAPID key
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

const NotificationManager = ({ compact = false }) => {
  const { canEdit, user } = useAuth();
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(false);
  const [showSendDialog, setShowSendDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [notificationHistory, setNotificationHistory] = useState([]);
  const [sending, setSending] = useState(false);
  const [notSupported, setNotSupported] = useState(false);

  const [sendForm, setSendForm] = useState({
    title: '',
    body: '',
    targetGroups: ['all']
  });

  const targetGroupOptions = [
    { value: 'all', label: 'All Participants' },
    { value: 'staff', label: 'Staff/Cadre' },
    { value: '6th_cts', label: '6th CTS' },
    { value: '21st_cts', label: '21st CTS' },
    { value: '22nd_cts', label: '22nd CTS' },
    { value: 'alpha', label: 'Alpha Flight' },
    { value: 'bravo', label: 'Bravo Flight' },
    { value: 'charlie', label: 'Charlie Flight' },
    { value: 'delta', label: 'Delta Flight' },
    { value: 'echo', label: 'Echo Flight' },
    { value: 'foxtrot', label: 'Foxtrot Flight' }
  ];

  const checkSubscription = useCallback(async () => {
    // Check if notifications are supported
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      setNotSupported(true);
      setLoading(false);
      return;
    }

    try {
      const status = await getNotificationStatus();
      setIsSubscribed(status.subscribed);
    } catch (error) {
      console.error('Error checking subscription status:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSubscription();
  }, [checkSubscription]);

  const handleSubscribe = async () => {
    if (notSupported) {
      toast.error('Push notifications are not supported in this browser');
      return;
    }

    setSubscribing(true);
    try {
      // Request notification permission
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        toast.error('Notification permission denied');
        setSubscribing(false);
        return;
      }

      // Register service worker
      const registration = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;

      // Get VAPID key
      const { publicKey } = await getVapidKey();
      const applicationServerKey = urlBase64ToUint8Array(publicKey);

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey
      });

      // Send subscription to server
      const subscriptionData = subscription.toJSON();
      await subscribeToNotifications({
        endpoint: subscriptionData.endpoint,
        keys: subscriptionData.keys
      });

      setIsSubscribed(true);
      toast.success('Notifications enabled! You\'ll receive schedule updates.');
    } catch (error) {
      console.error('Error subscribing:', error);
      toast.error('Failed to enable notifications');
    } finally {
      setSubscribing(false);
    }
  };

  const handleUnsubscribe = async () => {
    setSubscribing(true);
    try {
      await unsubscribeFromNotifications();
      
      // Also unsubscribe from browser
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
      }

      setIsSubscribed(false);
      toast.success('Notifications disabled');
    } catch (error) {
      console.error('Error unsubscribing:', error);
      toast.error('Failed to disable notifications');
    } finally {
      setSubscribing(false);
    }
  };

  const handleTargetGroupToggle = (value) => {
    let newGroups = [...sendForm.targetGroups];
    
    if (value === 'all') {
      newGroups = ['all'];
    } else {
      newGroups = newGroups.filter(g => g !== 'all');
      
      if (newGroups.includes(value)) {
        newGroups = newGroups.filter(g => g !== value);
      } else {
        newGroups.push(value);
      }
      
      if (newGroups.length === 0) {
        newGroups = ['all'];
      }
    }
    
    setSendForm({ ...sendForm, targetGroups: newGroups });
  };

  const handleSendNotification = async (e) => {
    e.preventDefault();
    if (!sendForm.title || !sendForm.body) {
      toast.error('Please fill in title and message');
      return;
    }

    setSending(true);
    try {
      const result = await sendNotification(
        sendForm.title,
        sendForm.body,
        sendForm.targetGroups
      );
      toast.success(result.message);
      setShowSendDialog(false);
      setSendForm({ title: '', body: '', targetGroups: ['all'] });
    } catch (error) {
      toast.error('Failed to send notification');
    } finally {
      setSending(false);
    }
  };

  const loadHistory = async () => {
    try {
      const history = await getNotificationHistory();
      setNotificationHistory(history);
    } catch (error) {
      toast.error('Failed to load notification history');
    }
  };

  if (loading) {
    return null;
  }

  // Compact version for header
  if (compact) {
    return (
      <button
        onClick={isSubscribed ? handleUnsubscribe : handleSubscribe}
        disabled={subscribing || notSupported}
        className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
          isSubscribed 
            ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200' 
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        } ${(subscribing || notSupported) ? 'opacity-50 cursor-not-allowed' : ''}`}
        title={notSupported ? 'Notifications not supported' : (isSubscribed ? 'Disable notifications' : 'Enable notifications')}
        data-testid="notification-toggle"
      >
        {isSubscribed ? (
          <Bell className="w-3.5 h-3.5" />
        ) : (
          <BellOff className="w-3.5 h-3.5" />
        )}
      </button>
    );
  }

  // Full version for settings/admin page
  return (
    <div className="bg-white border border-slate-200 rounded-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-[#00205B]" />
          <h3 className="font-bold text-[#00205B] uppercase text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Push Notifications
          </h3>
        </div>
        
        {isSubscribed ? (
          <span className="flex items-center gap-1 text-xs text-emerald-600">
            <CheckCircle className="w-4 h-4" />
            Enabled
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <XCircle className="w-4 h-4" />
            Disabled
          </span>
        )}
      </div>

      {notSupported ? (
        <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Push notifications are not supported in this browser.</span>
        </div>
      ) : (
        <>
          <p className="text-sm text-slate-600 mb-4">
            {isSubscribed 
              ? 'You will receive notifications when the schedule is updated or important announcements are made.'
              : 'Enable notifications to stay updated on schedule changes and announcements.'}
          </p>

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={isSubscribed ? handleUnsubscribe : handleSubscribe}
              disabled={subscribing}
              variant={isSubscribed ? 'outline' : 'default'}
              className={isSubscribed ? 'border-red-200 text-red-600 hover:bg-red-50' : 'bg-[#00205B]'}
              data-testid="notification-toggle-btn"
            >
              {subscribing ? (
                'Processing...'
              ) : isSubscribed ? (
                <>
                  <BellOff className="w-4 h-4 mr-2" />
                  Disable Notifications
                </>
              ) : (
                <>
                  <Bell className="w-4 h-4 mr-2" />
                  Enable Notifications
                </>
              )}
            </Button>

            {canEdit() && (
              <>
                <Dialog open={showSendDialog} onOpenChange={setShowSendDialog}>
                  <DialogTrigger asChild>
                    <Button variant="outline" data-testid="send-notification-btn">
                      <Send className="w-4 h-4 mr-2" />
                      Send Notification
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-md">
                    <DialogHeader>
                      <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                        Send Notification
                      </DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleSendNotification} className="space-y-4 mt-4">
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Title</Label>
                        <Input
                          value={sendForm.title}
                          onChange={(e) => setSendForm({ ...sendForm, title: e.target.value })}
                          placeholder="Schedule Update"
                          required
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Message</Label>
                        <Textarea
                          value={sendForm.body}
                          onChange={(e) => setSendForm({ ...sendForm, body: e.target.value })}
                          placeholder="The schedule has been updated..."
                          required
                          className="mt-1"
                          rows={3}
                        />
                      </div>
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600 flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          Recipients
                        </Label>
                        <div className="mt-2 border border-slate-200 rounded p-3 bg-slate-50 max-h-40 overflow-y-auto">
                          <div className="space-y-2">
                            {targetGroupOptions.map(option => (
                              <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                                <Checkbox
                                  checked={sendForm.targetGroups.includes(option.value)}
                                  onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                  disabled={option.value !== 'all' && sendForm.targetGroups.includes('all')}
                                />
                                <span className="text-sm">{option.label}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="flex justify-end gap-2 pt-2">
                        <Button type="button" variant="outline" onClick={() => setShowSendDialog(false)}>
                          Cancel
                        </Button>
                        <Button type="submit" disabled={sending} className="bg-[#00205B]">
                          {sending ? 'Sending...' : 'Send'}
                        </Button>
                      </div>
                    </form>
                  </DialogContent>
                </Dialog>

                <Dialog open={showHistoryDialog} onOpenChange={(open) => {
                  setShowHistoryDialog(open);
                  if (open) loadHistory();
                }}>
                  <DialogTrigger asChild>
                    <Button variant="outline" data-testid="notification-history-btn">
                      <History className="w-4 h-4 mr-2" />
                      History
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                        Notification History
                      </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 mt-4">
                      {notificationHistory.length === 0 ? (
                        <p className="text-center text-slate-400 py-8">No notifications sent yet</p>
                      ) : (
                        notificationHistory.map((notification, idx) => (
                          <div key={idx} className="border border-slate-200 rounded p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-slate-900">{notification.title}</span>
                              <span className="text-xs text-slate-400">
                                {format(parseISO(notification.sent_at), 'MMM d, h:mm a')}
                              </span>
                            </div>
                            <p className="text-sm text-slate-600">{notification.body}</p>
                            <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
                              <span>Sent to: {notification.target_groups.join(', ')}</span>
                              <span>•</span>
                              <span>{notification.recipient_count} recipients</span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </DialogContent>
                </Dialog>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default NotificationManager;
