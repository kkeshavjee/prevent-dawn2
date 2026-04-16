import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/client';

interface MFAStatus {
    mfa_enabled: boolean;
    mfa_method: string | null;
}

const Settings = () => {
    const navigate = useNavigate();
    const { user, logout, refreshUser } = useAuth();
    const [mfaStatus, setMfaStatus] = useState<MFAStatus | null>(null);
    const [isEnablingMFA, setIsEnablingMFA] = useState(false);
    const [mfaMethod, setMfaMethod] = useState<'email' | 'sms'>('email');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        loadMFAStatus();
    }, []);

    const loadMFAStatus = async () => {
        try {
            const status = await authApi.mfa.status();
            setMfaStatus(status);
        } catch (err) {
            console.error('Failed to load MFA status', err);
        }
    };

    const handleEnableMFA = async () => {
        setError('');
        setIsEnablingMFA(true);

        try {
            const result = await authApi.mfa.enable({ method: mfaMethod });
            setSuccess(result.message || 'MFA enabled! Please log in again.');
            await loadMFAStatus();
            await refreshUser();

            // Redirect to login since tokens were revoked
            setTimeout(() => {
                logout();
                navigate('/login');
            }, 2000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to enable MFA');
        }

        setIsEnablingMFA(false);
    };

    const handleDisableMFA = async () => {
        setError('');

        try {
            const result = await authApi.mfa.disable();
            setSuccess(result.message || 'MFA disabled');
            await loadMFAStatus();
            await refreshUser();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to disable MFA');
        }
    };

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <div className="p-6 max-w-2xl mx-auto">
            <h1 className="text-2xl font-light mb-8">Settings</h1>

            {/* Profile Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white/5 rounded-2xl p-6 mb-6"
            >
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    Profile
                </h2>

                {user && (
                    <div className="space-y-3 text-sm">
                        <div className="flex justify-between items-center">
                            <span className="opacity-60">Email</span>
                            <span>{user.email}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="opacity-60">Role</span>
                            <span className="capitalize">{user.role}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="opacity-60">Email Verified</span>
                            <span className={user.is_verified ? 'text-green-400' : 'text-yellow-400'}>
                                {user.is_verified ? '✓ Verified' : '⚠ Pending'}
                            </span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="opacity-60">Member Since</span>
                            <span>{new Date(user.created_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                )}
            </motion.div>

            {/* MFA Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white/5 rounded-2xl p-6 mb-6"
            >
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Two-Factor Authentication
                </h2>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg mb-4 text-sm">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-2 rounded-lg mb-4 text-sm">
                        {success}
                    </div>
                )}

                {mfaStatus?.mfa_enabled ? (
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <p className="text-green-400 font-medium">✓ MFA Enabled</p>
                                <p className="text-sm opacity-60">Method: {mfaStatus.mfa_method}</p>
                            </div>
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={handleDisableMFA}
                                className="px-4 py-2 text-sm rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30"
                            >
                                Disable MFA
                            </motion.button>
                        </div>
                    </div>
                ) : (
                    <div>
                        <p className="text-sm opacity-60 mb-4">
                            Add an extra layer of security to your account by enabling two-factor authentication.
                        </p>

                        <div className="mb-4">
                            <label className="block text-sm opacity-70 mb-2">Authentication Method</label>
                            <select
                                value={mfaMethod}
                                onChange={(e) => setMfaMethod(e.target.value as 'email' | 'sms')}
                                className="dawn-input w-full"
                            >
                                <option value="email">Email</option>
                                <option value="sms">SMS (requires phone number)</option>
                            </select>
                        </div>

                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={handleEnableMFA}
                            disabled={isEnablingMFA}
                            className="dawn-button"
                        >
                            {isEnablingMFA ? 'Enabling...' : 'Enable MFA'}
                        </motion.button>
                    </div>
                )}
            </motion.div>

            {/* Logout Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/5 rounded-2xl p-6"
            >
                <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    Session
                </h2>

                <p className="text-sm opacity-60 mb-4">
                    Sign out of your account on this device.
                </p>

                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleLogout}
                    className="px-6 py-2 text-sm rounded-lg bg-white/10 hover:bg-white/20 border border-white/10"
                >
                    Sign Out
                </motion.button>
            </motion.div>
        </div>
    );
};

export default Settings;
