import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../services/api';
import { Report } from '../types';
import {
  Plus,
  Play,
  Pause,
  Copy,
  Trash2,
  Send,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  Edit2
} from 'lucide-react';
import { getReportTypeIcon } from '../utils/reportIcons';

interface DashboardPageProps {
  onCreateReport: () => void;
  onEditReport: (reportId: string) => void;
  onViewHistory: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onCreateReport,
  onEditReport,
  onViewHistory,
}) => {
  const { t } = useLanguage();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [reportToDelete, setReportToDelete] = useState<Report | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadReports = async () => {
    try {
      const data = await api.listReports();
      setReports(data);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handlePause = async (id: string) => {
    setActionLoading(id);
    try {
      await api.pauseReport(id);
      await loadReports();
    } finally {
      setActionLoading(null);
    }
  };

  const handleResume = async (id: string) => {
    setActionLoading(id);
    try {
      await api.resumeReport(id);
      await loadReports();
    } finally {
      setActionLoading(null);
    }
  };

  const handleDuplicate = async (id: string) => {
    setActionLoading(id);
    try {
      await api.duplicateReport(id);
      await loadReports();
    } finally {
      setActionLoading(null);
    }
  };

  const confirmDelete = async () => {
    if (!reportToDelete) return;
    setDeleteLoading(true);
    try {
      await api.deleteReport(reportToDelete.id);
      setReports(prev => prev.filter(r => r.id !== reportToDelete.id));
      setReportToDelete(null);
      await loadReports();
    } catch (err: any) {
      alert(t.dashboard.toast_delete_error + (err.message || ''));
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleSendNow = async (id: string) => {
    setActionLoading(id);
    try {
      await api.triggerTestSend(id);
      alert(t.dashboard.toast_send_success);
      await loadReports();
    } catch (err: any) {
      alert(t.dashboard.toast_send_error + (err.message || ''));
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Dashboard Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">{t.dashboard.title}</h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">{t.dashboard.subtitle}</p>
        </div>

        <button
          onClick={onCreateReport}
          className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>{t.dashboard.new_report}</span>
        </button>
      </div>

      {/* Reports Table or Empty State */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">{t.dashboard.loading}</div>
      ) : reports.length === 0 ? (
        <div className="p-12 rounded-2xl border border-slate-800 bg-[#121622] text-center max-w-lg mx-auto space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="font-bold text-sm text-white">{t.dashboard.empty_title}</div>
            <p className="text-xs text-slate-400 mt-1">{t.dashboard.empty_desc}</p>
          </div>
          <button
            onClick={onCreateReport}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors"
          >
            {t.dashboard.new_report}
          </button>
        </div>
      ) : (
        <div className="border border-slate-800 rounded-2xl bg-[#121622] overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-[#161c2b] text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800 font-semibold">
                <tr>
                  <th className="py-3.5 px-4">{t.dashboard.table_name}</th>
                  <th className="py-3.5 px-4">{t.dashboard.table_schedule}</th>
                  <th className="py-3.5 px-4">{t.dashboard.table_destinations}</th>
                  <th className="py-3.5 px-4">{t.dashboard.table_status}</th>
                  <th className="py-3.5 px-4">{t.dashboard.table_next_run}</th>
                  <th className="py-3.5 px-4">{t.dashboard.table_last_run}</th>
                  <th className="py-3.5 px-4 text-right">{t.dashboard.table_actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {reports.map((rep) => {
                  const tgDest = rep.destinations.find(d => d.destination_type === 'telegram');
                  const sheetsDest = rep.destinations.find(d => d.destination_type === 'google_sheets');
                  const RowIcon = getReportTypeIcon(null, {
                    metrics: rep.metrics,
                    goals: rep.campaign_filter_goals
                  });

                  return (
                    <tr key={rep.id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Name & Ad Account */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center space-x-2.5">
                          <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
                            <RowIcon className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="font-semibold text-slate-100">{rep.name}</div>
                            <div className="text-[11px] text-slate-400 flex items-center space-x-1.5 mt-0.5">
                              <span>{rep.meta_account_name}</span>
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-slate-800 text-indigo-300 font-mono">
                                {rep.currency}
                              </span>
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Schedule */}
                      <td className="py-3.5 px-4 font-mono text-[11px]">
                        <div>{rep.periodicity === 'daily' ? t.step4.periodicity_daily : rep.periodicity === 'weekly' ? t.step4.periodicity_weekly : t.step4.periodicity_monthly}</div>
                        <div className="text-slate-400">{rep.schedule_time} ({rep.send_timezone.split('/').pop()})</div>
                      </td>

                      {/* Destinations */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center space-x-2">
                          {tgDest && (
                            <span
                              title={tgDest.is_connected ? 'Telegram ✓' : 'Telegram ...'}
                              className={`p-1.5 rounded-lg text-xs flex items-center space-x-1 border ${
                                tgDest.is_connected
                                  ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                                  : 'bg-slate-800 text-slate-500 border-slate-700'
                              }`}
                            >
                              <Send className="w-3.5 h-3.5" />
                              <span className="text-[10px]">{tgDest.is_connected ? '✓' : '...'}</span>
                            </span>
                          )}

                          {sheetsDest && (
                            <span
                              title={sheetsDest.is_connected ? 'Google Sheets ✓' : 'Google Sheets'}
                              className="p-1.5 rounded-lg text-xs flex items-center space-x-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            >
                              <FileSpreadsheet className="w-3.5 h-3.5" />
                              <span className="text-[10px]">✓</span>
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        {rep.is_active ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-medium">
                            {t.dashboard.status_active}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 border border-slate-700 text-slate-400 font-medium">
                            {t.dashboard.status_paused}
                          </span>
                        )}
                      </td>

                      {/* Next Run */}
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400">
                        {rep.next_run_at ? new Date(rep.next_run_at).toLocaleString() : '—'}
                      </td>

                      {/* Last Run Result */}
                      <td className="py-3.5 px-4 text-[11px]">
                        {rep.last_run_status === 'success' ? (
                          <span className="text-emerald-400 flex items-center space-x-1">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>{t.history.status_success}</span>
                          </span>
                        ) : rep.last_run_status === 'failed' ? (
                          <span className="text-rose-400 flex items-center space-x-1" title={rep.last_run_error || ''}>
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>{t.history.status_failed}</span>
                          </span>
                        ) : (
                          <span className="text-slate-500">{t.dashboard.status_pending}</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => handleSendNow(rep.id)}
                            disabled={actionLoading === rep.id}
                            title={t.dashboard.action_send_now}
                            className="p-1.5 rounded-lg text-indigo-400 hover:bg-indigo-600/10 border border-transparent hover:border-indigo-500/30 transition-colors"
                          >
                            <Send className="w-3.5 h-3.5" />
                          </button>

                          {rep.is_active ? (
                            <button
                              onClick={() => handlePause(rep.id)}
                              disabled={actionLoading === rep.id}
                              title={t.dashboard.action_pause}
                              aria-label={t.dashboard.action_pause}
                              className="p-1.5 rounded-lg text-amber-400 hover:bg-amber-600/10 transition-colors"
                            >
                              <Pause className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleResume(rep.id)}
                              disabled={actionLoading === rep.id}
                              title={t.dashboard.action_resume}
                              aria-label={t.dashboard.action_resume}
                              className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-600/10 transition-colors"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                          )}

                          <button
                            onClick={() => onEditReport(rep.id)}
                            disabled={actionLoading === rep.id}
                            title={t.dashboard.action_edit}
                            aria-label={t.dashboard.action_edit}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleDuplicate(rep.id)}
                            disabled={actionLoading === rep.id}
                            title={t.dashboard.action_duplicate}
                            aria-label={t.dashboard.action_duplicate}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => setReportToDelete(rep)}
                            disabled={actionLoading === rep.id || deleteLoading}
                            title={t.dashboard.action_delete}
                            className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* In-App Delete Confirmation Modal */}
      {reportToDelete && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121622] border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div className="overflow-hidden">
                <h3 className="text-base font-bold text-white">
                  {t.dashboard.delete_modal_title}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 truncate">
                  {reportToDelete.name}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {t.dashboard.delete_modal_warning}
            </p>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setReportToDelete(null)}
                disabled={deleteLoading}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
              >
                {t.dashboard.cancel}
              </button>

              <button
                onClick={confirmDelete}
                disabled={deleteLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-colors flex items-center space-x-2 shadow-lg shadow-rose-600/20"
              >
                {deleteLoading ? (
                  <span>{t.dashboard.deleting}</span>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>{t.dashboard.action_delete}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
