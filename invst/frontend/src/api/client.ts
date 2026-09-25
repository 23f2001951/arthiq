import {
  DashboardResponse,
  RecommendationsResponse,
  QuickPicksResponse,
  BacktestRunRequest,
  BacktestRunResponse,
  BacktestHistoryItem,
  HealthResponse,
  UniverseResponse,
  ModelStatusResponse,
  ModelTrainRequest,
  ModelTrainResponse,
  EmailLookupResponse,
  SetPasswordResponse,
  UserProfile,
  AdminSummaryResponse,
  AdminCreateUserRequest,
  ChangePasswordRequest,
  ChangePasswordResponse,
  UpdateProfileRequest,
} from '../types/api';

const API_HOST = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') || '';
const BASE_URL = `${API_HOST}/api`;
const TOKEN_KEY = 'arth_iq_session_token';
const ROLE_KEY = 'arth_iq_user_role';
const EMAIL_KEY = 'arth_iq_user_email';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {}
}

export function getUserRole(): 'admin' | 'user' {
  try {
    return (localStorage.getItem(ROLE_KEY) as 'admin' | 'user') || 'user';
  } catch {
    return 'user';
  }
}

export function setUserRole(role: string): void {
  try {
    localStorage.setItem(ROLE_KEY, role);
  } catch {}
}

export function getUserEmail(): string {
  try {
    return localStorage.getItem(EMAIL_KEY) || '';
  } catch {
    return '';
  }
}

export function setUserEmail(email: string): void {
  try {
    localStorage.setItem(EMAIL_KEY, email);
  } catch {}
}

export function clearAuthToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(EMAIL_KEY);
  } catch {}
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Wrapper around standard fetch to provide informative messages when network/connection errors occur.
 */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err: any) {
    if (err?.name === 'TypeError' || err?.message === 'Failed to fetch' || err?.message?.includes('NetworkError')) {
      throw new Error('Unable to connect to the Arth IQ backend server. Please verify the backend is running and accessible.');
    }
    throw err;
  }
}

/**
 * Safely extract a clean, human-readable error string from an API response payload or JavaScript error.
 */
export function formatErrorDetail(errorPayload: any, fallbackMessage: string): string {
  if (!errorPayload) return fallbackMessage;

  if (typeof errorPayload === 'string') {
    const trimmed = errorPayload.trim();
    if (trimmed.toLowerCase() === 'internal server error') {
      return 'The server encountered an unexpected error. Please check backend logs or try again.';
    }
    return trimmed || fallbackMessage;
  }

  const detail = errorPayload.detail !== undefined ? errorPayload.detail : (errorPayload.message || errorPayload.error);

  if (typeof detail === 'string') {
    const trimmed = detail.trim();
    if (trimmed.toLowerCase() === 'internal server error') {
      return 'The server encountered an unexpected error. Please check backend logs or try again.';
    }
    return trimmed || fallbackMessage;
  }

  // Handle FastAPI validation error array: [{ loc: [...], msg: "...", type: "..." }]
  if (Array.isArray(detail)) {
    const messages = detail.map((err) => {
      if (typeof err === 'string') return err;
      if (err && typeof err === 'object') {
        const field = Array.isArray(err.loc) ? err.loc.filter((l: any) => l !== 'body').join('.') : '';
        const msg = err.msg || err.message || JSON.stringify(err);
        return field ? `${field}: ${msg}` : msg;
      }
      return String(err);
    });
    if (messages.length > 0) {
      return messages.join('; ');
    }
  }

  if (typeof detail === 'object' && detail !== null) {
    if (detail.msg) return String(detail.msg);
    if (detail.message) return String(detail.message);
    try {
      return JSON.stringify(detail);
    } catch {
      return fallbackMessage;
    }
  }

  return fallbackMessage;
}

async function handleResponse<T>(res: Response, fallbackError: string): Promise<T> {
  if (res.status === 401) {
    const errorData = await res.json().catch(() => null);
    const specificMessage = formatErrorDetail(errorData, 'Unauthorized session');
    clearAuthToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('arth:unauthorized'));
    }
    throw new Error(specificMessage);
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const msg = formatErrorDetail(errorData, res.statusText || fallbackError);
    throw new Error(msg);
  }
  return res.json();
}

export async function lookupEmail(email: string): Promise<EmailLookupResponse> {
  const res = await apiFetch(`${BASE_URL}/auth/lookup-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return handleResponse<EmailLookupResponse>(res, 'Email lookup failed');
}

export async function setPassword(email: string, password: string): Promise<SetPasswordResponse> {
  const res = await apiFetch(`${BASE_URL}/auth/set-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(formatErrorDetail(err, res.statusText || 'Failed to set password'));
  }
  const data: SetPasswordResponse = await res.json();
  if (data.token) {
    setAuthToken(data.token);
    setUserRole(data.role || 'user');
    setUserEmail(data.email || email);
  }
  return data;
}

export async function loginWithEmail(
  email: string,
  password: string
): Promise<{ success: boolean; role?: string; email?: string; error?: string }> {
  try {
    const res = await apiFetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      const detailStr = formatErrorDetail(err, res.statusText || 'Authentication failed');
      return { success: false, error: detailStr };
    }
    const data = await res.json();
    if (data.token) {
      setAuthToken(data.token);
      setUserRole(data.role || 'user');
      setUserEmail(data.email || email);
      return { success: true, role: data.role, email: data.email };
    }
    return { success: false, error: 'Authentication succeeded but no token was returned' };
  } catch (err: any) {
    return { success: false, error: err.message || 'Network error occurred during login' };
  }
}

export async function login(password: string): Promise<{ success: boolean; role?: string; error?: string }> {
  try {
    const res = await apiFetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      const detailStr = formatErrorDetail(err, res.statusText || 'Incorrect password');
      return { success: false, error: detailStr };
    }
    const data = await res.json();
    if (data.token) {
      setAuthToken(data.token);
      setUserRole(data.role || 'admin');
      setUserEmail(data.email || 'admin@arth.iq');
      return { success: true, role: data.role };
    }
    return { success: false, error: 'Authentication succeeded but no token was returned' };
  } catch (err: any) {
    return { success: false, error: err.message || 'Network error occurred during login' };
  }
}

export async function verifyAuth(): Promise<boolean> {
  const token = getAuthToken();
  if (!token) return false;
  try {
    const res = await apiFetch(`${BASE_URL}/auth/verify`, {
      headers: { ...authHeaders() },
    });
    if (!res.ok) {
      clearAuthToken();
      return false;
    }
    const data = await res.json();
    if (!data.authenticated) {
      clearAuthToken();
      return false;
    }
    if (data.role) {
      setUserRole(data.role);
    }
    if (data.email) {
      setUserEmail(data.email);
    }
    return true;
  } catch {
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await apiFetch(`${BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { ...authHeaders() },
    });
  } catch {}
  clearAuthToken();
}

export async function fetchCurrentUserProfile(): Promise<UserProfile> {
  const res = await apiFetch(`${BASE_URL}/auth/me`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<UserProfile>(res, 'Failed to fetch user profile');
}

export async function changePassword(payload: ChangePasswordRequest): Promise<ChangePasswordResponse> {
  const res = await apiFetch(`${BASE_URL}/auth/change-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse<ChangePasswordResponse>(res, 'Failed to update password');
}

export async function updateProfile(payload: UpdateProfileRequest): Promise<UserProfile> {
  const res = await apiFetch(`${BASE_URL}/auth/profile`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse<UserProfile>(res, 'Failed to update profile');
}

// -------------------------------------------------------------------------
// Admin API Methods
// -------------------------------------------------------------------------
export async function fetchAdminSummary(): Promise<AdminSummaryResponse> {
  const res = await apiFetch(`${BASE_URL}/admin/summary`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<AdminSummaryResponse>(res, 'Failed to fetch admin summary');
}

export async function fetchAdminUsers(): Promise<UserProfile[]> {
  const res = await apiFetch(`${BASE_URL}/admin/users`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<UserProfile[]>(res, 'Failed to fetch users');
}

export async function registerAdminUser(payload: AdminCreateUserRequest): Promise<UserProfile> {
  const res = await apiFetch(`${BASE_URL}/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse<UserProfile>(res, 'Failed to register new investor');
}

export async function updateAdminUserStatus(userId: number, status: string): Promise<UserProfile> {
  const res = await apiFetch(`${BASE_URL}/admin/users/${userId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ status }),
  });
  return handleResponse<UserProfile>(res, 'Failed to update user status');
}

export async function deleteAdminUser(userId: number): Promise<void> {
  const res = await apiFetch(`${BASE_URL}/admin/users/${userId}`, {
    method: 'DELETE',
    headers: { ...authHeaders() },
  });
  return handleResponse<void>(res, 'Failed to delete user');
}


export async function fetchDashboard(): Promise<DashboardResponse> {
  const res = await apiFetch(`${BASE_URL}/dashboard`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<DashboardResponse>(res, 'Dashboard request failed');
}

export async function fetchRecommendations(asof?: string, topN: number = 8): Promise<RecommendationsResponse> {
  const params = new URLSearchParams();
  if (asof) params.append('asof', asof);
  params.append('top_n', topN.toString());

  const res = await apiFetch(`${BASE_URL}/recommendations?${params.toString()}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<RecommendationsResponse>(res, 'Recommendations request failed');
}

export async function fetchQuickPicks(
  n: number = 2,
  asof?: string,
  excludeHoldings: boolean = true,
  horizonDays: number = 90
): Promise<QuickPicksResponse> {
  const params = new URLSearchParams();
  params.append('n', n.toString());
  if (asof) params.append('asof', asof);
  params.append('exclude_holdings', excludeHoldings ? 'true' : 'false');
  params.append('horizon_days', horizonDays.toString());

  const res = await apiFetch(`${BASE_URL}/recommendations/picks?${params.toString()}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<QuickPicksResponse>(res, 'Quick picks request failed');
}

export async function fetchModelStatus(): Promise<ModelStatusResponse> {
  const res = await apiFetch(`${BASE_URL}/ml/status`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<ModelStatusResponse>(res, 'Fetch model status failed');
}

export async function trainModel(req: ModelTrainRequest): Promise<ModelTrainResponse> {
  const res = await apiFetch(`${BASE_URL}/ml/train`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(req),
  });
  return handleResponse<ModelTrainResponse>(res, 'Model training failed');
}

export async function runBacktest(req: BacktestRunRequest): Promise<BacktestRunResponse> {
  const res = await apiFetch(`${BASE_URL}/backtest/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(req),
  });
  return handleResponse<BacktestRunResponse>(res, 'Backtest execution failed');
}

export async function fetchBacktestRuns(): Promise<BacktestHistoryItem[]> {
  const res = await apiFetch(`${BASE_URL}/backtest/runs`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<BacktestHistoryItem[]>(res, 'Backtest history request failed');
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await apiFetch(`${BASE_URL}/health`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<HealthResponse>(res, 'Health status request failed');
}

export async function fetchUniverse(asof?: string): Promise<UniverseResponse> {
  const params = new URLSearchParams();
  if (asof) params.append('asof', asof);
  const res = await apiFetch(`${BASE_URL}/universe?${params.toString()}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<UniverseResponse>(res, 'Universe query failed');
}

export async function fetchMacroPulse(fetchLive: boolean = true): Promise<import('../types/api').MacroPulseResponse> {
  const res = await apiFetch(`${BASE_URL}/v2/macro/pulse?fetch_live=${fetchLive ? 'true' : 'false'}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').MacroPulseResponse>(res, 'Macro pulse query failed');
}

export async function analyzeStock(symbol: string, fetchLive: boolean = true): Promise<import('../types/api').FullStockAnalysisResponse> {
  const clean = encodeURIComponent(symbol.trim().toUpperCase());
  const res = await apiFetch(`${BASE_URL}/v2/analyze/${clean}?fetch_live=${fetchLive ? 'true' : 'false'}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').FullStockAnalysisResponse>(res, `Stock analysis failed for ${symbol}`);
}

export async function fetchPortfolioHoldings(): Promise<import('../types/api').UserHoldingItem[]> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolio/holdings`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').UserHoldingItem[]>(res, 'Failed to fetch portfolio holdings');
}

export async function savePortfolioHoldings(
  holdings: import('../types/api').UserHoldingItem[],
  portfolioId?: string,
): Promise<{ status: string; count: number }> {
  const targetId = portfolioId || 'default';
  await updatePortfolio(targetId, { holdings });
  return { status: 'success', count: holdings.length };
}

export async function evaluatePortfolioHealth(
  holdings: import('../types/api').UserHoldingItem[],
  fetchLive: boolean = true,
): Promise<import('../types/api').PortfolioHealthResponse> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolio/health?fetch_live=${fetchLive ? 'true' : 'false'}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ holdings }),
  });
  return handleResponse<import('../types/api').PortfolioHealthResponse>(res, 'Failed to evaluate portfolio health');
}

export async function fetchPortfolios(portfolioType?: string): Promise<import('../types/api').PortfolioSummary[]> {
  const url = portfolioType
    ? `${BASE_URL}/v2/portfolios?portfolio_type=${encodeURIComponent(portfolioType)}`
    : `${BASE_URL}/v2/portfolios`;
  const res = await apiFetch(url, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').PortfolioSummary[]>(res, 'Failed to fetch portfolios');
}

export async function fetchPortfolio(portfolioId: string): Promise<import('../types/api').PortfolioDetail> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').PortfolioDetail>(res, `Failed to fetch portfolio ${portfolioId}`);
}

export async function createPortfolio(data: import('../types/api').CreatePortfolioRequest): Promise<import('../types/api').PortfolioDetail> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolios`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(data),
  });
  return handleResponse<import('../types/api').PortfolioDetail>(res, 'Failed to create portfolio');
}

export async function updatePortfolio(
  portfolioId: string,
  data: import('../types/api').UpdatePortfolioRequest,
): Promise<import('../types/api').PortfolioDetail> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(data),
  });
  return handleResponse<import('../types/api').PortfolioDetail>(res, `Failed to update portfolio ${portfolioId}`);
}

export async function deletePortfolio(portfolioId: string): Promise<{ status: string; portfolio_id: string }> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}`, {
    method: 'DELETE',
    headers: { ...authHeaders() },
  });
  return handleResponse<{ status: string; portfolio_id: string }>(res, `Failed to delete portfolio ${portfolioId}`);
}

export async function addStockToPortfolio(
  portfolioId: string,
  data: import('../types/api').AddStockToPortfolioRequest,
): Promise<{ status: string; symbol: string; portfolio_id: string }> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}/holdings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(data),
  });
  return handleResponse<{ status: string; symbol: string; portfolio_id: string }>(res, `Failed to add ${data.symbol} to portfolio`);
}

export async function removeStockFromPortfolio(
  portfolioId: string,
  symbol: string,
): Promise<{ status: string; symbol: string; portfolio_id: string }> {
  const res = await apiFetch(
    `${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}/holdings/${encodeURIComponent(symbol)}`,
    {
      method: 'DELETE',
      headers: { ...authHeaders() },
    },
  );
  return handleResponse<{ status: string; symbol: string; portfolio_id: string }>(res, `Failed to remove ${symbol} from portfolio`);
}

export async function evaluatePortfolioHealthById(
  portfolioId: string,
  fetchLive: boolean = true,
): Promise<import('../types/api').PortfolioHealthResponse> {
  const res = await apiFetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}/health?fetch_live=${fetchLive ? 'true' : 'false'}`, {
    method: 'POST',
    headers: {
      ...authHeaders(),
    },
  });
  return handleResponse<import('../types/api').PortfolioHealthResponse>(res, `Failed to evaluate health for portfolio ${portfolioId}`);
}

export async function moveStockBetweenPortfolios(
  sourceId: string,
  destId: string,
  data: import('../types/api').AddStockToPortfolioRequest,
): Promise<void> {
  await addStockToPortfolio(destId, data);
  await removeStockFromPortfolio(sourceId, data.symbol);
}

export async function fetchMarketTickerTape(): Promise<import('../types/api').TickerItem[]> {
  const res = await apiFetch(`${BASE_URL}/v2/market/ticker-tape`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').TickerItem[]>(res, 'Failed to fetch ticker tape');
}



