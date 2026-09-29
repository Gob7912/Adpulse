import React, { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  Send,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  ShieldCheck,
  ChevronDown,
  ArrowRight,
  TrendingUp,
  BarChart3
} from 'lucide-react';

interface LandingPageProps {
  onGetStarted: () => void;
  onLogin: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onGetStarted, onLogin }) => {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const faqs = [
    {
      q: t.landing.faq1_q,
      a: t.landing.faq1_a
    },
    {
      q: t.landing.faq2_q,
      a: t.landing.faq2_a
    },
    {
      q: t.landing.faq3_q,
      a: t.landing.faq3_a
    },
    {
      q: t.landing.faq4_q,
      a: t.landing.faq4_a
    }
  ];

  return (
    <div className="space-y-24 pb-20">
      {/* 1. HERO SECTION */}
      <section className="relative pt-12 sm:pt-20 px-4 sm:px-6 max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-950/60 border border-indigo-500/30 text-indigo-300 text-xs font-medium mb-8 shadow-inner">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>{t.landing.badge}</span>
        </div>

        <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold text-white tracking-tight max-w-4xl mx-auto leading-tight">
          {t.landing.hero_title_part1}<span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-400">{t.landing.hero_tg}</span>{t.landing.hero_and}<span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">{t.landing.hero_sheets}</span>
        </h1>

        <p className="mt-6 text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
          {t.landing.hero_subtitle}
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={onGetStarted}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold text-white shadow-xl shadow-indigo-600/25 transition-all flex items-center justify-center space-x-2 group"
          >
            <span>{user ? t.landing.cta_dashboard : t.landing.cta_start}</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
          {!user && (
            <button
              onClick={onLogin}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-sm font-medium text-slate-300 transition-colors"
            >
              {t.landing.cta_login}
            </button>
          )}
        </div>

        {/* Telegram Mockup Preview in Hero */}
        <div className="mt-14 max-w-md mx-auto">
          <div className="bg-[#121622] border border-slate-800 rounded-2xl p-4 shadow-2xl text-left">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
              <div className="flex items-center space-x-2 text-sky-400">
                <Send className="w-4 h-4" />
                <span className="font-semibold text-white">AdPulse Bot</span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">08:00 AM</span>
            </div>

            <div className="bg-[#181f2f] rounded-xl p-4 text-xs font-mono space-y-2 mt-3 text-slate-200">
              <div className="font-bold text-white border-b border-slate-700/50 pb-1">
                📊 Daily Report: Клиент X
              </div>
              <div className="text-[11px] text-slate-400">
                🏢 E-Commerce Store (USD) • 2026-09-28
              </div>
              <div className="space-y-1 pt-1">
                <div className="flex justify-between"><span>• {language === 'uz' ? 'Xarajat' : language === 'en' ? 'Spend' : 'Расход'}:</span><span className="font-semibold text-indigo-300">$145.20</span></div>
                <div className="flex justify-between"><span>• {language === 'uz' ? 'Ko\'rsatishlar' : language === 'en' ? 'Impressions' : 'Показы'}:</span><span className="font-semibold text-indigo-300">28 450</span></div>
                <div className="flex justify-between"><span>• {language === 'uz' ? 'Qamrov' : language === 'en' ? 'Reach' : 'Охват'}:</span><span className="font-semibold text-indigo-300">21 300</span></div>
                <div className="flex justify-between"><span>• {language === 'uz' ? 'Lidlar' : language === 'en' ? 'Leads' : 'Лиды'}:</span><span className="font-semibold text-emerald-400">42</span></div>
                <div className="flex justify-between"><span>• CPL:</span><span className="font-semibold text-indigo-300">$3.45</span></div>
                <div className="flex justify-between"><span>• ROAS:</span><span className="font-semibold text-emerald-400">3.85</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. THREE KEY BENEFITS */}
      <section className="px-4 sm:px-6 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-white">{t.landing.benefit1_title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.landing.benefit1_desc}
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-sky-600/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-white">{t.landing.benefit2_title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.landing.benefit2_desc}
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-white">{t.landing.benefit3_title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.landing.benefit3_desc}
            </p>
          </div>
        </div>
      </section>

      {/* 3. MANUAL VS AUTOMATIC COMPARISON */}
      <section className="px-4 sm:px-6 max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {t.landing.compare_title}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2">
            {t.landing.compare_subtitle}
          </p>
        </div>

        <div className="border border-slate-800 rounded-2xl bg-[#121622] overflow-hidden shadow-xl">
          <div className="grid grid-cols-2 divide-x divide-slate-800 text-xs">
            <div className="p-4 sm:p-6 bg-slate-900/30">
              <div className="font-bold text-slate-400 uppercase text-[11px] mb-4 flex items-center space-x-1.5">
                <XCircle className="w-4 h-4 text-rose-400" />
                <span>{t.landing.compare_manual_title}</span>
              </div>
              <ul className="space-y-3 text-slate-400">
                <li className="flex items-start space-x-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>{t.landing.compare_m1}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>{t.landing.compare_m2}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>{t.landing.compare_m3}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span>{t.landing.compare_m4}</span>
                </li>
              </ul>
            </div>

            <div className="p-4 sm:p-6 bg-indigo-950/10">
              <div className="font-bold text-indigo-400 uppercase text-[11px] mb-4 flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>{t.landing.compare_auto_title}</span>
              </div>
              <ul className="space-y-3 text-slate-200">
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>{t.landing.compare_a1}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>{t.landing.compare_a2}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>{t.landing.compare_a3}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>{t.landing.compare_a4}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 4. HOW IT WORKS IN 3 STEPS */}
      <section className="px-4 sm:px-6 max-w-5xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-12">
          {t.landing.how_title}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
          <div className="relative p-6 rounded-2xl border border-slate-800 bg-[#121622]">
            <div className="text-3xl font-black text-indigo-500/30 mb-3 font-mono">01</div>
            <h3 className="font-bold text-sm text-white mb-1">{t.landing.how_step1_title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.landing.how_step1_desc}
            </p>
          </div>

          <div className="relative p-6 rounded-2xl border border-slate-800 bg-[#121622]">
            <div className="text-3xl font-black text-indigo-500/30 mb-3 font-mono">02</div>
            <h3 className="font-bold text-sm text-white mb-1">{t.landing.how_step2_title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.landing.how_step2_desc}
            </p>
          </div>

          <div className="relative p-6 rounded-2xl border border-slate-800 bg-[#121622]">
            <div className="text-3xl font-black text-indigo-500/30 mb-3 font-mono">03</div>
            <h3 className="font-bold text-sm text-white mb-1">{t.landing.how_step3_title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.landing.how_step3_desc}
            </p>
          </div>
        </div>
      </section>

      {/* 5. FAQ ACCORDION */}
      <section className="px-4 sm:px-6 max-w-3xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight text-center mb-8">
          {t.landing.faq_title}
        </h2>

        <div className="space-y-3">
          {faqs.map((f, i) => {
            const isOpen = openFaq === i;
            return (
              <div
                key={i}
                className="border border-slate-800 rounded-xl bg-[#121622] overflow-hidden transition-colors"
              >
                <button
                  onClick={() => setOpenFaq(isOpen ? null : i)}
                  className="w-full p-4 text-left text-xs sm:text-sm font-semibold text-white flex items-center justify-between"
                >
                  <span>{f.q}</span>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 text-xs text-slate-400 leading-relaxed border-t border-slate-800/60 pt-3">
                    {f.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-slate-800 pt-8 px-4 text-center text-xs text-slate-500 space-y-2">
        <div>© 2026 {t.app_name}. {t.landing.footer_text}.</div>
        <div className="space-x-4 text-[11px] text-slate-400">
          <a href="#" className="hover:underline">{t.landing.privacy_policy}</a>
          <span>•</span>
          <a href="#" className="hover:underline">{t.landing.terms_of_service}</a>
          <span>•</span>
          <a href="#" className="hover:underline">{t.landing.docs_link}</a>
        </div>
      </footer>
    </div>
  );
};
