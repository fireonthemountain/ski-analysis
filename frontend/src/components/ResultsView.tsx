import { Fragment, useEffect, useRef, useState } from 'react'
import type { ItemResult, Result, RunDetail, Verdict } from '../types'
import { fileUrl, fmtNum, fmtTime, getRun } from '../api'
import { BandBar, TimeChart } from './Charts'

const ICON: Record<Verdict, string> = { agree: '✓', disagree: '✕', inconclusive: '?' }
const WORD: Record<Verdict, string> = { agree: 'Agrees', disagree: 'Disagrees', inconclusive: 'Inconclusive' }
export const VerdictBadge = ({ v }: { v: Verdict }) => <span className={`verdict ${v}`}><span aria-hidden>{ICON[v]}</span>{WORD[v]}</span>

const CHARTS: { key: string; title: string; unit: string; sub: string; item?: string }[] = [
  { key: 'inclination', title: 'Lean (inclination)', unit: 'deg', sub: 'leg axis vs vertical · + = image right' },
  { key: 'edge_proxy', title: 'Edge angle proxy', unit: 'deg', sub: 'outside shin tilt into the turn', item: 'edge_angle' },
  { key: 'angulation', title: 'Angulation', unit: 'deg', sub: 'legs inclined more than torso', item: 'angulation' },
  { key: 'knee_mean', title: 'Knee angle', unit: 'deg', sub: 'mean of both legs · 180 = straight', item: 'stance_height' },
  { key: 'hip_angle', title: 'Hip angle', unit: 'deg', sub: 'torso vs thigh · 180 = upright', item: 'hip_flexion' },
  { key: 'stance_width_2d', title: 'Stance width', unit: 'x hip width', sub: 'ankle spacing across the body', item: 'stance_width' },
  { key: 'fore_aft', title: 'Fore-aft', unit: 'deg', sub: 'ankle to centre of mass vs slope normal · + = forward', item: 'fore_aft' },
  { key: 'separation', title: 'Upper / lower separation', unit: 'deg', sub: 'shoulders vs feet · + = turned to skier’s right', item: 'separation' },
  { key: 'counter', title: 'Counter', unit: 'deg', sub: '+ = facing outside of the turn', item: 'counter' },
  { key: 'pose_conf', title: 'Pose confidence', unit: '', sub: 'core joints · below 0.5 a frame is not used' },
]

export function ResultsView({ id, onBack }: { id: string; onBack: () => void }) {
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let stop = false
    const tick = async () => {
      try {
        const r = await getRun(id)
        if (stop) return
        setRun(r)
        if (r.status === 'pending' || r.status === 'processing') setTimeout(tick, 1000)
      } catch (e) { if (!stop) setError((e as Error).message) }
    }
    tick()
    return () => { stop = true }
  }, [id])

  if (error) return <div className="card"><div className="notice err">{error}</div><button className="btn" onClick={onBack}>Back</button></div>
  if (!run) return <div className="card">Loading…</div>
  if (run.status === 'failed') return <div className="card"><h2>{run.run_label}</h2><div className="notice err">Processing failed: {run.error}</div><button className="btn" onClick={onBack}>Back</button></div>
  if (run.status !== 'completed' || !run.result) {
    const p = run.progress
    return (
      <div className="card">
        <h2>Analysing “{run.run_label}”</h2>
        <div className="progress"><div style={{ width: `${(p?.fraction ?? 0) * 100}%` }} /></div>
        <div className="small muted">{p?.message ?? (run.status === 'pending' ? 'Queued behind another run' : 'Working…')}</div>
        <div className="tiny" style={{ marginTop: 6 }}>Pose estimation runs on this Mac’s CPU: roughly 5–10 frames per second with the heavy model.</div>
      </div>
    )
  }
  return <Report run={run} res={run.result} onBack={onBack} />
}

function Report({ run, res, onBack }: { run: RunDetail; res: Result; onBack: () => void }) {
  const [open, setOpen] = useState<string | null>(res.results.find(r => r.verdict === 'disagree')?.item_id ?? null)
  const [hoverT, setHoverT] = useState<number | null>(null)
  const [zoom, setZoom] = useState<string | null>(null)
  const video = useRef<HTMLVideoElement>(null)
  const s = res.summary
  const isVideo = res.media.kind === 'video'
  const seek = (t: number) => { if (video.current) { video.current.currentTime = t; video.current.pause() } }
  const byId: Record<string, ItemResult> = Object.fromEntries(res.results.map(r => [r.item_id, r]))
  const charts = CHARTS.filter(c => res.series[c.key]?.some(v => v !== null))

  return (
    <div>
      <div className="row" style={{ marginBottom: 12 }}>
        <button className="btn" onClick={onBack}>← New validation</button>
        <h2 style={{ margin: 0 }}>{res.assessment.run_label}</h2>
        <span className="small muted">
          {fmtTime(run.created_at)} · {isVideo ? `video ${res.media.duration_s}s @ ${res.media.analysis_fps} fps analysed` : `${res.media.files.length} still image(s)`}
          {' · '}{res.view.view === 'frontal' ? 'front/back view' : `${res.view.view} view`}{res.view.source === 'user' ? ' (set by you)' : ' (auto)'}{res.view.facing ? `, skier ${res.view.facing}` : ''}
        </span>
      </div>
      {res.warnings.map(w => <div key={w} className="notice warn">{w}</div>)}

      <div className="tiles" style={{ marginBottom: 14 }}>
        <div className="tile"><div className="k">Agreement</div><div className="v">{s.agreement_rate === null ? '–' : `${Math.round(s.agreement_rate * 100)}%`}</div><div className="d">{s.agree} of {s.decided} items the evidence could decide</div></div>
        <div className="tile"><div className="k">✓ Agrees</div><div className="v" style={{ color: 'var(--good)' }}>{s.agree}</div><div className="d">evidence supports your rating</div></div>
        <div className="tile"><div className="k">✕ Disagrees</div><div className="v" style={{ color: 'var(--bad)' }}>{s.disagree}</div><div className="d">measured outside your band</div></div>
        <div className="tile"><div className="k">? Inconclusive</div><div className="v">{s.inconclusive}</div><div className="d">not measurable or too close to call</div></div>
        <div className="tile"><div className="k">Pose quality</div><div className="v">{res.pose.mean_confidence.toFixed(2)}</div><div className="d">{res.pose.frames_confident} of {res.pose.frames} frames confident{res.pose.has_3d ? '' : ' · 2D only'}</div></div>
        {isVideo && <div className="tile"><div className="k">Turns found</div><div className="v">{res.turns.length}</div><div className="d">{res.turns.filter(t => t.direction === 'left').length} left · {res.turns.filter(t => t.direction === 'right').length} right</div></div>}
      </div>

      <div className="card">
        <h2>Agreement table <span className="tiny">click a row for evidence frames, thresholds and method</span></h2>
        <div style={{ overflowX: 'auto' }}>
          <table className="agree">
            <thead><tr><th>Item</th><th>You assessed</th><th>Measured</th><th style={{ minWidth: 300 }}>Where it sits</th><th>Verdict</th><th>Confidence</th><th>Why</th></tr></thead>
            <tbody>
              {res.results.map(r => (
                <Fragment key={r.item_id}>
                  <tr className="main" onClick={() => setOpen(open === r.item_id ? null : r.item_id)}>
                    <td><b>{r.label}</b>{r.experimental && <> <span className="tag warn">experimental</span></>}<div className="tiny">{r.group}</div></td>
                    <td>{r.assessed.label}{r.assessed.notes && <div className="tiny">“{r.assessed.notes}”</div>}</td>
                    <td>{r.measured ? <>
                      <b>{r.measured.value === null ? r.measured.category_label : fmtNum(r.measured.value, r.unit)}</b>
                      {r.measured.uncertainty !== null && <span className="muted"> ± {fmtNum(r.measured.uncertainty, r.unit === 'deg' || r.unit === '%' ? r.unit : '')}</span>}
                      <div className="tiny">{r.measured.value !== null && `${r.measured.category_label} · `}{r.measured.n_turns ? `${r.measured.n_turns} turns · ` : ''}{r.measured.n_frames} frames</div>
                    </> : <span className="muted">not measured</span>}</td>
                    <td><BandBar r={r} /></td>
                    <td><VerdictBadge v={r.verdict} /></td>
                    <td>{r.measured ? <><span className="conf"><i style={{ width: `${r.confidence * 100}%` }} /></span>{r.confidence.toFixed(2)} <span className="tiny">{r.confidence_label}</span></> : <span className="muted">–</span>}</td>
                    <td className="small" style={{ maxWidth: 420 }}>{r.reason}</td>
                  </tr>
                  {open === r.item_id && (
                    <tr className="detail"><td colSpan={7}>
                      <div className="small"><b>How it is measured:</b> {r.method}</div>
                      <div className="tiny">Bands: {r.thresholds.labels.map((l, i) => `${l}${i < r.thresholds.bounds.length ? ` | ${r.thresholds.bounds[i]} ${r.unit} |` : ''}`).join(' ')} · {r.fundamental}</div>
                      {[...r.notes, ...r.limitations].map(n => <div key={n} className="tiny">• {n}</div>)}
                      {r.evidence.length > 0 ? (
                        <div className="thumbs">
                          {r.evidence.filter(e => e.image).map(e => (
                            <figure key={e.frame} className="thumb" onClick={() => setZoom(fileUrl(run.id, e.image!))}>
                              <img src={fileUrl(run.id, e.image!)} alt={e.caption} loading="lazy" />
                              <figcaption>{isVideo ? <a href="#" onClick={ev => { ev.preventDefault(); ev.stopPropagation(); seek(e.t ?? 0) }}>{(e.t ?? 0).toFixed(2)} s</a> : e.source} · {e.caption} · pose {e.pose_conf?.toFixed(2)}</figcaption>
                            </figure>
                          ))}
                        </div>
                      ) : <div className="tiny" style={{ marginTop: 6 }}>No evidence frames: nothing was measured for this item.</div>}
                    </td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {isVideo ? (
        <div className="two" style={{ marginTop: 14 }}>
          <div className="card">
            <h2>Annotated video <span className="tiny">skeleton overlay · click a chart to jump here</span></h2>
            {res.annotated_video
              ? <video ref={video} src={fileUrl(run.id, res.annotated_video)} controls playsInline onTimeUpdate={e => setHoverT((e.target as HTMLVideoElement).currentTime)} />
              : <div className="muted small">No annotated video (ffmpeg not found on the server).</div>}
            <div className="legend" style={{ marginTop: 8 }}>
              <span><i style={{ background: '#3caaff' }} />skier’s left side</span><span><i style={{ background: '#ffc850' }} />right side</span>
              <span><i style={{ background: '#ff3c3c' }} />leg axis</span><span><i style={{ background: '#ffff3c' }} />torso axis</span>
            </div>
          </div>
          <div className="card">
            <h2>Metrics over time</h2>
            <div className="legend">
              <span><i style={{ background: 'var(--band-right)', border: '1px solid var(--border)' }} />right turn</span>
              <span><i style={{ background: 'var(--band-left)', border: '1px solid var(--border)' }} />left turn</span>
              <span>- - - rating threshold</span><span>● evidence frame</span><span>gaps = no confident pose</span>
            </div>
            {charts.map(c => {
              const it = c.item ? byId[c.item] : undefined
              return <TimeChart key={c.key} title={c.title} subtitle={c.sub} unit={c.unit} t={res.series.t} y={res.series[c.key]} turns={res.turns}
                refs={it ? it.thresholds.bounds.map((b, i) => ({ value: b, label: `${it.thresholds.labels[i].split(' / ')[0]} | ${it.thresholds.labels[i + 1].split(' / ')[0]}` })) : c.key === 'pose_conf' ? [{ value: 0.5, label: 'trust gate' }] : []}
                markers={it ? it.evidence.map(e => e.t ?? 0) : []} hoverT={hoverT} onHover={setHoverT} onPick={seek} />
            })}
          </div>
        </div>
      ) : (
        <div className="card">
          <h2>Your images with pose overlay <span className="tiny">check the skeleton sits on the skier - if it does not, the numbers are not trustworthy</span></h2>
          <div className="thumbs">
            {res.gallery.map(g => (
              <figure key={g.frame} className="thumb" style={{ width: 340 }} onClick={() => setZoom(fileUrl(run.id, g.image))}>
                <img src={fileUrl(run.id, g.image)} alt={g.source} loading="lazy" />
                <figcaption>{g.source} · {g.detected ? `pose confidence ${g.pose_conf.toFixed(2)}` : 'no skier detected'}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}

      <div className="tiny" style={{ marginTop: 10 }}>
        Pose model: {res.pose.estimator} · processed in {res.processing_seconds}s · thresholds are this tool’s defaults (backend/pipeline/assessment.py), not published PSIA numbers.
      </div>
      {zoom && <div className="lightbox" onClick={() => setZoom(null)}><img src={zoom} alt="annotated frame" /></div>}
    </div>
  )
}
