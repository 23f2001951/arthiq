// IIM — TradingView lightweight-charts candlestick chart wrapper
// Renders: Candlesticks + EMA21 + VWAP + Supertrend + Volume bars
// Signal markers: ▲ BUY / ▼ SELL with horizontal SL / T1 / T2 lines

import { useEffect, useMemo, useRef } from 'react';
import {
  createChart,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  ColorType,
  LineStyle,
  Time,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from 'lightweight-charts';
import type { Candle, ChartData, IntradaySignal } from '../types/intraday';

interface IntradayChartProps {
  chartData: ChartData | null;
  signals: IntradaySignal[];
  symbol: string;
  height?: number;
}

const TERMINAL_COLORS = {
  bg: '#0f1117',
  grid: '#1e2330',
  text: '#94a3b8',
  border: '#1e2330',
  upCandle: '#22c55e',
  downCandle: '#ef4444',
  wickUp: '#22c55e',
  wickDown: '#ef4444',
  ema21: '#f59e0b',
  vwap: '#818cf8',
  supertrendBull: '#22c55e',
  supertrendBear: '#ef4444',
  sl: '#ef444488',
  t1: '#22c55e88',
  t2: '#10b98188',
  volUp: '#22c55e44',
  volDown: '#ef444444',
};
const RESEARCH_COLORS = {
  bg: '#fbf9f3', grid: '#e9e5da', text: '#74786e', border: '#d9d5ca',
  upCandle: '#21664d', downCandle: '#a8443c', wickUp: '#21664d', wickDown: '#a8443c',
  ema21: '#9a742d', vwap: '#53694b', supertrendBull: '#21664d', supertrendBear: '#a8443c',
  sl: '#a8443c88', t1: '#21664d88', t2: '#2f806188', volUp: '#21664d35', volDown: '#a8443c35',
};

function toTimestamp(iso: string): Time {
  return Math.floor(new Date(iso).getTime() / 1000) as Time;
}

export default function IntradayChart({
  chartData,
  signals,
  symbol,
  height = 480,
}: IntradayChartProps) {
  const theme = document.documentElement.dataset.theme;
  const COLORS = useMemo(() => theme === 'research' ? RESEARCH_COLORS : TERMINAL_COLORS, [theme]);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const ema21Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const vwapRef = useRef<ISeriesApi<'Line'> | null>(null);

  // Initialise chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: COLORS.bg },
        textColor: COLORS.text,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: COLORS.border },
      timeScale: {
        borderColor: COLORS.border,
        timeVisible: true,
        secondsVisible: false,
      },
    });
    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: COLORS.upCandle,
      downColor: COLORS.downCandle,
      wickUpColor: COLORS.wickUp,
      wickDownColor: COLORS.wickDown,
      borderUpColor: COLORS.upCandle,
      borderDownColor: COLORS.downCandle,
    });
    candleSeriesRef.current = candleSeries;

    // Volume histogram (separate price scale)
    const volSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    });
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volSeriesRef.current = volSeries;

    // EMA21
    const ema21 = chart.addSeries(LineSeries, {
      color: COLORS.ema21,
      lineWidth: 1,
      lineStyle: LineStyle.Solid,
      title: 'EMA21',
      priceLineVisible: false,
    });
    ema21Ref.current = ema21;

    // VWAP
    const vwap = chart.addSeries(LineSeries, {
      color: COLORS.vwap,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'VWAP',
      priceLineVisible: false,
    });
    vwapRef.current = vwap;

    // Responsive resize
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [height, COLORS]);

  // Update data when chartData changes
  useEffect(() => {
    if (!chartData || !candleSeriesRef.current) return;

    const candles = chartData.candles;

    const ohlcv = candles.map((c: Candle) => ({
      time: toTimestamp(c.candle_time),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candleSeriesRef.current.setData(ohlcv);

    // Volume
    if (volSeriesRef.current) {
      const vol = candles.map((c: Candle) => ({
        time: toTimestamp(c.candle_time),
        value: c.volume,
        color: c.close >= c.open ? COLORS.volUp : COLORS.volDown,
      }));
      volSeriesRef.current.setData(vol);
    }

    // EMA21
    if (ema21Ref.current) {
      const ema = candles
        .filter((c: Candle) => c.ema21 != null)
        .map((c: Candle) => ({ time: toTimestamp(c.candle_time), value: c.ema21! }));
      ema21Ref.current.setData(ema);
    }

    // VWAP
    if (vwapRef.current) {
      const vwap = candles
        .filter((c: Candle) => c.vwap != null)
        .map((c: Candle) => ({ time: toTimestamp(c.candle_time), value: c.vwap! }));
      vwapRef.current.setData(vwap);
    }

    // Key levels as price lines
    const chart = chartRef.current;
    const series = candleSeriesRef.current;
    if (!chart || !series) return;

    // ORB levels
    if (chartData.orb_high) {
      series.createPriceLine({
        price: chartData.orb_high,
        color: '#f59e0b',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: 'ORB H',
      });
    }
    if (chartData.orb_low) {
      series.createPriceLine({
        price: chartData.orb_low,
        color: '#f59e0b',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: 'ORB L',
      });
    }

    // Pivot
    if (chartData.pivot_levels?.pivot) {
      series.createPriceLine({
        price: chartData.pivot_levels.pivot,
        color: '#64748b',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'P',
      });
    }

    // Signal markers (▲ BUY / ▼ SELL)
    if (signals.length > 0) {
      const markers = signals
        .filter(s => s.entry_price != null)
        .map(s => ({
          time: toTimestamp(s.created_at),
          position: s.signal_type === 'LONG' ? 'belowBar' : 'aboveBar',
          color: s.signal_type === 'LONG' ? COLORS.upCandle : COLORS.downCandle,
          shape: s.signal_type === 'LONG' ? 'arrowUp' : 'arrowDown',
          text: `${s.signal_type === 'LONG' ? '▲' : '▼'} ${s.symbol}`,
          size: 2,
        }));
      // @ts-ignore — lightweight-charts typing for markers
      candleSeriesRef.current?.setMarkers(markers);

      // SL / T1 / T2 horizontal lines for active signals
      signals
        .filter(s => ['PENDING', 'ENTRY_FILLED'].includes(s.current_status))
        .forEach(s => {
          series.createPriceLine({ price: s.sl_price, color: COLORS.sl, lineWidth: 1, lineStyle: LineStyle.Solid, axisLabelVisible: true, title: `SL ${s.symbol}` });
          series.createPriceLine({ price: s.target_1, color: COLORS.t1, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: `T1 ${s.symbol}` });
          if (s.target_2) {
            series.createPriceLine({ price: s.target_2, color: COLORS.t2, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: `T2 ${s.symbol}` });
          }
        });
    }

    chartRef.current?.timeScale().fitContent();
  }, [chartData, signals, COLORS]);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-800">
      <div className="absolute top-2 left-3 z-10 flex items-center gap-3 text-xs text-slate-400">
        <span className="font-mono font-bold text-slate-200">{symbol}</span>
        <span className="text-amber-400">── EMA21</span>
        <span className="text-indigo-400">- - VWAP</span>
        <span className="text-emerald-400">▲ BUY</span>
        <span className="text-red-400">▼ SELL</span>
      </div>
      <div ref={containerRef} style={{ height }} />
    </div>
  );
}
