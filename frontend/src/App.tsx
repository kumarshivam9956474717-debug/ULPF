import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Ingestion } from './pages/Ingestion';
import { Events } from './pages/Events';
import { Parsers } from './pages/Parsers';
import { Onboarding } from './pages/Onboarding';
import { ParserProfiles } from './pages/ParserProfiles';
import { Analytics } from './pages/Analytics';
import { SecurityAnalytics } from './pages/SecurityAnalytics';
import { SupervisoryAssessment } from './pages/SupervisoryAssessment';
import { EvaluationWorkspace } from './pages/EvaluationWorkspace';
import { Sources } from './pages/Sources';
import { SystemSettings } from './pages/Settings';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="demo" element={<EvaluationWorkspace />} />
            <Route path="supervisory" element={<SupervisoryAssessment />} />
            <Route path="security-analytics" element={<SecurityAnalytics />} />
            <Route path="ingestion" element={<Ingestion />} />
            <Route path="onboarding" element={<Onboarding />} />
            <Route path="profiles" element={<ParserProfiles />} />
            <Route path="events" element={<Events />} />
            <Route path="parsers" element={<Parsers />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="sources" element={<Sources />} />
            <Route path="settings" element={<SystemSettings />} />
          </Route>
          {/* Direct any legacy /login link or unknown routes straight to Dashboard */}
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
