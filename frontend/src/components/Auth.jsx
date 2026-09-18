import React, { useState } from 'react';
import { Mail, Lock, User, Loader2, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { authApi } from '../lib/api';
import logoIcon from '../assets/logo-icon.png';

/**
 * Turn a backend error payload into a human-readable string.
 * FastAPI/pydantic 422s return detail as a list of {msg, ...} objects.
 */
const formatServerError = (err) => {
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0]?.msg || 'Invalid input. Please check your details.';
  }
  return 'Something went wrong. Please try again.';
};

const Auth = ({ onAuthSuccess }) => {
  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isSignup = mode === 'signup';

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setError('');
  };

  // Mirrors the backend's pydantic validators so users get instant feedback
  const validate = () => {
    const emailTrim = email.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(emailTrim)) {
      return 'Enter a valid email address.';
    }
    if (isSignup) {
      const uname = username.trim();
      if (uname.length < 3 || uname.length > 30) {
        return 'Username must be 3-30 characters.';
      }
      if (!/^[a-zA-Z0-9_.-]+$/.test(uname)) {
        return 'Username can only contain letters, numbers, _ . -';
      }
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters.';
    }
    if (!/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
      return 'Password must contain at least one letter and one number.';
    }
    return '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;
    setError('');

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);
    try {
      const data = isSignup
        ? await authApi.register(email.trim(), username.trim(), password)
        : await authApi.login(email.trim(), password);
      onAuthSuccess(data.access_token, data.user);
    } catch (err) {
      setError(formatServerError(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-10 bg-gradient-to-br from-slate-50 via-primary-50/40 to-slate-100 animate-fade-in">

      {/* Brand */}
      <div className="flex flex-col items-center mb-8">
        <img
          src={logoIcon}
          alt="MedPak AI"
          className="w-20 h-20 mb-4 drop-shadow-md"
        />
        <h1 className="text-3xl font-extrabold text-navy tracking-tight">
          MedPak <span className="text-primary-600">AI</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1.5">
          Smart Medicine Information, Better Health <span className="font-urdu">— آپ کا طبی ساتھی</span>
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md glass-card rounded-3xl p-8 md:p-10 !translate-y-0">

        {/* Login / Signup tabs */}
        <div className="flex bg-slate-100 rounded-xl p-1 mb-7">
          <button
            type="button"
            onClick={() => switchMode('login')}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
              !isSignup ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => switchMode('signup')}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
              isSignup ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              autoComplete="email"
              className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl pl-12 pr-4 py-3.5 text-[15px] shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
              disabled={isLoading}
            />
          </div>

          {/* Username (signup only) */}
          {isSignup && (
            <div className="relative animate-fade-in">
              <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                autoComplete="username"
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl pl-12 pr-4 py-3.5 text-[15px] shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                disabled={isLoading}
              />
            </div>
          )}

          {/* Password */}
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl pl-12 pr-12 py-3.5 text-[15px] shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-600 rounded-lg transition-colors"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          {isSignup && (
            <p className="text-xs text-slate-400 leading-relaxed">
              Password must be at least 8 characters and include a letter and a number.
            </p>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 animate-fade-in">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-medical-600 to-primary-600 text-white font-semibold py-3.5 rounded-xl shadow-md shadow-medical-500/20 hover:shadow-lg hover:brightness-110 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {isSignup ? 'Creating account...' : 'Signing in...'}
              </>
            ) : (
              isSignup ? 'Create Account' : 'Sign In'
            )}
          </button>
        </form>
      </div>

      {/* Safety note */}
      <p className="mt-8 text-xs text-slate-400 flex items-center gap-1.5 max-w-md text-center leading-relaxed">
        <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
        MedPak AI provides medicine information only — it does not prescribe or diagnose. Always consult a licensed doctor or pharmacist.
      </p>
    </div>
  );
};

export default Auth;
