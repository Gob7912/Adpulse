export type Language = 'ru' | 'uz' | 'en';
export type Theme = 'dark' | 'light';

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  has_meta_connection: boolean;
  is_meta_valid?: boolean;
  meta_user_name?: string | null;
  meta_avatar_url?: string | null;
}

export interface MetaProfile {
  meta_user_id?: string | null;
  meta_user_name?: string | null;
  meta_avatar_url?: string | null;
  is_valid: boolean;
}

export interface MetaAdAccount {
  id: string;
  account_id?: string | null;
  name: string;
  currency: string;
  timezone_name: string;
  account_status: number;
  business_name?: string | null;
}

export interface MetaCampaign {
  id: string;
  name: string;
  objective: string;
  status: string;
  effective_status: string;
}

export interface MetricDefinition {
  key: string;
  category: string;
  is_additive: boolean;
  format_type: 'currency' | 'integer' | 'percent' | 'decimal';
  ru_label: string;
  uz_label: string;
  en_label: string;
  tooltip_ru: string;
  tooltip_uz: string;
  tooltip_en: string;
  is_limited: boolean;
  sample_value: number;
}

export interface TemplateInfo {
  id: string;
  is_recommended: boolean;
  title_ru: string;
  title_uz: string;
  title_en: string;
  desc_ru: string;
  desc_uz: string;
  desc_en: string;
  metrics: string[];
}

export interface Destination {
  id: string;
  report_id: string;
  destination_type: 'telegram' | 'google_sheets';
  is_enabled: boolean;
  telegram_target_type?: 'personal' | 'group_channel' | null;
  telegram_chat_id?: number | null;
  telegram_thread_id?: number | null;
  telegram_chat_title?: string | null;
  one_time_code?: string | null;
  is_connected: boolean;
  sheets_url?: string | null;
  sheets_spreadsheet_id?: string | null;
  sheets_tab_name?: string | null;
  deep_link_personal?: string | null;
  deep_link_group?: string | null;
  bot_username?: string | null;
  link_error?: string | null;
}

export interface TelegramBotInfoResponse {
  bot_username: string | null;
  is_configured: boolean;
  error: string | null;
}

export interface Report {
  id: string;
  user_id: number;
  name: string;
  meta_account_id: string;
  meta_account_name: string;
  currency: string;
  account_timezone: string;
  campaign_scope_type: 'all' | 'filtered' | 'specific';
  campaign_filter_goals: string[];
  campaign_filter_name?: string | null;
  specific_campaign_ids: string[];
  metrics: string[];
  smart_metric_detection: boolean;
  metric_labels: Record<string, string>;
  metric_lang: Language;
  periodicity: 'daily' | 'weekly' | 'monthly';
  schedule_time: string;
  schedule_weekday?: number | null;
  schedule_monthday?: number | null;
  send_timezone: string;
  show_comparison?: boolean;
  is_active: boolean;
  next_run_at?: string | null;
  last_run_at?: string | null;
  last_run_status?: string | null;
  last_run_error?: string | null;
  created_at: string;
  updated_at: string;
  destinations: Destination[];
}

export interface RunHistory {
  id: string;
  report_id: string;
  run_at: string;
  period_type: string;
  period_start: string;
  period_end: string;
  status: 'success' | 'failed' | 'partial' | 'no_data';
  is_test?: boolean;
  duration_seconds: number;
  metrics_data: Record<string, any>;
  telegram_delivered: boolean;
  telegram_error?: string | null;
  sheets_delivered: boolean;
  sheets_error?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface WizardState {
  // Step 1
  platform: 'meta';
  deliveryChannels: ('telegram' | 'google_sheets')[];

  // Step 2
  adAccount: MetaAdAccount | null;
  campaignScopeType: 'all' | 'filtered' | 'specific';
  campaignFilterGoals: string[];
  campaignFilterName: string;
  specificCampaignIds: string[];

  // Step 3
  selectedTemplate: string | null;
  metrics: string[];
  smartMetricDetection: boolean;
  metricLabels: Record<string, string>;
  metricLang: Language;

  // Step 4
  reportName: string;
  periodicity: 'daily' | 'weekly' | 'monthly';
  scheduleTime: string;
  scheduleWeekday: number;
  scheduleMonthday: number;
  sendTimezone: string;
  showComparison: boolean;

  // Step 5 (Created report & destinations)
  createdReport: Report | null;
  sheetsUrl: string;
  sheetsTabName: string;
}
