'use client';

import { useEffect, useRef, useState } from 'react';
import { TimerIcon } from '@phosphor-icons/react';
import type { Timing } from '@/lib/game';

export function clockText(seconds: number) {
  const whole = Math.max(0, Math.ceil(seconds));
  return `${String(Math.floor(whole / 60)).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`;
}

export default function StageClock({ timing, weight, hints, onExpired }: {
  timing: Timing; weight: number; hints: number; onExpired: () => void;
}) {
  const [remaining, setRemaining] = useState(timing.remaining_seconds);
  const expiredCallback = useRef(onExpired);
  expiredCallback.current = onExpired;
  useEffect(() => {
    const start = performance.now();
    let notified = false;
    function tick() {
      const value = timing.solved ? timing.remaining_seconds
        : Math.max(0, timing.remaining_seconds - (performance.now() - start) / 1000);
      setRemaining(value);
      if (!timing.solved && value <= 0 && !notified) {
        notified = true; expiredCallback.current();
      }
    }
    tick();
    const interval = setInterval(tick, 200);
    return () => clearInterval(interval);
  }, [timing]);
  const elapsed = Math.max(0, Math.floor(timing.limit_seconds - remaining));
  const base = weight * 100;
  const raw = base / 2 + Math.floor(base * (timing.limit_seconds - elapsed) / (2 * timing.limit_seconds));
  const points = remaining <= 0 ? 0 : Math.floor(Math.max(0, raw - hints * 25) / (timing.attempt > 1 ? 2 : 1));
  return <div className={`stage-clock ${!timing.solved && remaining <= 30 ? 'time-low' : ''}`}>
    <div className="clock-main"><TimerIcon size={23} /><div><span className="clock-label">{timing.solved ? 'Thời gian giải' : 'Thời gian còn lại'}</span>
      <strong role="timer" aria-label={timing.solved ? 'Thời gian giải' : 'Thời gian còn lại'} aria-live="off" data-testid="stage-timer">{timing.legacy_scoring ? '—' : clockText(timing.solved ? Math.floor(timing.elapsed_seconds || 0) : remaining)}</strong></div>
      <span className="clock-limit">Giới hạn {timing.limit_seconds / 60} phút<br />Lượt {timing.attempt}</span></div>
    <p className="clock-points">{timing.solved ? timing.legacy_scoring ? `Đã lưu ${timing.awarded_points} điểm · luật cũ` : `Đã nhận ${timing.awarded_points} điểm`
      : <>Điểm dự kiến nếu giải ngay: <strong data-testid="live-points">{points}</strong>{timing.attempt > 1 && ' · Lượt chơi lại giảm 50%'}</>}</p>
  </div>;
}
