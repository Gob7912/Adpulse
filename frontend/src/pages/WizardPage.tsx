import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { WizardStepper } from '../components/WizardStepper';
import { PreviewBubble } from '../components/PreviewBubble';
import { api } from '../services/api';
import {
  MetaAdAccount,
  MetaCampaign,
  MetaProfile,
  MetricDefinition,
  TemplateInfo,
  Language,
  Report,
  TelegramBotInfoResponse
} from '../types';
import {
  Check,
  Info,
  ChevronDown,
  Search,
  ExternalLink,
  Copy,
  RefreshCw,
  Send,
  FileSpreadsheet,
  AlertCircle,
  Sparkles,
  Layers,
  ArrowRight,
  ArrowLeft
} from 'lucide-react';
import { getReportTypeIcon } from '../utils/reportIcons';

interface WizardPageProps {
  onFinish: () => void;
  onNavigateToTokenGuide: () => void;
  editingReportId?: string | null;
}

export const WizardPage: React.FC<WizardPageProps> = ({
  onFinish,
  onNavigateToTokenGuide,
  editingReportId,
}) => {
  const { language, t } = useLanguage();
  const { user, refreshUser } = useAuth();

  // Wizard Step (1 to 5)
  const [step, setStep] = useState<number>(1);

  // Loading & error state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  // Metadata from backend
  const [metricsList, setMetricsList] = useState<MetricDefinition[]>([]);
  const [metricsMap, setMetricsMap] = useState<Record<string, MetricDefinition>>({});
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [optimizationGoals, setOptimizationGoals] = useState<{ key: string; ru: string; uz: string; en: string }[]>([]);

  // Step 1: Platform & Delivery
  const [deliveryChannels, setDeliveryChannels] = useState<('telegram' | 'google_sheets')[]>(['telegram']);

  // Step 2: Meta Profile & Account & Campaigns
  const [metaProfile, setMetaProfile] = useState<MetaProfile | null>(null);
  const [tokenInput, setTokenInput] = useState('');
  const [verifyingToken, setVerifyingToken] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);

  const [adAccounts, setAdAccounts] = useState<MetaAdAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<MetaAdAccount | null>(null);
  const [accountSearch, setAccountSearch] = useState('');
  const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);

  const [campaignScope, setCampaignScope] = useState<'all' | 'filtered' | 'specific'>('all');
  const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
  const [nameContains, setNameContains] = useState('');
  const [availableCampaigns, setAvailableCampaigns] = useState<MetaCampaign[]>([]);
  const [selectedCampaignIds, setSelectedCampaignIds] = useState<string[]>([]);
  const [campaignSearch, setCampaignSearch] = useState('');

  // Step 3: Metrics
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>('daily_pulse');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    'spend', 'impressions', 'reach', 'new_followers', 'cpm', 'cpp'
  ]);
  const [smartDetection, setSmartDetection] = useState(true);
  const [metricLabels, setMetricLabels] = useState<Record<string, string>>({});
  const [labelsLang, setLabelsLang] = useState<Language>(language);

  // Step 4: Schedule
  const [reportName, setReportName] = useState('');
  const [periodicity, setPeriodicity] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [scheduleTime, setScheduleTime] = useState('08:00');
  const [scheduleWeekday, setScheduleWeekday] = useState(0); // Monday
  const [scheduleMonthday, setScheduleMonthday] = useState(1);
  const [sendTimezone, setSendTimezone] = useState('Asia/Tashkent');

  // Step 5: Connection & Created report
  const [createdReport, setCreatedReport] = useState<Report | null>(null);
  const [sheetsUrl, setSheetsUrl] = useState('');
  const [sheetsTabName, setSheetsTabName] = useState('Sheet1');
  const [sheetsVerifyStatus, setSheetsVerifyStatus] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);
  const [testSending, setTestSending] = useState(false);
  const [botInfo, setBotInfo] = useState<TelegramBotInfoResponse | null>(null);

  const [serviceAccountEmail, setServiceAccountEmail] = useState<string>('adpulse-service@adpulse-reports.iam.gserviceaccount.com');

  // Edit mode tracking state
  const [isDirty, setIsDirty] = useState(false);
  const [accountChangedNotice, setAccountChangedNotice] = useState(false);
  const initialAccountIdRef = React.useRef<string | null>(null);

  const handleClose = () => {
    if (isDirty && step !== 5) {
      if (!window.confirm(t.stepper.unsaved_confirm)) {
        return;
      }
    }
    onFinish();
  };

  // Load Telegram bot info and Sheets service account email at runtime
  useEffect(() => {
    api.getTelegramBotInfo()
      .then(setBotInfo)
      .catch((err) => {
        setBotInfo({ bot_username: null, is_configured: false, error: err.message });
      });

    api.getSheetsServiceInfo()
      .then((info) => {
        if (info.service_account_email) {
          setServiceAccountEmail(info.service_account_email);
        }
      })
      .catch(() => {});
  }, [step]);

  // Load existing report if editingReportId is provided
  useEffect(() => {
    if (!editingReportId) return;
    async function loadEditingReport() {
      setLoading(true);
      try {
        const report = await api.getReport(editingReportId!);
        setReportName(report.name);
        setPeriodicity(report.periodicity);
        setScheduleTime(report.schedule_time);
        if (report.schedule_weekday !== null && report.schedule_weekday !== undefined) {
          setScheduleWeekday(report.schedule_weekday);
        }
        if (report.schedule_monthday !== null && report.schedule_monthday !== undefined) {
          setScheduleMonthday(report.schedule_monthday);
        }
        setSendTimezone(report.send_timezone);
        setCampaignScope(report.campaign_scope_type);
        setSelectedGoals(report.campaign_filter_goals || []);
        setNameContains(report.campaign_filter_name || '');
        setSelectedCampaignIds(report.specific_campaign_ids || []);
        setSelectedMetrics(report.metrics || []);
        setSmartDetection(report.smart_metric_detection);
        if (report.metric_labels) {
          setMetricLabels(report.metric_labels);
        }
        if (report.metric_lang) {
          setLabelsLang(report.metric_lang);
        }

        const channels: ('telegram' | 'google_sheets')[] = [];
        report.destinations.forEach((d) => {
          if (d.destination_type === 'telegram' && !channels.includes('telegram')) channels.push('telegram');
          if (d.destination_type === 'google_sheets' && !channels.includes('google_sheets')) channels.push('google_sheets');
        });
        if (channels.length > 0) {
          setDeliveryChannels(channels);
        }

        const sheets = report.destinations.find((d) => d.destination_type === 'google_sheets');
        if (sheets) {
          if (sheets.sheets_url) setSheetsUrl(sheets.sheets_url);
          if (sheets.sheets_tab_name) setSheetsTabName(sheets.sheets_tab_name);
        }

        setSelectedAccount({
          id: report.meta_account_id,
          name: report.meta_account_name,
          currency: report.currency,
          timezone_name: report.account_timezone,
          account_status: 1,
        });

        initialAccountIdRef.current = report.meta_account_id;
        setSelectedTemplate(null);
        setCreatedReport(report);
        setIsDirty(false);
      } catch (err: any) {
        setError(`Ошибка загрузки отчёта: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    loadEditingReport();
  }, [editingReportId]);

  // Load metadata on mount
  useEffect(() => {
    async function loadMeta() {
      try {
        const meta = await api.getMetadata();
        setMetricsList(meta.metrics);
        const map: Record<string, MetricDefinition> = {};
        meta.metrics.forEach((m: MetricDefinition) => {
          map[m.key] = m;
        });
        setMetricsMap(map);
        setTemplates(meta.templates);
        setOptimizationGoals(meta.optimization_goals);

        // Check if user already has connected profile
        try {
          const profile = await api.getMetaProfile();
          setMetaProfile(profile);
          // Load accounts
          const accs = await api.getAdAccounts();
          setAdAccounts(accs);
        } catch (_) {}
      } catch (err: any) {
        console.error('Failed to load metadata', err);
      }
    }
    loadMeta();
  }, []);

  // Sync labels when labelsLang changes or on initial load
  const resetMetricLabels = (targetLang: Language) => {
    const defaults: Record<string, string> = {};
    metricsList.forEach((m) => {
      defaults[m.key] = targetLang === 'uz' ? m.uz_label : targetLang === 'en' ? m.en_label : m.ru_label;
    });
    setMetricLabels(defaults);
  };

  useEffect(() => {
    if (metricsList.length > 0 && Object.keys(metricLabels).length === 0) {
      resetMetricLabels(labelsLang);
    }
  }, [metricsList, labelsLang]);

  // When ad account changes, load campaigns if needed
  useEffect(() => {
    if (selectedAccount) {
      api.getCampaigns(selectedAccount.id).then((camps) => {
        setAvailableCampaigns(camps);
      }).catch(err => {
        console.warn('Could not load campaigns for account', err);
      });
    }
  }, [selectedAccount]);

  // Step 2 Token Verification
  const handleVerifyToken = async () => {
    if (!tokenInput.trim()) return;
    setVerifyingToken(true);
    setTokenError(null);
    try {
      const profile = await api.verifyToken(tokenInput.trim());
      setMetaProfile(profile);
      await refreshUser();
      // Fetch ad accounts
      const accs = await api.getAdAccounts();
      setAdAccounts(accs);
      if (accs.length > 0) {
        setSelectedAccount(accs[0]);
      }
      setTokenInput('');
    } catch (err: any) {
      setTokenError(err.message || 'Ошибка проверки токена. Убедитесь в наличии права ads_read.');
    } finally {
      setVerifyingToken(false);
    }
  };

  // Switch/Disconnect Meta Account
  const handleSwitchAccount = async () => {
    try {
      await api.disconnectMeta();
      setMetaProfile(null);
      setAdAccounts([]);
      setSelectedAccount(null);
      await refreshUser();
    } catch (err: any) {
      console.error(err);
    }
  };

  // Step 3 Template selection
  const handleSelectTemplate = (tmpl: TemplateInfo) => {
    setSelectedTemplate(tmpl.id);
    setSelectedMetrics(tmpl.metrics);
    setIsDirty(true);
  };

  const toggleMetric = (key: string) => {
    setSelectedTemplate(null);
    setSelectedMetrics(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
    setIsDirty(true);
  };

  // Step 4 Validation & Submission to backend
  const handleSaveReport = async () => {
    if (!selectedAccount) return;
    setLoading(true);
    setError(null);

    const payload = {
      name: reportName.trim() || `${selectedAccount.name} — ${t.stepper.step4}`,
      meta_account_id: selectedAccount.id,
      meta_account_name: selectedAccount.name,
      currency: selectedAccount.currency,
      account_timezone: selectedAccount.timezone_name,
      campaign_scope_type: campaignScope,
      campaign_filter_goals: selectedGoals,
      campaign_filter_name: nameContains.trim() || null,
      specific_campaign_ids: selectedCampaignIds,
      metrics: selectedMetrics,
      smart_metric_detection: smartDetection,
      metric_labels: metricLabels,
      metric_lang: language,
      periodicity,
      schedule_time: scheduleTime,
      schedule_weekday: scheduleWeekday,
      schedule_monthday: scheduleMonthday,
      send_timezone: sendTimezone,
      delivery_channels: deliveryChannels,
      sheets_url: sheetsUrl.trim() || null,
      sheets_tab_name: sheetsTabName.trim() || 'Sheet1',
    };

    try {
      let saved: Report;
      if (editingReportId) {
        saved = await api.updateReport(editingReportId, payload);
        setIsDirty(false);
        setCreatedReport(saved);
        setToast(t.step5.report_updated_toast || 'Отчёт успешно обновлен!');
        setTimeout(() => {
          onFinish();
        }, 1200);
      } else {
        saved = await api.createReport(payload);
        setIsDirty(false);
        setCreatedReport(saved);
        setStep(5);
        setToast(t.step5.report_created_toast);
        setTimeout(() => setToast(null), 5000);
      }
    } catch (err: any) {
      setError(err.message || 'Ошибка сохранения отчёта');
    } finally {
      setLoading(false);
    }
  };

  // Step 5 Actions
  const handleRefreshDestinations = async () => {
    if (!createdReport) return;
    try {
      const dests = await api.getDestinationsStatus(createdReport.id);
      setCreatedReport({ ...createdReport, destinations: dests });
      setToast(t.step5.status_updated_toast || 'Status refreshed');
      setTimeout(() => setToast(null), 3000);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleTestSend = async () => {
    if (!createdReport) return;
    setTestSending(true);
    try {
      const res = await api.triggerTestSend(createdReport.id);
      if (res.status === 'success') {
        setToast(t.step5.test_sent_toast);
      } else if (res.status === 'partial') {
        const detail = [res.telegram_error, res.sheets_error].filter(Boolean).join('; ');
        setToast(`${t.step5.test_sent_toast} (${detail})`);
      } else {
        const detail = [res.error, res.telegram_error, res.sheets_error].filter(Boolean).join('; ') || res.status;
        setToast(`Результат теста: ${detail}`);
      }
      setTimeout(() => setToast(null), 6000);
    } catch (err: any) {
      setToast(`Ошибка отправки: ${err.message}`);
      setTimeout(() => setToast(null), 6000);
    } finally {
      setTestSending(false);
    }
  };

  const handleVerifySheets = async () => {
    if (!sheetsUrl.trim()) return;
    try {
      const res = await api.verifyGoogleSheet(sheetsUrl.trim(), sheetsTabName);
      if (res.tab_name) {
        setSheetsTabName(res.tab_name);
      }
      if (res.service_account_email) {
        setServiceAccountEmail(res.service_account_email);
      }
      setSheetsVerifyStatus(res.message);
    } catch (err: any) {
      setSheetsVerifyStatus(err.message);
    }
  };

  // Validation helpers for Next button
  const canGoNextFromStep1 = deliveryChannels.length > 0;
  const canGoNextFromStep2 =
    Boolean(selectedAccount) &&
    (campaignScope !== 'specific' || selectedCampaignIds.length > 0);
  const canGoNextFromStep3 = selectedMetrics.length > 0;
  const canSaveFromStep4 = Boolean(selectedAccount);

  // Telegram destination details from createdReport
  const telegramDest = createdReport?.destinations.find(d => d.destination_type === 'telegram');
  const sheetsDest = createdReport?.destinations.find(d => d.destination_type === 'google_sheets');

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#161c2b] border border-indigo-500/50 text-slate-100 px-4 py-3 rounded-xl shadow-2xl flex items-center space-x-3 text-xs animate-bounce">
          <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
          <span>{toast}</span>
        </div>
      )}

      {/* Centered Main Wizard Card */}
      <div className="bg-[#121622] border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl relative">
        {/* Pill Stepper with Close Button */}
        <WizardStepper
          currentStep={step}
          isEditing={Boolean(editingReportId)}
          onStepClick={(s) => setStep(s)}
          onClose={handleClose}
        />

        {/* Step Header */}
        <div className="mb-6">
          <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
            {editingReportId
              ? `${t.stepper.edit_title} • ${t.stepper.step} ${step} ${t.stepper.of} 5`
              : `${t.stepper.step} ${step} ${t.stepper.of} 5`}
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {editingReportId
              ? `${t.stepper.edit_title}: ${reportName || createdReport?.name || '...'}`
              : (step === 1 && t.step1.title) ||
                (step === 2 && t.step2.title) ||
                (step === 3 && t.step3.title) ||
                (step === 4 && t.step4.title) ||
                t.step5.title}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {step === 1 && t.step1.subtitle}
            {step === 2 && t.step2.subtitle}
            {step === 3 && t.step3.subtitle}
            {step === 4 && t.step4.subtitle}
            {step === 5 && t.step5.subtitle}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: Platform and Delivery Channels */}
        {step === 1 && (
          <div className="space-y-6">
            {/* Platform Selection */}
            <div>
              <div className="text-xs font-semibold text-slate-200 mb-1">{t.step1.platform_heading}</div>
              <p className="text-xs text-slate-400 mb-3">{t.step1.platform_desc}</p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Meta Card (Selected) */}
                <div className="p-4 rounded-xl border-2 border-indigo-600 bg-indigo-950/20 flex flex-col justify-between cursor-pointer transition-all">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
                      ∞
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold">
                      {t.step1.active_badge}
                    </span>
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-white">Meta (Facebook)</div>
                    <div className="text-[10px] text-slate-400">Instagram & FB Ads</div>
                  </div>
                </div>

                {/* Google Ads (Disabled) */}
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 opacity-40 cursor-not-allowed">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-xs">
                      ▲
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-400">
                      {t.step1.soon_badge}
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-slate-300">Google Ads</div>
                </div>

                {/* TikTok (Disabled) */}
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 opacity-40 cursor-not-allowed">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs">
                      ♫
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-400">
                      {t.step1.soon_badge}
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-slate-300">TikTok</div>
                </div>

                {/* Shopify (Disabled) */}
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 opacity-40 cursor-not-allowed">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                      S
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-400">
                      {t.step1.soon_badge}
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-slate-300">Shopify</div>
                </div>
              </div>
            </div>

            {/* Delivery Channels */}
            <div>
              <div className="text-xs font-semibold text-slate-200 mb-1">{t.step1.destinations_heading}</div>
              <p className="text-xs text-slate-400 mb-3">{t.step1.destinations_desc}</p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Telegram Card */}
                <div
                  onClick={() => {
                    setDeliveryChannels(prev =>
                      prev.includes('telegram')
                        ? prev.filter(c => c !== 'telegram')
                        : [...prev, 'telegram']
                    );
                  }}
                  className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                    deliveryChannels.includes('telegram')
                      ? 'border-indigo-600 bg-indigo-950/20 ring-1 ring-indigo-500'
                      : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
                      <Send className="w-4 h-4" />
                    </div>
                    {deliveryChannels.includes('telegram') ? (
                      <span className="w-4 h-4 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px]">
                        ✓
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-semibold">
                        {t.step1.active_badge}
                      </span>
                    )}
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-white">Telegram</div>
                    <div className="text-[10px] text-slate-400">Личка, группа, темы</div>
                  </div>
                </div>

                {/* Google Sheets Card */}
                <div
                  onClick={() => {
                    setDeliveryChannels(prev =>
                      prev.includes('google_sheets')
                        ? prev.filter(c => c !== 'google_sheets')
                        : [...prev, 'google_sheets']
                    );
                  }}
                  className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                    deliveryChannels.includes('google_sheets')
                      ? 'border-indigo-600 bg-indigo-950/20 ring-1 ring-indigo-500'
                      : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                      <FileSpreadsheet className="w-4 h-4" />
                    </div>
                    {deliveryChannels.includes('google_sheets') ? (
                      <span className="w-4 h-4 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px]">
                        ✓
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-semibold">
                        {t.step1.active_badge}
                      </span>
                    )}
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-white">Google Sheets</div>
                    <div className="text-[10px] text-slate-400">Автозапись строк</div>
                  </div>
                </div>

                {/* Slack (Soon) */}
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 opacity-40 cursor-not-allowed">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center text-xs font-bold">
                      #
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-400">
                      {t.step1.soon_badge}
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-slate-300">Slack</div>
                </div>

                {/* WhatsApp (Soon) */}
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 opacity-40 cursor-not-allowed">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-7 h-7 rounded-lg bg-green-500/20 text-green-400 flex items-center justify-center text-xs font-bold">
                      W
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-slate-800 text-slate-400">
                      {t.step1.soon_badge}
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-slate-300">WhatsApp</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Campaigns */}
        {step === 2 && (
          <div className="space-y-6">
            {/* a) Meta Connection Profile or Input */}
            {metaProfile ? (
              <div className="p-4 rounded-xl border border-indigo-500/40 bg-indigo-950/20 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {metaProfile.meta_avatar_url ? (
                    <img
                      src={metaProfile.meta_avatar_url}
                      alt="Profile"
                      className="w-10 h-10 rounded-full border border-indigo-500/50 object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center font-bold text-white">
                      FB
                    </div>
                  )}
                  <div>
                    <div className="font-bold text-xs sm:text-sm text-white">
                      {metaProfile.meta_user_name || 'Meta System User'}
                    </div>
                    <div className="text-[11px] text-slate-400">{t.step2.token_connected_desc}</div>
                  </div>
                </div>
                <button
                  onClick={handleSwitchAccount}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs text-slate-300 hover:text-white transition-colors"
                >
                  {t.step2.token_change_btn}
                </button>
              </div>
            ) : (
              <div className="p-4 rounded-xl border border-slate-800 bg-[#161c2b] space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-200">
                    {t.step2.token_label}
                  </label>
                  <button
                    onClick={onNavigateToTokenGuide}
                    className="text-[11px] text-indigo-400 hover:underline flex items-center space-x-1"
                  >
                    <span>{t.step2.token_help_link}</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>

                <div className="flex gap-2">
                  <input
                    type="password"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder={t.step2.token_placeholder}
                    className="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <button
                    onClick={handleVerifyToken}
                    disabled={verifyingToken || !tokenInput.trim()}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white transition-colors flex items-center space-x-1.5"
                  >
                    {verifyingToken && <RefreshCw className="w-3 h-3 animate-spin" />}
                    <span>{t.step2.token_verify_btn}</span>
                  </button>
                </div>

                {tokenError && (
                  <p className="text-xs text-rose-400 mt-1">{tokenError}</p>
                )}
              </div>
            )}

            {/* b) Ad Account Searchable Dropdown */}
            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                {t.step2.ad_account_label}
              </label>

              <div className="relative">
                <button
                  type="button"
                  onClick={() => setAccountDropdownOpen(!accountDropdownOpen)}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-left text-xs text-slate-200 flex items-center justify-between hover:border-slate-600 transition-colors"
                >
                  <span>
                    {selectedAccount
                      ? `${selectedAccount.name} (${selectedAccount.currency})`
                      : t.step2.ad_account_placeholder}
                  </span>
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </button>

                {accountDropdownOpen && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-[#161c2b] border border-slate-700 rounded-xl shadow-2xl p-2 z-30 max-h-60 overflow-y-auto">
                    {/* Search input inside dropdown */}
                    <div className="relative mb-2">
                      <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                      <input
                        type="text"
                        value={accountSearch}
                        onChange={(e) => setAccountSearch(e.target.value)}
                        placeholder={t.step2.search_account}
                        className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div className="space-y-1">
                      {adAccounts
                        .filter(a =>
                          a.name.toLowerCase().includes(accountSearch.toLowerCase()) ||
                          a.id.toLowerCase().includes(accountSearch.toLowerCase())
                        )
                        .map(acc => (
                          <div
                            key={acc.id}
                            onClick={() => {
                              if (selectedAccount?.id !== acc.id) {
                                setSelectedAccount(acc);
                                setSelectedCampaignIds([]);
                                setIsDirty(true);
                                if (editingReportId && initialAccountIdRef.current && initialAccountIdRef.current !== acc.id) {
                                  setAccountChangedNotice(true);
                                } else {
                                  setAccountChangedNotice(false);
                                }
                              }
                              setAccountDropdownOpen(false);
                            }}
                            className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                              selectedAccount?.id === acc.id
                                ? 'bg-indigo-600/20 text-indigo-300 font-semibold'
                                : 'hover:bg-slate-800 text-slate-200'
                            }`}
                          >
                            <span>{acc.name}</span>
                            <span className="text-[11px] text-slate-400 font-mono">
                              {acc.currency} • {acc.account_id || acc.id}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              {accountChangedNotice && (
                <div className="mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{t.step2.account_changed_notice}</span>
                </div>
              )}
            </div>

            {/* c) Campaign Scope */}
            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                {t.step2.campaign_scope_label}
              </label>

              <select
                value={campaignScope}
                onChange={(e) => setCampaignScope(e.target.value as any)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 mb-3"
              >
                <option value="all">{t.step2.scope_all}</option>
                <option value="filtered">{t.step2.scope_filtered}</option>
                <option value="specific">{t.step2.scope_specific}</option>
              </select>

              {/* Mode 2: Filtered Campaigns */}
              {campaignScope === 'filtered' && (
                <div className="p-4 rounded-xl border border-slate-800 bg-[#161c2b] space-y-4">
                  <p className="text-xs text-slate-400">{t.step2.filter_hint}</p>

                  <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
                    <Check className="w-3.5 h-3.5" />
                    <span>{t.step2.new_campaigns_badge}</span>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-2">
                      {t.step2.goals_label}
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {optimizationGoals.map(g => {
                        const label = language === 'uz' ? g.uz : language === 'en' ? g.en : g.ru;
                        const isChecked = selectedGoals.includes(g.key);
                        return (
                          <label
                            key={g.key}
                            className={`flex items-center space-x-2.5 px-3 py-2 rounded-xl border text-xs cursor-pointer transition-colors ${
                              isChecked
                                ? 'border-indigo-600 bg-indigo-950/20 text-indigo-300'
                                : 'border-slate-800 bg-slate-900/40 text-slate-300 hover:border-slate-700'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {
                                setSelectedGoals(prev =>
                                  prev.includes(g.key) ? prev.filter(k => k !== g.key) : [...prev, g.key]
                                );
                              }}
                              className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                            />
                            <span>{label}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      {t.step2.name_contains_label}
                    </label>
                    <input
                      type="text"
                      value={nameContains}
                      onChange={(e) => setNameContains(e.target.value)}
                      placeholder={t.step2.name_contains_placeholder}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Mode 3: Specific Campaigns */}
              {campaignScope === 'specific' && (
                <div className="p-4 rounded-xl border border-slate-800 bg-[#161c2b] space-y-3">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                    <input
                      type="text"
                      value={campaignSearch}
                      onChange={(e) => setCampaignSearch(e.target.value)}
                      placeholder={t.step2.search_campaigns}
                      className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none"
                    />
                  </div>

                  <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
                    {availableCampaigns.length === 0 ? (
                      <p className="text-xs text-slate-500 text-center py-4">{t.step2.no_campaigns}</p>
                    ) : (
                      availableCampaigns
                        .filter(c => c.name.toLowerCase().includes(campaignSearch.toLowerCase()))
                        .map(c => {
                          const isSelected = selectedCampaignIds.includes(c.id);
                          return (
                            <div
                              key={c.id}
                              onClick={() => {
                                setSelectedCampaignIds(prev =>
                                  prev.includes(c.id) ? prev.filter(id => id !== c.id) : [...prev, c.id]
                                );
                              }}
                              className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer border transition-colors ${
                                isSelected
                                  ? 'border-indigo-600 bg-indigo-950/30 text-indigo-300'
                                  : 'border-slate-800 hover:border-slate-700 text-slate-300'
                              }`}
                            >
                              <div className="flex items-center space-x-2">
                                <div className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[10px] ${isSelected ? 'bg-indigo-600 text-white' : 'border border-slate-700'}`}>
                                  {isSelected && '✓'}
                                </div>
                                <span className="font-medium">{c.name}</span>
                              </div>
                              <span className="text-[10px] text-slate-400 font-mono">{c.status}</span>
                            </div>
                          );
                        })
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 3: Metrics */}
        {step === 3 && (
          <div className="space-y-6">
            {/* 4 Template Cards */}
            <div>
              <div className="text-xs font-semibold text-slate-200 mb-1">{t.step3.templates_heading}</div>
              <p className="text-xs text-slate-400 mb-3">{t.step3.templates_desc}</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                {templates.map(tmpl => {
                  const isSelected = selectedTemplate === tmpl.id;
                  const title = language === 'uz' ? tmpl.title_uz : language === 'en' ? tmpl.title_en : tmpl.title_ru;
                  const desc = language === 'uz' ? tmpl.desc_uz : language === 'en' ? tmpl.desc_en : tmpl.desc_ru;
                  const TemplateIcon = getReportTypeIcon(tmpl.id);

                  return (
                    <div
                      key={tmpl.id}
                      onClick={() => handleSelectTemplate(tmpl)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-950/20 ring-1 ring-indigo-500'
                          : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2.5">
                          <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                            <TemplateIcon className="w-4 h-4" />
                          </div>
                          {tmpl.is_recommended && (
                            <span className="px-2 py-0.5 rounded text-[9px] bg-indigo-600 text-white font-semibold">
                              {t.step3.recommended_badge}
                            </span>
                          )}
                        </div>
                        <div className="font-bold text-xs text-white mb-1">{title}</div>
                        <div className="text-[10px] text-slate-400 leading-tight">{desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Checkbox Grid with 24 Metrics */}
            <div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {metricsList.map(m => {
                  const isChecked = selectedMetrics.includes(m.key);
                  const label = language === 'uz' ? m.uz_label : language === 'en' ? m.en_label : m.ru_label;
                  const tooltip = language === 'uz' ? m.tooltip_uz : language === 'en' ? m.tooltip_en : m.tooltip_ru;

                  return (
                    <div
                      key={m.key}
                      onClick={() => toggleMetric(m.key)}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl border text-xs cursor-pointer select-none transition-all ${
                        isChecked
                          ? 'border-indigo-500 bg-indigo-950/30 text-indigo-300'
                          : 'border-slate-800 bg-slate-900/30 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <div className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[10px] ${isChecked ? 'bg-indigo-600 text-white' : 'border border-slate-700'}`}>
                          {isChecked && '✓'}
                        </div>
                        <span>{label}</span>
                      </div>
                      <div className="relative group/tip" onClick={(e) => e.stopPropagation()}>
                        <Info className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300" />
                        <div className="absolute right-0 bottom-full mb-1 hidden group-hover/tip:block w-48 p-2 rounded-lg bg-slate-900 border border-slate-700 text-[10px] text-slate-300 shadow-xl z-50">
                          {tooltip}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Smart Detection Checkbox */}
            <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-800 bg-slate-900/40 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={smartDetection}
                onChange={() => setSmartDetection(!smartDetection)}
                className="rounded border-slate-700 text-indigo-600 focus:ring-0"
              />
              <span>{t.step3.smart_detection_label}</span>
            </label>

            {/* Labels Customization & Live Preview Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              {/* Left Column: Editable Labels */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-200">{t.step3.labels_heading}</div>
                  <div className="flex items-center space-x-2">
                    <select
                      value={labelsLang}
                      onChange={(e) => {
                        const nl = e.target.value as Language;
                        setLabelsLang(nl);
                        resetMetricLabels(nl);
                      }}
                      className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-700 text-[11px] text-white"
                    >
                      <option value="ru">Русский</option>
                      <option value="uz">Узбекский</option>
                      <option value="en">English</option>
                    </select>
                    <button
                      onClick={() => resetMetricLabels(labelsLang)}
                      className="text-[11px] text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 border border-slate-700"
                    >
                      {t.step3.reset_labels}
                    </button>
                  </div>
                </div>

                <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                  {selectedMetrics.map(key => {
                    const defn = metricsMap[key];
                    return (
                      <div key={key}>
                        <div className="text-[10px] text-slate-400 mb-0.5">{defn?.ru_label || key}</div>
                        <input
                          type="text"
                          value={metricLabels[key] || ''}
                          onChange={(e) => {
                            setMetricLabels({ ...metricLabels, [key]: e.target.value });
                          }}
                          className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                        />
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Live Telegram Message Preview Bubble */}
              <div>
                <PreviewBubble
                  reportName={reportName || selectedAccount?.name || 'Daily Report'}
                  selectedMetrics={selectedMetrics}
                  metricsMap={metricsMap}
                  customLabels={metricLabels}
                  lang={labelsLang}
                  currency={selectedAccount?.currency || 'USD'}
                  periodicity={periodicity}
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Schedule */}
        {step === 4 && (
          <div className="space-y-6">
            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                {t.step4.report_name_label}
              </label>
              <input
                type="text"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder={t.step4.report_name_placeholder}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                {t.step4.periodicity_label}
              </label>
              <select
                value={periodicity}
                onChange={(e) => setPeriodicity(e.target.value as any)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="daily">{t.step4.periodicity_daily}</option>
                <option value="weekly">{t.step4.periodicity_weekly}</option>
                <option value="monthly">{t.step4.periodicity_monthly}</option>
              </select>
            </div>

            {/* Weekly picker */}
            {periodicity === 'weekly' && (
              <div>
                <label className="block text-xs font-semibold text-slate-200 mb-1">
                  {t.step4.weekday_label}
                </label>
                <select
                  value={scheduleWeekday}
                  onChange={(e) => setScheduleWeekday(Number(e.target.value))}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                >
                  {t.step4.weekdays.map((wName, idx) => (
                    <option key={idx} value={idx}>{wName}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Monthly picker */}
            {periodicity === 'monthly' && (
              <div>
                <label className="block text-xs font-semibold text-slate-200 mb-1">
                  {t.step4.monthday_label}
                </label>
                <select
                  value={scheduleMonthday}
                  onChange={(e) => setScheduleMonthday(Number(e.target.value))}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                >
                  {Array.from({ length: 28 }, (_, i) => i + 1).map(day => (
                    <option key={day} value={day}>{day}{t.step4.day_suffix}</option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                {t.step4.time_label}
              </label>
              <input
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none font-mono"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                {t.step4.data_tz_hint.replace('{tz}', selectedAccount?.timezone_name || 'UTC')}
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                {t.step4.send_tz_label}
              </label>
              <select
                value={sendTimezone}
                onChange={(e) => setSendTimezone(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none font-mono"
              >
                <option value="Asia/Tashkent">Asia/Tashkent (UTC+5)</option>
                <option value="Asia/Samarkand">Asia/Samarkand (UTC+5)</option>
                <option value="Asia/Almaty">Asia/Almaty (UTC+5)</option>
                <option value="Europe/Moscow">Europe/Moscow (UTC+3)</option>
                <option value="UTC">UTC (UTC+0)</option>
                <option value="Europe/London">Europe/London (UTC+1)</option>
                <option value="America/New_York">America/New_York (UTC-4)</option>
              </select>
              <p className="text-[11px] text-slate-500 mt-1">{t.step4.send_tz_hint}</p>
            </div>
          </div>
        )}

        {/* STEP 5: Connection */}
        {step === 5 && createdReport && (
          <div className="space-y-6">
            {/* Telegram Destination Card */}
            {deliveryChannels.includes('telegram') && (
              <div className="p-5 rounded-xl border border-slate-800 bg-[#161c2b] space-y-4">
                <div className="flex items-center space-x-2 text-sky-400 font-bold text-sm">
                  <Send className="w-4 h-4" />
                  <span>{t.step5.telegram_title}</span>
                </div>

                {/* Bot username or link error banner */}
                {(telegramDest?.link_error || (botInfo && !botInfo.is_configured && botInfo.error)) && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                    <div>
                      <span className="font-semibold">Ошибка подключения Telegram: </span>
                      <span>{telegramDest?.link_error || botInfo?.error}</span>
                    </div>
                  </div>
                )}

                <div className="text-xs text-slate-400 space-y-1">
                  <p className="text-emerald-400 font-semibold">✓ {t.step5.tg_step1}</p>
                  <p>{t.step5.tg_step2}:</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  {/* Subcard 1: Personal Telegram */}
                  <div className="p-4 rounded-xl border border-slate-700/60 bg-slate-900/60 flex flex-col justify-between">
                    <div>
                      <div className="font-semibold text-xs text-white mb-1">
                        {t.step5.personal_title}
                      </div>
                      <p className="text-xs text-slate-400 mb-4">{t.step5.personal_desc}</p>
                    </div>

                    {telegramDest?.is_connected ? (
                      <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs text-center font-medium">
                        ✓ {t.step5.connected_status || 'Connected'}: {telegramDest.telegram_chat_title || 'Telegram'}
                      </div>
                    ) : (
                      <div className="space-y-1.5">
                        <button
                          type="button"
                          disabled={!telegramDest?.deep_link_personal}
                          onClick={() => {
                            if (telegramDest?.deep_link_personal) {
                              window.open(telegramDest.deep_link_personal, '_blank', 'noreferrer');
                            }
                          }}
                          className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-white text-center transition-colors block"
                        >
                          {t.step5.personal_btn}
                        </button>
                        {!telegramDest?.deep_link_personal && (
                          <p className="text-[11px] text-rose-400 text-center">
                            {telegramDest?.link_error || botInfo?.error || 'Ссылка недоступна: имя бота или код некорректны.'}
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Subcard 2: Group / Channel */}
                  <div className="p-4 rounded-xl border border-slate-700/60 bg-slate-900/60 flex flex-col justify-between">
                    <div>
                      <div className="font-semibold text-xs text-white mb-1">
                        {t.step5.group_title}
                      </div>
                      <p className="text-xs text-slate-400 mb-2">{t.step5.group_desc}</p>
                      <div className="text-[11px] text-slate-300 space-y-1 mb-3">
                        <p>{t.step5.group_inst1}</p>
                        <p>{t.step5.group_inst2}</p>
                        <p>
                          {t.step5.group_inst3}{' '}
                          <code className="bg-black/40 px-1.5 py-0.5 rounded text-indigo-300 font-mono">
                            /link {telegramDest?.one_time_code}
                          </code>
                        </p>
                        <p className="text-slate-500 italic">{t.step5.group_topic_hint}</p>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <button
                        type="button"
                        disabled={!telegramDest?.deep_link_group}
                        onClick={() => {
                          if (telegramDest?.deep_link_group) {
                            window.open(telegramDest.deep_link_group, '_blank', 'noreferrer');
                          }
                        }}
                        className="w-full py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-slate-200 text-center transition-colors block"
                      >
                        {t.step5.group_btn}
                      </button>
                      {!telegramDest?.deep_link_group && (
                        <p className="text-[11px] text-rose-400 text-center">
                          {telegramDest?.link_error || botInfo?.error || 'Ссылка недоступна.'}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Google Sheets Destination Card */}
            {deliveryChannels.includes('google_sheets') && (
              <div className="p-5 rounded-xl border border-slate-800 bg-[#161c2b] space-y-4">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm">
                  <FileSpreadsheet className="w-4 h-4" />
                  <span>{t.step5.sheets_title}</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-2">
                  <div className="text-slate-400">{t.step5.service_email_label}</div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-black/40 border border-slate-700 font-mono text-indigo-300 text-[11px]">
                    <span className="truncate">{serviceAccountEmail}</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(serviceAccountEmail);
                        setCopySuccess(true);
                        setTimeout(() => setCopySuccess(false), 2000);
                      }}
                      className="ml-2 flex items-center space-x-1 text-slate-400 hover:text-white"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      <span>{copySuccess ? t.step5.copied : t.step5.copy_email}</span>
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-400">{t.step5.sheets_instruction}</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      {t.step5.sheets_url_label}
                    </label>
                    <input
                      type="text"
                      value={sheetsUrl}
                      onChange={(e) => setSheetsUrl(e.target.value)}
                      placeholder={t.step5.sheets_url_placeholder}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      {t.step5.sheets_tab_label}
                    </label>
                    <input
                      type="text"
                      value={sheetsTabName}
                      onChange={(e) => setSheetsTabName(e.target.value)}
                      placeholder={t.step5.sheets_tab_placeholder}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleVerifySheets}
                    className="px-4 py-2 rounded-xl bg-emerald-600/80 hover:bg-emerald-600 text-xs font-semibold text-white transition-colors"
                  >
                    {t.step5.verify_sheets_btn}
                  </button>
                  {sheetsVerifyStatus && (
                    <span className="text-xs text-slate-300">{sheetsVerifyStatus}</span>
                  )}
                </div>
              </div>
            )}

            {/* Status & Test Send Action Bar */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleRefreshDestinations}
                    className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 flex items-center space-x-1.5 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>{t.step5.refresh_status_btn}</span>
                  </button>

                  <button
                    onClick={handleTestSend}
                    disabled={testSending}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white flex items-center space-x-1.5 transition-colors"
                  >
                    {testSending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    <span>{t.step5.test_report_btn}</span>
                  </button>
                </div>

                <div className="text-right text-[11px] text-slate-400 font-mono">
                  <div>
                    {t.step5.first_run_label}{' '}
                    <span className="text-indigo-400 font-semibold">
                      {createdReport.next_run_at ? new Date(createdReport.next_run_at).toLocaleString() : 'завтра'}
                    </span>
                  </div>
                  <div>
                    {t.step5.report_id_label} <span>{createdReport.id}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer Navigation Buttons (Назад / Далее) */}
        <div className="flex items-center justify-between pt-6 border-t border-slate-800/80 mt-6">
          {step > 1 && step < 5 ? (
            <button
              onClick={() => setStep(prev => prev - 1)}
              className="px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-300 transition-colors flex items-center space-x-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{t.stepper.back}</span>
            </button>
          ) : (
            <div></div>
          )}

          {step === 1 && (
            <button
              onClick={() => setStep(2)}
              disabled={!canGoNextFromStep1}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-semibold text-white transition-colors flex items-center space-x-1.5 ml-auto"
            >
              <span>{t.stepper.next}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {step === 2 && (
            <button
              onClick={() => setStep(3)}
              disabled={!canGoNextFromStep2}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-semibold text-white transition-colors flex items-center space-x-1.5"
            >
              <span>{t.stepper.next}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {step === 3 && (
            <button
              onClick={() => setStep(4)}
              disabled={!canGoNextFromStep3}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-semibold text-white transition-colors flex items-center space-x-1.5"
            >
              <span>{t.stepper.next}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {step === 4 && (
            <button
              onClick={handleSaveReport}
              disabled={loading || !canSaveFromStep4}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-semibold text-white transition-colors flex items-center space-x-1.5"
            >
              {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
              <span>{editingReportId ? t.stepper.save_changes : t.stepper.save_and_continue}</span>
            </button>
          )}

          {step === 5 && (
            <button
              onClick={onFinish}
              className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors flex items-center space-x-1.5 ml-auto"
            >
              <span>{t.stepper.finish}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
