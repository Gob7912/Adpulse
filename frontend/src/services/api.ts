import {
  User,
  MetaProfile,
  MetaAdAccount,
  MetaCampaign,
  Report,
  RunHistory,
  Destination,
  TelegramBotInfoResponse
} from '../types';

const API_BASE = '/api';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('adpulse_jwt');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('adpulse_jwt', token);
    } else {
      localStorage.removeItem('adpulse_jwt');
    }
  }

  getToken() {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // Support HTTP-only cookies
    });

    if (!response.ok) {
      let errorMsg = `Request failed: ${response.statusText}`;
      try {
        const data = await response.json();
        errorMsg = data.detail || data.message || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    return response.json();
  }

  // Auth
  async register(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await this.request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } finally {
      this.setToken(null);
    }
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async deleteAccount(): Promise<void> {
    await this.request('/auth/me', { method: 'DELETE' });
    this.setToken(null);
  }

  // Meta
  async getMetadata(): Promise<{
    metrics: any[];
    templates: any[];
    optimization_goals: { key: string; ru: string; uz: string; en: string }[];
  }> {
    return this.request('/meta/metadata');
  }

  async verifyToken(accessToken: string): Promise<MetaProfile> {
    return this.request<MetaProfile>('/meta/verify-token', {
      method: 'POST',
      body: JSON.stringify({ access_token: accessToken }),
    });
  }

  async getMetaProfile(): Promise<MetaProfile> {
    return this.request<MetaProfile>('/meta/profile');
  }

  async disconnectMeta(): Promise<void> {
    await this.request('/meta/connection', { method: 'DELETE' });
  }

  async getAdAccounts(): Promise<MetaAdAccount[]> {
    return this.request<MetaAdAccount[]>('/meta/adaccounts');
  }

  async getCampaigns(adAccountId: string): Promise<MetaCampaign[]> {
    return this.request<MetaCampaign[]>(`/meta/campaigns?ad_account_id=${encodeURIComponent(adAccountId)}`);
  }

  // Reports
  async listReports(): Promise<Report[]> {
    return this.request<Report[]>('/reports');
  }

  async createReport(data: any): Promise<Report> {
    return this.request<Report>('/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/reports/${reportId}`);
  }

  async updateReport(reportId: string, data: any): Promise<Report> {
    return this.request<Report>(`/reports/${reportId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteReport(reportId: string): Promise<void> {
    await this.request(`/reports/${reportId}`, { method: 'DELETE' });
  }

  async pauseReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/reports/${reportId}/pause`, { method: 'POST' });
  }

  async resumeReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/reports/${reportId}/resume`, { method: 'POST' });
  }

  async duplicateReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/reports/${reportId}/duplicate`, { method: 'POST' });
  }

  async triggerTestSend(reportId: string): Promise<any> {
    return this.request(`/reports/${reportId}/test-send`, { method: 'POST' });
  }

  async generateLivePreview(data: {
    metrics: string[];
    metric_labels?: Record<string, string>;
    lang?: string;
    currency?: string;
    periodicity?: string;
    report_name?: string;
  }): Promise<{ formatted_text: string; sample_values: Record<string, number> }> {
    return this.request('/reports/live-preview', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Destinations & Sheets
  async getTelegramBotInfo(): Promise<TelegramBotInfoResponse> {
    return this.request<TelegramBotInfoResponse>('/destinations/telegram/bot-info');
  }

  async getSheetsServiceInfo(): Promise<{ service_account_email: string | null; is_configured: boolean }> {
    return this.request<{ service_account_email: string | null; is_configured: boolean }>('/destinations/sheets/service-info');
  }

  async verifyGoogleSheet(sheetsUrl: string, sheetsTabName?: string): Promise<{
    success: boolean;
    title?: string;
    tab_name?: string;
    message: string;
    service_account_email?: string;
  }> {
    return this.request('/destinations/sheets/verify', {
      method: 'POST',
      body: JSON.stringify({ sheets_url: sheetsUrl, sheets_tab_name: sheetsTabName }),
    });
  }

  async getDestinationsStatus(reportId: string): Promise<Destination[]> {
    return this.request<Destination[]>(`/destinations/${reportId}/status`);
  }

  // History
  async getRunHistory(): Promise<RunHistory[]> {
    return this.request<RunHistory[]>('/history');
  }

  async getReportHistory(reportId: string): Promise<RunHistory[]> {
    return this.request<RunHistory[]>(`/history/report/${reportId}`);
  }
}

export const api = new ApiClient();
