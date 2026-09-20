import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ShieldAlert, Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, user, hasRole } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-slate-100">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500 mb-3" />
        <p className="text-sm font-medium text-slate-300">Verifying air-gapped credentials...</p>
        <span className="text-xs text-slate-500 mt-1">OmniLogix Local RBAC</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && !hasRole(...allowedRoles)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mb-4">
          <ShieldAlert className="w-8 h-8 text-rose-600" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Access Denied (403 Forbidden)</h2>
        <p className="text-sm text-slate-600 max-w-md mb-4">
          Your current account (<span className="font-semibold text-slate-900">{user?.username}</span>) with role{' '}
          <span className="font-mono px-2 py-0.5 bg-slate-100 text-slate-800 rounded text-xs font-bold border border-slate-200">
            {user?.role}
          </span>{' '}
          lacks permission to access this module.
        </p>
        <p className="text-xs text-slate-500">Required Privilege: {allowedRoles.join(' or ')}</p>
      </div>
    );
  }

  return <>{children}</>;
};
