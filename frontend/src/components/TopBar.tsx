import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { Sun, Moon, Globe, LogOut, Trash2, Clock, Activity, ChevronDown, User as UserIcon } from 'lucide-react';
import { Language } from '../types';

interface TopBarProps {
  onNavigate: (page: string) => void;
  currentPage: string;
}

export const TopBar: React.FC<TopBarProps> = ({ onNavigate, currentPage }) => {
  const { theme, toggleTheme } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const { user, logout, deleteAccount } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [langMenuOpen, setLangMenuOpen] = useState(false);

  const languages: { code: Language; label: string; flag: string }[] = [
    { code: 'ru', label: 'Русский', flag: '🇷🇺' },
    { code: 'uz', label: 'O\'zbekcha', flag: '🇺🇿' },
    { code: 'en', label: 'English', flag: '🇬🇧' },
  ];

  const currentLangObj = languages.find(l => l.code === language) || languages[0];

  const [deleteAccountModalOpen, setDeleteAccountModalOpen] = useState(false);
  const [deleteAccountLoading, setDeleteAccountLoading] = useState(false);

  const confirmDeleteAccount = async () => {
    setDeleteAccountLoading(true);
    try {
      await deleteAccount();
      setDeleteAccountModalOpen(false);
      onNavigate('landing');
    } catch (err: any) {
      alert('Error deleting account: ' + (err.message || ''));
    } finally {
      setDeleteAccountLoading(false);
    }
  };

  return (
    <header className="border-b border-slate-800 bg-[#0c0f17]/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div 
          onClick={() => onNavigate(user ? 'dashboard' : 'landing')}
          className="flex items-center space-x-3 cursor-pointer group"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-lg tracking-tight text-white group-hover:text-indigo-400 transition-colors">
              {t.app_name}
            </span>
            <span className="text-[10px] text-slate-400 tracking-wider uppercase font-medium">Meta Ads Automation</span>
          </div>
        </div>

        {/* Navigation links if logged in */}
        {user && (
          <nav className="hidden md:flex items-center space-x-1">
            <button
              onClick={() => onNavigate('dashboard')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                currentPage === 'dashboard'
                  ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {t.nav.dashboard}
            </button>
            <button
              onClick={() => onNavigate('history')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                currentPage === 'history'
                  ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {t.nav.history}
            </button>
          </nav>
        )}

        {/* Right side controls: Theme, Language, User Menu */}
        <div className="flex items-center space-x-3">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800 transition-colors"
            title={theme === 'dark' ? t.theme.light : t.theme.dark}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
          </button>

          {/* Language Switcher Dropdown */}
          <div className="relative">
            <button
              onClick={() => setLangMenuOpen(!langMenuOpen)}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs text-slate-300 hover:bg-slate-800 border border-slate-800 transition-colors"
            >
              <span>{currentLangObj.flag}</span>
              <span className="font-medium uppercase">{currentLangObj.code}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {langMenuOpen && (
              <div 
                className="absolute right-0 mt-2 w-36 bg-[#161c2b] border border-slate-800 rounded-xl shadow-xl py-1 z-50"
                onClick={() => setLangMenuOpen(false)}
              >
                {languages.map(l => (
                  <button
                    key={l.code}
                    onClick={() => setLanguage(l.code)}
                    className={`w-full flex items-center space-x-2 px-3 py-2 text-xs text-left hover:bg-slate-800/70 transition-colors ${
                      language === l.code ? 'text-indigo-400 font-semibold' : 'text-slate-300'
                    }`}
                  >
                    <span>{l.flag}</span>
                    <span>{l.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* User Profile Menu or Auth Buttons */}
          {user ? (
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center space-x-2 p-1.5 pl-2 rounded-xl bg-slate-800/70 border border-slate-700 hover:border-slate-600 transition-colors"
              >
                {user.meta_avatar_url ? (
                  <img src={user.meta_avatar_url} alt="Avatar" className="w-6 h-6 rounded-full object-cover" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-xs text-indigo-300 font-bold">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="text-xs text-slate-200 hidden sm:inline-block max-w-[120px] truncate">
                  {user.email}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {userMenuOpen && (
                <div 
                  className="absolute right-0 mt-2 w-56 bg-[#161c2b] border border-slate-800 rounded-xl shadow-2xl py-1.5 z-50 text-xs"
                  onClick={() => setUserMenuOpen(false)}
                >
                  <div className="px-3 py-2 border-b border-slate-800">
                    <p className="text-[11px] text-slate-400">{t.topbar?.logged_as || 'Signed in as'}</p>
                    <p className="font-semibold text-slate-200 truncate">{user.email}</p>
                    {user.has_meta_connection && (
                      <div className="mt-1 flex items-center space-x-1 text-[10px] text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>{(t.topbar?.meta_connected || 'Meta connected:')} {user.meta_user_name}</span>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => onNavigate('dashboard')}
                    className="w-full flex items-center space-x-2 px-3 py-2 text-slate-300 hover:bg-slate-800 transition-colors"
                  >
                    <Activity className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{t.nav.dashboard}</span>
                  </button>

                  <button
                    onClick={() => onNavigate('history')}
                    className="w-full flex items-center space-x-2 px-3 py-2 text-slate-300 hover:bg-slate-800 transition-colors"
                  >
                    <Clock className="w-3.5 h-3.5 text-sky-400" />
                    <span>{t.nav.history}</span>
                  </button>

                  <div className="my-1 border-t border-slate-800"></div>

                  <button
                    onClick={() => setDeleteAccountModalOpen(true)}
                    className="w-full flex items-center space-x-2 px-3 py-2 text-rose-400 hover:bg-rose-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>{t.nav.delete_account}</span>
                  </button>

                  <button
                    onClick={async () => {
                      await logout();
                      onNavigate('landing');
                    }}
                    className="w-full flex items-center space-x-2 px-3 py-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>{t.nav.logout}</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onNavigate('login')}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-800 transition-colors"
              >
                {t.nav.login}
              </button>
              <button
                onClick={() => onNavigate('register')}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-md shadow-indigo-600/20"
              >
                {t.nav.register}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Delete Account In-App Confirmation Modal */}
      {deleteAccountModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121622] border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {t.nav.delete_account}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 truncate">
                  {user?.email}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {t.topbar?.delete_confirm || 'Are you sure you want to permanently delete your account and all data?'}
            </p>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setDeleteAccountModalOpen(false)}
                disabled={deleteAccountLoading}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
              >
                {t.dashboard?.cancel || 'Cancel'}
              </button>

              <button
                onClick={confirmDeleteAccount}
                disabled={deleteAccountLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-colors flex items-center space-x-2 shadow-lg shadow-rose-600/20"
              >
                {deleteAccountLoading ? (
                  <span>{t.dashboard?.deleting || 'Deleting...'}</span>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>{t.nav.delete_account}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
