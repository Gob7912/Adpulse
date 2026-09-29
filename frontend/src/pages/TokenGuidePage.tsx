import React from 'react';
import { useLanguage } from '../context/LanguageContext';
import { ArrowLeft, KeyRound, ShieldCheck, CheckCircle2, Copy } from 'lucide-react';

interface TokenGuidePageProps {
  onBack: () => void;
}

export const TokenGuidePage: React.FC<TokenGuidePageProps> = ({ onBack }) => {
  const { t } = useLanguage();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Top Header */}
      <div className="flex items-center space-x-3 mb-6">
        <button
          onClick={onBack}
          className="p-2 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-300 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {t.token_guide.title}
          </h1>
          <p className="text-xs text-slate-400">
            {t.token_guide.subtitle}
          </p>
        </div>
      </div>

      {/* Guide Content */}
      <div className="space-y-6">
        {/* Step 1 */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center text-xs font-bold font-mono">
              1
            </div>
            <h3 className="font-bold text-sm text-white">{t.token_guide.step1_title}</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed pl-10">
            {t.token_guide.step1_desc}
          </p>
        </div>

        {/* Step 2 */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center text-xs font-bold font-mono">
              2
            </div>
            <h3 className="font-bold text-sm text-white">{t.token_guide.step2_title}</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed pl-10">
            {t.token_guide.step2_desc}
          </p>
          <div className="ml-10 p-3 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
            💡 {t.token_guide.step2_note}
          </div>
        </div>

        {/* Step 3 */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center text-xs font-bold font-mono">
              3
            </div>
            <h3 className="font-bold text-sm text-white">{t.token_guide.step3_title}</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed pl-10">
            {t.token_guide.step3_desc}
          </p>
        </div>

        {/* Step 4 */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center text-xs font-bold font-mono">
              4
            </div>
            <h3 className="font-bold text-sm text-white">{t.token_guide.step4_title}</h3>
          </div>
          <div className="space-y-2 text-xs text-slate-300 pl-10 leading-relaxed">
            <p>{t.token_guide.step4_step1}</p>
            <p>{t.token_guide.step4_step2}</p>
            <p>{t.token_guide.step4_step3}</p>
            <p>{t.token_guide.step4_step4}</p>
            <div className="flex items-center space-x-2 my-2">
              <span className="px-2.5 py-1 rounded bg-indigo-950/60 border border-indigo-500/40 text-indigo-300 font-mono font-semibold">
                ads_read
              </span>
              <span className="text-slate-400">{t.token_guide.step4_perm_desc}</span>
            </div>
            <p>{t.token_guide.step4_step5}</p>
          </div>
        </div>

        {/* Step 5 */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-[#121622] space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-full bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center text-xs font-bold font-mono">
              5
            </div>
            <h3 className="font-bold text-sm text-white">{t.token_guide.step5_title}</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed pl-10">
            {t.token_guide.step5_desc}
          </p>
        </div>
      </div>
    </div>
  );
};
