import React, { useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TopBar } from './components/TopBar';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { WizardPage } from './pages/WizardPage';
import { HistoryPage } from './pages/HistoryPage';
import { TokenGuidePage } from './pages/TokenGuidePage';

const AppContent: React.FC = () => {
  const { user, loading } = useAuth();
  const { t } = useLanguage();
  const [currentPage, setCurrentPage] = useState<string>('landing');
  const [editingReportId, setEditingReportId] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center dark:bg-[#0c0f17] bg-[#f8fafc] text-indigo-500 text-xs font-mono">
        {t.app_name}...
      </div>
    );
  }

  // Automatic routing if user logs in while on landing
  const activePage = user && currentPage === 'landing' ? 'dashboard' : currentPage;

  return (
    <div className="min-h-screen dark:bg-[#0c0f17] bg-[#f8fafc] dark:text-slate-100 text-slate-800 flex flex-col font-mono selection:bg-indigo-600 selection:text-white transition-colors duration-150">
      <TopBar onNavigate={(page) => setCurrentPage(page)} currentPage={activePage} />

      <main className="flex-1">
        {activePage === 'landing' && (
          <LandingPage
            onGetStarted={() => setCurrentPage(user ? 'dashboard' : 'register')}
            onLogin={() => setCurrentPage('login')}
          />
        )}

        {activePage === 'login' && (
          <LoginPage
            onSuccess={() => setCurrentPage('dashboard')}
            onNavigateRegister={() => setCurrentPage('register')}
          />
        )}

        {activePage === 'register' && (
          <RegisterPage
            onSuccess={() => setCurrentPage('dashboard')}
            onNavigateLogin={() => setCurrentPage('login')}
          />
        )}

        {activePage === 'dashboard' && (
          <DashboardPage
            onCreateReport={() => {
              setEditingReportId(null);
              setCurrentPage('wizard');
            }}
            onEditReport={(id) => {
              setEditingReportId(id);
              setCurrentPage('wizard');
            }}
            onViewHistory={() => setCurrentPage('history')}
          />
        )}

        {activePage === 'wizard' && (
          <WizardPage
            onFinish={() => setCurrentPage('dashboard')}
            onNavigateToTokenGuide={() => setCurrentPage('token-guide')}
            editingReportId={editingReportId}
          />
        )}

        {activePage === 'history' && (
          <HistoryPage onBack={() => setCurrentPage('dashboard')} />
        )}

        {activePage === 'token-guide' && (
          <TokenGuidePage onBack={() => setCurrentPage(user ? 'dashboard' : 'landing')} />
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
