import { useMemo, useRef } from 'react'
import type { ItemResult, Turn } from '../types'
import { fmtNum } from '../api'

const W = 1000

/** One measure against time (never two y-scales): 2px line, turn bands, threshold lines, crosshair tooltip. */
export function TimeChart({ title, subtitle, unit, t, y, turns, refs = [], hoverT, onHover, onPick, markers = [] }: {
  title: string; subtitle?: string; unit: string
  t: (number | null)[]; y: (number | null)[]; turns: Turn[]
  refs?: { value: number; label: string }[]
  hoverT: number | null; onHover: (t: number | null) => void; onPick?: (t: number) => void
  markers?: number[]
}) {
  const H = 132, L = 46, R = 12, T = 8, B = 20
  const ref = useRef<SVGSVGElement>(null)
  const { x, yy, path, lo, hi, ticks, tmax } = useMemo(() => {
    const vals = y.filter((v): v is number => v !== null).concat(refs.map(r => r.value))
    let lo = Math.min(...vals), hi = Math.max(...vals)
    if (!isFinite(lo)) { lo = 0; hi = 1 }
    if (lo > 0 && lo < (hi - lo)) lo = 0
    const pad = (hi - lo || 1) * 0.08
    lo -= lo === 0 ? 0 : pad; hi += pad
    const tmax = Math.max(...(t.filter(v => v !== null) as number[]), 0.001)
    const x = (v: number) => L + (v / tmax) * (W - L - R)
    const yy = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B)
    let path = '', pen = false
    y.forEach((v, i) => {
      if (v === null || t[i] === null) { pen = false; return }
      path += `${pen ? 'L' : 'M'}${x(t[i] as number).toFixed(1)},${yy(v).toFixed(1)}`
      pen = true
    })
    const step = niceStep((hi - lo) / 3)
    const ticks: number[] = []
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(+v.toFixed(6))
    return { x, yy, path, lo, hi, ticks, tmax }
  }, [t, y, refs])

  const idx = hoverT === null ? -1 : nearest(t, hoverT)
  const hv = idx >= 0 ? y[idx] : null
  const tOf = (e: React.MouseEvent) => {
    const r = ref.current!.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    return Math.max(0, Math.min(tmax, ((px - L) / (W - L - R)) * tmax))
  }
  return (
    <div className="chart">
      <div className="title">{title}{subtitle && <span>{subtitle}</span>}</div>
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} over time`}
        onMouseMove={e => onHover(tOf(e))} onMouseLeave={() => onHover(null)} onClick={e => onPick?.(tOf(e))}
        style={{ cursor: onPick ? 'pointer' : 'crosshair' }}>
        {turns.map((u, i) => (
          <rect key={i} x={x(u.t_start)} y={T} width={Math.max(0, x(u.t_end) - x(u.t_start))} height={H - T - B}
            fill={u.direction === 'right' ? 'var(--band-right)' : 'var(--band-left)'} />
        ))}
        {ticks.map(v => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={yy(v)} y2={yy(v)} stroke="var(--border)" strokeWidth={v === 0 ? 1.2 : 0.6} />
            <text x={L - 6} y={yy(v) + 3.5} textAnchor="end" fontSize="10.5" fill="var(--text-3)">{fmtTick(v)}</text>
          </g>
        ))}
        {refs.filter(r => r.value > lo && r.value < hi).map(r => (
          <g key={r.label}>
            <line x1={L} x2={W - R} y1={yy(r.value)} y2={yy(r.value)} stroke="var(--text-3)" strokeWidth="1" strokeDasharray="5 4" />
            <text x={W - R - 2} y={yy(r.value) - 3} textAnchor="end" fontSize="10" fill="var(--text-2)">{r.label}</text>
          </g>
        ))}
        {Array.from({ length: Math.floor(tmax) + 1 }, (_, s) => s).filter(s => s % Math.ceil((tmax + 1) / 12) === 0).map(s => (
          <text key={s} x={x(s)} y={H - 5} textAnchor="middle" fontSize="10.5" fill="var(--text-3)">{s}s</text>
        ))}
        <path d={path} fill="none" stroke="var(--series-1)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {markers.map((m, i) => {
          const k = nearest(t, m); const v = k >= 0 ? y[k] : null
          return v === null ? null : <circle key={i} cx={x(m)} cy={yy(v)} r="4.5" fill="var(--series-1)" stroke="var(--surface)" strokeWidth="2" />
        })}
        {idx >= 0 && t[idx] !== null && (
          <g>
            <line x1={x(t[idx] as number)} x2={x(t[idx] as number)} y1={T} y2={H - B} stroke="var(--text-2)" strokeWidth="1" />
            {hv !== null && <circle cx={x(t[idx] as number)} cy={yy(hv)} r="4" fill="var(--series-1)" stroke="var(--surface)" strokeWidth="2" />}
          </g>
        )}
      </svg>
      {idx >= 0 && t[idx] !== null && (
        <div className="tip" style={{ left: `min(calc(${(x(t[idx] as number) / W) * 100}% + 8px), calc(100% - 190px))` }}>
          <b>{hv === null ? 'no confident pose' : fmtNum(hv, unit)}</b> <span className="muted">at {(t[idx] as number).toFixed(2)} s</span>
        </div>
      )}
    </div>
  )
}

function nearest(t: (number | null)[], target: number): number {
  let best = -1, d = Infinity
  t.forEach((v, i) => { if (v !== null && Math.abs(v - target) < d) { d = Math.abs(v - target); best = i } })
  return best
}
function niceStep(raw: number): number {
  const p = Math.pow(10, Math.floor(Math.log10(Math.max(raw, 1e-9))))
  const f = raw / p
  return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p
}
const fmtTick = (v: number) => (Math.abs(v) < 10 && v % 1 !== 0 ? v.toFixed(1) : v.toFixed(0))

/** Number line for one item: the rating bands, the band the assessor chose, and the measured value +/- uncertainty. */
export function BandBar({ r }: { r: ItemResult }) {
  const m = r.measured
  if (!m || m.value === null || m.uncertainty === null) return null
  const b = r.thresholds.bounds, u = m.uncertainty
  const span = b.length > 1 ? b[b.length - 1] - b[0] : Math.max(Math.abs(b[0]), u * 4, 1e-6)
  const lo = Math.min(b[0] - span * 0.6, m.value - u * 1.6), hi = Math.max(b[b.length - 1] + span * 0.6, m.value + u * 1.6)
  const WW = 420, H = 46, x = (v: number) => 4 + ((v - lo) / (hi - lo)) * (WW - 8)
  const edges = [lo, ...b, hi]
  const color = r.verdict === 'agree' ? 'var(--good)' : r.verdict === 'disagree' ? 'var(--bad)' : 'var(--neutral)'
  return (
    <svg viewBox={`0 0 ${WW} ${H}`} style={{ width: '100%', maxWidth: 440, display: 'block' }} role="img"
      aria-label={`${r.label}: measured ${fmtNum(m.value, r.unit)} plus or minus ${fmtNum(u, r.unit)}; assessed ${r.assessed.label}`}>
      {r.thresholds.options.map((id, i) => {
        const on = id === r.assessed.rating
        const x0 = x(edges[i]) + 1, x1 = x(edges[i + 1]) - 1
        return (
          <g key={id}>
            <rect x={x0} y={18} width={Math.max(0, x1 - x0)} height={10} rx={3} fill={on ? 'var(--text-3)' : 'var(--neutral-bg)'} />
            <text x={(x0 + x1) / 2} y={41} textAnchor="middle" fontSize="9.5" fill={on ? 'var(--text)' : 'var(--text-3)'}
              fontWeight={on ? 700 : 400}>{r.thresholds.labels[i].split(' / ')[0]}{on ? ' (assessed)' : ''}</text>
          </g>
        )
      })}
      {b.map(v => <text key={v} x={x(v)} y={13} textAnchor="middle" fontSize="9" fill="var(--text-3)">{fmtTick(v)}</text>)}
      <line x1={x(m.value - u)} x2={x(m.value + u)} y1={23} y2={23} stroke={color} strokeWidth="3" strokeLinecap="round" />
      <circle cx={x(m.value)} cy={23} r="6" fill={color} stroke="var(--surface)" strokeWidth="2" />
    </svg>
  )
}
