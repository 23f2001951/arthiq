import React, { useState, useEffect, useRef } from 'react';
import {
  Lock,
  Unlock,
  Eye,
  EyeOff,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Mail,
  UserCheck,
  KeyRound,
  ArrowLeft,
  CheckCircle2,
} from 'lucide-react';
import { lookupEmail, setPassword, loginWithEmail } from '../api/client';

interface AuthGateProps {
  onAuthenticated: () => void;
}

type AuthStep = 'EMAIL' | 'ENTER_PASSWORD' | 'CREATE_PASSWORD';


export const AuthGate: React.FC<AuthGateProps> = ({ onAuthenticated }) => {
  const [step, setStep] = useState<AuthStep>('EMAIL');
  const [email, setEmail] = useState('');
  const [userName, setUserName] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<string | null>(null);

  const [password, setPasswordState] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [shake, setShake] = useState(false);

  const emailInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (step === 'EMAIL' && emailInputRef.current) {
      emailInputRef.current.focus();
    } else if (passwordInputRef.current) {
      passwordInputRef.current.focus();
    }
  }, [step]);

  const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 500);
  };

  // Step 1: Look up email to determine flow
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      triggerShake();
      return;
    }
    if (!EMAIL_REGEX.test(cleanEmail)) {
      setErrorMessage('Please enter a valid email address (e.g. name@company.com).');
      triggerShake();
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await lookupEmail(cleanEmail);
      setIsLoading(false);

      if (!res.exists || res.status === 'NOT_FOUND') {
        setErrorMessage('This email address is not registered. Please contact your platform administrator for an invitation.');
        triggerShake();
        return;
      }

      if (res.status === 'SUSPENDED') {
        setErrorMessage('This account is suspended. Please contact platform administrator.');
        triggerShake();
        return;
      }

      setUserName(res.name || null);
      setUserRole(res.role || null);

      if (res.status === 'INVITED') {
        setStep('CREATE_PASSWORD');
      } else {
        setStep('ENTER_PASSWORD');
      }
    } catch (err: any) {
      setIsLoading(false);
      const msg = err?.message || 'Email lookup failed. Please check network connection.';
      setErrorMessage(msg);
      triggerShake();
    }
  };

  // Step 2A: First-time invited user sets password
  const handleCreatePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 4) {
      setErrorMessage('Password must be at least 4 characters long.');
      triggerShake();
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      triggerShake();
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await setPassword(email.trim().toLowerCase(), password);
      setIsLoading(false);
      onAuthenticated();
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err?.message || 'Failed to activate account. Try again.');
      triggerShake();
    }
  };

  // Step 2B: Active user enters password
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      setErrorMessage('Please enter your password.');
      triggerShake();
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    const res = await loginWithEmail(email.trim().toLowerCase(), password);
    setIsLoading(false);

    if (res.success) {
      onAuthenticated();
    } else {
      setErrorMessage(res.error || 'Authentication failed. Please check your password.');
      triggerShake();
      if (passwordInputRef.current) {
        passwordInputRef.current.select();
      }
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#040508] relative overflow-hidden px-4 select-none">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-amber-500/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-sky-600/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-600/10 rounded-full blur-[180px] pointer-events-none" />

      {/* Luxury Auth Card */}
      <div
        className={`w-full max-w-md relative z-10 transition-transform duration-300 ${
          shake ? 'animate-shake' : ''
        }`}
      >
        <div className="p-8 sm:p-10 rounded-3xl bg-[#080b13]/90 backdrop-blur-2xl border border-white/[0.09] shadow-[0_0_50px_rgba(0,0,0,0.8)] relative overflow-hidden">
          {/* Top Accent Highlight */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-amber-400/60 to-transparent" />

          {/* Logo & Header */}
          <div className="flex flex-col items-center text-center mb-6">
            <div className="relative mb-4 group">
              <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 via-sky-500 to-amber-500 rounded-2xl blur-md opacity-40 group-hover:opacity-75 transition duration-500" />
              <img
                src="/Arth_IQ.png"
                alt="Arth IQ"
                className="relative w-16 h-16 rounded-2xl object-contain bg-black/80 border border-amber-500/40 shadow-2xl p-1"
              />
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#080b13] border border-amber-500/40 flex items-center justify-center">
                <Lock className="w-3 h-3 text-amber-400" />
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-black tracking-tight text-white">
                ARTH <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-300 to-yellow-200">IQ</span>
              </h1>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/25">
                ENTERPRISE
              </span>
            </div>

            <p className="text-xs text-slate-400 mt-1.5 font-medium">
              Institutional Investment Intelligence Platform
            </p>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="flex items-center space-x-2 mb-5 px-3.5 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs animate-fadeIn">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* STEP 1: Email Input */}
          {step === 'EMAIL' && (
            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2 tracking-wide flex items-center justify-between">
                  <span>ENTER YOUR EMAIL</span>
                  <span className="text-[10px] text-slate-500">Pro Investor Onboarding</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4 text-slate-400" />
                  </div>
                  <input
                    ref={emailInputRef}
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Enter your Email"
                    disabled={isLoading}
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#0d111c] border border-white/[0.1] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400/70 focus:ring-2 focus:ring-amber-400/20 transition-all font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-sm shadow-[0_0_25px_rgba(245,158,11,0.35)] hover:shadow-[0_0_35px_rgba(245,158,11,0.5)] transition-all flex items-center justify-center space-x-2 disabled:opacity-60 cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                    <span>Verifying Account...</span>
                  </>
                ) : (
                  <>
                    <span>Continue</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* STEP 2A: Create Password for Invited User */}
          {step === 'CREATE_PASSWORD' && (
            <form onSubmit={handleCreatePasswordSubmit} className="space-y-4">
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center space-x-2.5 text-xs text-emerald-300">
                <UserCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <div>
                  <p className="font-semibold">Welcome {userName || 'Pro Investor'}!</p>
                  <p className="text-[11px] text-emerald-400/80">
                    Create your password to activate your account for <span className="font-mono text-white">{email}</span>.
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  NEW PASSWORD
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <KeyRound className="w-4 h-4 text-slate-400" />
                  </div>
                  <input
                    ref={passwordInputRef}
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => {
                      setPasswordState(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Create a secure password..."
                    disabled={isLoading}
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-[#0d111c] border border-white/[0.1] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400/70 focus:ring-2 focus:ring-amber-400/20 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  CONFIRM PASSWORD
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <CheckCircle2 className="w-4 h-4 text-slate-400" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Re-enter password..."
                    disabled={isLoading}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#0d111c] border border-white/[0.1] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400/70 focus:ring-2 focus:ring-amber-400/20 font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-400 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-sm shadow-[0_0_25px_rgba(16,185,129,0.35)] transition-all flex items-center justify-center space-x-2 cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                    <span>Activating Account...</span>
                  </>
                ) : (
                  <>
                    <Unlock className="w-4 h-4" />
                    <span>Activate Account & Enter</span>
                  </>
                )}
              </button>

              <div className="text-center pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setPasswordState('');
                    setConfirmPassword('');
                    setStep('EMAIL');
                  }}
                  className="text-xs text-slate-500 hover:text-slate-300 inline-flex items-center space-x-1 font-mono"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Use different email</span>
                </button>
              </div>
            </form>
          )}

          {/* STEP 2B: Enter Password for Existing Active User */}
          {step === 'ENTER_PASSWORD' && (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div className="p-3 rounded-xl bg-[#0d111c] border border-white/[0.08] flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-mono text-slate-300">{email}</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setPasswordState('');
                    setStep('EMAIL');
                  }}
                  className="text-[11px] text-amber-400/80 hover:text-amber-300 font-mono"
                >
                  Change
                </button>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center justify-between">
                  <span>ENTER PASSWORD</span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {userRole === 'admin' ? 'PLATFORM ADMIN' : 'PRO INVESTOR'}
                  </span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4 text-slate-400" />
                  </div>
                  <input
                    ref={passwordInputRef}
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => {
                      setPasswordState(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Enter your password..."
                    disabled={isLoading}
                    className="w-full pl-10 pr-10 py-3 rounded-xl bg-[#0d111c] border border-white/[0.1] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400/70 focus:ring-2 focus:ring-amber-400/20 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-sm shadow-[0_0_25px_rgba(245,158,11,0.35)] transition-all flex items-center justify-center space-x-2 cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                    <span>Signing In...</span>
                  </>
                ) : (
                  <>
                    <Unlock className="w-4 h-4" />
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Institutional Trust Footer */}
          <div className="mt-7 pt-4 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <div className="flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Zero-Lookahead RBAC</span>
            </div>
            <div className="flex items-center space-x-1 text-slate-400">
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Role-Enforced Security</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
