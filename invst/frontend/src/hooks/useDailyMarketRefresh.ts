import { useEffect, useRef } from 'react';

const getIstParts = () => {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date());
  return Object.fromEntries(parts.map(({ type, value }) => [type, value]));
};

/** Re-check daily market views after the scheduled India EOD price ingestion. */
export const useDailyMarketRefresh = (refresh: () => void | Promise<void>) => {
  const refreshRef = useRef(refresh);
  const refreshedDateRef = useRef('');
  refreshRef.current = refresh;

  useEffect(() => {
    let timerId = 0;

    const refreshIfDue = () => {
      const parts = getIstParts();
      const today = `${parts.year}-${parts.month}-${parts.day}`;
      const afterCloseRefreshTime = Number(parts.hour) > 19 || (Number(parts.hour) === 19 && Number(parts.minute) >= 40);
      if (afterCloseRefreshTime && refreshedDateRef.current !== today && document.visibilityState === 'visible') {
        refreshedDateRef.current = today;
        void refreshRef.current();
      }
    };

    const scheduleNext = () => {
      const parts = getIstParts();
      const today = `${parts.year}-${parts.month}-${parts.day}`;
      const targetToday = Date.parse(`${today}T19:40:00+05:30`);
      const target = targetToday > Date.now() ? targetToday : targetToday + 24 * 60 * 60 * 1000;
      timerId = window.setTimeout(() => {
        refreshIfDue();
        scheduleNext();
      }, Math.max(1_000, target - Date.now()));
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') refreshIfDue();
    };

    scheduleNext();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      window.clearTimeout(timerId);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);
};
