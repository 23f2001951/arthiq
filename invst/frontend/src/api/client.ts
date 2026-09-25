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
} from '../types/api';

const API_HOST = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') || '';
const BASE_URL = `${API_HOST}/api`;
const TOKEN_KEY = 'arth_iq_session_token';

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

export function clearAuthToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {}
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response, fallbackError: string): Promise<T> {
  if (res.status === 401) {
    clearAuthToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('arth:unauthorized'));
    }
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || fallbackError);
  }
  return res.json();
}

export async function login(password: string): Promise<{ success: boolean; error?: string }> {
  try {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Incorrect password' }));
      return { success: false, error: err.detail || 'Authentication failed' };
    }
    const data = await res.json();
    if (data.token) {
      setAuthToken(data.token);
      return { success: true };
    }
    return { success: false, error: 'No token returned' };
  } catch (err: any) {
    return { success: false, error: err.message || 'Network error' };
  }
}

export async function verifyAuth(): Promise<boolean> {
  const token = getAuthToken();
  if (!token) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/verify`, {
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
    return true;
  } catch {
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { ...authHeaders() },
    });
  } catch {}
  clearAuthToken();
}

export async function fetchDashboard(): Promise<DashboardResponse> {
  const res = await fetch(`${BASE_URL}/dashboard`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<DashboardResponse>(res, 'Dashboard request failed');
}

export async function fetchRecommendations(asof?: string, topN: number = 8): Promise<RecommendationsResponse> {
  const params = new URLSearchParams();
  if (asof) params.append('asof', asof);
  params.append('top_n', topN.toString());

  const res = await fetch(`${BASE_URL}/recommendations?${params.toString()}`, {
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

  const res = await fetch(`${BASE_URL}/recommendations/picks?${params.toString()}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<QuickPicksResponse>(res, 'Quick picks request failed');
}

export async function fetchModelStatus(): Promise<ModelStatusResponse> {
  const res = await fetch(`${BASE_URL}/ml/status`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<ModelStatusResponse>(res, 'Fetch model status failed');
}

export async function trainModel(req: ModelTrainRequest): Promise<ModelTrainResponse> {
  const res = await fetch(`${BASE_URL}/ml/train`, {
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
  const res = await fetch(`${BASE_URL}/backtest/run`, {
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
  const res = await fetch(`${BASE_URL}/backtest/runs`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<BacktestHistoryItem[]>(res, 'Backtest history request failed');
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<HealthResponse>(res, 'Health status request failed');
}

export async function fetchUniverse(asof?: string): Promise<UniverseResponse> {
  const params = new URLSearchParams();
  if (asof) params.append('asof', asof);
  const res = await fetch(`${BASE_URL}/universe?${params.toString()}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<UniverseResponse>(res, 'Universe query failed');
}

export async function fetchMacroPulse(fetchLive: boolean = true): Promise<import('../types/api').MacroPulseResponse> {
  const res = await fetch(`${BASE_URL}/v2/macro/pulse?fetch_live=${fetchLive ? 'true' : 'false'}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').MacroPulseResponse>(res, 'Macro pulse query failed');
}

export async function analyzeStock(symbol: string, fetchLive: boolean = true): Promise<import('../types/api').FullStockAnalysisResponse> {
  const clean = encodeURIComponent(symbol.trim().toUpperCase());
  const res = await fetch(`${BASE_URL}/v2/analyze/${clean}?fetch_live=${fetchLive ? 'true' : 'false'}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').FullStockAnalysisResponse>(res, `Stock analysis failed for ${symbol}`);
}

export async function fetchPortfolioHoldings(): Promise<import('../types/api').UserHoldingItem[]> {
  const res = await fetch(`${BASE_URL}/v2/portfolio/holdings`, {
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
  const res = await fetch(`${BASE_URL}/v2/portfolio/health?fetch_live=${fetchLive ? 'true' : 'false'}`, {
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
  const res = await fetch(url, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').PortfolioSummary[]>(res, 'Failed to fetch portfolios');
}

export async function fetchPortfolio(portfolioId: string): Promise<import('../types/api').PortfolioDetail> {
  const res = await fetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<import('../types/api').PortfolioDetail>(res, `Failed to fetch portfolio ${portfolioId}`);
}

export async function createPortfolio(data: import('../types/api').CreatePortfolioRequest): Promise<import('../types/api').PortfolioDetail> {
  const res = await fetch(`${BASE_URL}/v2/portfolios`, {
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
  const res = await fetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}`, {
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
  const res = await fetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}`, {
    method: 'DELETE',
    headers: { ...authHeaders() },
  });
  return handleResponse<{ status: string; portfolio_id: string }>(res, `Failed to delete portfolio ${portfolioId}`);
}

export async function addStockToPortfolio(
  portfolioId: string,
  data: import('../types/api').AddStockToPortfolioRequest,
): Promise<{ status: string; symbol: string; portfolio_id: string }> {
  const res = await fetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}/holdings`, {
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
  const res = await fetch(
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
  const res = await fetch(`${BASE_URL}/v2/portfolios/${encodeURIComponent(portfolioId)}/health?fetch_live=${fetchLive ? 'true' : 'false'}`, {
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


