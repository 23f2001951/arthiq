import React, { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  Mail,
  User,
  ShieldCheck,
  RotateCw,
  Search,
  CheckCircle2,
  Clock,
  Ban,
  Trash2,
  X,
  AlertCircle,
} from 'lucide-react';
import {
  fetchAdminUsers,
  registerAdminUser,
  updateAdminUserStatus,
  deleteAdminUser,
  getUserEmail,
} from '../api/client';
import { UserProfile } from '../types/api';

export const UserManagementView: React.FC = () => {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Invite Modal State
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState<'user' | 'admin'>('user');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const currentAdminEmail = getUserEmail() || 'admin@arth.iq';

  const loadUsers = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchAdminUsers();
      setUsers(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load users');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = inviteEmail.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setModalError('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    setModalError(null);

    try {
      await registerAdminUser({
        email: cleanEmail,
        name: inviteName.trim() || undefined,
        role: inviteRole,
        user_type: inviteRole === 'admin' ? 'ADMIN' : 'PRO_INVESTOR',
      });

      setIsSubmitting(false);
      setIsInviteModalOpen(false);
      setInviteEmail('');
      setInviteName('');
      setInviteRole('user');
      setSuccessMessage(`Successfully invited ${cleanEmail}. The user can now create their password on first login.`);
      setTimeout(() => setSuccessMessage(null), 6000);
      loadUsers();
    } catch (err: any) {
      setIsSubmitting(false);
      setModalError(err.message || 'Failed to register investor');
    }
  };

  const handleToggleStatus = async (user: UserProfile) => {
    if (user.email === currentAdminEmail) {
      setErrorMessage('Cannot suspend your own active administrator account.');
      return;
    }

    const nextStatus = user.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    try {
      await updateAdminUserStatus(user.id, nextStatus);
      setSuccessMessage(`User ${user.email} marked as ${nextStatus}.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      loadUsers();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update user status');
    }
  };

  const handleDeleteUser = async (user: UserProfile) => {
    if (user.email === currentAdminEmail) {
      setErrorMessage('Cannot delete your own active administrator account.');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete ${user.email}? This action cannot be undone.`)) {
      return;
    }

    try {
      await deleteAdminUser(user.id);
      setSuccessMessage(`User ${user.email} has been deleted.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      loadUsers();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete user');
    }
  };

  const filteredUsers = users.filter((u) => {
    const term = searchTerm.toLowerCase();
    return (
      u.email.toLowerCase().includes(term) ||
      (u.name && u.name.toLowerCase().includes(term)) ||
      u.status.toLowerCase().includes(term) ||
      u.role.toLowerCase().includes(term) ||
      (u.user_type && u.user_type.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Banner */}
      <div className="p-6 rounded-3xl bg-[#080c18] border border-white/[0.08] relative overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs text-amber-400 font-mono mb-1">
            <Users className="w-4 h-4" />
            <span>PLATFORM USER GOVERNANCE</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Pro Investor Management
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl">
            Invite institutional pro investors by their email. Users will create their password upon their initial login attempt.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadUsers}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white transition-all cursor-pointer"
            title="Refresh user roster"
          >
            <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setIsInviteModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-xs flex items-center space-x-2 shadow-[0_0_20px_rgba(245,158,11,0.25)] transition-all cursor-pointer"
          >
            <UserPlus className="w-4 h-4 text-slate-950" />
            <span>Register New User</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Search & Stats Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
            <Search className="w-4 h-4 text-slate-400" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search email, name, role..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-[#080c18] border border-white/[0.08] text-white text-xs placeholder-slate-500 focus:outline-none focus:border-amber-400/60 font-mono"
          />
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>{users.filter((u) => u.status === 'ACTIVE').length} Active</span>
          </span>
          <span>•</span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>{users.filter((u) => u.status === 'INVITED').length} Invited</span>
          </span>
          <span>•</span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-400" />
            <span>{users.filter((u) => u.status === 'SUSPENDED').length} Suspended</span>
          </span>
        </div>
      </div>

      {/* Users Table */}
      <div className="rounded-3xl bg-[#080c18] border border-white/[0.08] overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/[0.02] border-b border-white/[0.06] text-slate-400 font-mono text-[11px] uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-6">User / Email</th>
                <th className="py-3.5 px-6">User Type / Role</th>
                <th className="py-3.5 px-6">Status</th>
                <th className="py-3.5 px-6">Registered</th>
                <th className="py-3.5 px-6">Last Login</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 font-mono text-xs">
                    {isLoading ? 'Loading users...' : 'No users match your search query.'}
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-white/[0.02] transition-colors">
                    {/* User / Email */}
                    <td className="py-4 px-6">
                      <div className="font-bold text-white text-sm">{user.name || 'Unnamed Investor'}</div>
                      <div className="font-mono text-slate-400 text-xs mt-0.5 flex items-center space-x-1.5">
                        <Mail className="w-3 h-3 text-slate-500" />
                        <span>{user.email}</span>
                      </div>
                    </td>

                    {/* User Type / Role */}
                    <td className="py-4 px-6">
                      {(user.user_type === 'ADMIN' || user.role === 'admin') ? (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/25 flex items-center space-x-1 w-max">
                          <ShieldCheck className="w-3 h-3 text-amber-400" />
                          <span>ADMIN</span>
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-sky-500/15 text-sky-300 border border-sky-500/25 flex items-center space-x-1 w-max">
                          <User className="w-3 h-3 text-sky-400" />
                          <span>PRO INVESTOR</span>
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="py-4 px-6">
                      {user.status === 'ACTIVE' ? (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 flex items-center space-x-1 w-max">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>ACTIVE</span>
                        </span>
                      ) : user.status === 'INVITED' ? (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/25 flex items-center space-x-1 w-max">
                          <Clock className="w-3 h-3 text-amber-400" />
                          <span>AWAITING PASSWORD</span>
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/25 flex items-center space-x-1 w-max">
                          <Ban className="w-3 h-3 text-rose-400" />
                          <span>SUSPENDED</span>
                        </span>
                      )}
                    </td>

                    {/* Registered Date */}
                    <td className="py-4 px-6 font-mono text-slate-400 text-xs">
                      {user.created_at ? user.created_at.slice(0, 10) : '—'}
                    </td>

                    {/* Last Login Date */}
                    <td className="py-4 px-6 font-mono text-slate-400 text-xs">
                      {user.last_login ? user.last_login : 'Never'}
                    </td>

                    {/* Actions */}
                    <td className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        {user.email !== currentAdminEmail && (
                          <>
                            <button
                              onClick={() => handleToggleStatus(user)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-mono border transition-all cursor-pointer ${
                                user.status === 'ACTIVE'
                                  ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border-rose-500/30'
                                  : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                              }`}
                              title={user.status === 'ACTIVE' ? 'Suspend account' : 'Activate account'}
                            >
                              {user.status === 'ACTIVE' ? 'Suspend' : 'Activate'}
                            </button>

                            <button
                              onClick={() => handleDeleteUser(user)}
                              className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-white/[0.06] transition-all cursor-pointer"
                              title="Delete user"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal Dialog */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="w-full max-w-md rounded-3xl bg-[#080c18] border border-white/[0.1] shadow-2xl p-6 sm:p-8 relative">
            <button
              onClick={() => setIsInviteModalOpen(false)}
              className="absolute top-5 right-5 p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center space-x-2.5 mb-2">
              <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <UserPlus className="w-4 h-4" />
              </div>
              <h2 className="text-xl font-bold text-white">Register Pro Investor</h2>
            </div>
            <p className="text-xs text-slate-400 mb-6">
              Enter the investor's institutional email address. An invitation record will be created, and the user will create their password upon their first login.
            </p>

            {modalError && (
              <div className="p-3 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleInviteUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  EMAIL ADDRESS <span className="text-amber-400">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4 text-slate-400" />
                  </div>
                  <input
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="e.g. rajiv@alphafund.com"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#0d1222] border border-white/[0.1] text-white text-xs focus:outline-none focus:border-amber-400/70 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  FULL NAME (OPTIONAL)
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <User className="w-4 h-4 text-slate-400" />
                  </div>
                  <input
                    type="text"
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    placeholder="e.g. Rajiv Sharma"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#0d1222] border border-white/[0.1] text-white text-xs focus:outline-none focus:border-amber-400/70"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  ACCESS ROLE
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'user' | 'admin')}
                  className="w-full px-3 py-2.5 rounded-xl bg-[#0d1222] border border-white/[0.1] text-white text-xs focus:outline-none focus:border-amber-400/70 font-mono"
                >
                  <option value="user">Pro Investor (Executive Dashboard, Alpha Picks, Portfolio)</option>
                  <option value="admin">Platform Admin (Governance, Training, Backtests)</option>
                </select>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-xs flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-lg shadow-amber-500/20"
                >
                  {isSubmitting ? (
                    <span>Registering Investor...</span>
                  ) : (
                    <>
                      <UserPlus className="w-4 h-4 text-slate-950" />
                      <span>Send Onboarding Invitation</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
