import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { authApi } from '../api/client';

const ForgotPassword = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            await authApi.forgotPassword(email);
            setSubmitted(true);
        } catch (error: any) {
            setError(error.response?.data?.detail || 'Something went wrong. Please try again.');
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
                    <h1 className="text-3xl font-light tracking-tight">Reset Password</h1>
                    <p className="text-sm opacity-50 mt-2">
                        {submitted ? 'Check your email for a reset code' : "Enter your email and we'll send you a reset code"}
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
                </AnimatePresence>

                {!submitted ? (
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
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            type="submit"
                            disabled={isLoading}
                            className="dawn-button w-full mt-6"
                        >
                            {isLoading ? 'Sending...' : 'Send Reset Code'}
                        </motion.button>
                    </form>
                ) : (
                    <div className="space-y-4">
                        <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg text-sm text-center">
                            ✓ Reset code sent! Check your email inbox.
                        </div>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => navigate('/reset-password', { state: { email } })}
                            className="dawn-button w-full"
                        >
                            Enter Reset Code
                        </motion.button>
                    </div>
                )}

                <div className="mt-6 text-center text-sm opacity-50">
                    Remember your password?{' '}
                    <Link to="/login" className="text-primary hover:underline">
                        Sign in
                    </Link>
                </div>
            </motion.div>
        </div>
    );
};

export default ForgotPassword;