import React, { useState, useEffect, useRef } from 'react';
import { Lock, Unlock, Eye, EyeOff, ShieldCheck, AlertCircle, Sparkles, ArrowRight } from 'lucide-react';
import { login } from '../api/client';

interface AuthGateProps {
  onAuthenticated: () => void;
}

export const AuthGate: React.FC<AuthGateProps> = ({ onAuthenticated }) => {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setErrorMessage('Please enter your master password');
      triggerShake();
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    const res = await login(password);
    setIsLoading(false);

    if (res.success) {
      onAuthenticated();
    } else {
      setErrorMessage(res.error || 'Incorrect master password. Access denied.');
      triggerShake();
      if (inputRef.current) {
        inputRef.current.select();
      }
    }
  };

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 500);
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#040508] relative overflow-hidden px-4 select-none">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-winsor-700/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-amber-500/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-600/10 rounded-full blur-[180px] pointer-events-none" />

      {/* Luxury Auth Card */}
      <div
        className={`w-full max-w-md relative z-10 transition-transform duration-300 ${
          shake ? 'animate-shake' : ''
        }`}
      >
        <div className="p-8 sm:p-10 rounded-3xl bg-[#080b13]/90 backdrop-blur-2xl border border-white/[0.09] shadow-[0_0_50px_rgba(0,0,0,0.8)] relative overflow-hidden">
          {/* Subtle Top Accent Highlight Line */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-amber-400/60 to-transparent" />

          {/* Logo & Header */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="relative mb-5 group">
              <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 via-sky-500 to-amber-500 rounded-2xl blur-md opacity-40 group-hover:opacity-75 transition duration-500" />
              <img
                src="/Arth_IQ.png"
                alt="Arth IQ"
                className="relative w-20 h-20 rounded-2xl object-contain bg-black/80 border border-amber-500/40 shadow-2xl p-1.5"
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
                SECURE
              </span>
            </div>

            <p className="text-xs text-slate-400 mt-2 font-medium">
              Your Personal Investment Intelligence Engine
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
              Single-User Protected Access
            </p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2 tracking-wide flex items-center justify-between">
                <span>MASTER PASSWORD</span>
                <span className="text-[10px] text-slate-500 font-normal">Encrypted Session</span>
              </label>

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4 text-slate-400" />
                </div>
                <input
                  ref={inputRef}
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="Enter master password..."
                  disabled={isLoading}
                  className="w-full pl-10 pr-11 py-3 rounded-xl bg-[#0d111c] border border-white/[0.1] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400/70 focus:ring-2 focus:ring-amber-400/20 transition-all font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              {errorMessage && (
                <div className="flex items-center space-x-2 mt-2.5 px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs animate-fadeIn">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                  <span>{errorMessage}</span>
                </div>
              )}
            </div>

            {/* Unlock Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-sm shadow-[0_0_25px_rgba(245,158,11,0.35)] hover:shadow-[0_0_35px_rgba(245,158,11,0.5)] transition-all flex items-center justify-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed group cursor-pointer"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                  <span>Authenticating Engine...</span>
                </>
              ) : (
                <>
                  <Unlock className="w-4 h-4 text-slate-950" />
                  <span>Unlock Arth IQ Engine</span>
                  <ArrowRight className="w-4 h-4 text-slate-950 group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Institutional Trust Footer */}
          <div className="mt-8 pt-5 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <div className="flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Zero-Lookahead Engine</span>
            </div>
            <div className="flex items-center space-x-1 text-slate-400">
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Institutional Grade</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
