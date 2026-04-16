import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { authApi } from '../api/client';

const VerifyEmail = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email || 'your email';

    const [otpCode, setOtpCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [resendDisabled, setResendDisabled] = useState(false);

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            await authApi.verifyEmail(otpCode);
            setSuccess('Email verified successfully! Redirecting to login...');
            setTimeout(() => navigate('/login'), 2000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Verification failed');
        }

        setIsLoading(false);
    };

    const handleResend = async () => {
        setError('');
        setResendDisabled(true);

        try {
            await authApi.resendVerification();
            setSuccess('Verification code sent! Check your email.');
            setTimeout(() => setSuccess(''), 5000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to resend code');
        }

        // Enable resend after 60 seconds
        setTimeout(() => setResendDisabled(false), 60000);
    };

    return (
        <div className="app-bg flex flex-col items-center justify-center">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className="relative z-10 w-full max-w-md px-8 text-center"
            >
                <div className="mb-8">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-primary/20 flex items-center justify-center">
                        <svg className="w-10 h-10 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <h1 className="text-3xl font-light tracking-tight">Verify Your Email</h1>
                    <p className="text-sm opacity-50 mt-2">
                        We've sent a 6-digit code to<br />
                        <span className="text-primary">{email}</span>
                    </p>
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
                    {success && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg mb-4 text-sm"
                        >
                            {success}
                        </motion.div>
                    )}
                </AnimatePresence>

                <form onSubmit={handleVerify} className="space-y-4">
                    <div>
                        <input
                            type="text"
                            value={otpCode}
                            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            className="dawn-input w-full text-center text-3xl tracking-[0.5em] py-4"
                            placeholder="000000"
                            maxLength={6}
                            autoFocus
                            required
                        />
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        type="submit"
                        disabled={isLoading || otpCode.length !== 6}
                        className="dawn-button w-full"
                    >
                        {isLoading ? 'Verifying...' : 'Verify Email'}
                    </motion.button>
                </form>

                <div className="mt-6">
                    <button
                        onClick={handleResend}
                        disabled={resendDisabled}
                        className="text-sm text-primary hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {resendDisabled ? 'Code sent! Check your inbox' : "Didn't receive the code? Resend"}
                    </button>
                </div>

                <div className="mt-8 text-xs opacity-40">
                    Check your spam folder if you don't see the email
                </div>
            </motion.div>
        </div>
    );
};

export default VerifyEmail;
