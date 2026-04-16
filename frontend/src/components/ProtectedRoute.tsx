import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
    children: React.ReactNode;
    requireVerified?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requireVerified = false }) => {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();

    // Show loading while checking auth
    if (isLoading) {
        return (
            <div className="app-bg flex items-center justify-center">
                <div className="text-center">
                    <div className="w-12 h-12 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto mb-4" />
                    <p className="text-sm opacity-50">Loading...</p>
                </div>
            </div>
        );
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Optionally require email verification
    if (requireVerified && user && !user.is_verified) {
        return <Navigate to="/verify-email" state={{ email: user.email }} replace />;
    }

    return <>{children}</>;
};

export default ProtectedRoute;
