import React, { useState, useEffect } from 'react';
import {
  X,
  User,
  Lock,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Calendar,
  Clock,
  Sparkles,
  LogOut,
  Save,
} from 'lucide-react';
import { UserProfile } from '../types/api';
import {
  fetchCurrentUserProfile,
  changePassword,
  updateProfile,
  getUserEmail,
  getUserRole,
} from '../api/client';

interface ProfileSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogout?: () => void;
}

export const ProfileSettingsModal: React.FC<ProfileSettingsModalProps> = ({
  isOpen,
  onClose,
  onLogout,
}) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile');

  // Profile Edit State
  const [displayName, setDisplayName] = useState<string>('');
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [profileMsg, setProfileMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Password Update State
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showCurrent, setShowCurrent] = useState<boolean>(false);
  const [showNew, setShowNew] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);
  const [updatingPassword, setUpdatingPassword] = useState<boolean>(false);
  const [passwordMsg, setPasswordMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Load profile on modal open
  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setProfileMsg(null);
    setPasswordMsg(null);
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');

    fetchCurrentUserProfile()
      .then((data) => {
        setProfile(data);
        setDisplayName(data.name || '');
      })
      .catch(() => {
        // Fallback to local storage values
        setProfile({
          id: 1,
          email: getUserEmail() || 'user@arth.iq',
          name: '',
          role: getUserRole(),
          status: 'ACTIVE',
          created_at: null,
          last_login: null,
        });
      })
      .finally(() => setLoading(false));
  }, [isOpen]);

  if (!isOpen) return null;

  const role = profile?.role || getUserRole();
  const email = profile?.email || getUserEmail() || 'user@arth.iq';
  const initial = (profile?.name?.charAt(0) || email.charAt(0) || 'U').toUpperCase();

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setProfileMsg(null);
    try {
      const updated = await updateProfile({ name: displayName });
      setProfile(updated);
      setProfileMsg({ text: 'Profile display name updated successfully.', type: 'success' });
    } catch (err: any) {
      setProfileMsg({ text: err.message || 'Failed to update profile.', type: 'error' });
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);

    if (!currentPassword) {
      setPasswordMsg({ text: 'Please enter your current password.', type: 'error' });
      return;
    }
    if (newPassword.length < 4) {
      setPasswordMsg({ text: 'New password must be at least 4 characters.', type: 'error' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMsg({ text: 'New passwords do not match. Please re-enter.', type: 'error' });
      return;
    }

    setUpdatingPassword(true);
    try {
      const res = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMsg({
        text: res.message || 'Password successfully updated! Use your new password on next login.',
        type: 'success',
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordMsg({ text: err.message || 'Failed to update password.', type: 'error' });
    } finally {
      setUpdatingPassword(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      {/* Click outside to close */}
      <div className="fixed inset-0 -z-10" onClick={onClose} />

      <div className="relative w-full max-w-xl bg-[#090c15] border border-white/10 rounded-3xl shadow-2xl shadow-black/95 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Top Banner & Header */}
        <div className="relative p-6 bg-gradient-to-b from-[#111728] to-[#090c15] border-b border-white/[0.08]">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center space-x-4">
            <div
              className={`w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl shadow-lg border ${
                role === 'admin'
                  ? 'bg-gradient-to-tr from-amber-500 via-amber-400 to-yellow-200 text-slate-950 border-amber-400/40 shadow-amber-500/20'
                  : 'bg-gradient-to-tr from-sky-500 via-sky-400 to-blue-300 text-slate-950 border-sky-400/40 shadow-sky-500/20'
              }`}
            >
              {initial}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-white truncate">
                  {profile?.name || (role === 'admin' ? 'Platform Administrator' : 'Pro Investor')}
                </h2>
                <span
                  className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                    role === 'admin'
                      ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                      : 'bg-sky-500/15 text-sky-300 border-sky-500/30'
                  }`}
                >
                  {role === 'admin' ? 'PLATFORM ADMIN' : 'PRO INVESTOR'}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono truncate mt-0.5">{email}</p>
              <div className="flex items-center space-x-2 mt-1.5">
                <span className="flex items-center space-x-1 text-[10px] font-mono text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>Account Active</span>
                </span>
                <span className="text-slate-600 text-xs">•</span>
                <span className="text-[10px] font-mono text-slate-400">
                  PBKDF2-SHA256 Encrypted
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Sub-Tabs */}
          <div className="flex space-x-2 mt-6 bg-[#060810] p-1 rounded-2xl border border-white/[0.06]">
            <button
              onClick={() => setActiveTab('profile')}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'profile'
                  ? 'bg-winsor-700 text-white shadow-md border border-sky-400/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              <span>Profile Details</span>
            </button>
            <button
              onClick={() => setActiveTab('password')}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'password'
                  ? 'bg-winsor-700 text-white shadow-md border border-sky-400/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Update Password</span>
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {loading ? (
            <div className="py-12 text-center text-xs font-mono text-slate-400 animate-pulse">
              LOADING PROFILE INFORMATION...
            </div>
          ) : activeTab === 'profile' ? (
            /* TAB 1: Profile Details */
            <div className="space-y-6">
              {profileMsg && (
                <div
                  className={`p-3.5 rounded-2xl text-xs font-mono flex items-center space-x-2.5 border ${
                    profileMsg.type === 'success'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  }`}
                >
                  {profileMsg.type === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  )}
                  <span>{profileMsg.text}</span>
                </div>
              )}

              {/* Display Name Edit Form */}
              <form onSubmit={handleSaveProfile} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Display Name
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="e.g. Mandeep Sharma"
                      className="flex-1 px-3.5 py-2.5 rounded-xl bg-[#0e1220] border border-white/10 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-winsor-500"
                    />
                    <button
                      type="submit"
                      disabled={savingProfile}
                      className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl bg-gradient-to-r from-winsor-600 to-sky-500 hover:brightness-110 text-white text-xs font-bold transition-all disabled:opacity-50 cursor-pointer shadow-md"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>{savingProfile ? 'Saving...' : 'Save'}</span>
                    </button>
                  </div>
                </div>
              </form>

              {/* Read-Only Account Details Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="p-3.5 rounded-2xl bg-[#0e1220] border border-white/[0.06]">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Registered Email
                  </span>
                  <p className="text-xs font-mono font-semibold text-white truncate">{email}</p>
                  <span className="inline-flex items-center space-x-1 text-[9px] font-mono text-sky-400 mt-1">
                    <ShieldCheck className="w-2.5 h-2.5" />
                    <span>Verified Primary Identity</span>
                  </span>
                </div>

                <div className="p-3.5 rounded-2xl bg-[#0e1220] border border-white/[0.06]">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Access Clearance
                  </span>
                  <p className="text-xs font-semibold text-white">
                    {role === 'admin' ? 'Full Administrator Access' : 'Pro Institutional Tier'}
                  </p>
                  <span className="inline-flex items-center space-x-1 text-[9px] font-mono text-amber-400 mt-1">
                    <Sparkles className="w-2.5 h-2.5" />
                    <span>{role === 'admin' ? 'System Governance' : 'NSE 500 Factor Roster'}</span>
                  </span>
                </div>

                <div className="p-3.5 rounded-2xl bg-[#0e1220] border border-white/[0.06]">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Account Provisioned
                  </span>
                  <div className="flex items-center space-x-1.5 text-xs text-slate-300 font-mono">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>{profile?.created_at ? profile.created_at.slice(0, 10) : 'Active Master'}</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-[#0e1220] border border-white/[0.06]">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Last Authenticated
                  </span>
                  <div className="flex items-center space-x-1.5 text-xs text-slate-300 font-mono">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>{profile?.last_login ? profile.last_login.slice(0, 16) : 'Current Session'}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* TAB 2: Update Password */
            <form onSubmit={handlePasswordUpdate} className="space-y-4">
              {passwordMsg && (
                <div
                  className={`p-3.5 rounded-2xl text-xs font-mono flex items-center space-x-2.5 border ${
                    passwordMsg.type === 'success'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  }`}
                >
                  {passwordMsg.type === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  )}
                  <span>{passwordMsg.text}</span>
                </div>
              )}

              {/* Current Password Field */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrent ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-[#0e1220] border border-white/10 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-winsor-500 font-mono"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrent(!showCurrent)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* New Password Field */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNew ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 4 characters"
                    className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-[#0e1220] border border-white/10 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-winsor-500 font-mono"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew(!showNew)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm New Password Field */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-[#0e1220] border border-white/10 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-winsor-500 font-mono"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm(!showConfirm)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={updatingPassword}
                  className="w-full flex items-center justify-center space-x-2 py-3 rounded-xl bg-gradient-to-r from-winsor-600 to-sky-500 hover:brightness-110 text-white text-xs font-bold transition-all disabled:opacity-50 cursor-pointer shadow-lg shadow-winsor-900/30"
                >
                  <Lock className="w-4 h-4" />
                  <span>{updatingPassword ? 'Updating Password...' : 'Update Password'}</span>
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-[#060810] border-t border-white/[0.06] flex items-center justify-between">
          {onLogout ? (
            <button
              onClick={() => {
                onClose();
                onLogout();
              }}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 transition-all cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          ) : (
            <div />
          )}

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-white/[0.05] hover:bg-white/[0.1] border border-white/10 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
