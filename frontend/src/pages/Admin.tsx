import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

interface InviteCode {
    id: string;
    code: string;
    physician_email: string;
    physician_name: string | null;
    is_used: boolean;
    used_at: string | null;
    expires_at: string;
    is_active: boolean;
    created_at: string;
    email_sent: boolean;
}

export default function Admin() {
    const { user, token } = useAuth();
    const navigate = useNavigate();

    const [activeTab, setActiveTab] = useState<'invites' | 'users'>('invites');
    const [inviteCodes, setInviteCodes] = useState<InviteCode[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Create invite form
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [newInvite, setNewInvite] = useState({
        physician_email: '',
        physician_name: '',
        expires_in_days: 7
    });
    const [isCreating, setIsCreating] = useState(false);

    // Include used codes
    const [includeUsed, setIncludeUsed] = useState(false);

    // Check admin access
    useEffect(() => {
        if (user && user.role !== 'admin') {
            navigate('/dashboard');
        }
    }, [user, navigate]);

    // Fetch invite codes
    const fetchInviteCodes = async () => {
        if (!token) return;

        setIsLoading(true);
        setError('');

        try {
            const response = await fetch(`/auth/admin/invite-codes?include_used=${includeUsed}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch invite codes');
            }

            const data = await response.json();
            setInviteCodes(data.codes || []);
        } catch (err) {
            setError('Failed to load invite codes');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchInviteCodes();
    }, [token, includeUsed]);

    // Create new invite
    const handleCreateInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;

        setIsCreating(true);
        setError('');
        setSuccess('');

        try {
            const response = await fetch('/auth/admin/invite-codes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(newInvite)
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to create invite');
            }

            const data = await response.json();
            setSuccess(`Invite code ${data.code} created and sent to ${data.physician_email}`);
            setNewInvite({ physician_email: '', physician_name: '', expires_in_days: 7 });
            setShowCreateForm(false);
            fetchInviteCodes();
        } catch (err: any) {
            setError(err.message || 'Failed to create invite');
        } finally {
            setIsCreating(false);
        }
    };

    // Delete invite
    const handleDeleteInvite = async (id: string, code: string) => {
        if (!token) return;
        if (!confirm(`Delete invite code ${code}?`)) return;

        try {
            const response = await fetch(`/auth/admin/invite-codes/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete invite');
            }

            setSuccess('Invite code deleted');
            fetchInviteCodes();
        } catch (err) {
            setError('Failed to delete invite code');
        }
    };

    // Format date
    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Check if expired
    const isExpired = (dateStr: string) => {
        return new Date(dateStr) < new Date();
    };

    if (!user || user.role !== 'admin') {
        return (
            <div className="app-bg flex items-center justify-center">
                <p className="opacity-50">Access denied. Admin only.</p>
            </div>
        );
    }

    return (
        <div className="app-bg min-h-screen">
            <div className="max-w-6xl mx-auto px-4 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-light tracking-tight">Admin Dashboard</h1>
                    <p className="text-sm opacity-50 mt-1">Manage physicians and system settings</p>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6">
                    <button
                        onClick={() => setActiveTab('invites')}
                        className={`px-6 py-3 rounded-lg transition-all ${activeTab === 'invites'
                                ? 'bg-primary text-black font-medium'
                                : 'bg-white/5 hover:bg-white/10'
                            }`}
                    >
                        Physician Invites
                    </button>
                    <button
                        onClick={() => setActiveTab('users')}
                        className={`px-6 py-3 rounded-lg transition-all ${activeTab === 'users'
                                ? 'bg-primary text-black font-medium'
                                : 'bg-white/5 hover:bg-white/10'
                            }`}
                    >
                        Users
                    </button>
                </div>

                {/* Messages */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-4"
                        >
                            {error}
                        </motion.div>
                    )}
                    {success && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg mb-4"
                        >
                            ✓ {success}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Invites Tab */}
                {activeTab === 'invites' && (
                    <div>
                        {/* Actions Bar */}
                        <div className="flex justify-between items-center mb-6">
                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2 text-sm opacity-70">
                                    <input
                                        type="checkbox"
                                        checked={includeUsed}
                                        onChange={(e) => setIncludeUsed(e.target.checked)}
                                        className="dawn-checkbox"
                                    />
                                    Show used codes
                                </label>
                            </div>
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setShowCreateForm(true)}
                                className="dawn-button"
                            >
                                + New Invite
                            </motion.button>
                        </div>

                        {/* Create Form Modal */}
                        <AnimatePresence>
                            {showCreateForm && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
                                    onClick={() => setShowCreateForm(false)}
                                >
                                    <motion.div
                                        initial={{ scale: 0.9, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0.9, opacity: 0 }}
                                        className="bg-gray-900 border border-white/10 rounded-2xl p-6 w-full max-w-md"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        <h2 className="text-xl font-light mb-4">Invite New Physician</h2>
                                        <p className="text-sm opacity-50 mb-6">
                                            An invite code will be generated and emailed to the physician.
                                        </p>

                                        <form onSubmit={handleCreateInvite} className="space-y-4">
                                            <div>
                                                <label className="block text-sm opacity-70 mb-1">
                                                    Physician Email <span className="text-primary">*</span>
                                                </label>
                                                <input
                                                    type="email"
                                                    value={newInvite.physician_email}
                                                    onChange={(e) => setNewInvite(prev => ({
                                                        ...prev,
                                                        physician_email: e.target.value
                                                    }))}
                                                    className="dawn-input w-full"
                                                    placeholder="doctor@hospital.com"
                                                    required
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-sm opacity-70 mb-1">
                                                    Physician Name
                                                </label>
                                                <input
                                                    type="text"
                                                    value={newInvite.physician_name}
                                                    onChange={(e) => setNewInvite(prev => ({
                                                        ...prev,
                                                        physician_name: e.target.value
                                                    }))}
                                                    className="dawn-input w-full"
                                                    placeholder="Dr. John Smith"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-sm opacity-70 mb-1">
                                                    Expires In (days)
                                                </label>
                                                <select
                                                    value={newInvite.expires_in_days}
                                                    onChange={(e) => setNewInvite(prev => ({
                                                        ...prev,
                                                        expires_in_days: parseInt(e.target.value)
                                                    }))}
                                                    className="dawn-input w-full"
                                                >
                                                    <option value={1}>1 day</option>
                                                    <option value={3}>3 days</option>
                                                    <option value={7}>7 days</option>
                                                    <option value={14}>14 days</option>
                                                    <option value={30}>30 days</option>
                                                </select>
                                            </div>

                                            <div className="flex gap-3 mt-6">
                                                <button
                                                    type="button"
                                                    onClick={() => setShowCreateForm(false)}
                                                    className="flex-1 py-3 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                                                >
                                                    Cancel
                                                </button>
                                                <motion.button
                                                    whileHover={{ scale: 1.02 }}
                                                    whileTap={{ scale: 0.98 }}
                                                    type="submit"
                                                    disabled={isCreating}
                                                    className="dawn-button flex-1"
                                                >
                                                    {isCreating ? 'Sending...' : 'Send Invite'}
                                                </motion.button>
                                            </div>
                                        </form>
                                    </motion.div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Invite Codes Table */}
                        {isLoading ? (
                            <div className="text-center py-12 opacity-50">Loading...</div>
                        ) : inviteCodes.length === 0 ? (
                            <div className="text-center py-12 opacity-50">
                                No invite codes found. Create one to invite a physician.
                            </div>
                        ) : (
                            <div className="bg-white/5 rounded-xl overflow-hidden">
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b border-white/10">
                                            <th className="text-left px-4 py-3 text-sm opacity-50 font-normal">Code</th>
                                            <th className="text-left px-4 py-3 text-sm opacity-50 font-normal">Physician</th>
                                            <th className="text-left px-4 py-3 text-sm opacity-50 font-normal">Email</th>
                                            <th className="text-left px-4 py-3 text-sm opacity-50 font-normal">Status</th>
                                            <th className="text-left px-4 py-3 text-sm opacity-50 font-normal">Expires</th>
                                            <th className="text-right px-4 py-3 text-sm opacity-50 font-normal">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {inviteCodes.map((invite) => (
                                            <tr key={invite.id} className="border-b border-white/5 hover:bg-white/5">
                                                <td className="px-4 py-3">
                                                    <code className="bg-primary/20 text-primary px-2 py-1 rounded font-mono text-sm">
                                                        {invite.code}
                                                    </code>
                                                </td>
                                                <td className="px-4 py-3">
                                                    {invite.physician_name || <span className="opacity-30">—</span>}
                                                </td>
                                                <td className="px-4 py-3 text-sm opacity-70">
                                                    {invite.physician_email}
                                                    {invite.email_sent && (
                                                        <span className="ml-2 text-xs text-green-400">✓ sent</span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {invite.is_used ? (
                                                        <span className="px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs">
                                                            Used
                                                        </span>
                                                    ) : isExpired(invite.expires_at) ? (
                                                        <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs">
                                                            Expired
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs">
                                                            Active
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3 text-sm opacity-50">
                                                    {formatDate(invite.expires_at)}
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    {!invite.is_used && (
                                                        <button
                                                            onClick={() => handleDeleteInvite(invite.id, invite.code)}
                                                            className="text-red-400 hover:text-red-300 text-sm"
                                                        >
                                                            Delete
                                                        </button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* Users Tab */}
                {activeTab === 'users' && (
                    <div className="text-center py-12 opacity-50">
                        User management coming soon...
                    </div>
                )}
            </div>
        </div>
    );
}
