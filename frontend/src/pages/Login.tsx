import React, { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

const Login = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, verifyMFA, mfaPending } = useAuth();

    // Check if user just registered
    const justRegistered = location.state?.registered;

    const [email, setEmail] = useState(location.state?.email || '');
    const [password, setPassword] = useState('');
    const [otpCode, setOtpCode] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        const result = await login(email, password);

        setIsLoading(false);

        if (!result.success) {
            setError(result.error || 'Login failed');
            return;
        }

        if (!result.mfaRequired) {
            navigate('/dashboard');
        }
        // If MFA required, the mfaPending state will be set and we show OTP input
    };

    const handleMFAVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!mfaPending) return;

        setError('');
        setIsLoading(true);

        const result = await verifyMFA(mfaPending.mfa_token, otpCode);

        setIsLoading(false);

        if (!result.success) {
            setError(result.error || 'MFA verification failed');
            return;
        }

        navigate('/dashboard');
    };

    return (
        <div className="app-bg flex flex-col items-center justify-center">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className="relative z-10 w-full max-w-md px-8"
            >
                <div className="text-center mb-8">
                    <img
                        src="/PREVENT logo.png"
                        alt="PREVENT Logo"
                        className="w-20 h-auto mx-auto mb-4 opacity-90"
                    />
                    <h1 className="text-3xl font-light tracking-tight">
                        {mfaPending ? 'Verify Your Identity' : justRegistered ? 'Registration Complete!' : 'Welcome Back'}
                    </h1>
                    <p className="text-sm opacity-50 mt-2">
                        {mfaPending
                            ? `Enter the code sent to your ${mfaPending.mfa_method} to verify your email and log in`
                            : justRegistered
                                ? 'Sign in to complete verification'
                                : 'Sign in to continue your wellness journey'
                        }
                    </p>
                </div>

                <AnimatePresence mode="wait">
                    {justRegistered && !mfaPending && !error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg mb-4 text-sm"
                        >
                            ✓ Account created! Enter your password to receive a verification code.
                        </motion.div>
                    )}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-4 text-sm"
                        >
                            {error}
                        </motion.div>
                    )}
                </AnimatePresence>

                {!mfaPending ? (
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div>
                            <label className="block text-sm opacity-70 mb-1">Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="dawn-input w-full"
                                placeholder="you@example.com"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm opacity-70 mb-1">Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="dawn-input w-full"
                                placeholder="••••••••"
                                required
                            />
                        </div>

                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            type="submit"
                            disabled={isLoading}
                            className="dawn-button w-full mt-6"
                        >
                            {isLoading ? 'Signing in...' : 'Sign In'}
                        </motion.button>
                    </form>
                ) : (
                    <form onSubmit={handleMFAVerify} className="space-y-4">
                        <div>
                            <label className="block text-sm opacity-70 mb-1">Verification Code</label>
                            <input
                                type="text"
                                value={otpCode}
                                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                className="dawn-input w-full text-center text-2xl tracking-[0.5em]"
                                placeholder="000000"
                                maxLength={6}
                                required
                            />
                        </div>

                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            type="submit"
                            disabled={isLoading || otpCode.length !== 6}
                            className="dawn-button w-full mt-6"
                        >
                            {isLoading ? 'Verifying...' : 'Verify'}
                        </motion.button>
                    </form>
                )}

                <div className="mt-6 text-center text-sm opacity-50">
                    Don't have an account?{' '}
                    <Link to="/register" className="text-primary hover:underline">
                        Register
                    </Link>
                </div>
            </motion.div>
        </div>
    );
};

export default Login;
