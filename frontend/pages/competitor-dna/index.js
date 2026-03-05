import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = {
  dna:      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>,
  lightning:<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  classify: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  simulate: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  calendar: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
  clock:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  refresh:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  ai:       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>,
  warn:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>,
  fire:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" /><path strokeLinecap="round" strokeLinejoin="round" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" /></svg>,
};

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function classificationColors(c) {
  if (c === 'HOLD')    return { bg: 'rgba(16,185,129,0.15)', border: 'rgba(16,185,129,0.35)', text: '#34d399', label: 'HOLD — Don\'t reprice' };
  if (c === 'RESPOND') return { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.35)', text: '#fbbf24', label: 'RESPOND — Action needed' };
  if (c === 'IGNORE')  return { bg: 'rgba(99,102,241,0.15)', border: 'rgba(99,102,241,0.35)', text: '#a78bfa', label: 'IGNORE — No action needed' };
  return { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af', label: c };
}

function aggressionColor(score) {
  if (score >= 75) return '#f87171';
  if (score >= 45) return '#fbbf24';
  return '#34d399';
}

function revertColor(rate) {
  if (rate >= 60) return '#34d399';
  if (rate >= 35) return '#fbbf24';
  return '#f87171';
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color, icon }) {
  const styles = {
    blue:    { bg: 'rgba(37,99,235,0.12)',  border: 'rgba(37,99,235,0.2)',   text: '#60a5fa' },
    emerald: { bg: 'rgba(5,150,105,0.12)',  border: 'rgba(5,150,105,0.2)',   text: '#34d399' },
    amber:   { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.2)',  text: '#fbbf24' },
    red:     { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.2)',   text: '#f87171' },
    violet:  { bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.2)',  text: '#a78bfa' },
  }[color] || { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af' };

  return (
    <div className="rounded-2xl p-5 flex items-center gap-4 animate-fade-in"
      style={{ background: styles.bg, border: `1px solid ${styles.border}` }}>
      <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: 'rgba(0,0,0,0.25)', color: styles.text }}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-white leading-none truncate">{value ?? '—'}</p>
        <p className="text-xs mt-1 leading-snug" style={{ color: 'rgba(255,255,255,0.5)' }}>{label}</p>
        {sub && <p className="text-xs mt-0.5 truncate" style={{ color: styles.text }}>{sub}</p>}
      </div>
    </div>
  );
}

function AggressionGauge({ score }) {
  const radius = 30;
  const stroke = 5;
  const normalizedRadius = radius - stroke;
  const circumference = 2 * Math.PI * normalizedRadius;
  const offset = circumference - (score / 100) * circumference;
  const color = aggressionColor(score);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg height={radius * 2} width={radius * 2} className="rotate-[-90deg]">
        <circle
          stroke="rgba(255,255,255,0.07)"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={offset}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="text-center -mt-1">
        <p className="text-xl font-bold leading-none" style={{ color }}>{score}</p>
        <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>/ 100</p>
      </div>
    </div>
  );
}

function DayBars({ dist }) {
  const vals = DAYS.map(d => dist?.[d] || 0);
  const maxVal = Math.max(...vals, 1);
  return (
    <div className="flex items-end gap-1 h-10">
      {DAYS.map((day, i) => {
        const pct = vals[i];
        const height = Math.max(3, (pct / maxVal) * 38);
        const isTop = pct === maxVal && pct > 0;
        return (
          <div key={day} className="flex flex-col items-center gap-0.5 flex-1" title={`${day}: ${pct.toFixed(1)}%`}>
            <div
              className="w-full rounded-sm transition-all duration-700"
              style={{
                height: `${height}px`,
                background: isTop ? '#f59e0b' : 'rgba(255,255,255,0.15)',
              }}
            />
            <span className="text-[8px] leading-none" style={{ color: isTop ? '#f59e0b' : 'rgba(255,255,255,0.3)' }}>
              {day.slice(0, 1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function HourHeatmap({ dist }) {
  if (!dist) return null;
  const vals = Object.values(dist);
  const maxVal = Math.max(...vals, 1);
  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);

  return (
    <div className="flex gap-px">
      {hours.map((h) => {
        const v = dist[h] || 0;
        const intensity = v / maxVal;
        return (
          <div
            key={h}
            className="flex-1 rounded-sm"
            style={{
              height: '14px',
              background: intensity > 0.1
                ? `rgba(245,158,11,${0.15 + intensity * 0.85})`
                : 'rgba(255,255,255,0.06)',
            }}
            title={`${h} UTC — ${v.toFixed(1)}%`}
          />
        );
      })}
    </div>
  );
}

function RevertBadge({ rate }) {
  const color = revertColor(rate);
  const label = rate >= 60 ? 'Mostly Promo' : rate >= 35 ? 'Mixed' : 'Mostly Permanent';
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full"
      style={{ background: `${color}22`, color, border: `1px solid ${color}44` }}>
      {label}
    </span>
  );
}

function Skeleton({ className = '' }) {
  return <div className={`rounded-xl animate-pulse ${className}`} style={{ background: 'rgba(255,255,255,0.06)' }} />;
}

// ─── DNA Profile Card ─────────────────────────────────────────────────────────
function DnaCard({ profile, onClassify }) {
  const [expanded, setExpanded] = useState(false);
  const patterns = profile.strike_patterns || {};
  const revert   = profile.revert_analysis || {};
  const lag      = profile.response_lag || {};

  return (
    <div
      className="rounded-2xl overflow-hidden animate-fade-in flex flex-col"
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-4 flex items-start gap-4">
        {/* Aggression gauge */}
        <div className="shrink-0">
          <AggressionGauge score={profile.aggression_score ?? 0} />
          <p className="text-[9px] text-center mt-1" style={{ color: 'rgba(255,255,255,0.35)' }}>Aggression</p>
        </div>

        {/* Name + badges */}
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-bold text-white truncate">{profile.competitor_name}</h3>
          <div className="flex flex-wrap gap-1.5 mt-2">
            <RevertBadge rate={revert.revert_rate_pct || 0} />
            {lag.avg_response_hours && (
              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(96,165,250,0.12)', color: '#60a5fa', border: '1px solid rgba(96,165,250,0.25)' }}>
                {Ico.clock} ~{lag.avg_response_hours}h lag
              </span>
            )}
            {profile.strike_prediction?.probability > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold"
                style={{
                  background: profile.strike_prediction.probability >= 60
                    ? 'rgba(248,113,113,0.15)' : 'rgba(245,158,11,0.12)',
                  color: profile.strike_prediction.probability >= 60 ? '#f87171' : '#fbbf24',
                  border: `1px solid ${profile.strike_prediction.probability >= 60 ? 'rgba(248,113,113,0.3)' : 'rgba(245,158,11,0.25)'}`,
                }}>
                {profile.strike_prediction.probability}% strike this week
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Strike pattern */}
      <div className="px-5 pb-4 space-y-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'rgba(255,255,255,0.35)' }}>
            Strike Pattern (day)
          </p>
          <DayBars dist={patterns.day_distribution} />
        </div>

        {patterns.hour_distribution && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'rgba(255,255,255,0.35)' }}>
              Strike Pattern (hour UTC)
            </p>
            <HourHeatmap dist={patterns.hour_distribution} />
            <div className="flex justify-between mt-1">
              <span className="text-[8px]" style={{ color: 'rgba(255,255,255,0.25)' }}>00:00</span>
              <span className="text-[8px]" style={{ color: 'rgba(255,255,255,0.25)' }}>12:00</span>
              <span className="text-[8px]" style={{ color: 'rgba(255,255,255,0.25)' }}>23:00</span>
            </div>
          </div>
        )}
      </div>

      {/* Metrics row */}
      <div className="px-5 pb-4 grid grid-cols-3 gap-2">
        <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
          <p className="text-base font-bold" style={{ color: revertColor(revert.revert_rate_pct || 0) }}>
            {revert.revert_rate_pct ?? '—'}%
          </p>
          <p className="text-[9px] mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>Revert rate</p>
        </div>
        <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
          <p className="text-base font-bold text-white">{profile.avg_drop_pct ? `-${profile.avg_drop_pct}%` : '—'}</p>
          <p className="text-[9px] mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>Avg drop</p>
        </div>
        <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
          <p className="text-base font-bold text-white">{profile.data_points ?? '—'}</p>
          <p className="text-[9px] mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>Data pts</p>
        </div>
      </div>

      {/* Peak window */}
      {patterns.most_active_day && (
        <div className="px-5 pb-3 flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs" style={{ color: '#f59e0b' }}>
            <span className="text-base">⚡</span>
            <span className="font-medium">Peaks {patterns.most_active_day}s · {patterns.peak_window_utc}</span>
          </div>
        </div>
      )}

      {/* AI Summary */}
      {profile.ai_summary && (
        <div className="mx-5 mb-4 p-3 rounded-xl" style={{ background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.15)' }}>
          <div className="flex items-start gap-2">
            <span style={{ color: '#f59e0b' }} className="shrink-0 mt-0.5">{Ico.ai}</span>
            <p className="text-xs italic leading-relaxed" style={{ color: 'rgba(255,255,255,0.65)' }}>
              {profile.ai_summary}
            </p>
          </div>
        </div>
      )}

      {/* Revert interpretation */}
      {expanded && revert.interpretation && (
        <div className="px-5 pb-3">
          <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {revert.interpretation}
          </p>
          {lag.interpretation && (
            <p className="text-xs leading-relaxed mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
              {lag.interpretation}
            </p>
          )}
        </div>
      )}

      {/* Footer actions */}
      <div className="mt-auto px-5 py-3 flex gap-2" style={{ borderTop: '1px solid var(--border)' }}>
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex-1 py-2 text-xs rounded-xl transition-colors"
          style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)' }}
        >
          {expanded ? 'Less detail' : 'More detail'}
        </button>
        <button
          onClick={() => onClassify(profile.competitor_name)}
          className="flex-1 py-2 text-xs font-semibold rounded-xl transition-colors"
          style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)' }}
        >
          Classify Change
        </button>
      </div>
    </div>
  );
}

// ─── Strike Calendar ──────────────────────────────────────────────────────────
function StrikeCalendar({ predictions }) {
  if (!predictions) return null;
  const calendar = predictions.calendar || {};
  const todayIdx = new Date().getDay();
  // Convert Sunday=0 to Monday-first (0=Mon..6=Sun)
  const todayName = DAYS[(todayIdx + 6) % 7];

  return (
    <div className="grid grid-cols-7 gap-1.5">
      {DAYS.map((day) => {
        const items = calendar[day] || [];
        const isToday = day === todayName;
        const topProb = items.length > 0 ? Math.max(...items.map(i => i.probability)) : 0;
        const danger = topProb >= 65;
        const moderate = topProb >= 35 && !danger;

        return (
          <div
            key={day}
            className="rounded-xl p-2 flex flex-col gap-1.5 min-h-[90px]"
            style={{
              background: isToday
                ? 'rgba(245,158,11,0.08)'
                : 'rgba(255,255,255,0.02)',
              border: `1px solid ${isToday ? 'rgba(245,158,11,0.25)' : 'var(--border)'}`,
            }}
          >
            <p className="text-[9px] font-bold uppercase tracking-wider text-center"
              style={{ color: isToday ? '#f59e0b' : 'rgba(255,255,255,0.4)' }}>
              {day.slice(0, 3)}
              {isToday && <span className="ml-1 text-[8px]">●</span>}
            </p>

            {items.length === 0 ? (
              <p className="text-[9px] text-center flex-1 flex items-center justify-center"
                style={{ color: 'rgba(255,255,255,0.2)' }}>
                —
              </p>
            ) : (
              <div className="flex flex-col gap-1 flex-1">
                {items.slice(0, 3).map((item, i) => (
                  <div key={i} className="rounded-lg px-1.5 py-1"
                    style={{
                      background: item.likely_promo
                        ? 'rgba(52,211,153,0.1)' : 'rgba(248,113,113,0.1)',
                    }}>
                    <p className="text-[8px] font-semibold truncate leading-none"
                      style={{ color: item.likely_promo ? '#34d399' : '#f87171' }}>
                      {item.competitor.slice(0, 10)}
                    </p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
                        <div className="h-full rounded-full"
                          style={{
                            width: `${item.probability}%`,
                            background: item.likely_promo ? '#34d399' : '#f87171',
                          }}
                        />
                      </div>
                      <span className="text-[7px] shrink-0" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        {item.probability}%
                      </span>
                    </div>
                  </div>
                ))}
                {items.length > 3 && (
                  <p className="text-[8px] text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    +{items.length - 3} more
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Classification Result ────────────────────────────────────────────────────
function ClassificationResult({ result }) {
  const style = classificationColors(result.classification);
  return (
    <div className="animate-fade-in space-y-4">
      {/* Big classification badge */}
      <div className="rounded-2xl p-5 text-center"
        style={{ background: style.bg, border: `2px solid ${style.border}` }}>
        <p className="text-3xl font-black tracking-wide" style={{ color: style.text }}>
          {result.classification}
        </p>
        <p className="text-sm font-semibold mt-1" style={{ color: style.text }}>
          {style.label}
        </p>
        <div className="flex items-center justify-center gap-2 mt-2">
          <span className="text-xs px-2 py-0.5 rounded-full capitalize"
            style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.55)' }}>
            {result.confidence} confidence
          </span>
          {result.change_pct !== undefined && (
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: result.is_drop ? 'rgba(248,113,113,0.12)' : 'rgba(52,211,153,0.12)',
                color: result.is_drop ? '#f87171' : '#34d399',
              }}>
              {result.change_pct > 0 ? '+' : ''}{result.change_pct?.toFixed(1)}%
            </span>
          )}
        </div>
      </div>

      {/* Promo signals */}
      {result.promo_signals?.length > 0 && (
        <div className="rounded-xl p-3 space-y-1.5" style={{ background: 'rgba(52,211,153,0.07)', border: '1px solid rgba(52,211,153,0.2)' }}>
          <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#34d399' }}>Live Promo Signals</p>
          {result.promo_signals.map((sig, i) => (
            <p key={i} className="text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>• {sig}</p>
          ))}
        </div>
      )}

      {/* Reasoning */}
      {result.reasoning && (
        <div className="rounded-xl p-3" style={{ background: 'var(--bg-elevated)' }}>
          <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>{result.reasoning}</p>
        </div>
      )}

      {/* Recommended action */}
      {result.recommended_action && (
        <div className="rounded-xl p-3" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#f59e0b' }}>Recommended Action</p>
          <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>{result.recommended_action}</p>
        </div>
      )}

      {/* AI Narrative */}
      {result.ai_narrative && (
        <div className="rounded-xl p-3" style={{ background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.12)' }}>
          <div className="flex items-start gap-2">
            <span style={{ color: '#f59e0b' }} className="shrink-0 mt-0.5">{Ico.ai}</span>
            <p className="text-xs italic leading-relaxed" style={{ color: 'rgba(255,255,255,0.65)' }}>{result.ai_narrative}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Simulation Result ────────────────────────────────────────────────────────
function SimulationResult({ result }) {
  const horizons = [
    { key: 't_plus_24h', label: 'T + 24h' },
    { key: 't_plus_48h', label: 'T + 48h' },
    { key: 't_plus_72h', label: 'T + 72h' },
  ];

  return (
    <div className="animate-fade-in space-y-4">
      {/* Summary header */}
      <div className="rounded-2xl p-4 text-center" style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.25)' }}>
        <p className="text-xs uppercase tracking-wider font-semibold mb-1" style={{ color: 'rgba(96,165,250,0.7)' }}>Proposed Price</p>
        <p className="text-3xl font-black text-white">${result.proposed_price?.toFixed(2)}</p>
        {result.current_price && (
          <p className="text-sm mt-1" style={{ color: result.price_change_pct < 0 ? '#f87171' : '#34d399' }}>
            {result.price_change_pct > 0 ? '+' : ''}{result.price_change_pct?.toFixed(1)}% from ${result.current_price?.toFixed(2)}
          </p>
        )}
      </div>

      {/* Timeline projections */}
      <div className="grid grid-cols-3 gap-2">
        {horizons.map(({ key, label }) => {
          const h = result.market_state?.[key];
          if (!h) return null;
          return (
            <div key={key} className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
              <p className="text-[9px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</p>
              <p className="text-base font-bold" style={{ color: h.you_are_cheapest ? '#34d399' : 'rgba(255,255,255,0.8)' }}>
                {h.your_rank}
              </p>
              <p className="text-[9px] mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>market rank</p>
              {h.lowest_competitor && (
                <>
                  <div className="my-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.07)' }} />
                  <p className="text-xs font-bold" style={{ color: '#f87171' }}>${h.lowest_competitor?.toFixed(2)}</p>
                  <p className="text-[9px]" style={{ color: 'rgba(255,255,255,0.35)' }}>lowest rival</p>
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* Per-competitor reactions */}
      {result.competitor_projections?.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <div className="px-4 py-2.5" style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border)' }}>
            <p className="text-xs font-semibold text-white">Projected Competitor Responses</p>
          </div>
          <div className="divide-y" style={{ divideColor: 'var(--border)' }}>
            {result.competitor_projections.map((proj, i) => (
              <div key={i} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-white truncate">{proj.competitor}</p>
                  <p className="text-[10px] mt-0.5 leading-snug" style={{ color: 'rgba(255,255,255,0.45)' }}>
                    {proj.reasoning?.slice(0, 80)}{proj.reasoning?.length > 80 ? '…' : ''}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  {proj.will_respond ? (
                    <>
                      <p className="text-xs font-bold" style={{ color: '#f87171' }}>${proj.projected_price?.toFixed(2)}</p>
                      <p className="text-[9px] mt-0.5" style={{ color: '#f87171' }}>~{proj.expected_response_hours}h</p>
                    </>
                  ) : (
                    <>
                      <p className="text-xs font-bold" style={{ color: '#34d399' }}>${proj.current_price?.toFixed(2)}</p>
                      <p className="text-[9px] mt-0.5" style={{ color: '#34d399' }}>won't react</p>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Recommendation */}
      {result.ai_recommendation && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <div className="flex items-start gap-2">
            <span style={{ color: '#f59e0b' }} className="shrink-0 mt-0.5">{Ico.ai}</span>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#f59e0b' }}>AI Recommendation</p>
              <p className="text-xs italic leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>{result.ai_recommendation}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function CompetitorDNAPage() {
  const [profiles, setProfiles]           = useState(null);
  const [predictions, setPredictions]     = useState(null);
  const [products, setProducts]           = useState([]);
  const [loading, setLoading]             = useState(true);
  const [activeTab, setActiveTab]         = useState('profiles'); // 'profiles' | 'calendar' | 'tools'

  // Classifier state
  const [classComp, setClassComp]         = useState('');
  const [classProduct, setClassProduct]   = useState('');
  const [classOldPrice, setClassOldPrice] = useState('');
  const [classNewPrice, setClassNewPrice] = useState('');
  const [classLoading, setClassLoading]   = useState(false);
  const [classResult, setClassResult]     = useState(null);
  const [classError, setClassError]       = useState('');
  const [classifyFor, setClassifyFor]     = useState(null); // competitor name pre-fill

  // Simulator state
  const [simProduct, setSimProduct]       = useState('');
  const [simPrice, setSimPrice]           = useState('');
  const [simLoading, setSimLoading]       = useState(false);
  const [simResult, setSimResult]         = useState(null);
  const [simError, setSimError]           = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getDnaProfiles(),
      api.getDnaStrikePredictions(),
      api.getProducts(),
    ]).then(([p, pred, prods]) => {
      setProfiles(p);
      setPredictions(pred);
      setProducts(prods || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  // Pre-fill classifier when coming from a DNA card
  useEffect(() => {
    if (classifyFor) {
      setClassComp(classifyFor);
      setClassifyFor(null);
      setActiveTab('tools');
    }
  }, [classifyFor]);

  const handleClassify = async (e) => {
    e.preventDefault();
    if (!classComp || !classProduct || !classOldPrice || !classNewPrice) return;
    setClassLoading(true);
    setClassResult(null);
    setClassError('');
    try {
      const res = await api.classifyPriceChange(classComp, parseInt(classProduct), parseFloat(classOldPrice), parseFloat(classNewPrice));
      setClassResult(res);
    } catch (err) {
      setClassError(err.message || 'Classification failed');
    } finally {
      setClassLoading(false);
    }
  };

  const handleSimulate = async (e) => {
    e.preventDefault();
    if (!simProduct || !simPrice) return;
    setSimLoading(true);
    setSimResult(null);
    setSimError('');
    try {
      const res = await api.simulateReprice(parseInt(simProduct), parseFloat(simPrice));
      setSimResult(res);
    } catch (err) {
      setSimError(err.message || 'Simulation failed');
    } finally {
      setSimLoading(false);
    }
  };

  // Derived stats
  const sufficientProfiles = profiles?.profiles?.filter(p => p.sufficient_data) || [];
  const avgStrikeProb = sufficientProfiles.length
    ? Math.round(sufficientProfiles.reduce((s, p) => s + (p.strike_prediction?.probability || 0), 0) / sufficientProfiles.length)
    : null;
  const mostAggressive = sufficientProfiles.length
    ? sufficientProfiles.reduce((best, p) => (p.aggression_score || 0) > (best.aggression_score || 0) ? p : best, sufficientProfiles[0])
    : null;
  const avgRevert = sufficientProfiles.length
    ? Math.round(sufficientProfiles.reduce((s, p) => s + (p.revert_analysis?.revert_rate_pct || 0), 0) / sufficientProfiles.length)
    : null;

  const competitorNames = sufficientProfiles.map(p => p.competitor_name);

  const TABS = [
    { id: 'profiles',  label: 'DNA Profiles',          icon: Ico.dna },
    { id: 'calendar',  label: 'Strike Calendar',        icon: Ico.calendar },
    { id: 'tools',     label: 'Action Tools',           icon: Ico.classify },
  ];

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5 pb-24 lg:pb-10">

        {/* ── Page Header ── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
                {Ico.dna}
              </div>
              <h1 className="text-xl font-bold text-white">Strategy DNA</h1>
            </div>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Every competitor's pricing personality — strike patterns, promo rates, and predictive forecasts
            </p>
          </div>
          <button
            onClick={() => { setLoading(true); Promise.all([api.getDnaProfiles(), api.getDnaStrikePredictions()]).then(([p, pr]) => { setProfiles(p); setPredictions(pr); }).catch(console.error).finally(() => setLoading(false)); }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs shrink-0"
            style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.6)', border: '1px solid var(--border)' }}
          >
            {Ico.refresh} Refresh
          </button>
        </div>

        {/* ── Stat Cards ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="Competitors Analysed"
            value={loading ? '…' : sufficientProfiles.length}
            sub={profiles?.total_competitors ? `${profiles.total_competitors} total` : null}
            color="violet"
            icon={Ico.dna}
          />
          <StatCard
            label="Avg Strike Probability"
            value={loading ? '…' : avgStrikeProb != null ? `${avgStrikeProb}%` : '—'}
            sub="this week"
            color="amber"
            icon={Ico.lightning}
          />
          <StatCard
            label="Most Aggressive"
            value={loading ? '…' : mostAggressive?.competitor_name?.split(' ')[0] || '—'}
            sub={mostAggressive ? `Score ${mostAggressive.aggression_score}/100` : null}
            color="red"
            icon={Ico.fire}
          />
          <StatCard
            label="Avg Revert Rate"
            value={loading ? '…' : avgRevert != null ? `${avgRevert}%` : '—'}
            sub="drops are temporary promos"
            color="emerald"
            icon={Ico.classify}
          />
        </div>

        {/* ── Legend ── */}
        <div className="flex flex-wrap gap-3 text-[10px]" style={{ color: 'rgba(255,255,255,0.45)' }}>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: '#34d399' }} />
            High revert rate = mostly promos → HOLD
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: '#f87171' }} />
            Low revert rate = permanent cuts → RESPOND
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: '#f59e0b' }} />
            Peak day highlighted in amber
          </span>
        </div>

        {/* ── Tabs ── */}
        <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--bg-elevated)', width: 'fit-content' }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all"
              style={activeTab === tab.id
                ? { background: 'var(--bg-surface)', color: '#f59e0b', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }
                : { color: 'rgba(255,255,255,0.5)' }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* ── Tab: DNA Profiles Grid ── */}
        {activeTab === 'profiles' && (
          <div>
            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-80" />)}
              </div>
            ) : sufficientProfiles.length === 0 ? (
              <div className="rounded-2xl p-10 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-3"
                  style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
                  {Ico.dna}
                </div>
                <p className="text-sm font-semibold text-white mb-1">No DNA profiles yet</p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  DNA profiles require at least 3 price changes per competitor in the last 90 days.
                  Add more competitors and run your scraper to build up history.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {sufficientProfiles.map(profile => (
                  <DnaCard
                    key={profile.competitor_name}
                    profile={profile}
                    onClassify={(name) => setClassifyFor(name)}
                  />
                ))}
                {/* Insufficient data cards */}
                {profiles?.profiles?.filter(p => !p.sufficient_data).map(p => (
                  <div key={p.competitor_name} className="rounded-2xl p-5 flex flex-col gap-2 animate-fade-in"
                    style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', opacity: 0.6 }}>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.2)' }} />
                      <p className="text-sm font-semibold text-white">{p.competitor_name}</p>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs mt-1" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {Ico.warn} Insufficient data ({p.data_points || 0} changes)
                    </div>
                    <p className="text-[10px] leading-relaxed" style={{ color: 'rgba(255,255,255,0.3)' }}>
                      {p.message}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab: Strike Calendar ── */}
        {activeTab === 'calendar' && (
          <div className="space-y-4">
            <div className="rounded-2xl overflow-hidden"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <h2 className="text-sm font-semibold text-white">7-Day Strike Forecast</h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Predicted price change windows. Green = likely promo (hold). Red = likely permanent (act).
                </p>
              </div>
              <div className="p-4">
                {loading ? (
                  <Skeleton className="h-32" />
                ) : (
                  <StrikeCalendar predictions={predictions} />
                )}
              </div>
            </div>

            {/* Ranked predictions list */}
            {!loading && predictions?.predictions?.length > 0 && (
              <div className="rounded-2xl overflow-hidden"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                  <h2 className="text-sm font-semibold text-white">Ranked Strike Threats</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    Highest-probability competitors to move prices this week
                  </p>
                </div>
                <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                  {predictions.predictions.map((pred, i) => (
                    <div key={i} className="px-5 py-4 flex items-center gap-4">
                      <div className="w-8 h-8 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
                        style={{
                          background: i === 0 ? 'rgba(248,113,113,0.15)' : 'rgba(255,255,255,0.05)',
                          color: i === 0 ? '#f87171' : 'rgba(255,255,255,0.5)',
                        }}>
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white">{pred.competitor}</p>
                          {pred.prediction?.likely_promo ? (
                            <span className="text-[10px] px-1.5 py-0.5 rounded"
                              style={{ background: 'rgba(52,211,153,0.12)', color: '#34d399' }}>Promo likely</span>
                          ) : (
                            <span className="text-[10px] px-1.5 py-0.5 rounded"
                              style={{ background: 'rgba(248,113,113,0.12)', color: '#f87171' }}>Permanent likely</span>
                          )}
                        </div>
                        <p className="text-[10px] mt-1" style={{ color: 'rgba(255,255,255,0.45)' }}>
                          {pred.prediction?.interpretation?.slice(0, 100)}{pred.prediction?.interpretation?.length > 100 ? '…' : ''}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-lg font-black" style={{
                          color: pred.prediction.probability >= 65 ? '#f87171'
                            : pred.prediction.probability >= 40 ? '#fbbf24' : '#34d399'
                        }}>
                          {pred.prediction.probability}%
                        </p>
                        <p className="text-[9px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                          {pred.prediction.most_likely_day}
                        </p>
                        {pred.avg_expected_drop && (
                          <p className="text-[9px]" style={{ color: '#f87171' }}>-{pred.avg_expected_drop}% avg</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Tab: Action Tools ── */}
        {activeTab === 'tools' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Classifier */}
            <div className="rounded-2xl overflow-hidden"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-2">
                  <span style={{ color: '#34d399' }}>{Ico.classify}</span>
                  <div>
                    <h2 className="text-sm font-semibold text-white">HOLD / RESPOND / IGNORE</h2>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      Instantly classify a detected price change
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-5 space-y-4">
                <form onSubmit={handleClassify} className="space-y-3">
                  <div>
                    <label className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 block" style={{ color: 'rgba(255,255,255,0.45)' }}>
                      Competitor
                    </label>
                    {competitorNames.length > 0 ? (
                      <select
                        value={classComp}
                        onChange={e => setClassComp(e.target.value)}
                        className="glass-input w-full text-sm"
                        required
                      >
                        <option value="">Select competitor…</option>
                        {competitorNames.map(n => <option key={n} value={n}>{n}</option>)}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={classComp}
                        onChange={e => setClassComp(e.target.value)}
                        placeholder="e.g. Amazon"
                        className="glass-input w-full text-sm"
                        required
                      />
                    )}
                  </div>

                  <div>
                    <label className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 block" style={{ color: 'rgba(255,255,255,0.45)' }}>
                      Product
                    </label>
                    <select
                      value={classProduct}
                      onChange={e => setClassProduct(e.target.value)}
                      className="glass-input w-full text-sm"
                      required
                    >
                      <option value="">Select product…</option>
                      {products.map(p => <option key={p.id} value={p.id}>{p.title?.slice(0, 60)}</option>)}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 block" style={{ color: 'rgba(255,255,255,0.45)' }}>
                        Old Price ($)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={classOldPrice}
                        onChange={e => setClassOldPrice(e.target.value)}
                        placeholder="49.99"
                        className="glass-input w-full text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 block" style={{ color: 'rgba(255,255,255,0.45)' }}>
                        New Price ($)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={classNewPrice}
                        onChange={e => setClassNewPrice(e.target.value)}
                        placeholder="43.99"
                        className="glass-input w-full text-sm"
                        required
                      />
                    </div>
                  </div>

                  {classError && (
                    <p className="text-xs px-3 py-2 rounded-xl" style={{ background: 'rgba(248,113,113,0.1)', color: '#f87171' }}>
                      {classError}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={classLoading}
                    className="w-full py-2.5 rounded-xl text-sm font-semibold transition-opacity"
                    style={{ background: 'linear-gradient(135deg,#f59e0b,#f97316)', color: '#000', opacity: classLoading ? 0.6 : 1 }}
                  >
                    {classLoading ? 'Analysing…' : 'Classify This Change'}
                  </button>
                </form>

                {classResult && <ClassificationResult result={classResult} />}
              </div>
            </div>

            {/* Simulator */}
            <div className="rounded-2xl overflow-hidden"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-2">
                  <span style={{ color: '#60a5fa' }}>{Ico.simulate}</span>
                  <div>
                    <h2 className="text-sm font-semibold text-white">Before You Reprice</h2>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      Simulate how the market reacts to your price change
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-5 space-y-4">
                <form onSubmit={handleSimulate} className="space-y-3">
                  <div>
                    <label className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 block" style={{ color: 'rgba(255,255,255,0.45)' }}>
                      Product
                    </label>
                    <select
                      value={simProduct}
                      onChange={e => setSimProduct(e.target.value)}
                      className="glass-input w-full text-sm"
                      required
                    >
                      <option value="">Select product…</option>
                      {products.map(p => <option key={p.id} value={p.id}>{p.title?.slice(0, 60)}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 block" style={{ color: 'rgba(255,255,255,0.45)' }}>
                      Your Proposed Price ($)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={simPrice}
                      onChange={e => setSimPrice(e.target.value)}
                      placeholder="44.99"
                      className="glass-input w-full text-sm"
                      required
                    />
                  </div>

                  {/* Tip */}
                  <div className="flex items-start gap-2 rounded-xl p-3" style={{ background: 'rgba(96,165,250,0.07)', border: '1px solid rgba(96,165,250,0.15)' }}>
                    <span className="text-xs shrink-0" style={{ color: '#60a5fa' }}>💡</span>
                    <p className="text-[10px] leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>
                      We'll predict how each competitor responds at T+24h, T+48h, and T+72h using their DNA profile.
                    </p>
                  </div>

                  {simError && (
                    <p className="text-xs px-3 py-2 rounded-xl" style={{ background: 'rgba(248,113,113,0.1)', color: '#f87171' }}>
                      {simError}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={simLoading}
                    className="w-full py-2.5 rounded-xl text-sm font-semibold transition-opacity"
                    style={{ background: 'linear-gradient(135deg,#3b82f6,#6366f1)', color: '#fff', opacity: simLoading ? 0.6 : 1 }}
                  >
                    {simLoading ? 'Simulating…' : 'Run Market Simulation'}
                  </button>
                </form>

                {simResult && <SimulationResult result={simResult} />}
              </div>
            </div>

          </div>
        )}

      </div>
    </Layout>
  );
}
