import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

const Register = () => {
    const navigate = useNavigate();
    const { register } = useAuth();

    const [formData, setFormData] = useState({
        email: '',
        password: '',
        confirmPassword: '',
        role: 'patient' as 'patient' | 'physician',
        mfa_method: 'email' as 'email' | 'sms',
        phone_number: '',
        physician_invite_code: '',
        consent_data_collection: false,
        consent_data_sharing: false,
    });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value, type } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validation
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (formData.password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }

        if (!formData.consent_data_collection) {
            setError('You must consent to data collection to register');
            return;
        }

        // Validate phone for SMS MFA
        if (formData.mfa_method === 'sms' && !formData.phone_number) {
            setError('Phone number is required for SMS verification');
            return;
        }

        // Validate invite code for physicians
        if (formData.role === 'physician' && !formData.physician_invite_code) {
            setError('Physician invite code is required');
            return;
        }

        setIsLoading(true);

        const result = await register({
            email: formData.email,
            password: formData.password,
            role: formData.role,
            mfa_method: formData.mfa_method,
            phone_number: formData.phone_number || undefined,
            physician_invite_code: formData.role === 'physician' ? formData.physician_invite_code : undefined,
            consent_data_collection: formData.consent_data_collection,
            consent_data_sharing: formData.consent_data_sharing,
        });

        setIsLoading(false);

        if (!result.success) {
            setError(result.error || 'Registration failed');
            return;
        }

        // Redirect to login - MFA will verify email on first login
        navigate('/login', { state: { registered: true, email: formData.email } });
    };

    return (
        <div className="app-bg flex flex-col items-center justify-center py-8 overflow-y-auto">
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
                    <h1 className="text-3xl font-light tracking-tight">Create Account</h1>
                    <p className="text-sm opacity-50 mt-2">
                        Join PREVENT Dawn to start your wellness journey
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

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm opacity-70 mb-1">Email</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="dawn-input w-full"
                            placeholder="you@example.com"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm opacity-70 mb-1">Password</label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            className="dawn-input w-full"
                            placeholder="••••••••"
                            minLength={8}
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm opacity-70 mb-1">Confirm Password</label>
                        <input
                            type="password"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            className="dawn-input w-full"
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm opacity-70 mb-1">I am a</label>
                        <select
                            name="role"
                            value={formData.role}
                            onChange={handleChange}
                            className="dawn-input w-full"
                        >
                            <option value="patient">Patient</option>
                            <option value="physician">Physician</option>
                        </select>
                    </div>

                    {formData.role === 'physician' && (
                        <div>
                            <label className="block text-sm opacity-70 mb-1">
                                Physician Invite Code <span className="text-primary">*</span>
                            </label>
                            <input
                                type="text"
                                name="physician_invite_code"
                                value={formData.physician_invite_code}
                                onChange={(e) => setFormData(prev => ({
                                    ...prev,
                                    physician_invite_code: e.target.value.toUpperCase()
                                }))}
                                className="dawn-input w-full font-mono tracking-wider"
                                placeholder="ABCD1234"
                                required
                            />
                            <p className="text-xs opacity-40 mt-1">Contact your administrator for an invite code</p>
                        </div>
                    )}

                    <div>
                        <label className="block text-sm opacity-70 mb-1">Verification Method</label>
                        <select
                            name="mfa_method"
                            value={formData.mfa_method}
                            onChange={handleChange}
                            className="dawn-input w-full"
                        >
                            <option value="email">Email</option>
                            <option value="sms">SMS (Text Message)</option>
                        </select>
                        <p className="text-xs opacity-40 mt-1">How you'll receive login verification codes</p>
                    </div>

                    {formData.mfa_method === 'sms' && (
                        <div>
                            <label className="block text-sm opacity-70 mb-1">
                                Phone Number <span className="text-primary">*</span>
                            </label>
                            <input
                                type="tel"
                                name="phone_number"
                                value={formData.phone_number}
                                onChange={handleChange}
                                className="dawn-input w-full"
                                placeholder="+1234567890"
                                required
                            />
                        </div>
                    )}

                    <div className="border-t border-white/10 pt-4 mt-4">
                        <p className="text-sm opacity-70 mb-3">Privacy & Consent</p>

                        <label className="flex items-start gap-3 cursor-pointer mb-3">
                            <input
                                type="checkbox"
                                name="consent_data_collection"
                                checked={formData.consent_data_collection}
                                onChange={handleChange}
                                className="mt-1 dawn-checkbox"
                            />
                            <span className="text-sm opacity-80">
                                <strong className="text-primary">Required:</strong> I consent to the collection and processing of my health data for diabetes prevention purposes.
                            </span>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                name="consent_data_sharing"
                                checked={formData.consent_data_sharing}
                                onChange={handleChange}
                                className="mt-1 dawn-checkbox"
                            />
                            <span className="text-sm opacity-80">
                                I consent to sharing my data with my assigned healthcare provider.
                            </span>
                        </label>
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        type="submit"
                        disabled={isLoading || !formData.consent_data_collection}
                        className="dawn-button w-full mt-6"
                    >
                        {isLoading ? 'Creating Account...' : 'Create Account'}
                    </motion.button>
                </form>

                <div className="mt-6 text-center text-sm opacity-50">
                    Already have an account?{' '}
                    <Link to="/login" className="text-primary hover:underline">
                        Sign In
                    </Link>
                </div>
            </motion.div>
        </div>
    );
};

export default Register;
