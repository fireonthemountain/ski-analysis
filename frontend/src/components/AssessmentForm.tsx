import { useMemo, useRef, useState } from 'react'
import type { Catalog, CatalogItem } from '../types'
import { submitRun, fmtNum } from '../api'

type Kind = 'video' | 'images' | null
const ext = (n: string) => n.slice(n.lastIndexOf('.')).toLowerCase()

function rangeText(o: { min: number | null; max: number | null }, unit: string): string {
  if (o.min === null && o.max === null) return ''
  if (o.min === null) return `< ${fmtNum(o.max, unit)}`
  if (o.max === null) return `≥ ${fmtNum(o.min, unit)}`
  const bare = (v: number) => (unit === 'deg' || unit === '%' ? v.toFixed(0) : String(+v.toFixed(2)))
  return `${bare(o.min)} to ${fmtNum(o.max, unit)}`
}

export function AssessmentForm({ catalog, onSubmitted }: { catalog: Catalog; onSubmitted: (id: string) => void }) {
  const [files, setFiles] = useState<File[]>([])
  const [ratings, setRatings] = useState<Record<string, string>>({})
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [meta, setMeta] = useState({ run_label: '', skier: '', assessed_by: '', terrain: '', general_notes: '' })
  const [view, setView] = useState<'auto' | 'frontal' | 'side'>('auto')
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const input = useRef<HTMLInputElement>(null)

  const kind: Kind = files.length === 0 ? null : catalog.video_extensions.includes(ext(files[0].name)) ? 'video' : 'images'
  const groups = useMemo(() => {
    const g: Record<string, CatalogItem[]> = {}
    catalog.items.forEach(i => { (g[i.group] ||= []).push(i) })
    return g
  }, [catalog])

  const addFiles = (list: FileList | File[]) => {
    const incoming = Array.from(list)
    const bad = incoming.filter(f => ![...catalog.video_extensions, ...catalog.image_extensions].includes(ext(f.name)))
    if (bad.length) { setError(`Unsupported file type: ${bad.map(f => f.name).join(', ')}`); return }
    const vids = incoming.filter(f => catalog.video_extensions.includes(ext(f.name)))
    setError(null)
    if (vids.length) {
      if (incoming.length > 1) setError('Use ONE video, or a set of images - not both. Keeping the first video.')
      setFiles([vids[0]])
    } else {
      const prev = kind === 'images' ? files : []
      setFiles([...prev, ...incoming].slice(0, catalog.limits.max_images))
    }
  }

  /** Why an item cannot be measured with the media/view chosen so far (shown before submitting). */
  const blocked = (i: CatalogItem): string | null => {
    if (i.needs_video && kind === 'images') return 'needs video'
    if (i.needs_view && view !== 'auto' && view !== i.needs_view) return `needs a ${i.needs_view === 'frontal' ? 'front/back' : 'side'} view`
    return null
  }
  const rated = Object.keys(ratings).length
  const canSubmit = files.length > 0 && rated > 0 && busy === null

  const submit = async () => {
    setError(null); setBusy(0)
    const assessment = {
      run_label: meta.run_label.trim() || files[0].name,
      skier: meta.skier || null, assessed_by: meta.assessed_by || null, terrain: meta.terrain || null,
      general_notes: meta.general_notes || null, camera_view: view,
      items: Object.entries(ratings).map(([item_id, rating]) => ({ item_id, rating, notes: notes[item_id] || null })),
    }
    try {
      const { id } = await submitRun(assessment, files, setBusy)
      onSubmitted(id)
    } catch (e) {
      setError((e as Error).message); setBusy(null)
    }
  }

  return (
    <div className="grid-form">
      <div>
        <div className="card">
          <h2>1. Media</h2>
          <div className={`drop ${over ? 'over' : ''}`} onClick={() => input.current?.click()}
            onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
            onDrop={e => { e.preventDefault(); setOver(false); addFiles(e.dataTransfer.files) }}>
            <b>Drop one video, or several screenshots</b>
            <div className="small muted">or click to choose · video up to {catalog.limits.max_video_mb} MB (first {catalog.limits.max_analysis_seconds}s analysed) · up to {catalog.limits.max_images} images</div>
            <input ref={input} type="file" multiple hidden
              accept={[...catalog.video_extensions, ...catalog.image_extensions].join(',')}
              onChange={e => { if (e.target.files) addFiles(e.target.files); e.target.value = '' }} />
          </div>
          {files.length > 0 && (
            <ul className="filelist">
              {files.map((f, i) => (
                <li key={i}><span>{f.name} <span className="tiny">{(f.size / 1048576).toFixed(1)} MB</span></span>
                  <button className="btn link" onClick={() => setFiles(files.filter((_, k) => k !== i))}>remove</button></li>
              ))}
            </ul>
          )}
          {kind === 'images' && <div className="notice warn" style={{ marginTop: 10 }}>Screenshots only: stance, flexion, edge angle, angulation and separation can be checked. Timing, turn shape, symmetry and flexion range need video.</div>}
          <div style={{ marginTop: 12 }}>
            <div className="small muted" style={{ marginBottom: 4 }}>Camera view</div>
            <div className="seg">
              {([['auto', 'Auto-detect'], ['frontal', 'Front / back'], ['side', 'Side']] as const).map(([v, l]) => (
                <button key={v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>{l}</button>
              ))}
            </div>
            <div className="tiny" style={{ marginTop: 4 }}>Front/back: skier coming at or going away from the camera (edging, angulation, turns). Side: fore-aft balance.</div>
          </div>
        </div>
        <div className="card">
          <h2>2. Run details <span className="tiny">(optional)</span></h2>
          <label className="field"><span>Run label</span><input type="text" value={meta.run_label} placeholder="e.g. Blue groomer, run 3" onChange={e => setMeta({ ...meta, run_label: e.target.value })} /></label>
          <div className="row">
            <label className="field" style={{ flex: 1 }}><span>Skier</span><input type="text" value={meta.skier} onChange={e => setMeta({ ...meta, skier: e.target.value })} /></label>
            <label className="field" style={{ flex: 1 }}><span>Assessed by</span><input type="text" value={meta.assessed_by} onChange={e => setMeta({ ...meta, assessed_by: e.target.value })} /></label>
          </div>
          <label className="field"><span>Terrain / conditions</span><input type="text" value={meta.terrain} onChange={e => setMeta({ ...meta, terrain: e.target.value })} /></label>
          <label className="field"><span>General observations</span><textarea value={meta.general_notes} onChange={e => setMeta({ ...meta, general_notes: e.target.value })} /></label>
        </div>
        <div className="card">
          {error && <div className="notice err">{error}</div>}
          {busy !== null && <><div className="small">Uploading… {busy}%</div><div className="progress"><div style={{ width: `${busy}%` }} /></div></>}
          <button className="btn primary" disabled={!canSubmit} onClick={submit} style={{ width: '100%' }}>
            Validate {rated || ''} assessment item{rated === 1 ? '' : 's'}
          </button>
          <div className="tiny" style={{ marginTop: 6 }}>{files.length === 0 ? 'Add media. ' : ''}{rated === 0 ? 'Rate at least one item on the right.' : ''}</div>
        </div>
      </div>

      <div className="card">
        <h2>3. Your assessment <span className="tiny">{catalog.framework} · rate only what you observed; click a rating again to clear it</span></h2>
        {Object.entries(groups).map(([g, list]) => (
          <div key={g}>
            <div className="groupname">{g}</div>
            <div className="items">
              {list.map(i => {
                const why = blocked(i)
                return (
                  <div key={i.id} className={`item ${ratings[i.id] ? 'rated' : ''} ${why ? 'unavailable' : ''}`}>
                    <h3>{i.label}
                      {i.needs_video && <span className="tag">video only</span>}
                      {i.needs_view && <span className="tag">{i.needs_view === 'frontal' ? 'front/back view' : 'side view'}</span>}
                      {i.experimental && <span className="tag warn">experimental</span>}
                      {why && <span className="tag warn">will be inconclusive: {why}</span>}
                    </h3>
                    <div className="small muted">{i.question}</div>
                    <div className="opts">
                      {i.options.map(o => (
                        <button key={o.id} className={`opt ${ratings[i.id] === o.id ? 'on' : ''}`} title={o.hint}
                          onClick={() => setRatings(r => { const n = { ...r }; if (n[i.id] === o.id) delete n[i.id]; else n[i.id] = o.id; return n })}>
                          {o.label}<span className="rng">{rangeText(o, i.unit)}</span>
                        </button>
                      ))}
                    </div>
                    <details>
                      <summary className="tiny" style={{ cursor: 'pointer' }}>How it is measured · {i.fundamental.split(' - ')[0]}</summary>
                      <div className="tiny" style={{ marginTop: 4 }}>{i.measure} Uncertainty floor ±{i.base_uncertainty} {i.unit}.</div>
                      <div className="tiny">{i.fundamental}</div>
                      {i.limitations.map(l => <div key={l} className="tiny">• {l}</div>)}
                    </details>
                    {ratings[i.id] && <input type="text" style={{ marginTop: 6 }} placeholder="What did you see? (optional note)"
                      value={notes[i.id] || ''} onChange={e => setNotes({ ...notes, [i.id]: e.target.value })} />}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
