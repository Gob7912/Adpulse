import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../services/api';
import { RunHistory } from '../types';
import { Clock, Send, FileSpreadsheet, CheckCircle2, AlertTriangle, ArrowLeft } from 'lucide-react';

interface HistoryPageProps {
  onBack: () => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({ onBack }) => {
  const { t } = useLanguage();
  const [history, setHistory] = useState<RunHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getRunHistory();
        setHistory(data);
      } catch (err) {
        console.error('Failed to load history', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center space-x-3 mb-6">
        <button
          onClick={onBack}
          className="p-2 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-300 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{t.nav.history}</h1>
          <p className="text-xs text-slate-400">{t.history.subtitle}</p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">{t.history.loading}</div>
      ) : history.length === 0 ? (
        <div className="p-12 rounded-2xl border border-slate-800 bg-[#121622] text-center max-w-lg mx-auto space-y-3">
          <Clock className="w-8 h-8 text-slate-600 mx-auto" />
          <div className="font-bold text-sm text-white">{t.history.empty_title}</div>
          <p className="text-xs text-slate-400">{t.history.empty_desc}</p>
        </div>
      ) : (
        <div className="border border-slate-800 rounded-2xl bg-[#121622] overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-[#161c2b] text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800 font-semibold">
                <tr>
                  <th className="py-3 px-4">{t.history.th_time}</th>
                  <th className="py-3 px-4">{t.history.th_period}</th>
                  <th className="py-3 px-4">{t.history.th_status}</th>
                  <th className="py-3 px-4">{t.history.th_channels}</th>
                  <th className="py-3 px-4">{t.history.th_duration}</th>
                  <th className="py-3 px-4">{t.history.th_details}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {history.map((h) => (
                  <tr key={h.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-200">
                      {new Date(h.run_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px]">
                      <div>{h.period_start === h.period_end ? h.period_start : `${h.period_start} — ${h.period_end}`}</div>
                      <div className="text-[10px] text-slate-500 uppercase">{h.period_type}</div>
                    </td>
                    <td className="py-3 px-4">
                      {h.status === 'success' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold flex items-center space-x-1 w-fit">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>{t.history.status_success}</span>
                        </span>
                      ) : h.status === 'partial' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-400 font-semibold flex items-center space-x-1 w-fit">
                          <AlertTriangle className="w-3 h-3" />
                          <span>{t.history.status_partial}</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold flex items-center space-x-1 w-fit">
                          <AlertTriangle className="w-3 h-3" />
                          <span>{t.history.status_failed}</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`p-1 rounded text-xs ${
                            h.telegram_delivered ? 'text-sky-400' : 'text-slate-600'
                          }`}
                          title={h.telegram_delivered ? 'Telegram: ok' : h.telegram_error || 'Telegram: -'}
                        >
                          <Send className="w-3.5 h-3.5" />
                        </span>
                        <span
                          className={`p-1 rounded text-xs ${
                            h.sheets_delivered ? 'text-emerald-400' : 'text-slate-600'
                          }`}
                          title={h.sheets_delivered ? 'Google Sheets: ok' : h.sheets_error || 'Sheets: -'}
                        >
                          <FileSpreadsheet className="w-3.5 h-3.5" />
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {h.duration_seconds.toFixed(2)} {t.history.sec}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px] max-w-xs truncate">
                      {h.error_message ? (
                        <span className="text-rose-400" title={h.error_message}>{h.error_message}</span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
