import React from 'react';
import { Send } from 'lucide-react';
import { MetricDefinition, Language } from '../types';

interface PreviewBubbleProps {
  reportName: string;
  selectedMetrics: string[];
  metricsMap: Record<string, MetricDefinition>;
  customLabels: Record<string, string>;
  lang: Language;
  currency?: string;
  periodicity?: string;
}

export const PreviewBubble: React.FC<PreviewBubbleProps> = ({
  reportName,
  selectedMetrics,
  metricsMap,
  customLabels,
  lang,
  currency = 'USD',
  periodicity = 'daily',
}) => {
  const getHeaderTitle = () => {
    if (lang === 'uz') {
      return periodicity === 'daily' ? 'Kunlik hisobot' : periodicity === 'weekly' ? 'Haftalik hisobot' : 'Oylik hisobot';
    }
    if (lang === 'en') {
      return periodicity === 'daily' ? 'Daily Report' : periodicity === 'weekly' ? 'Weekly Report' : 'Monthly Report';
    }
    return periodicity === 'daily' ? 'Ежедневный отчёт' : periodicity === 'weekly' ? 'Еженедельный отчёт' : 'Ежемесячный отчёт';
  };

  const formatSample = (defn?: MetricDefinition) => {
    if (!defn) return '0';
    const val = defn.sample_value;
    if (defn.format_type === 'currency') {
      return currency === 'USD' ? `$${val.toFixed(2)}` : `${val.toFixed(2)} ${currency}`;
    }
    if (defn.format_type === 'percent') {
      return `${val.toFixed(2)}%`;
    }
    if (defn.format_type === 'integer') {
      return Math.round(val).toLocaleString('ru-RU').replace(',', ' ');
    }
    return val.toFixed(2);
  };

  return (
    <div className="bg-[#121620] border border-slate-800 rounded-2xl p-4 shadow-xl">
      {/* Telegram preview card header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3 text-xs">
        <div className="flex items-center space-x-2 text-sky-400">
          <Send className="w-4 h-4" />
          <span className="font-semibold text-slate-200">Telegram</span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-medium">Bot</span>
      </div>

      {/* Message bubble */}
      <div className="bg-[#181f2f] border border-slate-700/60 rounded-xl p-4 text-xs font-mono space-y-2 text-slate-200 shadow-inner">
        <div className="font-bold text-slate-100 flex items-center space-x-1.5 pb-1 border-b border-slate-700/40">
          <span>📊</span>
          <span>{getHeaderTitle()}: {reportName || 'Demo Report'}</span>
        </div>

        <div className="text-[11px] text-slate-400">
          🏢 Demo Ad Account ({currency})<br />
          📅 2026-09-28
        </div>

        <div className="space-y-1.5 pt-1">
          {selectedMetrics.length === 0 ? (
            <div className="text-slate-500 italic py-2 text-center">
              {lang === 'uz' ? 'Predprosmotrni ko\'rish uchun yuqoridagi metrikalarni tanlang' : lang === 'en' ? 'Select metrics above to see preview' : 'Выберите метрики выше, чтобы увидеть предпросмотр'}
            </div>
          ) : (
            selectedMetrics.map((key) => {
              const defn = metricsMap[key];
              const label =
                customLabels[key] ||
                (defn
                  ? lang === 'uz'
                    ? defn.uz_label
                    : lang === 'en'
                    ? defn.en_label
                    : defn.ru_label
                  : key);

              return (
                <div key={key} className="flex justify-between items-center py-0.5 border-b border-slate-800/40 last:border-0">
                  <span className="text-slate-300">• {label}:</span>
                  <span className="font-semibold text-indigo-300">{formatSample(defn)}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
