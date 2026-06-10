import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { authApi } from '../api/client';

const ResetPassword = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState(location.state?.email || '');
    const [otpCode, setOtpCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (newPassword !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }
        if (newPassword.length < 8) {
            setError('Password must be at least 8 characters.');
            return;
        }
        setIsLoading(true);
        try {
            await authApi.resetPassword({ email, otp_code: otpCode, new_password: newPassword });
            navigate('/login', { state: { passwordReset: true } });
        } catch (error: any) {
            setError(error.response?.data?.detail || 'Reset failed. Please try again.');
        } finally {
            setIsLoading(false);
        }
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
                    <img src="/PREVENT logo.png" alt="PREVENT Logo" className="w-20 h-auto mx-auto mb-4 opacity-90" />
                    <h1 className="text-3xl font-light tracking-tight">Set New Password</h1>
                    <p className="text-sm opacity-50 mt-2">Enter the code from your email and choose a new password</p>
                </div>

                <AnimatePresence mode="wait">
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

                <form onSubmit={handleSubmit} className="space-y-4">
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
                        <label className="block text-sm opacity-70 mb-1">Reset Code</label>
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
                    <div>
                        <label className="block text-sm opacity-70 mb-1">New Password</label>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            className="dawn-input w-full"
                            placeholder="At least 8 characters"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm opacity-70 mb-1">Confirm New Password</label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="dawn-input w-full"
                            placeholder="Repeat your new password"
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
                        {isLoading ? 'Resetting...' : 'Reset Password'}
                    </motion.button>
                </form>

                <div className="mt-6 text-center text-sm opacity-50">
                    <Link to="/forgot-password" className="text-primary hover:underline">
                        Resend reset code
                    </Link>
                    {' · '}
                    <Link to="/login" className="text-primary hover:underline">
                        Back to login
                    </Link>
                </div>
            </motion.div>
        </div>
    );
};

export default ResetPassword;