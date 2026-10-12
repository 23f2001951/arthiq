import React, { useState, useEffect } from 'react';
import {
  searchMutualFunds,
  fetchMFSchemeDetails,
  fetchMFRollingReturns,
  fetchMFRiskMetrics,
  getMFRecommendations,
  calculateMFSIP,
  fetchMFPortfolio,
  addOrUpdateMFSIP,
  editMFSIP,
  deleteMFSIP,
  resumeMFSIP,
  reallocateMFSIP,
  resetMFPortfolio,
  predictMFPortfolioHealth,
  saveMFPortfolio,
  submitMFSIPCheckin,
  submitMFSIPBatchCheckin,
  calculatePowerAge,
} from '../api/client';
import {
  MFSchemeSearchItem,
  MFSchemeDetailResponse,
  MFRollingReturnsResponse,
  MFRiskMetricsResponse,
  MFRecommendationResponse,
  MFSIPCalculateResponse,
  MFPortfolioResponse,
  MFPortfolioHealthResponse,
  MFPowerAgeResponse,
  MFPowerAgeRequest,
} from '../types/api';
import {
  Search,
  Sliders,
  TrendingUp,
  PieChart,
  ShieldCheck,
  Sparkles,
  ArrowUpRight,
  Coins,
  Layers,
  PlusCircle,
  Clock,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  Pencil,
  Activity,
  Award,
  Check,
  ArrowRightLeft,
  ChevronDown,
  ChevronUp,
  BookmarkCheck,
  Calendar,
  Bell,
  Save,
  XCircle,
  History,
  FileText,
  Scale,
  Play,
  CheckSquare,
  Square,
  Zap,
} from 'lucide-react';
import { MFNavChart } from '../components/mf/MFNavChart';
import { MFRollingReturnsVisualizer } from '../components/mf/MFRollingReturnsVisualizer';
import { MFAssetAllocationDonut } from '../components/mf/MFAssetAllocationDonut';
import { MFWealthTrajectoryChart } from '../components/mf/MFWealthTrajectoryChart';
import { MFFundComparisonBar } from '../components/mf/MFFundComparisonBar';

export interface MutualFundsViewProps {
  initialTab?: 'analyzer' | 'advisor' | 'sip_planner' | 'portfolio' | 'power_age';
  mode?: 'screener' | 'advisor' | 'portfolio' | 'power_age' | 'all';
}

export const MutualFundsView: React.FC<MutualFundsViewProps> = ({
  initialTab,
  mode = 'all',
}) => {
  const getStartingTab = () => {
    if (initialTab) return initialTab;
    if (mode === 'screener') return 'analyzer';
    if (mode === 'advisor') return 'advisor';
    if (mode === 'portfolio') return 'portfolio';
    if (mode === 'power_age') return 'power_age';
    return 'analyzer';
  };

  const [activeTab, setActiveTab] = useState<'analyzer' | 'advisor' | 'sip_planner' | 'portfolio' | 'power_age'>(getStartingTab);
  const [expandedSwitchSipId, setExpandedSwitchSipId] = useState<string | null>(null);

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    } else if (mode === 'screener') {
      setActiveTab('analyzer');
    } else if (mode === 'advisor') {
      setActiveTab('advisor');
    } else if (mode === 'portfolio') {
      setActiveTab('portfolio');
    } else if (mode === 'power_age') {
      setActiveTab('power_age');
    }
  }, [initialTab, mode]);

  // ---------------------------------------------------------------------------
  // 1. Fund Screener & Analyzer State
  // ---------------------------------------------------------------------------
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchResults, setSearchResults] = useState<MFSchemeSearchItem[]>([]);
  const [selectedSchemeCode, setSelectedSchemeCode] = useState<number>(122639);
  const [schemeDetails, setSchemeDetails] = useState<MFSchemeDetailResponse | null>(null);
  const [rollingReturns, setRollingReturns] = useState<MFRollingReturnsResponse | null>(null);
  const [rollingWindow, setRollingWindow] = useState<number>(3);
  const [riskMetrics, setRiskMetrics] = useState<MFRiskMetricsResponse | null>(null);
  const riskMetricsTrustworthy = Boolean(riskMetrics && riskMetrics.volatility >= 1 && Math.abs(riskMetrics.sharpe_ratio) <= 5 && Math.abs(riskMetrics.sortino_ratio) <= 5);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [minRating, setMinRating] = useState<number>(0);
  const [maxExpenseRatio, setMaxExpenseRatio] = useState<number>(0);
  const [minAumCr, setMinAumCr] = useState<number>(0);
  const [sortBy, setSortBy] = useState<'rating_high' | 'expense_low' | 'aum_high' | 'name'>('rating_high');

  const displayedFunds = React.useMemo(() => {
    let list = [...searchResults];
    if (minRating > 0) {
      list = list.filter((f) => f.crisil_rating != null && f.crisil_rating >= minRating);
    }
    if (maxExpenseRatio > 0) {
      list = list.filter((f) => f.expense_ratio != null && f.expense_ratio <= maxExpenseRatio);
    }
    if (minAumCr > 0) {
      list = list.filter((f) => (f.aum_cr || 0) >= minAumCr);
    }
    list.sort((a, b) => {
      if (sortBy === 'rating_high') {
        return (b.crisil_rating ?? -1) - (a.crisil_rating ?? -1);
      }
      if (sortBy === 'expense_low') {
        return (a.expense_ratio ?? Number.POSITIVE_INFINITY) - (b.expense_ratio ?? Number.POSITIVE_INFINITY);
      }
      if (sortBy === 'aum_high') {
        return (b.aum_cr || 0) - (a.aum_cr || 0);
      }
      return a.scheme_name.localeCompare(b.scheme_name);
    });
    return list;
  }, [searchResults, minRating, maxExpenseRatio, minAumCr, sortBy]);

  // ---------------------------------------------------------------------------
  // 2. Goal & Recommendation Advisor State
  // ---------------------------------------------------------------------------
  const [riskProfile, setRiskProfile] = useState<'CONSERVATIVE' | 'MODERATE' | 'GROWTH' | 'AGGRESSIVE'>('GROWTH');
  const [horizonYears, setHorizonYears] = useState<number>(7);
  const [goalType, setGoalType] = useState<string>('WEALTH_CREATION');
  const [monthlyBudget, setMonthlyBudget] = useState<number>(25000);
  const [advisorStepUp, setAdvisorStepUp] = useState<number>(10);
  const [advisorResult, setAdvisorResult] = useState<MFRecommendationResponse | null>(null);
  const [isGeneratingAdvisor, setIsGeneratingAdvisor] = useState(false);

  // ---------------------------------------------------------------------------
  // 3. SIP Simulator State
  // ---------------------------------------------------------------------------
  const [calcSipAmount, setCalcSipAmount] = useState<number>(15000);
  const [calcCagr, setCalcCagr] = useState<number>(13.5);
  const [calcYears, setCalcYears] = useState<number>(12);
  const [calcStepUp, setCalcStepUp] = useState<number>(10);
  const [calcInflation, setCalcInflation] = useState<number>(6);
  const [sipResult, setSipResult] = useState<MFSIPCalculateResponse | null>(null);

  // ---------------------------------------------------------------------------
  // 4. Portfolio & Active/Closed SIP Diagnostics State
  // ---------------------------------------------------------------------------
  const [portfolioData, setPortfolioData] = useState<MFPortfolioResponse | null>(null);
  const [isLoadingPortfolio, setIsLoadingPortfolio] = useState(false);
  const [showAddSipModal, setShowAddSipModal] = useState(false);
  const [editingSipId, setEditingSipId] = useState<string | null>(null);
  const [newSipScheme, setNewSipScheme] = useState<number>(122639);
  const [selectedSchemeName, setSelectedSchemeName] = useState<string>('Parag Parikh Flexi Cap Fund - Direct Plan - Growth');
  const [modalSearchQuery, setModalSearchQuery] = useState('');
  const [modalSearchResults, setModalSearchResults] = useState<MFSchemeSearchItem[]>([]);
  const [isSearchingModal, setIsSearchingModal] = useState(false);
  const [newSipAmount, setNewSipAmount] = useState<number>(10000);
  const [newSipStartDate, setNewSipStartDate] = useState<string>('2024-01-05');
  const [newSipEndDate, setNewSipEndDate] = useState<string>('');
  const [newSipStatus, setNewSipStatus] = useState<string>('ACTIVE');
  const [newSipStepUp, setNewSipStepUp] = useState<number>(0);
  const [customInvested, setCustomInvested] = useState<string>('');
  const [customCurrentValue, setCustomCurrentValue] = useState<string>('');
  const [newSipDay, setNewSipDay] = useState<number>(5);
  const [skippedMonths, setSkippedMonths] = useState<string[]>([]);
  const [closedSipActiveTab, setClosedSipActiveTab] = useState<Record<string, 'resume' | 'reallocate' | 'let_compound'>>({});
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [actionProcessingId, setActionProcessingId] = useState<string | null>(null);
  const [reallocateSelectedTarget, setReallocateSelectedTarget] = useState<Record<string, number>>({});
  const [reallocateMode, setReallocateMode] = useState<Record<string, 'full_switch' | 'partial_switch' | 'pause_and_redirect'>>({});
  const [resumeCustomAmount, setResumeCustomAmount] = useState<Record<string, number>>({});
  const [resumeCustomDay, setResumeCustomDay] = useState<Record<string, number>>({});
  const [healthResult, setHealthResult] = useState<MFPortfolioHealthResponse | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);
  const [isResettingPortfolio, setIsResettingPortfolio] = useState(false);

  // ---------------------------------------------------------------------------
  // 5. Power Age (FIRE Freedom) Calculator State
  // ---------------------------------------------------------------------------
  const [powerAgeInputAge, setPowerAgeInputAge] = useState<number>(28);
  const [powerAgeInputCorpus, setPowerAgeInputCorpus] = useState<number>(75000);
  const [powerAgeInputSip, setPowerAgeInputSip] = useState<number>(10000);
  const [powerAgeInputStepUp, setPowerAgeInputStepUp] = useState<number>(10);
  const [powerAgeInputCagr, setPowerAgeInputCagr] = useState<number>(13.5);
  const [powerAgeInputExpense, setPowerAgeInputExpense] = useState<number>(50000);
  const [powerAgeInputInflation, setPowerAgeInputInflation] = useState<number>(6);
  const [powerAgeInputSwr, setPowerAgeInputSwr] = useState<number>(5);
  const [powerAgeResult, setPowerAgeResult] = useState<MFPowerAgeResponse | null>(null);
  const [isLoadingPowerAge, setIsLoadingPowerAge] = useState<boolean>(false);
  const [showYearByYearTable, setShowYearByYearTable] = useState<boolean>(false);

  const handleCalculatePowerAge = async (overrideParams?: Partial<MFPowerAgeRequest>) => {
    setIsLoadingPowerAge(true);
    try {
      const res = await calculatePowerAge({
        current_age: overrideParams?.current_age ?? powerAgeInputAge,
        current_corpus: overrideParams?.current_corpus ?? powerAgeInputCorpus,
        monthly_sip: overrideParams?.monthly_sip ?? powerAgeInputSip,
        annual_step_up_pct: overrideParams?.annual_step_up_pct ?? powerAgeInputStepUp,
        expected_cagr_pct: overrideParams?.expected_cagr_pct ?? powerAgeInputCagr,
        target_monthly_expense_today: overrideParams?.target_monthly_expense_today ?? powerAgeInputExpense,
        inflation_pct: overrideParams?.inflation_pct ?? powerAgeInputInflation,
        swr_pct: overrideParams?.swr_pct ?? powerAgeInputSwr,
        max_age: 80,
      });
      setPowerAgeResult(res);
    } catch (err) {
      console.error('Failed to calculate Power Age:', err);
    } finally {
      setIsLoadingPowerAge(false);
    }
  };

  const handleStartDateChange = (val: string) => {
    setNewSipStartDate(val);
    if (val) {
      const parts = val.split('-');
      if (parts.length === 3) {
        const d = parseInt(parts[2], 10);
        if (!isNaN(d) && d >= 1 && d <= 28) {
          setNewSipDay(d);
        }
      }
    }
  };

  const getInstallmentMonths = (startStr: string, endStr?: string) => {
    if (!startStr) return [];
    const parts = startStr.split('-');
    if (parts.length < 3) return [];
    const start = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));

    let end = new Date();
    if (endStr) {
      const endParts = endStr.split('-');
      if (endParts.length === 3) {
        end = new Date(parseInt(endParts[0], 10), parseInt(endParts[1], 10) - 1, parseInt(endParts[2], 10));
      }
    }
    if (isNaN(start.getTime()) || isNaN(end.getTime()) || start > end) return [];

    const months: Array<{ key: string; label: string; dateDisplay: string }> = [];
    const cur = new Date(start.getFullYear(), start.getMonth(), 1);
    const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);
    const day = Math.min(Math.max(1, newSipDay || start.getDate()), 28);

    while (cur <= endMonth) {
      const y = cur.getFullYear();
      const m = String(cur.getMonth() + 1).padStart(2, '0');
      const key = `${y}-${m}`;
      const monthName = cur.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
      months.push({
        key,
        label: monthName,
        dateDisplay: `${day} ${monthName}`,
      });
      cur.setMonth(cur.getMonth() + 1);
    }
    return months;
  };

  const toggleSkippedMonth = (mKey: string) => {
    setSkippedMonths((prev) =>
      prev.includes(mKey) ? prev.filter((k) => k !== mKey) : [...prev, mKey]
    );
  };

  const handleResumeSip = async (sipId: string, defaultAmt: number, defaultDay: number) => {
    setActionProcessingId(sipId);
    try {
      const amt = resumeCustomAmount[sipId] ?? defaultAmt;
      const day = resumeCustomDay[sipId] ?? defaultDay;
      const res = await resumeMFSIP(sipId, { amount: amt, sip_day: day });
      setActionSuccessMessage(res.message || 'SIP schedule successfully resumed');
      setTimeout(() => setActionSuccessMessage(null), 5000);
      await loadPortfolio();
    } catch (err) {
      console.error('Failed to resume SIP', err);
    } finally {
      setActionProcessingId(null);
    }
  };

  const handleReallocateSip = async (
    sipId: string,
    defaultTargetCode: number,
    defaultAmt?: number
  ) => {
    setActionProcessingId(sipId);
    try {
      const targetCode = reallocateSelectedTarget[sipId] ?? defaultTargetCode;
      const mode = reallocateMode[sipId] ?? 'full_switch';
      const res = await reallocateMFSIP(sipId, {
        target_scheme_code: targetCode,
        allocation_mode: mode,
        amount: defaultAmt,
      });
      setActionSuccessMessage(res.message || 'Reallocation executed successfully');
      setTimeout(() => setActionSuccessMessage(null), 5000);
      await loadPortfolio();
    } catch (err) {
      console.error('Failed to reallocate SIP', err);
    } finally {
      setActionProcessingId(null);
    }
  };

  const handleOpenAddModal = () => {
    setEditingSipId(null);
    setNewSipScheme(122639);
    setSelectedSchemeName('Parag Parikh Flexi Cap Fund - Direct Plan - Growth');
    setModalSearchQuery('');
    setNewSipAmount(10000);
    setNewSipStartDate('2024-01-05');
    setNewSipEndDate('');
    setNewSipStatus('ACTIVE');
    setNewSipDay(5);
    setNewSipStepUp(0);
    setCustomInvested('');
    setCustomCurrentValue('');
    setSkippedMonths([]);
    setShowAddSipModal(true);
  };

  const handleOpenEditModal = (sip: any) => {
    setEditingSipId(sip.sip_id);
    setNewSipScheme(sip.scheme_code);
    setSelectedSchemeName(sip.scheme_name);
    setModalSearchQuery(sip.scheme_name);
    setNewSipAmount(sip.monthly_amount);
    setNewSipStartDate(sip.start_date || '');
    setNewSipEndDate(sip.end_date || '');
    setNewSipStatus(sip.status || 'ACTIVE');
    setNewSipDay(sip.sip_day || 5);
    setNewSipStepUp(sip.step_up_pct || 0);
    setCustomInvested(sip.total_invested ? String(sip.total_invested) : '');
    setCustomCurrentValue(sip.current_value ? String(sip.current_value) : '');
    setSkippedMonths(sip.skipped_months && Array.isArray(sip.skipped_months) ? [...sip.skipped_months] : []);
    setShowAddSipModal(true);
  };

  const handleDeleteSip = async (sipId: string, schemeName: string) => {
    if (
      !window.confirm(
        `Are you sure you want to delete "${schemeName}" from your portfolio?\n\nThis will remove only this entry and its associated transactions, leaving all other portfolio holdings intact.`
      )
    ) {
      return;
    }
    setActionProcessingId(sipId);
    try {
      await deleteMFSIP(sipId);
      setActionSuccessMessage(`✓ Successfully removed "${schemeName}" from your portfolio.`);
      setTimeout(() => setActionSuccessMessage(null), 5000);
      await loadPortfolio();
      if (healthResult) {
        handlePredictHealth();
      }
    } catch (err) {
      console.error('Failed to delete SIP', err);
      alert('Could not delete SIP entry. Please try again.');
    } finally {
      setActionProcessingId(null);
    }
  };

  // Save Portfolio and Monthly SIP Check-In States
  const [isSavingPortfolio, setIsSavingPortfolio] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [portfolioName, setPortfolioName] = useState<string>('My Mutual Funds');
  const [portfolioNotes, setPortfolioNotes] = useState<string>('');
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [checkinSubmittingId, setCheckinSubmittingId] = useState<string | null>(null);
  const [checkinFeedback, setCheckinFeedback] = useState<string | null>(null);
  const [showCheckinHistory, setShowCheckinHistory] = useState(false);

  // Initial Data Fetch
  useEffect(() => {
    loadSearchResults();
    loadSchemeDetails(selectedSchemeCode);
    loadPortfolio();
    runSipCalculation();
    handleCalculatePowerAge();
  }, []);

  const loadSearchResults = async (query = '', cat = 'All') => {
    try {
      const res = await searchMutualFunds(query, cat);
      setSearchResults(res);
      if (modalSearchResults.length === 0 && res.length > 0) {
        setModalSearchResults(res);
      }
    } catch (err) {
      console.error('Failed to search mutual funds', err);
    }
  };

  const handleModalSearch = async (q: string) => {
    setModalSearchQuery(q);
    if (!q.trim()) {
      setModalSearchResults(searchResults.slice(0, 20));
      return;
    }
    setIsSearchingModal(true);
    try {
      const res = await searchMutualFunds(q);
      setModalSearchResults(res);
    } catch (err) {
      console.error('Modal scheme search failed', err);
    } finally {
      setIsSearchingModal(false);
    }
  };

  const loadSchemeDetails = async (code: number) => {
    setIsLoadingDetails(true);
    setSelectedSchemeCode(code);
    try {
      const [details, rolling, risk] = await Promise.all([
        fetchMFSchemeDetails(code),
        fetchMFRollingReturns(code, rollingWindow),
        fetchMFRiskMetrics(code),
      ]);
      setSchemeDetails(details);
      setRollingReturns(rolling);
      setRiskMetrics(risk);
    } catch (err) {
      console.error('Failed to load scheme details', err);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleWindowChange = async (w: number) => {
    setRollingWindow(w);
    try {
      const rolling = await fetchMFRollingReturns(selectedSchemeCode, w);
      setRollingReturns(rolling);
    } catch (err) {
      console.error('Failed to update rolling returns', err);
    }
  };

  const handleGenerateRecommendation = async () => {
    setIsGeneratingAdvisor(true);
    try {
      const res = await getMFRecommendations({
        risk_profile: riskProfile,
        horizon_years: horizonYears,
        goal_type: goalType,
        monthly_budget: monthlyBudget,
        step_up_pct: advisorStepUp,
      });
      setAdvisorResult(res);
    } catch (err) {
      console.error('Failed to generate recommendation', err);
    } finally {
      setIsGeneratingAdvisor(false);
    }
  };

  const runSipCalculation = async () => {
    try {
      const res = await calculateMFSIP({
        monthly_sip: calcSipAmount,
        expected_cagr_pct: calcCagr,
        years: calcYears,
        step_up_pct: calcStepUp,
        inflation_pct: calcInflation,
      });
      setSipResult(res);
    } catch (err) {
      console.error('Failed to calculate SIP', err);
    }
  };

  const loadPortfolio = async () => {
    setIsLoadingPortfolio(true);
    try {
      const res = await fetchMFPortfolio();
      setPortfolioData(res);
      if (res.portfolio_name) {
        setPortfolioName(res.portfolio_name);
      }
      if (res.notes) {
        setPortfolioNotes(res.notes);
      }
      const portVal = res.current_value || res.total_portfolio_value || 0;
      const portSip = res.monthly_sip_run_rate || res.total_monthly_sip || 0;
      if (portVal > 0) {
        setPowerAgeInputCorpus(Math.round(portVal));
      }
      if (portSip > 0) {
        setPowerAgeInputSip(Math.round(portSip));
      }
      if (res.power_age_projection) {
        setPowerAgeResult(res.power_age_projection);
      }
    } catch (err) {
      console.error('Failed to load MF portfolio', err);
    } finally {
      setIsLoadingPortfolio(false);
    }
  };

  const handleSavePortfolio = async (name?: string, notes?: string) => {
    setIsSavingPortfolio(true);
    try {
      const finalName = name !== undefined ? name : (portfolioName || 'My Mutual Funds');
      const finalNotes = notes !== undefined ? notes : portfolioNotes;
      const res = await saveMFPortfolio({
        portfolio_name: finalName,
        notes: finalNotes,
      });
      setPortfolioName(res.portfolio_name);
      setPortfolioData((prev) =>
        prev
          ? {
              ...prev,
              portfolio_name: res.portfolio_name,
              last_saved_at: res.last_saved_at,
              notes: finalNotes,
            }
          : null
      );
      const timePart = res.last_saved_at ? res.last_saved_at.split(' ')[1] : 'just now';
      setSaveSuccessMsg(`✓ Portfolio "${res.portfolio_name}" saved to cloud database at ${timePart}.`);
      setShowSaveModal(false);
      setTimeout(() => setSaveSuccessMsg(null), 5000);
    } catch (err) {
      console.error('Failed to save portfolio', err);
      alert('Could not save portfolio to server.');
    } finally {
      setIsSavingPortfolio(false);
    }
  };

  const handleConfirmCheckin = async (
    sip_id: string,
    due_date: string,
    status: 'PAID' | 'SKIPPED',
    amount?: number
  ) => {
    const key = `${sip_id}_${due_date}`;
    setCheckinSubmittingId(key);
    try {
      await submitMFSIPCheckin({
        sip_id,
        due_date,
        status,
        amount,
      });
      setCheckinFeedback(
        status === 'PAID'
          ? `✓ Installment for ${due_date} recorded as PAID. Compounding ledger and personal XIRR updated!`
          : `⚠️ Installment for ${due_date} recorded as SKIPPED. Discipline forensics updated.`
      );
      setTimeout(() => setCheckinFeedback(null), 5000);
      await loadPortfolio();
      if (healthResult) {
        handlePredictHealth();
      }
    } catch (err) {
      console.error('Failed to record SIP check-in', err);
      alert('Failed to update SIP check-in status.');
    } finally {
      setCheckinSubmittingId(null);
    }
  };

  const handleBatchCheckin = async (action: 'MARK_ALL_PAID' | 'MARK_ALL_SKIPPED') => {
    setCheckinSubmittingId('batch');
    try {
      const res = await submitMFSIPBatchCheckin({ action });
      setCheckinFeedback(res.message);
      setTimeout(() => setCheckinFeedback(null), 5000);
      await loadPortfolio();
      if (healthResult) {
        handlePredictHealth();
      }
    } catch (err) {
      console.error('Failed to batch confirm check-ins', err);
    } finally {
      setCheckinSubmittingId(null);
    }
  };

  const handleSaveSip = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        scheme_code: Number(newSipScheme),
        amount: Number(newSipAmount),
        start_date: newSipStartDate,
        end_date: newSipEndDate || null,
        status: newSipStatus,
        sip_day: Number(newSipDay),
        step_up_pct: Number(newSipStepUp),
        custom_invested: customInvested ? Number(customInvested) : null,
        custom_current_value: customCurrentValue ? Number(customCurrentValue) : null,
        skipped_months: skippedMonths,
      };

      if (editingSipId) {
        await editMFSIP(editingSipId, payload);
        setActionSuccessMessage(`✓ Updated holding details for "${selectedSchemeName}".`);
      } else {
        await addOrUpdateMFSIP(payload);
        setActionSuccessMessage(`✓ Added "${selectedSchemeName}" to your portfolio.`);
      }

      setShowAddSipModal(false);
      setEditingSipId(null);
      setCustomInvested('');
      setCustomCurrentValue('');
      setSkippedMonths([]);
      setTimeout(() => setActionSuccessMessage(null), 5000);
      await loadPortfolio();
      if (healthResult) {
        handlePredictHealth();
      }
    } catch (err) {
      console.error('Failed to save SIP schedule', err);
      alert('Could not save SIP schedule. Please check inputs.');
    }
  };

  const handlePredictHealth = async () => {
    setIsLoadingHealth(true);
    try {
      const res = await predictMFPortfolioHealth();
      setHealthResult(res);
    } catch (err) {
      console.error('Failed to predict portfolio health', err);
    } finally {
      setIsLoadingHealth(false);
    }
  };

  const handleResetPortfolio = async () => {
    if (!window.confirm('Are you sure you want to reset your Mutual Fund portfolio to an empty state? All SIP schedules and transaction records will be cleared.')) {
      return;
    }
    setIsResettingPortfolio(true);
    try {
      await resetMFPortfolio();
      setHealthResult(null);
      await loadPortfolio();
    } catch (err) {
      console.error('Failed to reset portfolio', err);
    } finally {
      setIsResettingPortfolio(false);
    }
  };

  const categories = [
    'All',
    'Equity: Flexi Cap',
    'Equity: Large Cap',
    'Equity: Mid Cap',
    'Equity: Small Cap',
    'Equity: ELSS',
    'Equity: Multi Cap',
    'Hybrid: Balanced Advantage',
    'Equity: Index / Passive',
    'Debt: Liquid',
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* --------------------------------------------------------------------- */}
      {/* DYNAMIC TOP HEADER & TAB SECTION BASED ON MODE                        */}
      {/* --------------------------------------------------------------------- */}
      {mode === 'screener' ? (
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold tracking-wider uppercase">
                Intelligence • Quant Screener
              </span>
              <span className="text-[11px] text-slate-500 font-medium">45,000+ Indian Mutual Funds</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Search className="h-6 w-6 text-emerald-400" />
              Fund Screener & Deep Quant Analyzer
            </h1>
            <p className="text-sm text-slate-400">
              Filter, search, and analyze any mutual fund in India with trailing CAGR, rolling return distributions, Sharpe/Alpha ratios, and stock forensics.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('All');
                loadSearchResults('', 'All');
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-all"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Filters
            </button>
          </div>
        </div>
      ) : mode === 'advisor' ? (
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold tracking-wider uppercase">
                Intelligence • Advisory
              </span>
              <span className="text-[11px] text-slate-500 font-medium">Institutional Wealth Architecture</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-amber-400" />
              Smart MF Advisor & Wealth Architect
            </h1>
            <p className="text-sm text-slate-400">
              Seasoned-analyst fund allocations tailored to your financial goals, risk appetite, and monthly SIP budget.
            </p>
          </div>

          {/* Advisor-Only Sub-Tabs */}
          <div className="flex items-center gap-1 rounded-xl bg-slate-900/80 p-1 border border-slate-800">
            <button
              onClick={() => {
                setActiveTab('advisor');
                if (!advisorResult) handleGenerateRecommendation();
              }}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'advisor'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" />
              Goal Discovery Basket
            </button>
            <button
              onClick={() => setActiveTab('sip_planner')}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'sip_planner'
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <TrendingUp className="h-3.5 w-3.5" />
              SIP Simulator
            </button>
          </div>
        </div>
      ) : mode === 'portfolio' ? (
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] font-bold tracking-wider uppercase">
                Portfolio & Risk • MF Holdings
              </span>
              <span className="text-[11px] text-slate-500 font-medium">Active & Stopped SIP Diagnostics</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <PieChart className="h-6 w-6 text-purple-400" />
              Mutual Fund & SIP Portfolio Health
            </h1>
            <p className="text-sm text-slate-400">
              Track actual holdings, active vs stopped SIP post-mortems, portfolio overlap diagnostics, and predictive health.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setActiveTab(activeTab === 'power_age' ? 'portfolio' : 'power_age');
                if (activeTab !== 'power_age' && !powerAgeResult) handleCalculatePowerAge();
              }}
              className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl border transition-all shadow-sm ${
                activeTab === 'power_age'
                  ? 'bg-amber-500/25 text-amber-300 border-amber-500/40 font-bold'
                  : 'bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/20'
              }`}
            >
              <Zap className="h-3.5 w-3.5 text-amber-400" />
              {activeTab === 'power_age' ? 'Back to Portfolio' : '⚡ Power Age (FIRE)'}
            </button>
            <button
              onClick={handlePredictHealth}
              disabled={isLoadingHealth}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 transition-all shadow-sm"
            >
              <Activity className="h-3.5 w-3.5" />
              {isLoadingHealth ? 'Predicting...' : 'Predict Health'}
            </button>
            <button
              onClick={() => setShowAddSipModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-purple-500 hover:bg-purple-600 text-white transition-all shadow-sm"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              Add SIP Schedule
            </button>
            <button
              onClick={handleResetPortfolio}
              disabled={isResettingPortfolio}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-900/50 transition-all"
              title="Clear all schedules and reset to empty state"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              {isResettingPortfolio ? 'Resetting...' : 'Reset'}
            </button>
          </div>
        </div>
      ) : (
        /* Full Unified Fallback */
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Coins className="h-6 w-6 text-emerald-400" />
              Mutual Funds & SIP Engine
            </h1>
            <p className="text-sm text-slate-400">
              Institutional quant fund analysis, intelligent goal-based recommendations, and active/closed SIP diagnostics.
            </p>
          </div>

          <div className="flex items-center gap-1 rounded-xl bg-slate-900/80 p-1 border border-slate-800">
            <button
              onClick={() => setActiveTab('analyzer')}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'analyzer'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Search className="h-3.5 w-3.5" />
              Fund Screener
            </button>
            <button
              onClick={() => {
                setActiveTab('advisor');
                if (!advisorResult) handleGenerateRecommendation();
              }}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'advisor'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" />
              Smart Advisor
            </button>
            <button
              onClick={() => setActiveTab('sip_planner')}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'sip_planner'
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <TrendingUp className="h-3.5 w-3.5" />
              SIP Simulator
            </button>
            <button
              onClick={() => {
                setActiveTab('portfolio');
                loadPortfolio();
              }}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'portfolio'
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <PieChart className="h-3.5 w-3.5" />
              Portfolio & SIP Diagnostics
            </button>
            <button
              onClick={() => {
                setActiveTab('power_age');
                if (!powerAgeResult) handleCalculatePowerAge();
              }}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'power_age'
                  ? 'bg-gradient-to-r from-amber-500/25 to-orange-500/25 text-amber-300 border border-amber-500/40 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="h-3.5 w-3.5 text-amber-400" />
              ⚡ Power Age (FIRE)
            </button>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TAB 1: FUND SCREENER & DEEP ANALYZER                                   */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'analyzer' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Search & Fund List */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-4 space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search any fund or AMC in India (e.g. Tata, SBI, Quant, Axis)..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    loadSearchResults(e.target.value, selectedCategory);
                  }}
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
                />
              </div>

              {/* Category Filter Pills */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => {
                      setSelectedCategory(cat);
                      loadSearchResults(searchQuery, cat);
                    }}
                    className={`px-2.5 py-1 text-[11px] rounded-lg border transition-all ${
                      selectedCategory === cat
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-bold'
                        : 'bg-slate-950/40 text-slate-400 border-slate-800/60 hover:text-slate-300'
                    }`}
                  >
                    {cat.replace('Equity: ', '').replace('Debt: ', '').replace('Hybrid: ', '')}
                  </button>
                ))}
              </div>

              {/* Advanced Screener Controls: Rating, TER, AUM & Sort */}
              <div className="pt-2 border-t border-slate-800/80 space-y-2 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Min Rating</label>
                    <select
                      value={minRating}
                      onChange={(e) => setMinRating(Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    >
                      <option value="0">All Ratings</option>
                      <option value="3">3+ Stars ★★★</option>
                      <option value="4">4+ Stars ★★★★</option>
                      <option value="5">5 Stars Only ★★★★★</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Max TER (Cost)</label>
                    <select
                      value={maxExpenseRatio}
                      onChange={(e) => setMaxExpenseRatio(Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    >
                      <option value="0">Any Expense</option>
                      <option value="0.5">≤ 0.50% (Ultra-Low)</option>
                      <option value="0.8">≤ 0.80%</option>
                      <option value="1.0">≤ 1.00%</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-0.5">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Min AUM</label>
                    <select
                      value={minAumCr}
                      onChange={(e) => setMinAumCr(Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    >
                      <option value="0">Any AUM</option>
                      <option value="1000">&gt; ₹1,000 Cr</option>
                      <option value="5000">&gt; ₹5,000 Cr</option>
                      <option value="10000">&gt; ₹10,000 Cr</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Sort Results</label>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    >
                      <option value="rating_high">Highest Rating</option>
                      <option value="expense_low">Lowest Expense Ratio</option>
                      <option value="aum_high">Highest AUM</option>
                      <option value="name">Scheme Name A-Z</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500">
                  <span>Filtered: <strong className="text-emerald-400">{displayedFunds.length}</strong> of {searchResults.length} schemes</span>
                  {(minRating > 0 || maxExpenseRatio > 0 || minAumCr > 0) && (
                    <button
                      onClick={() => {
                        setMinRating(0);
                        setMaxExpenseRatio(0);
                        setMinAumCr(0);
                      }}
                      className="text-amber-400 hover:text-amber-300 transition-colors"
                    >
                      Clear Filters
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Fund Cards List */}
            <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
              {displayedFunds.length === 0 ? (
                <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800 text-center text-xs text-slate-500">
                  No funds match your current filter settings. Try relaxing the TER or rating criteria.
                </div>
              ) : (
                displayedFunds.map((fund) => {
                  const isSelected = fund.scheme_code === selectedSchemeCode;
                  return (
                    <div
                      key={fund.scheme_code}
                      onClick={() => loadSchemeDetails(fund.scheme_code)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-emerald-500/10 border-emerald-500/40 shadow-sm'
                          : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-800/40 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <h4 className="text-xs font-semibold text-white line-clamp-1">{fund.scheme_name}</h4>
                            {fund.category_rank && (
                              <span
                                className="text-[9px] font-bold px-1.5 py-0.5 rounded border bg-amber-500/10 text-amber-300 border-amber-500/30 whitespace-nowrap"
                                title={fund.category_rank.rank_label}
                              >
                                {fund.category_rank.rank_badge}
                              </span>
                            )}
                            {fund.powerup_form && (
                              <span
                                className={`text-[9px] font-bold px-1.5 py-0.5 rounded border flex items-center gap-0.5 whitespace-nowrap ${
                                  fund.powerup_form.badge === 'IN_FORM'
                                    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                    : fund.powerup_form.badge === 'ON_TRACK'
                                    ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                                    : fund.powerup_form.badge === 'OFF_TRACK'
                                    ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                                    : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                }`}
                              >
                                <span>{fund.powerup_form.badge_emoji}</span>
                                <span>{fund.powerup_form.badge_label}</span>
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400">{fund.fund_house}</p>
                        </div>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 whitespace-nowrap">
                            {fund.crisil_rating != null ? `★ ${fund.crisil_rating}` : 'Rating unavailable'}
                          </span>
                          {fund.current_nav && (
                            <span className="text-[10px] font-bold text-emerald-400">
                              ₹{fund.current_nav.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/60 pt-2">
                        <span className="text-emerald-400 font-medium">{fund.category}</span>
                        <span>TER: <strong className="text-slate-200">{fund.expense_ratio != null ? `${fund.expense_ratio}%` : '—'}</strong></span>
                        <span>AUM: <strong className="text-slate-200">₹{fund.aum_cr ? (fund.aum_cr / 1000).toFixed(1) + 'k' : '—'} Cr</strong></span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column: Deep-Dive Quantitative Analysis */}
          <div className="lg:col-span-8 space-y-6">
            {schemeDetails ? (
              <>
                {/* Header Banner */}
                <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold uppercase tracking-wider">
                          {schemeDetails.category}
                        </span>
                        <span className="text-xs text-slate-400">Direct Plan • Growth</span>
                        {schemeDetails.category_rank && (
                          <span
                            className="px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-bold flex items-center gap-1"
                            title={`${schemeDetails.category_rank.rank_label} • Top ${schemeDetails.category_rank.percentile}% percentile`}
                          >
                            <span>{schemeDetails.category_rank.rank_badge}</span>
                            <span className="text-[9px] opacity-80">({schemeDetails.category_rank.rank_label})</span>
                          </span>
                        )}
                        {schemeDetails.powerup_form && (
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                              schemeDetails.powerup_form.badge === 'IN_FORM'
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                : schemeDetails.powerup_form.badge === 'ON_TRACK'
                                ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                                : schemeDetails.powerup_form.badge === 'OFF_TRACK'
                                ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                                : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                            }`}
                            title={`Power Score: ${schemeDetails.powerup_form.power_score}/100 • ${schemeDetails.powerup_form.momentum_desc}`}
                          >
                            <span>{schemeDetails.powerup_form.badge_emoji}</span>
                            <span>{schemeDetails.powerup_form.badge_label}</span>
                            <span className="text-[9px] opacity-75 font-mono">({schemeDetails.powerup_form.power_score}/100)</span>
                          </span>
                        )}
                        {isLoadingDetails && (
                          <span className="text-[10px] text-amber-400 font-semibold animate-pulse ml-2">
                            • Loading...
                          </span>
                        )}
                      </div>
                      <h2 className="text-xl font-bold text-white mt-1.5">{schemeDetails.scheme_name}</h2>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Manager: <strong className="text-slate-300">{schemeDetails.fund_manager || 'Institutional Team'}</strong> • Benchmark: <strong className="text-slate-300">{schemeDetails.benchmark_index || 'Nifty 500 TRI'}</strong>
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="text-xs text-slate-400">Current NAV ({schemeDetails.latest_nav_date || 'Today'})</p>
                      <p className="text-2xl font-extrabold text-emerald-400 mt-0.5">₹{schemeDetails.current_nav?.toFixed(2) || '—'}</p>
                    </div>
                  </div>

                  {/* Trailing Returns Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 mt-5 border-t border-slate-800/80 pt-4">
                    {Object.entries(schemeDetails.trailing_returns).map(([period, ret]) => (
                      <div key={period} className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/60 text-center">
                        <span className="text-[10px] uppercase font-semibold text-slate-400">{period}</span>
                        <p className={`text-sm font-bold mt-0.5 ${
                          ret === null || ret === undefined
                            ? 'text-slate-500'
                            : ret >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}>
                          {ret !== null && ret !== undefined ? `${(ret * 100).toFixed(1)}%` : '—'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 1. High-Resolution Interactive NAV Time-Series Spline Chart */}
                <MFNavChart
                  schemeCode={schemeDetails.scheme_code}
                  schemeName={schemeDetails.scheme_name}
                  currentNav={schemeDetails.current_nav}
                />

                {/* 2. Fund vs Benchmark Alpha Comparison Bar */}
                <MFFundComparisonBar
                  fundName={schemeDetails.scheme_name}
                  category={schemeDetails.category}
                  benchmarkName={schemeDetails.benchmark_index}
                  trailingReturns={schemeDetails.trailing_returns}
                  expenseRatio={schemeDetails.expense_ratio}
                />

                {/* Seasoned Analyst Conviction & Qualitative Due Diligence Memo */}
                {schemeDetails.analyst_conviction && (
                  <div className="workspace-verdict-card bg-gradient-to-br from-slate-900 via-slate-900/90 to-slate-950 rounded-2xl border border-emerald-500/30 p-5 space-y-4 shadow-xl shadow-emerald-950/10">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                      <div className="flex items-center gap-3">
                        <div className="h-12 w-12 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center font-black text-xl text-emerald-400">
                          {schemeDetails.analyst_conviction.conviction_score}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase border ${
                              schemeDetails.analyst_conviction.conviction_score >= 80
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                                : schemeDetails.analyst_conviction.conviction_score >= 65
                                ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                                : schemeDetails.analyst_conviction.conviction_score >= 50
                                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                                : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                            }`}>
                              {schemeDetails.analyst_conviction.verdict}
                            </span>
                            <span className="text-xs font-semibold text-slate-300">
                              {schemeDetails.analyst_conviction.conviction_badge}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-1">
                            Assigned Portfolio Role: <strong className="text-emerald-400">{schemeDetails.analyst_conviction.portfolio_role}</strong>
                          </p>
                        </div>
                      </div>
                      <div className="text-right text-xs">
                        <span className="text-[10px] uppercase font-bold text-slate-400">Due Diligence Audit</span>
                        <p className="text-emerald-400 font-bold flex items-center justify-end gap-1 mt-0.5">
                          <Award className="h-4 w-4" /> Seasoned Quant Analyst
                        </p>
                      </div>
                    </div>

                    {/* 5 Pillars Breakdown */}
                    {schemeDetails.analyst_conviction.pillars && (
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-1">
                        {Object.entries(schemeDetails.analyst_conviction.pillars).map(([pillarKey, p]: [string, any]) => {
                          const names: Record<string, string> = {
                            alpha_consistency: 'Alpha Consistency',
                            downside_protection: 'Downside Shield',
                            cost_efficiency: 'TER Efficiency',
                            aum_liquidity: 'AUM Sweet-Spot',
                            rating_governance: 'Rating & Rank',
                          };
                          const pct = Math.round((p.score / p.max) * 100);
                          return (
                            <div key={pillarKey} className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/60 space-y-1.5">
                              <div className="flex items-center justify-between text-[10px]">
                                <span className="text-slate-400 font-medium truncate">{names[pillarKey] || pillarKey}</span>
                                <span className="font-bold text-slate-200">{p.score}/{p.max}</span>
                              </div>
                              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    pct >= 80 ? 'bg-emerald-400' : pct >= 60 ? 'bg-sky-400' : pct >= 40 ? 'bg-amber-400' : 'bg-rose-400'
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Analyst Bull Case & Bear Risks Memo */}
                    {schemeDetails.analyst_conviction.analyst_memo && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                        <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/20 space-y-1 text-xs">
                          <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                            <Check className="h-3 w-3" /> Bull Case & Edge
                          </span>
                          <p className="text-slate-300 leading-relaxed text-[11px]">
                            {schemeDetails.analyst_conviction.analyst_memo.bull_case}
                          </p>
                        </div>
                        <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/20 space-y-1 text-xs">
                          <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> Bear Risks & Headwinds
                          </span>
                          <p className="text-slate-300 leading-relaxed text-[11px]">
                            {schemeDetails.analyst_conviction.analyst_memo.bear_risks}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Rolling Returns & Risk Engine */}
                <div className="space-y-6">
                  {/* Rolling Returns Visualizer */}
                  {rollingReturns && !('error' in rollingReturns) ? (
                    <MFRollingReturnsVisualizer
                      rollingReturns={rollingReturns}
                      windowYears={rollingWindow}
                      onWindowChange={handleWindowChange}
                    />
                  ) : null}

                  {/* Institutional Risk Ratios Card */}
                  <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-4">
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-sky-400" />
                      Institutional Risk &amp; Alpha Metrics
                    </h3>

                    {riskMetrics ? (
                      <>
                      {!riskMetricsTrustworthy && <p className="rounded-lg border border-amber-700/20 bg-amber-950/20 px-3 py-2 text-xs text-amber-800">Risk ratios are hidden because the stored NAV series has too little variation to support a reliable estimate.</p>}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
                          <span className="text-[10px] text-slate-400 uppercase font-medium">Sharpe Ratio</span>
                          <p className="text-base font-bold text-white mt-0.5">{riskMetricsTrustworthy ? riskMetrics.sharpe_ratio : '—'}</p>
                          <span className="text-[10px] text-emerald-400">Risk-Adjusted Alpha</span>
                        </div>
                        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
                          <span className="text-[10px] text-slate-400 uppercase font-medium">Sortino Ratio</span>
                          <p className="text-base font-bold text-white mt-0.5">{riskMetricsTrustworthy ? riskMetrics.sortino_ratio : '—'}</p>
                          <span className="text-[10px] text-sky-400">Downside Alpha</span>
                        </div>
                        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
                          <span className="text-[10px] text-slate-400 uppercase font-medium">Volatility (Std Dev)</span>
                          <p className="text-base font-bold text-slate-200 mt-0.5">{riskMetricsTrustworthy ? `${riskMetrics.volatility}%` : '—'}</p>
                          <span className="text-[10px] text-slate-400">Annualized</span>
                        </div>
                        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
                          <span className="text-[10px] text-slate-400 uppercase font-medium">Beta vs Index</span>
                          <p className="text-base font-bold text-slate-200 mt-0.5">{riskMetricsTrustworthy ? riskMetrics.beta : '—'}</p>
                          <span className="text-[10px] text-slate-400">Systematic Risk</span>
                        </div>
                      </div>
                      </>
                    ) : null}
                  </div>
                </div>

                {/* Top 10 Portfolio Holdings Table */}
                <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Layers className="h-4 w-4 text-emerald-400" />
                    Top Portfolio Holdings Disclosure
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="pb-2 font-medium">Company Name</th>
                          <th className="pb-2 font-medium">Symbol</th>
                          <th className="pb-2 font-medium">Sector</th>
                          <th className="pb-2 font-medium text-right">Portfolio Weight</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {schemeDetails.top_holdings.map((h, i) => (
                          <tr key={i} className="hover:bg-slate-800/30">
                            <td className="py-2.5 font-medium text-white">{h.company_name}</td>
                            <td className="py-2.5 font-mono text-emerald-400">{h.symbol || '—'}</td>
                            <td className="py-2.5 text-slate-400">{h.sector || 'Equities'}</td>
                            <td className="py-2.5 text-right font-bold text-slate-200">{h.weight_pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-slate-500">Select a fund from the left to inspect metrics.</div>
            )}
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TAB 2: SMART GOAL & FUND ADVISOR WIZARD                                */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'advisor' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Interactive Questionnaire */}
          <div className="lg:col-span-5 bg-slate-900/60 rounded-2xl border border-slate-800/80 p-6 space-y-5">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-amber-400" />
                Goal Discovery & Profiler
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Answer 4 questions to generate a customized asset allocation and fund basket.
              </p>
            </div>

            {/* Question 1: Goal */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">1. What is your primary objective?</label>
              <select
                value={goalType}
                onChange={(e) => setGoalType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500/50"
              >
                <option value="WEALTH_CREATION">Long-term Wealth Creation (Multi-Cap Compounding)</option>
                <option value="TAX_SAVING">Tax Saving Section 80C (ELSS Focus)</option>
                <option value="RETIREMENT">Early Retirement / Financial Freedom (FIRE)</option>
                <option value="EMERGENCY_FUND">Capital Preservation / Emergency Fund</option>
              </select>
            </div>

            {/* Question 2: Risk Profile */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">2. Risk Tolerance & Market Drawdowns</label>
              <div className="grid grid-cols-2 gap-2">
                {(['CONSERVATIVE', 'MODERATE', 'GROWTH', 'AGGRESSIVE'] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRiskProfile(r)}
                    className={`p-2.5 rounded-xl border text-xs font-medium text-left transition-all ${
                      riskProfile === r
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-slate-950/40 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Question 3: Time Horizon */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-300">3. Investment Horizon:</span>
                <span className="font-bold text-amber-400">{horizonYears} Years</span>
              </div>
              <input
                type="range"
                min="1"
                max="25"
                value={horizonYears}
                onChange={(e) => setHorizonYears(Number(e.target.value))}
                className="w-full accent-amber-400"
              />
            </div>

            {/* Question 4: Monthly Budget & Step-Up */}
            <div className="space-y-3 border-t border-slate-800/80 pt-4">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-300">4. Monthly Investment Budget:</span>
                <span className="font-bold text-emerald-400">₹{monthlyBudget.toLocaleString('en-IN')}</span>
              </div>
              <input
                type="range"
                min="2000"
                max="100000"
                step="1000"
                value={monthlyBudget}
                onChange={(e) => setMonthlyBudget(Number(e.target.value))}
                className="w-full accent-emerald-400"
              />

              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-300">Annual Step-Up (Top-Up):</span>
                <span className="font-bold text-sky-400">{advisorStepUp}% / year</span>
              </div>
              <input
                type="range"
                min="0"
                max="25"
                step="5"
                value={advisorStepUp}
                onChange={(e) => setAdvisorStepUp(Number(e.target.value))}
                className="w-full accent-sky-400"
              />
            </div>

            <button
              onClick={handleGenerateRecommendation}
              disabled={isGeneratingAdvisor}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 transition-all"
            >
              <Sparkles className="h-4 w-4" />
              {isGeneratingAdvisor ? 'Synthesizing...' : 'Generate Recommended Portfolio'}
            </button>
          </div>

          {/* Right Column: Recommended Basket & Projections */}
          <div className="lg:col-span-7 space-y-6">
            {advisorResult ? (
              <>
                {/* 1. Interactive Asset Allocation Donut */}
                <MFAssetAllocationDonut
                  allocation={advisorResult.asset_allocation}
                  totalAmount={advisorResult.total_monthly_sip}
                  title="Tailored Category Asset Allocation"
                  subtitle={`${advisorResult.user_profile.risk_label} • Target: ~${advisorResult.user_profile.expected_cagr_pct}% CAGR`}
                  currencyPrefix="₹"
                />

                {/* 2. Multi-Scenario Wealth Accumulation Fan Chart */}
                <MFWealthTrajectoryChart
                  trajectory={
                    advisorResult.multi_scenario_projections?.unified_trajectory ||
                    advisorResult.wealth_projection.trajectory.map((t) => ({
                      year: t.year,
                      monthly_sip: t.monthly_sip,
                      total_invested: t.total_invested,
                      corpus_base: t.estimated_corpus,
                      corpus_bull: t.estimated_corpus * 1.15,
                      corpus_bear: t.estimated_corpus * 0.85,
                      real_purchasing_power: t.real_purchasing_power,
                    }))
                  }
                  expectedCagr={advisorResult.user_profile.expected_cagr_pct}
                  bullCagr={advisorResult.multi_scenario_projections?.bull_cagr}
                  bearCagr={advisorResult.multi_scenario_projections?.bear_cagr}
                  stepUpPct={advisorResult.user_profile.step_up_pct}
                />

                {/* 3. Seasoned Analyst Narrative Rationale */}
                {advisorResult.advisory_rationale && (
                  <div className="bg-gradient-to-br from-slate-900 via-slate-900/90 to-slate-950 rounded-2xl border border-amber-500/30 p-5 space-y-3 shadow-xl shadow-amber-950/10">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-amber-400" />
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                          Seasoned Analyst Strategic Rationale &amp; Allocation Thesis
                        </h4>
                      </div>
                      <span className="text-[10px] font-semibold text-amber-400 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
                        Institutional Wealth Architecture
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {advisorResult.advisory_rationale}
                    </p>
                    {advisorResult.market_context && (
                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-2">
                        <TrendingUp className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{advisorResult.market_context}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* 4. Budget 2024 Tax Optimization Memo & Rebalancing Protocol */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Tax Optimization Memo */}
                  <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-4 space-y-2.5">
                    <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                      <Scale className="h-4 w-4 text-emerald-400" />
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                        Budget 2024 Tax Efficiency Memo
                      </h4>
                    </div>
                    <div className="space-y-1.5 text-[11px] text-slate-300">
                      <div className="flex justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60">
                        <span className="text-slate-400">Equity LTCG (&gt;1Y):</span>
                        <strong className="text-emerald-300">12.5% over ₹1.25L exempt</strong>
                      </div>
                      <div className="flex justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60">
                        <span className="text-slate-400">Equity STCG (&lt;1Y):</span>
                        <strong className="text-amber-300">20% flat</strong>
                      </div>
                      <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-slate-300 leading-relaxed text-[11px]">
                        <strong className="text-emerald-400 block text-[10px] uppercase mb-0.5">Tax-Loss Harvesting Protocol:</strong>
                        Systematically realize up to ₹1,25,000 in LTCG tax-free each year before March 31 by redeeming and immediately reinvesting.
                      </div>
                    </div>
                  </div>

                  {/* Tactical Rebalancing Protocol */}
                  <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-4 space-y-2.5">
                    <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                      <ShieldCheck className="h-4 w-4 text-sky-400" />
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                        Tactical Rebalancing Protocol
                      </h4>
                    </div>
                    <div className="space-y-1.5 text-[11px] text-slate-300">
                      <div className="flex justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60">
                        <span className="text-slate-400">Tolerance Band:</span>
                        <strong className="text-sky-300">±5.0% asset class corridor</strong>
                      </div>
                      <div className="flex justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60">
                        <span className="text-slate-400">Execution Mode:</span>
                        <strong className="text-white">Cashflow SIP redirection</strong>
                      </div>
                      <div className="p-2.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-slate-300 leading-relaxed text-[11px]">
                        <strong className="text-sky-400 block text-[10px] uppercase mb-0.5">Maturity Glide-Path:</strong>
                        Initiate systematic STP from equity into liquid/arbitrage funds 24 to 36 months before your goal deadline to eliminate drawdown risk.
                      </div>
                    </div>
                  </div>
                </div>

                {/* 5. Recommended Funds List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Recommended Schemes & Monthly SIP Distribution
                  </h4>
                  {advisorResult.recommended_funds.map((fund) => (
                    <div
                      key={fund.scheme_code}
                      className="bg-slate-900/60 rounded-xl border border-slate-800/80 p-4 space-y-2 hover:border-slate-700 transition-all"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                              {fund.category} ({fund.allocation_pct}%)
                            </span>
                            {fund.category_rank && (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                                {fund.category_rank.rank_badge}
                              </span>
                            )}
                          </div>
                          <h5 className="text-sm font-bold text-white mt-0.5">{fund.scheme_name}</h5>
                          <p className="text-xs text-slate-400 mt-1">{fund.rationale}</p>
                        </div>
                        <div className="text-right whitespace-nowrap">
                          <span className="text-[10px] text-slate-400 uppercase">Suggested SIP</span>
                          <p className="text-base font-extrabold text-amber-300">
                            ₹{fund.monthly_sip.toLocaleString('en-IN')}/mo
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 6. Corpus Projection Highlight Card */}
                <div className="bg-gradient-to-br from-emerald-950/40 to-slate-900/80 rounded-2xl border border-emerald-500/30 p-5 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                      {advisorResult.user_profile.horizon_years}-Year Goal Projection
                    </span>
                    <p className="text-2xl font-black text-white mt-1">
                      ₹{(advisorResult.wealth_projection.estimated_corpus / 100000).toFixed(2)} Lakhs
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Total Invested: ₹{(advisorResult.wealth_projection.total_invested / 100000).toFixed(2)} Lakhs •{' '}
                      <strong className="text-emerald-400">
                        {advisorResult.wealth_projection.wealth_multiplier}x Multiplier
                      </strong>
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setCalcSipAmount(advisorResult.total_monthly_sip);
                      setCalcCagr(advisorResult.user_profile.expected_cagr_pct);
                      setCalcYears(advisorResult.user_profile.horizon_years);
                      setCalcStepUp(advisorResult.user_profile.step_up_pct);
                      setActiveTab('sip_planner');
                      runSipCalculation();
                    }}
                    className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs transition-all flex items-center gap-1.5"
                  >
                    View Year-by-Year Schedule
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-slate-500">Click generate to view tailored recommendations.</div>
            )}
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TAB 3: SIP SIMULATOR & STEP-UP PLANNER                                */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'sip_planner' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Simulator Controls */}
            <div className="lg:col-span-5 bg-slate-900/60 rounded-2xl border border-slate-800/80 p-6 space-y-5">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sliders className="h-4 w-4 text-sky-400" />
                SIP & Step-Up Parameters
              </h3>

              {/* Monthly SIP */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Starting Monthly SIP:</span>
                  <span className="font-bold text-emerald-400">₹{calcSipAmount.toLocaleString('en-IN')}</span>
                </div>
                <input
                  type="range"
                  min="1000"
                  max="100000"
                  step="1000"
                  value={calcSipAmount}
                  onChange={(e) => {
                    setCalcSipAmount(Number(e.target.value));
                  }}
                  className="w-full accent-emerald-400"
                />
              </div>

              {/* Expected CAGR */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Expected CAGR:</span>
                  <span className="font-bold text-amber-300">{calcCagr}% p.a.</span>
                </div>
                <input
                  type="range"
                  min="6"
                  max="22"
                  step="0.5"
                  value={calcCagr}
                  onChange={(e) => {
                    setCalcCagr(Number(e.target.value));
                  }}
                  className="w-full accent-amber-400"
                />
              </div>

              {/* Horizon Years */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Investment Period:</span>
                  <span className="font-bold text-sky-400">{calcYears} Years</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={calcYears}
                  onChange={(e) => {
                    setCalcYears(Number(e.target.value));
                  }}
                  className="w-full accent-sky-400"
                />
              </div>

              {/* Step Up % */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Annual Step-Up:</span>
                  <span className="font-bold text-purple-400">{calcStepUp}% / year</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="25"
                  step="5"
                  value={calcStepUp}
                  onChange={(e) => {
                    setCalcStepUp(Number(e.target.value));
                  }}
                  className="w-full accent-purple-400"
                />
              </div>

              {/* Inflation % */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Inflation Adjustment:</span>
                  <span className="font-bold text-rose-400">{calcInflation}% / year</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={calcInflation}
                  onChange={(e) => {
                    setCalcInflation(Number(e.target.value));
                  }}
                  className="w-full accent-rose-400"
                />
              </div>

              <button
                onClick={runSipCalculation}
                className="w-full py-2.5 rounded-xl bg-sky-500 hover:bg-sky-600 text-slate-950 font-bold text-xs transition-all"
              >
                Re-calculate Projection
              </button>
            </div>

            {/* Results Cards */}
            <div className="lg:col-span-7 space-y-6">
              {sipResult && (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Invested</span>
                      <p className="text-lg font-bold text-white mt-1">
                        ₹{(sipResult.total_invested / 100000).toFixed(2)} L
                      </p>
                    </div>

                    <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Estimated Corpus</span>
                      <p className="text-lg font-black text-emerald-400 mt-1">
                        ₹{(sipResult.estimated_corpus / 100000).toFixed(2)} L
                      </p>
                    </div>

                    <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Wealth Gain</span>
                      <p className="text-lg font-bold text-amber-300 mt-1">
                        ₹{(sipResult.estimated_gain / 100000).toFixed(2)} L
                      </p>
                    </div>

                    <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Multiplier</span>
                      <p className="text-lg font-bold text-sky-400 mt-1">{sipResult.wealth_multiplier}x</p>
                    </div>
                  </div>

                  {/* Year by Year Trajectory Table */}
                  <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-3">
                    <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                      Compounding Trajectory by Year
                    </h4>
                    <div className="overflow-x-auto max-h-[360px]">
                      <table className="w-full text-left text-xs">
                        <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 text-slate-400">
                          <tr>
                            <th className="py-2">Year</th>
                            <th className="py-2">Monthly SIP</th>
                            <th className="py-2">Invested Total</th>
                            <th className="py-2">Estimated Corpus</th>
                            <th className="py-2 text-right">Real Value (Post-Inflation)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {sipResult.trajectory.map((row) => (
                            <tr key={row.year} className="hover:bg-slate-800/30">
                              <td className="py-2 font-bold text-white">Year {row.year}</td>
                              <td className="py-2 text-slate-300">₹{row.monthly_sip.toLocaleString('en-IN')}</td>
                              <td className="py-2 text-slate-400">₹{row.total_invested.toLocaleString('en-IN')}</td>
                              <td className="py-2 font-bold text-emerald-400">
                                ₹{row.estimated_corpus.toLocaleString('en-IN')}
                              </td>
                              <td className="py-2 text-right text-slate-300">
                                ₹{row.real_purchasing_power.toLocaleString('en-IN')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TAB 4: PORTFOLIO & ACTIVE/CLOSED SIP DIAGNOSTICS                       */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'portfolio' && (
        <div className="space-y-6">
          {/* Header Summary & Actions Toolbar */}
          {portfolioData && (
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      <Coins className="h-5 w-5 text-purple-400" />
                      {portfolioData.portfolio_name || portfolioName || 'Mutual Fund Portfolio Diagnostics'}
                      {isLoadingPortfolio && (
                        <span className="text-[10px] text-purple-400 font-semibold animate-pulse">
                          (Syncing...)
                        </span>
                      )}
                    </h3>
                    <button
                      onClick={() => setShowSaveModal(true)}
                      className="p-1 rounded-lg bg-slate-800/70 hover:bg-slate-700 text-slate-400 hover:text-white transition-all text-xs"
                      title="Rename portfolio or edit notes"
                    >
                      <FileText className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Portfolio XIRR: <strong className="text-emerald-400">{portfolioData.portfolio_xirr_pct !== null && portfolioData.portfolio_xirr_pct !== undefined ? `${portfolioData.portfolio_xirr_pct}%` : '—'}</strong> • Active SIPs: <strong className="text-white">{portfolioData.active_sips_count}</strong> • Stopped SIPs: <strong className="text-white">{portfolioData.closed_sips_count}</strong>
                    {portfolioData.last_saved_at && (
                      <span className="ml-2 text-slate-400">
                        • Last saved: <strong className="text-emerald-400 font-medium">{portfolioData.last_saved_at}</strong>
                      </span>
                    )}
                  </p>
                  {portfolioData.notes && (
                    <p className="text-[11px] text-purple-300/80 italic mt-0.5">
                      Notes: {portfolioData.notes}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => handleSavePortfolio()}
                    disabled={isSavingPortfolio}
                    className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-500/20 transition-all"
                    title="Save portfolio state and sync with cloud"
                  >
                    {isSavingPortfolio ? (
                      <RotateCcw className="h-4 w-4 animate-spin" />
                    ) : (
                      <BookmarkCheck className="h-4 w-4" />
                    )}
                    {isSavingPortfolio ? 'Saving...' : 'Save Portfolio'}
                  </button>

                  <button
                    onClick={handlePredictHealth}
                    disabled={isLoadingHealth}
                    className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 transition-all"
                  >
                    <Activity className="h-4 w-4" />
                    {isLoadingHealth ? 'Diagnosing...' : 'Predict Portfolio Health'}
                  </button>

                  <button
                    onClick={handleOpenAddModal}
                    className="px-3.5 py-1.5 rounded-xl bg-purple-500 hover:bg-purple-600 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-purple-500/20 transition-all"
                  >
                    <PlusCircle className="h-4 w-4" />
                    Add SIP Schedule
                  </button>

                  <button
                    onClick={handleResetPortfolio}
                    disabled={isResettingPortfolio}
                    className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-800 hover:border-rose-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
                    title="Wipe portfolio and reset to empty state"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    {isResettingPortfolio ? 'Resetting...' : 'Reset'}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 border-t border-slate-800/80 pt-4">
                <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Invested</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">Capital</span>
                    </div>
                    <p className="text-base font-bold text-white mt-1">₹{portfolioData.total_invested.toLocaleString('en-IN')}</p>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5 flex-wrap">
                    <span className="text-blue-400 font-medium">Active: ₹{(portfolioData.active_invested ?? portfolioData.total_invested).toLocaleString('en-IN')}</span>
                    {(portfolioData.closed_invested ?? 0) > 0 && (
                      <>
                        <span className="text-slate-600">•</span>
                        <span className="text-slate-400">Retained: ₹{(portfolioData.closed_invested ?? 0).toLocaleString('en-IN')}</span>
                      </>
                    )}
                  </p>
                </div>

                <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Current Valuation</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-medium">Live NAV</span>
                    </div>
                    <p className="text-base font-bold text-emerald-400 mt-1">₹{portfolioData.current_value.toLocaleString('en-IN')}</p>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5 flex-wrap">
                    <span className="text-emerald-300 font-medium">Active: ₹{(portfolioData.active_current_value ?? portfolioData.current_value).toLocaleString('en-IN')}</span>
                    {(portfolioData.closed_current_value ?? 0) > 0 && (
                      <>
                        <span className="text-slate-600">•</span>
                        <span className="text-slate-400">Retained: ₹{(portfolioData.closed_current_value ?? 0).toLocaleString('en-IN')}</span>
                      </>
                    )}
                  </p>
                </div>

                <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Net Returns</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${portfolioData.unrealized_profit >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                        {portfolioData.absolute_return_pct >= 0 ? '+' : ''}{portfolioData.absolute_return_pct}%
                      </span>
                    </div>
                    <p className={`text-base font-bold mt-1 ${portfolioData.unrealized_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {portfolioData.unrealized_profit >= 0 ? '+' : ''}₹{portfolioData.unrealized_profit.toLocaleString('en-IN')}
                    </p>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5 flex-wrap">
                    <span className="text-emerald-300 font-medium">Active: +₹{(portfolioData.active_profit ?? 0).toLocaleString('en-IN')}</span>
                    {(portfolioData.closed_profit ?? 0) > 0 && (
                      <>
                        <span className="text-slate-600">•</span>
                        <span className="text-slate-400">Retained: +₹{(portfolioData.closed_profit ?? 0).toLocaleString('en-IN')}</span>
                      </>
                    )}
                  </p>
                </div>

                <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Active Monthly SIP</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 font-medium">Monthly Flow</span>
                    </div>
                    <p className="text-base font-bold text-amber-300 mt-1">₹{portfolioData.monthly_sip_run_rate.toLocaleString('en-IN')}/mo</p>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-2">
                    {portfolioData.active_sips_count} active fund{portfolioData.active_sips_count !== 1 ? 's' : ''} running • XIRR: <strong className="text-emerald-400">{portfolioData.portfolio_xirr_pct !== null && portfolioData.portfolio_xirr_pct !== undefined ? `${portfolioData.portfolio_xirr_pct}%` : '—'}</strong>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Feedback Toast Alerts */}
          {saveSuccessMsg && (
            <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between gap-2 shadow-lg animate-fadeIn">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>{saveSuccessMsg}</span>
              </div>
              <button onClick={() => setSaveSuccessMsg(null)} className="text-emerald-400 hover:text-white text-xs">✕</button>
            </div>
          )}

          {checkinFeedback && (
            <div className="p-3 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-200 text-xs flex items-center justify-between gap-2 shadow-lg animate-fadeIn">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-indigo-400 shrink-0" />
                <span>{checkinFeedback}</span>
              </div>
              <button onClick={() => setCheckinFeedback(null)} className="text-indigo-400 hover:text-white text-xs">✕</button>
            </div>
          )}

          {/* PowerUp Form Index & Power Score Meter */}
          {portfolioData && portfolioData.powerup_summary && portfolioData.total_invested > 0 && (
            <div className="bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950/80 rounded-2xl border border-emerald-500/30 p-5 space-y-4 shadow-xl">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500/20 to-teal-500/20 border border-emerald-500/40 flex flex-col items-center justify-center shadow-lg shadow-emerald-500/10">
                    <span className="text-[10px] uppercase font-bold text-emerald-400">Power</span>
                    <span className="text-xl font-extrabold text-white leading-none">
                      {portfolioData.powerup_summary.portfolio_power_score.toFixed(0)}
                    </span>
                    <span className="text-[9px] text-slate-400">/ 100</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                        <Zap className="h-3 w-3 text-emerald-400" />
                        PowerUp Form Index
                      </span>
                      <h4 className="text-sm font-bold text-white">
                        {portfolioData.powerup_summary.verdict}
                      </h4>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 max-w-xl">
                      {portfolioData.powerup_summary.verdict_description}
                    </p>
                  </div>
                </div>

                {/* Power Age Quick Shortcut */}
                {portfolioData.power_age_projection && (
                  <button
                    onClick={() => {
                      setActiveTab('power_age');
                      setPowerAgeResult(portfolioData.power_age_projection || null);
                    }}
                    className="p-3 rounded-xl bg-gradient-to-r from-amber-500/15 via-orange-500/15 to-amber-500/15 border border-amber-500/40 hover:border-amber-400 text-left transition-all group"
                  >
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-300">
                      <Zap className="h-3.5 w-3.5 text-amber-400" />
                      <span>Power Age: Age {portfolioData.power_age_projection.power_age}</span>
                      <ArrowUpRight className="h-3.5 w-3.5 ml-1 opacity-70 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                    </div>
                    <p className="text-[10px] text-slate-300 mt-0.5">
                      FIRE Freedom in {portfolioData.power_age_projection.years_to_freedom} yrs • Goal: ₹{(portfolioData.power_age_projection.corpus_at_power_age / 10000000).toFixed(2)} Cr
                    </p>
                  </button>
                )}
              </div>

              {/* Form Distribution Meter Bar */}
              <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">Portfolio Capital Form Allocation</span>
                  <div className="flex items-center gap-3 text-[11px]">
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                      In-Form: {portfolioData.powerup_summary.capital_distribution.in_form_pct}%
                    </span>
                    <span className="flex items-center gap-1 text-sky-400 font-medium">
                      <span className="w-2 h-2 rounded-full bg-sky-400"></span>
                      On-Track: {portfolioData.powerup_summary.capital_distribution.on_track_pct}%
                    </span>
                    {portfolioData.powerup_summary.capital_distribution.off_track_pct > 0 && (
                      <span className="flex items-center gap-1 text-amber-400 font-medium">
                        <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                        Off-Track: {portfolioData.powerup_summary.capital_distribution.off_track_pct}%
                      </span>
                    )}
                    {portfolioData.powerup_summary.capital_distribution.out_of_form_pct > 0 && (
                      <span className="flex items-center gap-1 text-rose-400 font-medium">
                        <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                        Out-of-Form: {portfolioData.powerup_summary.capital_distribution.out_of_form_pct}%
                      </span>
                    )}
                  </div>
                </div>

                {/* Stacked Progress Bar */}
                <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden flex shadow-inner">
                  <div
                    style={{ width: `${portfolioData.powerup_summary.capital_distribution.in_form_pct}%` }}
                    className="bg-emerald-500 h-full transition-all duration-500"
                    title={`In-Form: ${portfolioData.powerup_summary.capital_distribution.in_form_pct}%`}
                  />
                  <div
                    style={{ width: `${portfolioData.powerup_summary.capital_distribution.on_track_pct}%` }}
                    className="bg-sky-500 h-full transition-all duration-500"
                    title={`On-Track: ${portfolioData.powerup_summary.capital_distribution.on_track_pct}%`}
                  />
                  <div
                    style={{ width: `${portfolioData.powerup_summary.capital_distribution.off_track_pct}%` }}
                    className="bg-amber-500 h-full transition-all duration-500"
                    title={`Off-Track: ${portfolioData.powerup_summary.capital_distribution.off_track_pct}%`}
                  />
                  <div
                    style={{ width: `${portfolioData.powerup_summary.capital_distribution.out_of_form_pct}%` }}
                    className="bg-rose-500 h-full transition-all duration-500"
                    title={`Out-of-Form: ${portfolioData.powerup_summary.capital_distribution.out_of_form_pct}%`}
                  />
                </div>
              </div>

              {/* Actionable Rebalancing Plan Card */}
              {portfolioData.powerup_summary.has_rebalancing_needed && (
                <div className="bg-amber-500/10 rounded-xl border border-amber-500/30 p-4 space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                      <span className="text-xs font-bold text-amber-300">
                        PowerUp Actionable Rebalancing Plan ({portfolioData.powerup_summary.rebalancing_plan.length} fund{portfolioData.powerup_summary.rebalancing_plan.length > 1 ? 's' : ''} dragging capital)
                      </span>
                    </div>
                    <span className="text-[11px] font-semibold text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                      ₹{portfolioData.powerup_summary.capital_distribution.drag_capital_val.toLocaleString('en-IN')} ({portfolioData.powerup_summary.capital_distribution.drag_capital_pct}%) drag identified
                    </span>
                  </div>

                  <div className="space-y-3">
                    {portfolioData.powerup_summary.rebalancing_plan.map((item, idx) => (
                      <div key={idx} className="bg-slate-950/80 rounded-xl p-3 border border-amber-500/20 space-y-2">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-bold text-white">{item.scheme_name}</span>
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                {item.form_status === 'OFF_TRACK' ? '🟡 Off-Track' : '🔴 Out-of-Form'}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-300 mt-0.5">
                              Valuation: <strong className="text-white">₹{item.current_value.toLocaleString('en-IN')}</strong> • SIP: <strong className="text-white">₹{item.monthly_amount.toLocaleString('en-IN')}/mo</strong> • Alpha Lag: <strong className="text-rose-400">-{item.alpha_lag_pct.toFixed(1)}%</strong>
                            </p>
                          </div>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            Prescription: {item.action_mode === 'PAUSE_AND_REDIRECT' ? 'Pause SIP & Redirect' : 'Full Switch'}
                          </span>
                        </div>

                        <p className="text-[11px] text-amber-200/90 italic">
                          💡 {item.prescription}
                        </p>

                        {/* Top Recommended Replacement with Same AMC Priority */}
                        {item.recommended_switch && (
                          <div className="bg-slate-900/90 rounded-lg p-2.5 border border-slate-800 flex flex-wrap items-center justify-between gap-2">
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-1.5">
                                <span className="text-[10px] uppercase font-bold text-slate-400">Recommended Alternative:</span>
                                <span className="text-xs font-bold text-emerald-400">{item.recommended_switch.target_scheme_name}</span>
                                {item.recommended_switch.is_same_amc && (
                                  <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-0.5">
                                    <Zap className="h-2.5 w-2.5 text-emerald-400" />
                                    Same AMC Instant Switch (T+1)
                                  </span>
                                )}
                              </div>
                              <p className="text-[10px] text-slate-400">
                                {item.recommended_switch.comparison_advantage}
                              </p>
                            </div>

                            <button
                              onClick={() => {
                                if (item.sip_id) {
                                  setExpandedSwitchSipId(item.sip_id);
                                }
                              }}
                              className="px-2.5 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-[11px] transition-all"
                            >
                              View Switch Details
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Portfolio Asset Allocation Visual Donut */}
          {portfolioData && portfolioData.asset_allocation && Object.keys(portfolioData.asset_allocation).length > 0 && portfolioData.total_invested > 0 && (
            <MFAssetAllocationDonut
              allocation={portfolioData.asset_allocation}
              totalAmount={portfolioData.current_value}
              title="Portfolio Asset Class Allocation"
              subtitle="Current distribution of your mutual fund corpus across categories"
              currencyPrefix="₹"
            />
          )}

          {/* Consolidated Scheme Holdings & Net Worth Ledger */}
          {portfolioData && portfolioData.scheme_holdings && portfolioData.scheme_holdings.length > 0 && (
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Layers className="h-4 w-4 text-purple-400" />
                    Consolidated Scheme Holdings Ledger ({portfolioData.scheme_holdings.length})
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Aggregated holdings across all active and past SIP investments
                  </p>
                </div>
                <span className="text-xs font-mono text-purple-300 font-bold px-2.5 py-1 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  Total Value: ₹{portfolioData.current_value.toLocaleString('en-IN')}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                      <th className="py-2.5">Scheme Name</th>
                      <th className="py-2.5">Category</th>
                      <th className="py-2.5 text-right">Units Held</th>
                      <th className="py-2.5 text-right">Invested Capital</th>
                      <th className="py-2.5 text-right">Current Valuation</th>
                      <th className="py-2.5 text-right">Net Profit (Abs %)</th>
                      <th className="py-2.5 text-right">XIRR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {portfolioData.scheme_holdings.map((h) => (
                      <tr key={h.scheme_code} className="hover:bg-slate-800/30">
                        <td className="py-3 font-semibold text-white">
                          <div>{h.scheme_name}</div>
                          <div className="text-[10px] text-slate-500 font-normal">Code: {h.scheme_code} • NAV: ₹{h.current_nav?.toFixed(2)}</div>
                        </td>
                        <td className="py-3 text-slate-400">
                          <div className="flex flex-col gap-1 items-start">
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                              {h.category}
                            </span>
                            {h.category_rank && (
                              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/25 text-[9px] font-bold whitespace-nowrap" title={h.category_rank.rank_label}>
                                {h.category_rank.rank_badge}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 text-right font-mono">{h.total_units.toFixed(2)}</td>
                        <td className="py-3 text-right font-mono font-medium">₹{h.invested_amount.toLocaleString('en-IN')}</td>
                        <td className="py-3 text-right font-mono font-bold text-white">₹{h.current_value.toLocaleString('en-IN')}</td>
                        <td className="py-3 text-right font-mono font-semibold">
                          <span className={h.unrealized_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                            {h.unrealized_profit >= 0 ? '+' : ''}₹{h.unrealized_profit.toLocaleString('en-IN')} ({h.abs_return_pct}%)
                          </span>
                        </td>
                        <td className="py-3 text-right font-mono font-bold">
                          <span className={h.xirr_pct !== null && h.xirr_pct !== undefined && h.xirr_pct >= 0 ? 'text-emerald-400' : 'text-slate-400'}>
                            {h.xirr_pct !== null && h.xirr_pct !== undefined ? `${h.xirr_pct}%` : '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Monthly SIP Payment Check-In Alert & Confirmation Card */}
          {portfolioData && portfolioData.pending_checkins && portfolioData.pending_checkins.length > 0 && (
            <div className="bg-gradient-to-r from-purple-950/70 via-slate-900 to-slate-950 rounded-2xl border border-purple-500/40 p-5 space-y-4 shadow-xl shadow-purple-950/20">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
                    <Bell className="h-5 w-5 text-purple-300 animate-bounce" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                      Monthly SIP Payment Check-In
                      <span className="px-2 py-0.5 rounded-full bg-purple-500/30 text-purple-200 text-[10px] font-bold">
                        {portfolioData.pending_checkins.length} Scheduled {portfolioData.pending_checkins.length === 1 ? 'Debit' : 'Debits'} Due
                      </span>
                    </h4>
                    <p className="text-xs text-slate-300 mt-0.5">
                      Your monthly SIP date has arrived! Confirm whether these installments were debited to keep your portfolio valuation, XIRR, and discipline scores 100% accurate.
                    </p>
                  </div>
                </div>

                {portfolioData.pending_checkins.length > 1 && (
                  <button
                    onClick={() => handleBatchCheckin('MARK_ALL_PAID')}
                    disabled={checkinSubmittingId === 'batch'}
                    className="px-3.5 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-md transition-all"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {checkinSubmittingId === 'batch'
                      ? 'Recording...'
                      : `Mark All Due as Paid (₹${portfolioData.pending_checkins.reduce((acc, c) => acc + c.monthly_amount, 0).toLocaleString('en-IN')})`}
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                {portfolioData.pending_checkins.map((chk) => {
                  const isSubmitting = checkinSubmittingId === `${chk.sip_id}_${chk.due_date}`;
                  return (
                    <div
                      key={chk.checkin_id}
                      className="bg-slate-950/80 rounded-xl border border-slate-800 p-4 flex flex-col justify-between gap-3"
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            {chk.category}
                          </span>
                          <span className="text-[11px] text-amber-300 font-semibold flex items-center gap-1">
                            <Calendar className="h-3 w-3" /> Due: {chk.due_date} ({chk.days_ago === 0 ? 'Today' : `${chk.days_ago}d ago`})
                          </span>
                        </div>
                        <h5 className="text-xs font-bold text-white leading-snug">{chk.scheme_name}</h5>
                        <p className="text-[11px] text-slate-400">
                          Scheduled monthly installment: <strong className="text-white">₹{chk.monthly_amount.toLocaleString('en-IN')}</strong>
                        </p>
                      </div>

                      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
                        <span className="text-[11px] font-semibold text-slate-300">Did your bank debit this SIP?</span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleConfirmCheckin(chk.sip_id, chk.due_date, 'PAID', chk.monthly_amount)}
                            disabled={isSubmitting}
                            className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 font-bold text-xs flex items-center gap-1 transition-all"
                          >
                            <Check className="h-3.5 w-3.5" />
                            {isSubmitting ? 'Recording...' : 'Yes, Paid'}
                          </button>
                          <button
                            onClick={() => handleConfirmCheckin(chk.sip_id, chk.due_date, 'SKIPPED')}
                            disabled={isSubmitting}
                            className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-amber-300 border border-slate-700 text-xs font-semibold flex items-center gap-1 transition-all"
                          >
                            <XCircle className="h-3.5 w-3.5 text-amber-400" />
                            Skipped
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Empty Portfolio State Onboarding Hero */}
          {portfolioData && portfolioData.total_invested === 0 && portfolioData.active_sips_count === 0 && portfolioData.closed_sips_count === 0 && (
            <div className="bg-gradient-to-br from-slate-900/90 to-slate-950 rounded-2xl border border-slate-800/80 p-8 text-center space-y-5 shadow-xl">
              <div className="mx-auto h-16 w-16 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                <Coins className="h-8 w-8 text-purple-400" />
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <h3 className="text-xl font-bold text-white">Your Mutual Fund Portfolio is Fresh & Clean</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  You don't have any mutual fund holdings or SIPs recorded yet. Add your ongoing or past SIP investments along with your current invested capital and portfolio values to calculate your real XIRR and unlock full institutional health diagnostics.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                <button
                  onClick={handleOpenAddModal}
                  className="px-4 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-600 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-500/20 transition-all"
                >
                  <PlusCircle className="h-4 w-4" /> Add Your First SIP / Holding
                </button>
                <button
                  onClick={() => setActiveTab('advisor')}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center gap-2 border border-slate-700 transition-all"
                >
                  <Sparkles className="h-4 w-4 text-amber-400" /> Consult Smart Advisor
                </button>
                <button
                  onClick={() => setActiveTab('analyzer')}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center gap-2 border border-slate-700 transition-all"
                >
                  <Search className="h-4 w-4 text-emerald-400" /> Screen Top Funds
                </button>
              </div>
            </div>
          )}

          {/* Predictive Health & Forward Trajectory Engine Card */}
          {healthResult && (
            <div className="bg-gradient-to-br from-slate-900 via-slate-900/90 to-slate-950 rounded-2xl border border-emerald-500/30 p-5 space-y-4 shadow-xl shadow-emerald-950/10">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-3">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center font-black text-xl text-emerald-400">
                    {healthResult.health_score}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold uppercase tracking-wider">
                        {healthResult.rating_label}
                      </span>
                      <span className="text-xs text-slate-400">Forward Health Model</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Portfolio Status: <strong className="text-white">{healthResult.verdict.replace(/_/g, ' ')}</strong>
                      {healthResult.portfolio_xirr !== null && healthResult.portfolio_xirr !== undefined && (
                        <> • Historical XIRR: <strong className="text-emerald-400">{healthResult.portfolio_xirr}%</strong></>
                      )}
                    </p>
                  </div>
                </div>

                <div className="text-right text-xs">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Institutional Health Check</span>
                  <p className="text-emerald-400 font-bold flex items-center justify-end gap-1 mt-0.5">
                    <Activity className="h-4 w-4" /> Comprehensive Audit
                  </p>
                </div>
              </div>

              {/* 5 Quantitative Pillars Breakdown */}
              {healthResult.pillars && (
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-1">
                  <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/60 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 font-medium">Alpha vs Index</span>
                      <span className="font-bold text-slate-200">{healthResult.pillars.alpha_performance}/25</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-400"
                        style={{ width: `${Math.min(100, (healthResult.pillars.alpha_performance / 25) * 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/60 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 font-medium">Downside Protection</span>
                      <span className="font-bold text-slate-200">{healthResult.pillars.downside_protection != null ? `${healthResult.pillars.downside_protection}/20` : '—'}</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-teal-400"
                        style={{ width: `${Math.min(100, ((healthResult.pillars.downside_protection ?? 0) / 20) * 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/60 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 font-medium">Overlap Efficiency</span>
                      <span className="font-bold text-slate-200">{healthResult.pillars.overlap_efficiency}/20</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-purple-400"
                        style={{ width: `${Math.min(100, (healthResult.pillars.overlap_efficiency / 20) * 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/60 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 font-medium">Diversification</span>
                      <span className="font-bold text-slate-200">{healthResult.pillars.diversification}/20</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-sky-400"
                        style={{ width: `${Math.min(100, (healthResult.pillars.diversification / 20) * 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/60 space-y-1.5 col-span-2 sm:col-span-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 font-medium">SIP Regularity</span>
                      <span className="font-bold text-slate-200">{healthResult.pillars.sip_discipline}/15</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-amber-400"
                        style={{ width: `${Math.min(100, (healthResult.pillars.sip_discipline / 15) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Cash Flow Discipline & Skipped Installment Analysis Card */}
              {healthResult.cash_flow_discipline_analysis && (
                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-amber-400" />
                      Cash Flow Execution & SIP Timing Forensics:
                      <strong className={healthResult.cash_flow_discipline_analysis.total_skipped_installments > 0 ? "text-amber-400 ml-1" : "text-emerald-400 ml-1"}>
                        {healthResult.cash_flow_discipline_analysis.verdict}
                      </strong>
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Average Regularity: <strong className="text-white">{healthResult.cash_flow_discipline_analysis.average_regularity_pct}%</strong>
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {healthResult.cash_flow_discipline_analysis.insight}
                  </p>
                </div>
              )}

              {/* Actionable Recommendations */}
              {healthResult.actionable_recommendations && healthResult.actionable_recommendations.length > 0 && (
                <div className="space-y-2 pt-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Actionable Analyst Recommendations
                  </span>
                  <div className="space-y-1.5">
                    {healthResult.actionable_recommendations.map((rec, i) => (
                      <div key={i} className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/60 text-xs flex items-start gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-slate-300 leading-relaxed text-[11px]">{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3-Horizon Predictive Wealth Trajectory Scenarios */}
              {healthResult.predictive_scenarios && healthResult.predictive_scenarios.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-800/80">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                    Predictive Forward Wealth Trajectory (Based on Active Monthly SIP + Current Value)
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {healthResult.predictive_scenarios.map((sc) => (
                      <div key={sc.horizon_years} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-white">{sc.horizon_years}-Year Horizon</span>
                          <span className="text-[10px] text-emerald-400 font-semibold">{sc.wealth_multiplier != null ? `${sc.wealth_multiplier}x Multiplier` : '—'}</span>
                        </div>
                        <div className="space-y-1.5 text-xs">
                          <div className="flex justify-between text-[11px]">
                            <span className="text-slate-400">Total Invested:</span>
                            <span className="font-semibold text-slate-300">₹{((sc.total_invested_flat || 0) / 100000).toFixed(2)} L</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span className="text-slate-400">Expected Base (13.0%):</span>
                            <span className="font-bold text-emerald-400">₹{(sc.base_case_13pct / 100000).toFixed(2)} L</span>
                          </div>
                          {sc.base_case_real_power && (
                            <div className="flex justify-between text-[10px] bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800/60">
                              <span className="text-slate-400">Today's Purchasing Power:</span>
                              <span className="font-medium text-amber-300">₹{(sc.base_case_real_power / 100000).toFixed(2)} L</span>
                            </div>
                          )}
                          {sc.base_case_with_10pct_stepup && (
                            <div className="flex justify-between text-[10px] bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                              <span className="text-purple-300">With 10% Step-Up:</span>
                              <span className="font-bold text-purple-200">₹{(sc.base_case_with_10pct_stepup / 100000).toFixed(2)} L</span>
                            </div>
                          )}
                          <div className="flex justify-between text-[11px] pt-0.5 border-t border-slate-800/60">
                            <span className="text-slate-400">Conservative (8.5%):</span>
                            <span className="font-medium text-rose-300">₹{(sc.bear_case_8pct / 100000).toFixed(2)} L</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span className="text-slate-400">Optimistic Bull (16.0%):</span>
                            <span className="font-medium text-sky-400">₹{(sc.bull_case_16pct / 100000).toFixed(2)} L</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Active SIPs Diagnostic & Tactical Switching Options */}
          {portfolioData && portfolioData.active_sips && portfolioData.active_sips.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4" />
                    Active SIP Schedules & Intrinsic Health Diagnostics ({portfolioData.active_sips.length})
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Evaluated by benchmark-relative rolling alpha, downside protection, and cash flow regularity.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {portfolioData.active_sips.map((sip) => {
                  const isExpanded = expandedSwitchSipId === sip.sip_id;
                  const hasSwitches = sip.switch_options && sip.switch_options.length > 0;
                  const needsAction = sip.action_type && sip.action_type !== 'CONTINUE_CORE';

                  return (
                    <div
                      key={sip.sip_id}
                      className={`bg-slate-900/60 rounded-2xl border transition-all p-5 space-y-4 ${
                        needsAction ? 'border-amber-500/30 bg-slate-900/80 shadow-md' : 'border-slate-800/80'
                      }`}
                    >
                      {/* Top Header of Card */}
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                              {sip.category}
                            </span>
                            {sip.category_rank && (
                              <span
                                className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-amber-500/10 text-amber-300 border-amber-500/30 flex items-center gap-1"
                                title={sip.category_rank.rank_label}
                              >
                                <span>{sip.category_rank.rank_badge}</span>
                              </span>
                            )}
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                                sip.health_status === 'OUTPERFORMING'
                                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                  : sip.health_status === 'UNDERPERFORMING'
                                  ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                  : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                              }`}
                            >
                              {sip.health_status || 'ANALYZED'}
                            </span>
                            {sip.powerup_form && (
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                                  sip.powerup_form.badge === 'IN_FORM'
                                    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                    : sip.powerup_form.badge === 'ON_TRACK'
                                    ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                                    : sip.powerup_form.badge === 'OFF_TRACK'
                                    ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                                    : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                }`}
                                title={`Power Score: ${sip.powerup_form.power_score}/100 • ${sip.powerup_form.momentum_desc}`}
                              >
                                <span>{sip.powerup_form.badge_emoji}</span>
                                <span>{sip.powerup_form.badge_label}</span>
                                <span className="text-[9px] opacity-75 font-mono">({sip.powerup_form.power_score})</span>
                              </span>
                            )}
                            {sip.powerup_form?.is_drag_capital && (
                              <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/25">
                                ⚠️ Drag Capital
                              </span>
                            )}
                            <span className="text-[11px] text-slate-400">
                              Started: {sip.start_date} • SIP Day: {sip.sip_day}th
                            </span>
                            {sip.next_sip_date && (
                              <span className="text-[11px] text-purple-300 font-medium flex items-center gap-1 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                                <Calendar className="h-3 w-3 text-purple-400" />
                                Next: {sip.next_sip_date} ({sip.days_until_next_sip ?? 0}d)
                              </span>
                            )}
                            {sip.current_month_checkin_status === 'PAID' && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                                <Check className="h-3 w-3" /> Month Paid
                              </span>
                            )}
                            {sip.current_month_checkin_status === 'SKIPPED' && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                                <XCircle className="h-3 w-3" /> Month Skipped
                              </span>
                            )}
                            {sip.current_month_checkin_status === 'PENDING' && (
                              <div className="flex items-center gap-1">
                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center gap-1 animate-pulse">
                                  <Bell className="h-3 w-3" /> Due
                                </span>
                                <button
                                  onClick={() => handleConfirmCheckin(sip.sip_id, sip.due_date_current_month || '', 'PAID', sip.monthly_amount)}
                                  className="px-1.5 py-0.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 rounded text-[10px] font-bold border border-emerald-500/30"
                                  title="Mark this month's installment as paid"
                                >
                                  Paid
                                </button>
                                <button
                                  onClick={() => handleConfirmCheckin(sip.sip_id, sip.due_date_current_month || '', 'SKIPPED')}
                                  className="px-1.5 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] font-semibold border border-slate-700"
                                  title="Mark as skipped this month"
                                >
                                  Skip
                                </button>
                              </div>
                            )}
                          </div>
                          <h5 className="text-base font-bold text-white mt-1">{sip.scheme_name}</h5>
                        </div>

                        <div className="flex flex-col items-end gap-2">
                          <div className="text-right">
                            <span className="text-[10px] text-slate-400 uppercase block">Monthly Outflow</span>
                            <span className="text-base font-extrabold text-white">
                              ₹{sip.monthly_amount.toLocaleString('en-IN')}/mo
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => handleOpenEditModal(sip)}
                              className="px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/70 text-xs font-semibold flex items-center gap-1 transition-all shadow-sm"
                              title="Edit this SIP holding details, dates, skipped months, or values"
                            >
                              <Pencil className="h-3 w-3 text-purple-400" />
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteSip(sip.sip_id, sip.scheme_name)}
                              disabled={actionProcessingId === sip.sip_id}
                              className="px-2.5 py-1 rounded-lg bg-slate-800/90 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700/70 hover:border-rose-500/30 text-xs font-semibold flex items-center gap-1 transition-all shadow-sm"
                              title="Delete this SIP holding from your portfolio"
                            >
                              <Trash2 className="h-3 w-3 text-rose-400" />
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Capital and Return Snapshot */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
                        <div>
                          <span className="text-[10px] text-slate-400 uppercase">Invested Capital</span>
                          <p className="font-semibold text-slate-200 mt-0.5">₹{sip.total_invested.toLocaleString('en-IN')}</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 uppercase">Current Value</span>
                          <p className="font-semibold text-emerald-400 mt-0.5">₹{sip.current_value.toLocaleString('en-IN')}</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 uppercase">Personal SIP XIRR</span>
                          <p className="font-bold text-emerald-400 mt-0.5">{sip.xirr_pct ? `${sip.xirr_pct}%` : '—'}</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 uppercase">Fund 3Y CAGR</span>
                          <p className="font-bold text-white mt-0.5">
                            {sip.fund_cagr_3y ? `${sip.fund_cagr_3y}%` : '—'}
                            {sip.rolling_alpha_pct !== undefined && sip.rolling_alpha_pct !== null && (
                              <span className={`text-[10px] ml-1.5 font-bold ${sip.rolling_alpha_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                ({sip.rolling_alpha_pct >= 0 ? `+${sip.rolling_alpha_pct}%` : `${sip.rolling_alpha_pct}%`} alpha)
                              </span>
                            )}
                          </p>
                        </div>
                      </div>

                      {/* Disentangled Forensics & Skipped Installment Alert */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                        <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/60 space-y-1">
                          <span className="font-bold text-slate-300 flex items-center gap-1.5">
                            <Activity className="h-3.5 w-3.5 text-emerald-400" />
                            Fund Intrinsic Quality:
                          </span>
                          <p className="text-slate-400 leading-relaxed">
                            Benchmark: <strong className="text-slate-200">{sip.benchmark_name || 'Category Index'}</strong> ({sip.benchmark_cagr_3y != null ? `${sip.benchmark_cagr_3y}% 3Y CAGR` : '3Y return unavailable'}).
                            Downside Capture: <strong className="text-slate-200">{sip.downside_capture != null ? `${sip.downside_capture}%` : 'Unavailable'}</strong> (lower is more defensive during market dips).
                          </p>
                        </div>

                        <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/60 space-y-1">
                          <span className="font-bold text-slate-300 flex items-center gap-1.5">
                            <Clock className="h-3.5 w-3.5 text-amber-400" />
                            Investor Cashflow Discipline:
                          </span>
                          <p className="text-slate-400 leading-relaxed">
                            {sip.cashflow_diagnostic_memo || `Completed ${sip.installments_count} installments on schedule.`}
                          </p>
                        </div>
                      </div>

                      {/* Action Prescription Banner */}
                      <div
                        className={`p-3 rounded-xl border flex flex-wrap items-center justify-between gap-3 ${
                          sip.action_type === 'CONTINUE_CORE'
                            ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300'
                            : sip.action_type === 'PAUSE_AND_REDIRECT'
                            ? 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                            : sip.action_type === 'SWITCH_FULLY'
                            ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                            : 'bg-purple-500/10 border-purple-500/30 text-purple-200'
                        }`}
                      >
                        <div className="min-w-0 max-w-xl">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs uppercase tracking-wider">
                              Prescription: {sip.action_headline || sip.recommendation}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300 mt-1 leading-relaxed">{sip.recommendation}</p>
                        </div>

                        {hasSwitches && (
                          <button
                            onClick={() => setExpandedSwitchSipId(isExpanded ? null : sip.sip_id)}
                            className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-slate-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
                          >
                            <ArrowRightLeft className="h-3.5 w-3.5 text-purple-400" />
                            {isExpanded ? 'Hide Switch Options' : 'Explore Switch Options'}
                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          </button>
                        )}
                      </div>

                      {/* Expanded Tactical Switching Options with Full vs Partial vs Pause Details */}
                      {isExpanded && hasSwitches && (
                        <div className="bg-slate-950/80 rounded-xl border border-purple-500/30 p-4 space-y-4">
                          <div>
                            <span className="text-xs font-bold text-purple-300 flex items-center gap-1.5 uppercase tracking-wider">
                              <ArrowRightLeft className="h-4 w-4 text-purple-400" />
                              Recommended Top-Quartile Replacement Options & Execution Plan
                            </span>
                            <p className="text-[11px] text-slate-400 mt-0.5">
                              Scientifically vetted peers with proven rolling alpha, lower expense drag, and defensive downside capture.
                            </p>
                          </div>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {sip.switch_options!.map((opt) => (
                              <div
                                key={opt.target_scheme_code}
                                className={`rounded-xl border p-4 space-y-3 transition-all ${
                                  opt.is_same_amc
                                    ? 'bg-gradient-to-b from-emerald-500/10 via-slate-900/90 to-slate-900/95 border-emerald-500/40 shadow-sm shadow-emerald-950/20'
                                    : 'bg-slate-900/90 border-slate-800'
                                }`}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div>
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      {opt.is_same_amc ? (
                                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                                          <Zap className="h-3 w-3" /> Same AMC • Free & Instant
                                        </span>
                                      ) : (
                                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                          🏦 Inter-AMC Switch
                                        </span>
                                      )}
                                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                        ★ {opt.crisil_rating} CRISIL
                                      </span>
                                      <span className="text-[10px] text-slate-400">{opt.category}</span>
                                    </div>
                                    <h6 className="text-xs font-bold text-white mt-1">{opt.target_scheme_name}</h6>
                                    <p className="text-[10px] text-slate-400">
                                      {opt.fund_house}
                                      {opt.turnaround_time && (
                                        <span className="text-cyan-400 font-medium ml-2">• Settlement: {opt.turnaround_time}</span>
                                      )}
                                    </p>
                                  </div>
                                  <div className="text-right flex-shrink-0">
                                    <span className="text-[10px] text-slate-400 uppercase">3Y CAGR</span>
                                    <p className="text-sm font-extrabold text-emerald-400">{opt.trailing_3y_cagr}%</p>
                                  </div>
                                </div>

                                {opt.amc_advantage && (
                                  <div className={`p-2 rounded-lg text-[10px] leading-relaxed border ${
                                    opt.is_same_amc
                                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-200'
                                      : 'bg-slate-950/60 border-slate-800 text-slate-300'
                                  }`}>
                                    <strong>Switch Route:</strong> {opt.amc_advantage}
                                  </div>
                                )}

                                <div className="grid grid-cols-3 gap-2 text-[10px] bg-slate-950/70 p-2 rounded-lg border border-slate-800/80 text-center">
                                  <div>
                                    <span className="text-slate-400 uppercase">Expense TER</span>
                                    <p className="font-bold text-slate-200">{opt.expense_ratio}%</p>
                                  </div>
                                  <div>
                                    <span className="text-slate-400 uppercase">Downside Cap</span>
                                    <p className="font-bold text-teal-400">{opt.downside_capture != null ? `${opt.downside_capture}%` : '—'}</p>
                                  </div>
                                  <div>
                                    <span className="text-slate-400 uppercase">Stock Overlap</span>
                                    <p className="font-bold text-purple-400">{opt.overlap_with_current_pct}%</p>
                                  </div>
                                </div>

                                {/* 3 Tactical Execution Modes */}
                                <div className="space-y-2 pt-1 border-t border-slate-800 text-[11px]">
                                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                                    Tactical Execution Modes:
                                  </span>

                                  <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-0.5">
                                    <span className="font-bold text-emerald-300 text-[10px] uppercase">
                                      Mode 1: Pause Current SIP & Redirect (Recommended to Avoid Tax/Exit Load)
                                    </span>
                                    <p className="text-slate-300 text-[11px] leading-relaxed">
                                      {opt.execution_modes.pause_and_redirect}
                                    </p>
                                  </div>

                                  <div className="p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/20 space-y-0.5">
                                    <span className="font-bold text-purple-300 text-[10px] uppercase">
                                      Mode 2: Full Switch (Redeem & Shift 100%)
                                    </span>
                                    <p className="text-slate-300 text-[11px] leading-relaxed">
                                      {opt.execution_modes.full_switch}
                                    </p>
                                  </div>

                                  <div className="p-2.5 rounded-lg bg-sky-500/10 border border-sky-500/20 space-y-0.5">
                                    <span className="font-bold text-sky-300 text-[10px] uppercase">
                                      Mode 3: Partial Switch (50% Rebalance)
                                    </span>
                                    <p className="text-slate-300 text-[11px] leading-relaxed">
                                      {opt.execution_modes.partial_switch}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Closed / Paused SIPs Diagnostic (Post-Mortem) */}
          {portfolioData && portfolioData.closed_sips && portfolioData.closed_sips.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                Closed / Discontinued SIPs Post-Mortem ({portfolioData.closed_sips.length})
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {portfolioData.closed_sips.map((sip) => (
                  <div key={sip.sip_id} className="bg-slate-900/60 rounded-xl border border-amber-500/20 p-4 space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                            {sip.status} • {sip.category}
                          </span>
                          {sip.category_rank && (
                            <span
                              className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-amber-500/10 text-amber-300 border-amber-500/30 flex items-center gap-1"
                              title={sip.category_rank.rank_label}
                            >
                              <span>{sip.category_rank.rank_badge}</span>
                            </span>
                          )}
                          {sip.powerup_form && (
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                                sip.powerup_form.badge === 'IN_FORM'
                                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                  : sip.powerup_form.badge === 'ON_TRACK'
                                  ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                                  : sip.powerup_form.badge === 'OFF_TRACK'
                                  ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                                  : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                              }`}
                              title={`Power Score: ${sip.powerup_form.power_score}/100 • ${sip.powerup_form.momentum_desc}`}
                            >
                              <span>{sip.powerup_form.badge_emoji}</span>
                              <span>{sip.powerup_form.badge_label}</span>
                              <span className="text-[9px] opacity-75 font-mono">({sip.powerup_form.power_score})</span>
                            </span>
                          )}
                        </div>
                        <h5 className="text-sm font-bold text-white mt-1">{sip.scheme_name}</h5>
                        <p className="text-[11px] text-slate-400">
                          Active {sip.start_date} to {sip.end_date || 'Stopped'} ({sip.installments_count} installments)
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1.5">
                        <span className="text-xs font-bold text-slate-400">₹{sip.monthly_amount.toLocaleString('en-IN')}/mo</span>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleOpenEditModal(sip)}
                            className="px-2 py-0.5 rounded bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/70 text-[10px] font-semibold flex items-center gap-1 transition-all"
                            title="Edit this closed/paused SIP holding"
                          >
                            <Pencil className="h-2.5 w-2.5 text-amber-400" />
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteSip(sip.sip_id, sip.scheme_name)}
                            disabled={actionProcessingId === sip.sip_id}
                            className="px-2 py-0.5 rounded bg-slate-800/90 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700/70 hover:border-rose-500/30 text-[10px] font-semibold flex items-center gap-1 transition-all"
                            title="Delete this closed SIP holding from your portfolio"
                          >
                            <Trash2 className="h-2.5 w-2.5 text-rose-400" />
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center text-xs border-t border-slate-800/60 pt-2.5">
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase">Invested</span>
                        <p className="font-semibold text-slate-200">₹{sip.total_invested.toLocaleString('en-IN')}</p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase">Retained Value</span>
                        <p className="font-semibold text-amber-300">₹{sip.current_value.toLocaleString('en-IN')}</p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase">Realized XIRR</span>
                        <p className="font-bold text-amber-300">{sip.xirr_pct ? `${sip.xirr_pct}%` : '—'}</p>
                      </div>
                    </div>

                    {sip.post_mortem && (
                      <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-200">
                        <strong>Post-Mortem Verdict:</strong> {sip.post_mortem.verdict}
                      </div>
                    )}

                    {/* Action Success Banner */}
                    {actionSuccessMessage && actionProcessingId === null && (
                      <div className="p-2 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-[11px] text-emerald-300 flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5" /> {actionSuccessMessage}
                      </div>
                    )}

                    {/* Tactical Action Tabs for Closed SIPs */}
                    {sip.action_options && (
                      <div className="space-y-2">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">What To Do Next</span>
                        <div className="flex gap-1.5">
                          {sip.action_options.resume && (
                            <button
                              type="button"
                              onClick={() => setClosedSipActiveTab((prev) => ({ ...prev, [sip.sip_id]: 'resume' }))}
                              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition-all border ${
                                closedSipActiveTab[sip.sip_id] === 'resume'
                                  ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                                  : 'bg-slate-800/60 border-slate-700/50 text-slate-400 hover:text-emerald-300 hover:border-emerald-500/30'
                              }`}
                            >
                              <Play className="h-3 w-3" /> Resume SIP
                            </button>
                          )}
                          {sip.action_options.reallocate && (
                            <button
                              type="button"
                              onClick={() => setClosedSipActiveTab((prev) => ({ ...prev, [sip.sip_id]: 'reallocate' }))}
                              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition-all border ${
                                closedSipActiveTab[sip.sip_id] === 'reallocate'
                                  ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                                  : 'bg-slate-800/60 border-slate-700/50 text-slate-400 hover:text-purple-300 hover:border-purple-500/30'
                              }`}
                            >
                              <ArrowRightLeft className="h-3 w-3" /> Reallocate / Switch
                            </button>
                          )}
                          {sip.action_options.let_compound && (
                            <button
                              type="button"
                              onClick={() => setClosedSipActiveTab((prev) => ({ ...prev, [sip.sip_id]: 'let_compound' }))}
                              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition-all border ${
                                closedSipActiveTab[sip.sip_id] === 'let_compound'
                                  ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
                                  : 'bg-slate-800/60 border-slate-700/50 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30'
                              }`}
                            >
                              <TrendingUp className="h-3 w-3" /> Let Compound
                            </button>
                          )}
                        </div>

                        {/* Resume SIP Panel */}
                        {closedSipActiveTab[sip.sip_id] === 'resume' && sip.action_options.resume && (
                          <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2.5">
                            <div>
                              <h6 className="text-xs font-bold text-emerald-400">{sip.action_options.resume.title}</h6>
                              <p className="text-[10px] text-slate-400 mt-0.5">{sip.action_options.resume.description}</p>
                            </div>
                            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/15 text-[10px] text-emerald-300">
                              <strong>Rationale:</strong> {sip.action_options.resume.rationale}
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="text-[10px] text-slate-400 block mb-0.5">Monthly Amount (₹)</label>
                                <input
                                  type="number"
                                  value={resumeCustomAmount[sip.sip_id] ?? sip.action_options.resume.suggested_amount}
                                  onChange={(e) => setResumeCustomAmount((prev) => ({ ...prev, [sip.sip_id]: Number(e.target.value) }))}
                                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-[11px] text-slate-200"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] text-slate-400 block mb-0.5">SIP Day</label>
                                <input
                                  type="number"
                                  min={1}
                                  max={28}
                                  value={resumeCustomDay[sip.sip_id] ?? sip.action_options.resume.suggested_sip_day}
                                  onChange={(e) => setResumeCustomDay((prev) => ({ ...prev, [sip.sip_id]: Number(e.target.value) }))}
                                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-[11px] text-slate-200"
                                />
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleResumeSip(sip.sip_id, sip.action_options!.resume!.suggested_amount, sip.action_options!.resume!.suggested_sip_day)}
                              disabled={actionProcessingId === sip.sip_id}
                              className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
                            >
                              {actionProcessingId === sip.sip_id ? (
                                <RotateCcw className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Play className="h-3.5 w-3.5" />
                              )}
                              {actionProcessingId === sip.sip_id ? 'Resuming...' : 'Resume This SIP'}
                            </button>
                          </div>
                        )}

                        {/* Reallocate / Switch Panel */}
                        {closedSipActiveTab[sip.sip_id] === 'reallocate' && sip.action_options.reallocate && (
                          <div className="p-3 rounded-xl bg-purple-500/5 border border-purple-500/20 space-y-2.5">
                            <div>
                              <h6 className="text-xs font-bold text-purple-400">{sip.action_options.reallocate.title}</h6>
                              <p className="text-[10px] text-slate-400 mt-0.5">{sip.action_options.reallocate.description}</p>
                            </div>
                            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/15 text-[10px] text-purple-300">
                              <strong>Rationale:</strong> {sip.action_options.reallocate.rationale}
                            </div>

                            {/* Switch Mode Selector */}
                            <div>
                              <span className="text-[10px] font-semibold text-slate-400 block mb-1">Execution Mode</span>
                              <div className="flex gap-1.5 flex-wrap">
                                {(['full_switch', 'partial_switch', 'pause_and_redirect'] as const).map((mode) => (
                                  <button
                                    key={mode}
                                    type="button"
                                    onClick={() => setReallocateMode((prev) => ({ ...prev, [sip.sip_id]: mode }))}
                                    className={`px-2 py-1 rounded-lg text-[10px] font-medium border transition-all ${
                                      (reallocateMode[sip.sip_id] || 'full_switch') === mode
                                        ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                                        : 'bg-slate-800/60 border-slate-700/50 text-slate-500 hover:text-purple-300'
                                    }`}
                                  >
                                    {mode === 'full_switch' ? '🔄 Full Switch' : mode === 'partial_switch' ? '✂️ Partial Switch' : '⏸ Pause & Redirect'}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Switch Target Options */}
                            <div className="space-y-1.5">
                              <span className="text-[10px] font-semibold text-slate-400 block">Switch To</span>
                              {sip.action_options.reallocate.options.map((opt) => {
                                const isSelected = (reallocateSelectedTarget[sip.sip_id] || sip.action_options!.reallocate!.options[0]?.target_scheme_code) === opt.target_scheme_code;
                                return (
                                  <button
                                    key={opt.target_scheme_code}
                                    type="button"
                                    onClick={() => setReallocateSelectedTarget((prev) => ({ ...prev, [sip.sip_id]: opt.target_scheme_code }))}
                                    className={`w-full text-left p-2.5 rounded-xl border transition-all ${
                                      isSelected
                                        ? 'bg-purple-500/10 border-purple-500/40 ring-1 ring-purple-500/30'
                                        : opt.is_same_amc
                                        ? 'bg-emerald-500/5 border-emerald-500/25 hover:border-emerald-500/40'
                                        : 'bg-slate-900/40 border-slate-800/60 hover:border-purple-500/20'
                                    }`}
                                  >
                                    <div className="flex items-start justify-between gap-2">
                                      <div>
                                        <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                                          {opt.is_same_amc ? (
                                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                                              <Zap className="h-2.5 w-2.5" /> Same AMC (Free & Instant Switch)
                                            </span>
                                          ) : (
                                            <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                                              🏦 Inter-AMC Switch
                                            </span>
                                          )}
                                          {opt.turnaround_time && (
                                            <span className="text-[9px] text-cyan-400/90 font-medium">
                                              • {opt.turnaround_time}
                                            </span>
                                          )}
                                        </div>
                                        <span className="text-[11px] font-bold text-white block">{opt.target_scheme_name}</span>
                                        <span className="text-[10px] text-slate-400">{opt.fund_house} • {opt.category}</span>
                                      </div>
                                      <div className="text-right flex-shrink-0">
                                        <span className="text-[11px] font-bold text-emerald-400 block">{opt.trailing_3y_cagr.toFixed(1)}%</span>
                                        <span className="text-[9px] text-slate-500">3Y CAGR</span>
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">★ {opt.crisil_rating}</span>
                                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">ER: {opt.expense_ratio}%</span>
                                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">Overlap: {opt.overlap_with_current_pct}%</span>
                                    </div>
                                    {opt.amc_advantage && (
                                      <p className={`text-[9px] mt-1.5 leading-relaxed ${
                                        opt.is_same_amc ? 'text-emerald-300/90 font-medium' : 'text-slate-400'
                                      }`}>
                                        {opt.amc_advantage}
                                      </p>
                                    )}
                                    <p className="text-[9px] text-purple-300/80 mt-0.5">{opt.comparison_advantage}</p>
                                  </button>
                                );
                              })}
                            </div>

                            <button
                              type="button"
                              onClick={() =>
                                handleReallocateSip(
                                  sip.sip_id,
                                  sip.action_options!.reallocate!.options[0]?.target_scheme_code,
                                  sip.monthly_amount
                                )
                              }
                              disabled={actionProcessingId === sip.sip_id || (!reallocateSelectedTarget[sip.sip_id] && !sip.action_options.reallocate.options[0])}
                              className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
                            >
                              {actionProcessingId === sip.sip_id ? (
                                <RotateCcw className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <ArrowRightLeft className="h-3.5 w-3.5" />
                              )}
                              {actionProcessingId === sip.sip_id ? 'Processing...' : 'Execute Switch'}
                            </button>
                          </div>
                        )}

                        {/* Let Compound Panel */}
                        {closedSipActiveTab[sip.sip_id] === 'let_compound' && sip.action_options.let_compound && (
                          <div className="p-3 rounded-xl bg-cyan-500/5 border border-cyan-500/20 space-y-2.5">
                            <div>
                              <h6 className="text-xs font-bold text-cyan-400">{sip.action_options.let_compound.title}</h6>
                              <p className="text-[10px] text-slate-400 mt-0.5">{sip.action_options.let_compound.description}</p>
                            </div>
                            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/15 text-[10px] text-cyan-300">
                              <strong>Rationale:</strong> {sip.action_options.let_compound.rationale}
                            </div>
                            <div>
                              <span className="text-[10px] font-semibold text-slate-400 block mb-1.5">
                                Projected Value at {sip.action_options.let_compound.expected_cagr_pct}% CAGR
                              </span>
                              <div className="grid grid-cols-4 gap-2 text-center">
                                {[
                                  { label: '1 Year', val: sip.action_options.let_compound.projections.years_1 },
                                  { label: '3 Years', val: sip.action_options.let_compound.projections.years_3 },
                                  { label: '5 Years', val: sip.action_options.let_compound.projections.years_5 },
                                  { label: '10 Years', val: sip.action_options.let_compound.projections.years_10 },
                                ].map((p) => (
                                  <div key={p.label} className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/60">
                                    <span className="text-[9px] text-slate-500 block">{p.label}</span>
                                    <span className="text-[11px] font-bold text-cyan-300">
                                      ₹{p.val.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                            <div className="text-[10px] text-slate-500 flex items-center gap-1">
                              <Sparkles className="h-3 w-3 text-cyan-400" />
                              No action required — your existing units will continue to grow.
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cross-Fund Stock Overlap Matrix */}
          {portfolioData?.overlap_analysis && portfolioData.overlap_analysis.common_holdings && (
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Layers className="h-4 w-4 text-purple-400" />
                    Cross-Fund Stock Overlap Diagnostic
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Average Pairwise Stock Overlap: <strong className="text-purple-300">{portfolioData.overlap_analysis.average_overlap_pct}%</strong>
                  </p>
                </div>
                {portfolioData.overlap_analysis.high_overlap_warning && (
                  <span className="px-2.5 py-1 rounded-lg bg-rose-500/15 text-rose-400 border border-rose-500/30 text-xs font-semibold flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" /> High Redundancy Warning
                  </span>
                )}
              </div>

              {/* Common Holdings across funds */}
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase">Heavily Overlapping Stocks</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                  {portfolioData.overlap_analysis.common_holdings.slice(0, 6).map((item, idx) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/60 text-xs flex justify-between items-center">
                      <div>
                        <p className="font-bold text-white">{item.stock}</p>
                        <p className="text-[10px] text-slate-400">Held across {item.funds_holding_count} of your funds</p>
                      </div>
                      <span className="font-mono text-purple-400 font-bold">{item.avg_weight_pct}% avg</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Check-In History Drawer */}
          {portfolioData && portfolioData.checkin_history && portfolioData.checkin_history.length > 0 && (
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setShowCheckinHistory(!showCheckinHistory)}
                  className="flex items-center gap-2 text-xs font-bold text-slate-300 hover:text-white transition-colors"
                >
                  <History className="h-4 w-4 text-purple-400" />
                  Monthly SIP Debit & Check-in History ({portfolioData.checkin_history.length})
                  {showCheckinHistory ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                </button>
                <span className="text-[11px] text-slate-400">Past payment ledger records</span>
              </div>

              {showCheckinHistory && (
                <div className="overflow-x-auto pt-2">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                        <th className="py-2">Scheme Name</th>
                        <th className="py-2">Category</th>
                        <th className="py-2">Due Date</th>
                        <th className="py-2">Monthly Amount</th>
                        <th className="py-2">Payment Status</th>
                        <th className="py-2 text-right">Confirmed Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {portfolioData.checkin_history.map((h) => (
                        <tr key={h.checkin_id} className="hover:bg-slate-800/30">
                          <td className="py-2.5 font-semibold text-white">{h.scheme_name}</td>
                          <td className="py-2.5 text-slate-400">{h.category}</td>
                          <td className="py-2.5 text-slate-300">{h.due_date}</td>
                          <td className="py-2.5 font-bold text-white">₹{h.amount.toLocaleString('en-IN')}</td>
                          <td className="py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                h.status === 'PAID'
                                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                                  : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                              }`}
                            >
                              {h.status === 'PAID' ? '✓ PAID' : '✕ SKIPPED'}
                            </span>
                          </td>
                          <td className="py-2.5 text-right text-slate-400">{h.confirmed_date || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 5. POWER AGE (FIRE FREEDOM) SIMULATOR & INTERACTIVE ACCELERATOR       */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'power_age' && (
        <div className="space-y-6">
          {/* Header Banner */}
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2.5 py-0.5 rounded-full bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold tracking-wider uppercase flex items-center gap-1">
                    <Zap className="h-3 w-3 text-amber-400" />
                    PowerUp Money Engine • FIRE Freedom
                  </span>
                  <span className="text-[11px] text-slate-400">Institutional Compounding Simulation</span>
                </div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  Power Age (Financial Freedom) Calculator
                </h2>
                <p className="text-xs text-slate-400 mt-1 max-w-3xl">
                  Find your Power Age — the exact age when your mutual fund portfolio and SIP compounding produce enough passive income via Systematic Withdrawal (SWP) to fund your lifestyle for life without touching your principal.
                </p>
              </div>

              {portfolioData && ((portfolioData.current_value && portfolioData.current_value > 0) || (portfolioData.total_portfolio_value && portfolioData.total_portfolio_value > 0)) && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      const portVal = Math.round(portfolioData.current_value || portfolioData.total_portfolio_value || 0);
                      const portSip = Math.round(portfolioData.monthly_sip_run_rate || portfolioData.total_monthly_sip || 0);
                      setPowerAgeInputCorpus(portVal);
                      setPowerAgeInputSip(portSip);
                      handleCalculatePowerAge({
                        current_corpus: portVal,
                        monthly_sip: portSip,
                      });
                    }}
                    className="px-3 py-1.5 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
                    title="Sync inputs with your saved mutual fund portfolio and active monthly SIP"
                  >
                    <Coins className="h-3.5 w-3.5 text-purple-400" />
                    Sync with Portfolio (₹{Math.round(portfolioData.current_value || portfolioData.total_portfolio_value || 0).toLocaleString('en-IN')})
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Parameter Form & Sliders (5 cols) */}
            <div className="lg:col-span-5 space-y-4">
              <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-4 shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Sliders className="h-4 w-4 text-amber-400" />
                    Freedom Assumptions
                  </h3>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Customizable</span>
                </div>

                {/* 1. Current Age */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <label className="text-slate-300 font-medium">Current Age</label>
                    <span className="font-bold text-amber-400 font-mono text-sm">{powerAgeInputAge} yrs</span>
                  </div>
                  <input
                    type="range"
                    min="18"
                    max="65"
                    step="1"
                    value={powerAgeInputAge}
                    onChange={(e) => setPowerAgeInputAge(Number(e.target.value))}
                    className="w-full accent-amber-400 bg-slate-950 rounded-lg cursor-pointer h-1.5"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>18</span>
                    <span>40</span>
                    <span>65</span>
                  </div>
                </div>

                {/* 2. Current Portfolio Corpus */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <label className="text-slate-300 font-medium">Current Corpus (₹)</label>
                    <span className="font-bold text-white font-mono">₹{powerAgeInputCorpus.toLocaleString('en-IN')}</span>
                  </div>
                  <input
                    type="number"
                    step="10000"
                    min="0"
                    value={powerAgeInputCorpus}
                    onChange={(e) => setPowerAgeInputCorpus(Math.max(0, Number(e.target.value)))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-amber-500/50"
                  />
                </div>

                {/* 3. Monthly SIP Outflow */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <label className="text-slate-300 font-medium">Monthly SIP (₹)</label>
                    <span className="font-bold text-emerald-400 font-mono">₹{powerAgeInputSip.toLocaleString('en-IN')}/mo</span>
                  </div>
                  <input
                    type="number"
                    step="1000"
                    min="0"
                    value={powerAgeInputSip}
                    onChange={(e) => setPowerAgeInputSip(Math.max(0, Number(e.target.value)))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-amber-500/50"
                  />
                </div>

                {/* 4. Annual Step-Up % (PowerUp Accelerator) */}
                <div className="space-y-1.5 p-3 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20">
                  <div className="flex justify-between items-center text-xs">
                    <label className="text-amber-300 font-semibold flex items-center gap-1">
                      <Zap className="h-3 w-3 text-amber-400" />
                      Annual SIP Step-Up (%)
                    </label>
                    <span className="font-bold text-amber-300 font-mono text-sm">+{powerAgeInputStepUp}% / yr</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="25"
                    step="1"
                    value={powerAgeInputStepUp}
                    onChange={(e) => setPowerAgeInputStepUp(Number(e.target.value))}
                    className="w-full accent-amber-400 bg-slate-950 rounded-lg cursor-pointer h-1.5"
                  />
                  <div className="flex justify-between text-[10px] text-amber-300/60">
                    <span>0% (Flat)</span>
                    <span>10% (Optimal)</span>
                    <span>25% (Aggressive)</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">
                    PowerUp Secret: Increasing your SIP by +10% annually with salary hikes can shave off 4 to 6 years to your Power Age!
                  </p>
                </div>

                {/* 5. Expected Portfolio CAGR */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <label className="text-slate-300 font-medium">Expected Portfolio CAGR (%)</label>
                    <span className="font-bold text-sky-400 font-mono text-sm">{powerAgeInputCagr}% p.a.</span>
                  </div>
                  <input
                    type="range"
                    min="8"
                    max="18"
                    step="0.5"
                    value={powerAgeInputCagr}
                    onChange={(e) => setPowerAgeInputCagr(Number(e.target.value))}
                    className="w-full accent-sky-400 bg-slate-950 rounded-lg cursor-pointer h-1.5"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>8% (Debt/Hybrid)</span>
                    <span>13.5% (Equity)</span>
                    <span>18% (Small Cap)</span>
                  </div>
                </div>

                {/* 6. Target Monthly Living Expenses Today */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <label className="text-slate-300 font-medium">Monthly Living Expenses Today (₹)</label>
                    <span className="font-bold text-white font-mono">₹{powerAgeInputExpense.toLocaleString('en-IN')}/mo</span>
                  </div>
                  <input
                    type="number"
                    step="5000"
                    min="10000"
                    value={powerAgeInputExpense}
                    onChange={(e) => setPowerAgeInputExpense(Math.max(5000, Number(e.target.value)))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-amber-500/50"
                  />
                </div>

                {/* 7. Inflation & SWR Row */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <label className="text-slate-300 font-medium">Inflation (%)</label>
                      <span className="font-bold text-rose-400 font-mono">{powerAgeInputInflation}%</span>
                    </div>
                    <input
                      type="range"
                      min="4"
                      max="9"
                      step="0.5"
                      value={powerAgeInputInflation}
                      onChange={(e) => setPowerAgeInputInflation(Number(e.target.value))}
                      className="w-full accent-rose-400 bg-slate-950 rounded-lg cursor-pointer h-1.5"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <label className="text-slate-300 font-medium">SWR (%)</label>
                      <span className="font-bold text-purple-400 font-mono">{powerAgeInputSwr}%</span>
                    </div>
                    <input
                      type="range"
                      min="3"
                      max="6"
                      step="0.25"
                      value={powerAgeInputSwr}
                      onChange={(e) => setPowerAgeInputSwr(Number(e.target.value))}
                      className="w-full accent-purple-400 bg-slate-950 rounded-lg cursor-pointer h-1.5"
                    />
                  </div>
                </div>

                {/* Recalculate Button */}
                <button
                  type="button"
                  onClick={() => handleCalculatePowerAge()}
                  disabled={isLoadingPowerAge}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 transition-all cursor-pointer"
                >
                  <Zap className="h-4 w-4" />
                  {isLoadingPowerAge ? 'Simulating Compounding Curves...' : 'Recalculate Power Age & Trajectory'}
                </button>
              </div>
            </div>

            {/* Right Column: Results & Interactive SVG Visualizer (7 cols) */}
            <div className="lg:col-span-7 space-y-5">
              {powerAgeResult ? (
                <>
                  {/* Hero Milestone Card */}
                  <div className="bg-gradient-to-br from-amber-500/15 via-slate-900 to-slate-950 rounded-2xl border border-amber-500/40 p-6 space-y-4 shadow-xl">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-400 bg-amber-500/20 px-2.5 py-0.5 rounded-full border border-amber-500/30">
                          🌟 Financial Freedom Point
                        </span>
                        <h3 className="text-3xl font-extrabold text-white mt-1.5 flex items-center gap-2">
                          Power Age: <span className="text-amber-300">Age {powerAgeResult.power_age}</span>
                          <span className="text-sm font-normal text-slate-400">({powerAgeResult.financial_freedom_year})</span>
                        </h3>
                      </div>

                      <div className="text-right">
                        <span className="text-xs text-slate-400 block">Countdown to Freedom</span>
                        <span className="text-xl font-black text-emerald-400">
                          {powerAgeResult.years_to_freedom} {powerAgeResult.years_to_freedom === 1 ? 'Year' : 'Years'}
                        </span>
                      </div>
                    </div>

                    {/* Step-Up Advantage Callout */}
                    <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-center gap-3">
                      <div className="h-9 w-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
                        <Zap className="h-5 w-5 text-amber-300" />
                      </div>
                      <div className="text-xs text-amber-200">
                        <p className="font-semibold">
                          Step-Up Acceleration: <strong className="text-white">+{powerAgeResult.years_saved_by_step_up} Years Earlier</strong>
                        </p>
                        <p className="text-[11px] text-amber-300/80 mt-0.5">
                          With a +{powerAgeResult.assumptions.annual_step_up_pct}% annual step-up, you reach freedom at Age {powerAgeResult.power_age} instead of Age {powerAgeResult.standard_power_age} (Flat SIP).
                        </p>
                      </div>
                    </div>

                    {/* 4 Financial Freedom KPIs */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Target Corpus</span>
                        <p className="text-base font-bold text-white mt-0.5 font-mono">
                          ₹{(powerAgeResult.corpus_at_power_age / 10000000).toFixed(2)} Cr
                        </p>
                        <p className="text-[10px] text-slate-500">₹{powerAgeResult.corpus_at_power_age.toLocaleString('en-IN')}</p>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Monthly Expense</span>
                        <p className="text-base font-bold text-amber-300 mt-0.5 font-mono">
                          ₹{Math.round(powerAgeResult.monthly_expenses_at_power_age).toLocaleString('en-IN')}
                        </p>
                        <p className="text-[10px] text-slate-500">Inflation-adjusted at age {powerAgeResult.power_age}</p>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">SWP Passive Income</span>
                        <p className="text-base font-bold text-emerald-400 mt-0.5 font-mono">
                          ₹{Math.round(powerAgeResult.monthly_passive_income_swp).toLocaleString('en-IN')}
                        </p>
                        <p className="text-[10px] text-slate-500">At {powerAgeResult.assumptions.swr_pct}% safe withdrawal</p>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Current SIP</span>
                        <p className="text-base font-bold text-sky-400 mt-0.5 font-mono">
                          ₹{powerAgeResult.assumptions.monthly_sip.toLocaleString('en-IN')}/mo
                        </p>
                        <p className="text-[10px] text-slate-500">+{powerAgeResult.assumptions.annual_step_up_pct}% step-up/yr</p>
                      </div>
                    </div>
                  </div>

                  {/* Interactive SVG Compounding & Freedom Trajectory Chart */}
                  <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div>
                        <h4 className="text-sm font-bold text-white flex items-center gap-2">
                          <TrendingUp className="h-4 w-4 text-emerald-400" />
                          Compounding Trajectory: Growth Curves vs FIRE Threshold
                        </h4>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Visualizes the exponential inflection point where step-up compounding overtakes expenses.
                        </p>
                      </div>

                      {/* Chart Legend */}
                      <div className="flex flex-wrap items-center gap-3 text-[11px]">
                        <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                          <span className="w-2.5 h-1 bg-emerald-400 rounded"></span>
                          Step-Up SIP
                        </span>
                        <span className="flex items-center gap-1.5 text-sky-400 font-semibold">
                          <span className="w-2.5 h-1 bg-sky-400 rounded border-b border-dashed border-sky-400"></span>
                          Flat SIP
                        </span>
                        <span className="flex items-center gap-1.5 text-amber-400 font-semibold">
                          <span className="w-2.5 h-1 bg-amber-400 rounded"></span>
                          FIRE Target
                        </span>
                      </div>
                    </div>

                    {/* SVG Chart */}
                    {(() => {
                      const svgW = 760;
                      const svgH = 280;
                      const padL = 65;
                      const padR = 25;
                      const padT = 20;
                      const padB = 30;
                      const chartW = svgW - padL - padR;
                      const chartH = svgH - padT - padB;

                      const chartPoints = (powerAgeResult.trajectory || []).filter(
                        (p) => p.age <= Math.min(80, Math.max(powerAgeResult.power_age + 12, 60))
                      );

                      if (chartPoints.length < 2) return null;

                      const maxY = Math.max(
                        1,
                        ...chartPoints.map((p) => Math.max(p.accumulated_corpus, p.target_fire_corpus, p.flat_sip_corpus))
                      ) * 1.15;

                      const getX = (idx: number) => padL + (idx / (chartPoints.length - 1)) * chartW;
                      const getY = (val: number) => padT + chartH - (Math.max(0, val) / maxY) * chartH;

                      const areaAcc = `M ${getX(0)} ${padT + chartH} ` +
                        chartPoints.map((p, idx) => `L ${getX(idx)} ${getY(p.accumulated_corpus)}`).join(' ') +
                        ` L ${getX(chartPoints.length - 1)} ${padT + chartH} Z`;

                      const lineAcc = chartPoints.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(idx)} ${getY(p.accumulated_corpus)}`).join(' ');
                      const lineFlat = chartPoints.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(idx)} ${getY(p.flat_sip_corpus)}`).join(' ');
                      const lineTarget = chartPoints.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(idx)} ${getY(p.target_fire_corpus)}`).join(' ');

                      const freeIdx = chartPoints.findIndex((p) => p.age === powerAgeResult.power_age);
                      const freePoint = freeIdx >= 0 ? chartPoints[freeIdx] : null;

                      // Y ticks (4 levels)
                      const yTicks = [0, maxY * 0.33, maxY * 0.66, maxY];

                      return (
                        <div className="w-full overflow-x-auto">
                          <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full h-auto min-w-[550px]">
                            <defs>
                              <linearGradient id="powerAgeAreaGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
                                <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                              </linearGradient>
                            </defs>

                            {/* Horizontal Gridlines & Y-axis labels */}
                            {yTicks.map((yVal, i) => {
                              const yPos = getY(yVal);
                              const label = yVal >= 10000000
                                ? `₹${(yVal / 10000000).toFixed(1)} Cr`
                                : `₹${(yVal / 100000).toFixed(0)} L`;
                              return (
                                <g key={i}>
                                  <line
                                    x1={padL}
                                    y1={yPos}
                                    x2={svgW - padR}
                                    y2={yPos}
                                    stroke="#1e293b"
                                    strokeWidth="1"
                                    strokeDasharray={i === 0 ? undefined : '3,3'}
                                  />
                                  <text
                                    x={padL - 8}
                                    y={yPos + 4}
                                    textAnchor="end"
                                    fill="#64748b"
                                    fontSize="10"
                                    fontFamily="monospace"
                                  >
                                    {label}
                                  </text>
                                </g>
                              );
                            })}

                            {/* Accumulated Area */}
                            <path d={areaAcc} fill="url(#powerAgeAreaGrad)" />

                            {/* Flat SIP Line (dashed blue) */}
                            <path
                              d={lineFlat}
                              fill="none"
                              stroke="#38bdf8"
                              strokeWidth="2"
                              strokeDasharray="5,4"
                            />

                            {/* FIRE Target Line (amber) */}
                            <path
                              d={lineTarget}
                              fill="none"
                              stroke="#f59e0b"
                              strokeWidth="2"
                              strokeDasharray="4,3"
                            />

                            {/* Accumulated Line (solid emerald) */}
                            <path
                              d={lineAcc}
                              fill="none"
                              stroke="#10b981"
                              strokeWidth="2.5"
                            />

                            {/* Power Age Vertical Beacon Marker */}
                            {freePoint && freeIdx >= 0 && (
                              <g>
                                <line
                                  x1={getX(freeIdx)}
                                  y1={padT}
                                  x2={getX(freeIdx)}
                                  y2={padT + chartH}
                                  stroke="#f59e0b"
                                  strokeWidth="1.5"
                                  strokeDasharray="4,4"
                                />
                                <circle
                                  cx={getX(freeIdx)}
                                  cy={getY(freePoint.accumulated_corpus)}
                                  r="6"
                                  fill="#10b981"
                                  stroke="#f59e0b"
                                  strokeWidth="2.5"
                                />
                                <circle
                                  cx={getX(freeIdx)}
                                  cy={getY(freePoint.accumulated_corpus)}
                                  r="11"
                                  fill="none"
                                  stroke="#f59e0b"
                                  strokeWidth="1"
                                  opacity="0.6"
                                />
                                <text
                                  x={getX(freeIdx)}
                                  y={padT + 12}
                                  textAnchor="middle"
                                  fill="#fbbf24"
                                  fontSize="10"
                                  fontWeight="bold"
                                  className="bg-slate-900"
                                >
                                  ⚡ Age {powerAgeResult.power_age}
                                </text>
                              </g>
                            )}

                            {/* X-axis ticks (Age) */}
                            {chartPoints.map((p, idx) => {
                              const step = Math.ceil(chartPoints.length / 8);
                              if (idx % step !== 0 && idx !== chartPoints.length - 1 && idx !== freeIdx) return null;
                              return (
                                <g key={idx}>
                                  <text
                                    x={getX(idx)}
                                    y={padT + chartH + 16}
                                    textAnchor="middle"
                                    fill={idx === freeIdx ? '#fbbf24' : '#64748b'}
                                    fontSize="10"
                                    fontWeight={idx === freeIdx ? 'bold' : 'normal'}
                                  >
                                    {p.age}
                                  </text>
                                </g>
                              );
                            })}
                          </svg>
                        </div>
                      );
                    })()}

                    {/* Bottom Explanation Footer */}
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <Activity className="h-3.5 w-3.5 text-emerald-400" />
                        Safe Withdrawal Principal Sustainability:
                      </span>
                      <span className="text-slate-200">
                        At age {powerAgeResult.power_age}, corpus yields ₹{Math.round(powerAgeResult.monthly_passive_income_swp).toLocaleString('en-IN')}/mo vs expenses ₹{Math.round(powerAgeResult.monthly_expenses_at_power_age).toLocaleString('en-IN')}/mo.
                      </span>
                    </div>
                  </div>

                  {/* Year-by-Year Freedom Compounding Ledger */}
                  <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => setShowYearByYearTable(!showYearByYearTable)}
                        className="flex items-center gap-2 text-xs font-bold text-slate-300 hover:text-white transition-colors cursor-pointer"
                      >
                        <History className="h-4 w-4 text-amber-400" />
                        Year-by-Year Freedom Compounding Ledger ({powerAgeResult.trajectory.length} yrs)
                        {showYearByYearTable ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      </button>
                      <span className="text-[11px] text-slate-400">Month-by-month compounding snapshot</span>
                    </div>

                    {showYearByYearTable && (
                      <div className="overflow-x-auto pt-2">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                              <th className="py-2">Age</th>
                              <th className="py-2">Year</th>
                              <th className="py-2 text-right">Step-Up Corpus</th>
                              <th className="py-2 text-right">Flat SIP Corpus</th>
                              <th className="py-2 text-right">Target FIRE Corpus</th>
                              <th className="py-2 text-right">Monthly Expenses</th>
                              <th className="py-2 text-right">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 text-slate-300">
                            {powerAgeResult.trajectory.map((p) => {
                              const isPowerAgeRow = p.age === powerAgeResult.power_age;
                              return (
                                <tr
                                  key={p.age}
                                  className={`hover:bg-slate-800/30 ${
                                    isPowerAgeRow ? 'bg-amber-500/10 font-bold text-amber-200' : ''
                                  }`}
                                >
                                  <td className="py-2 font-mono">
                                    {p.age} {isPowerAgeRow && '⚡'}
                                  </td>
                                  <td className="py-2 text-slate-400">{p.year}</td>
                                  <td className="py-2 text-right font-mono font-semibold text-emerald-400">
                                    ₹{p.accumulated_corpus.toLocaleString('en-IN')}
                                  </td>
                                  <td className="py-2 text-right font-mono text-sky-300">
                                    ₹{p.flat_sip_corpus.toLocaleString('en-IN')}
                                  </td>
                                  <td className="py-2 text-right font-mono text-amber-300">
                                    ₹{p.target_fire_corpus.toLocaleString('en-IN')}
                                  </td>
                                  <td className="py-2 text-right font-mono text-slate-400">
                                    ₹{Math.round(p.monthly_expenses).toLocaleString('en-IN')}/mo
                                  </td>
                                  <td className="py-2 text-right">
                                    {p.is_financially_free ? (
                                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                                        ✓ FREE
                                      </span>
                                    ) : (
                                      <span className="text-[10px] text-slate-500">
                                        Accumulating
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-8 text-center space-y-3">
                  <Zap className="h-8 w-8 text-amber-400 mx-auto animate-pulse" />
                  <h4 className="text-base font-bold text-white">Simulating Your Power Age...</h4>
                  <p className="text-xs text-slate-400">
                    Calculating month-by-month compounding curves and safe withdrawal rates across your investment horizon.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add SIP Schedule */}
      {showAddSipModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              {editingSipId ? (
                <>
                  <Pencil className="h-5 w-5 text-purple-400" />
                  Edit SIP Holding & Recorded Details
                </>
              ) : (
                <>
                  <PlusCircle className="h-5 w-5 text-purple-400" />
                  Add SIP Schedule & Custom Valuation
                </>
              )}
            </h3>
            <p className="text-xs text-slate-400">
              {editingSipId
                ? 'Correct scheme, amount, dates, skipped months checklist, or custom invested/current valuation for this holding.'
                : 'Add your mutual fund investment. You can optionally override total invested amount and current market value to reflect your actual holdings.'}
            </p>
            <form onSubmit={handleSaveSip} className="space-y-3">
              {/* Searchable Scheme Picker */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  Select Mutual Fund Scheme (Search Any Fund in India)
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Type fund name or AMC (e.g. Tata, SBI, Quant, Axis, Bandhan)..."
                    value={modalSearchQuery}
                    onChange={(e) => handleModalSearch(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
                  />
                  {isSearchingModal && (
                    <span className="absolute right-3 top-2.5 text-[10px] text-purple-400 animate-pulse font-medium">
                      Searching...
                    </span>
                  )}
                </div>

                {/* Selected Fund Confirmation Badge */}
                {newSipScheme && (
                  <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-between">
                    <div className="min-w-0 pr-2">
                      <span className="text-[10px] text-purple-400 font-bold uppercase tracking-wider block">
                        Selected Fund
                      </span>
                      <span className="text-xs font-semibold text-white truncate block">
                        {selectedSchemeName}
                      </span>
                      <span className="text-[10px] text-slate-400 block mt-0.5">
                        Scheme Code: <strong className="text-slate-300">{newSipScheme}</strong>
                      </span>
                    </div>
                    <CheckCircle2 className="h-5 w-5 text-purple-400 flex-shrink-0" />
                  </div>
                )}

                {/* Matching Funds Picker List */}
                <div className="max-h-40 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/80 divide-y divide-slate-800/60">
                  {(modalSearchResults.length > 0 ? modalSearchResults : searchResults).map((f) => {
                    const isSelected = f.scheme_code === newSipScheme;
                    return (
                      <div
                        key={f.scheme_code}
                        onClick={() => {
                          setNewSipScheme(f.scheme_code);
                          setSelectedSchemeName(f.scheme_name);
                        }}
                        className={`p-2.5 text-xs cursor-pointer transition-all flex items-center justify-between gap-2 hover:bg-slate-900 ${
                          isSelected ? 'bg-purple-500/15 text-purple-200' : 'text-slate-300'
                        }`}
                      >
                        <div className="min-w-0">
                          <p className="font-medium text-white truncate text-xs">{f.scheme_name}</p>
                          <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                            <span className="text-emerald-400 font-medium">{f.category}</span>
                            <span>•</span>
                            <span>{f.fund_house}</span>
                          </div>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 flex-shrink-0">
                          {f.crisil_rating != null ? `★ ${f.crisil_rating}` : 'Rating unavailable'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Monthly Amount (₹)</label>
                <input
                  type="number"
                  value={newSipAmount}
                  onChange={(e) => setNewSipAmount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Start Date</label>
                  <input
                    type="date"
                    value={newSipStartDate}
                    onChange={(e) => handleStartDateChange(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                    required
                  />
                  {newSipStartDate && (
                    <span className="text-[10px] text-cyan-400 mt-0.5 inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" /> SIP Day: {newSipDay}th of every month
                    </span>
                  )}
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Status</label>
                  <select
                    value={newSipStatus}
                    onChange={(e) => setNewSipStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="PAUSED">PAUSED</option>
                    <option value="CLOSED">CLOSED</option>
                  </select>
                </div>
              </div>

              {newSipStatus !== 'ACTIVE' && (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Stopped / End Date</label>
                  <input
                    type="date"
                    value={newSipEndDate}
                    onChange={(e) => setNewSipEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                  />
                </div>
              )}

              {/* Month-by-Month Installment Checklist */}
              {newSipStartDate && (() => {
                const months = getInstallmentMonths(newSipStartDate, newSipEndDate || undefined);
                if (months.length === 0) return null;
                const paidCount = months.length - skippedMonths.length;
                return (
                  <div className="border border-cyan-500/20 bg-cyan-500/5 rounded-xl p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-cyan-400 flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        SIP Installment Checklist
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {paidCount} paid / {skippedMonths.length} skipped of {months.length} months
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Click a month to mark it as skipped. Skipped months won&apos;t count toward invested amount calculations.
                    </p>
                    <div className="flex flex-wrap gap-1.5 max-h-[160px] overflow-y-auto">
                      {months.map((m) => {
                        const isSkipped = skippedMonths.includes(m.key);
                        return (
                          <button
                            key={m.key}
                            type="button"
                            onClick={() => toggleSkippedMonth(m.key)}
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium transition-all cursor-pointer border ${
                              isSkipped
                                ? 'bg-rose-500/15 border-rose-500/30 text-rose-400 hover:bg-rose-500/25'
                                : 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400 hover:bg-emerald-500/20'
                            }`}
                          >
                            {isSkipped ? (
                              <Square className="h-3 w-3" />
                            ) : (
                              <CheckSquare className="h-3 w-3" />
                            )}
                            {m.dateDisplay}
                          </button>
                        );
                      })}
                    </div>
                    {skippedMonths.length > 0 && (
                      <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
                        <span className="text-[10px] text-rose-400">
                          ⚠ {skippedMonths.length} month{skippedMonths.length > 1 ? 's' : ''} skipped — XIRR will be adjusted accordingly
                        </span>
                        <button
                          type="button"
                          onClick={() => setSkippedMonths([])}
                          className="text-[10px] text-slate-400 hover:text-cyan-400 underline"
                        >
                          Reset all
                        </button>
                      </div>
                    )}
                  </div>
                );
              })()}

              <div>
                <label className="text-xs text-slate-400 block mb-1">Annual Step-Up (%)</label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  value={newSipStepUp}
                  onChange={(e) => setNewSipStepUp(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                />
              </div>

              {/* Custom Overrides for Actual Investor Values */}
              <div className="border-t border-slate-800 pt-3 space-y-2">
                <span className="text-[11px] font-semibold text-purple-400 block">
                  Custom Value Overrides (Optional)
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Actual Total Invested (₹)</label>
                    <input
                      type="number"
                      placeholder="e.g. 120000"
                      value={customInvested}
                      onChange={(e) => setCustomInvested(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-600"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Actual Current Value (₹)</label>
                    <input
                      type="number"
                      placeholder="e.g. 155000"
                      value={customCurrentValue}
                      onChange={(e) => setCustomCurrentValue(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-600"
                    />
                  </div>
                </div>
                <p className="text-[10px] text-slate-500">
                  Leave empty to calculate automatically from the start date and latest AMFI NAV.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddSipModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-purple-500 hover:bg-purple-600 text-white text-xs font-bold"
                >
                  {editingSipId ? 'Save Changes' : 'Add to Portfolio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Modal: Save Portfolio & Edit Name/Notes */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <BookmarkCheck className="h-5 w-5 text-indigo-400" />
                Save Mutual Fund Portfolio
              </h3>
              <button
                onClick={() => setShowSaveModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Name your portfolio and customize your investment notes. All active SIP schedules, custom unit overrides, and payment records will be saved to your cloud profile.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Portfolio Name</label>
                <input
                  type="text"
                  value={portfolioName}
                  onChange={(e) => setPortfolioName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                  placeholder="e.g. Core Long-Term Wealth"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Investment Notes (Optional)</label>
                <textarea
                  value={portfolioNotes}
                  onChange={(e) => setPortfolioNotes(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-600"
                  placeholder="e.g. 10% annual step-up target, allocated for 15Y financial independence"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowSaveModal(false)}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSavePortfolio(portfolioName, portfolioNotes)}
                disabled={isSavingPortfolio}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-indigo-500/20"
              >
                <Save className="h-4 w-4" />
                {isSavingPortfolio ? 'Saving...' : 'Save Portfolio'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
