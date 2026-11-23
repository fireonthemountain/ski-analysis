import { useEffect, useState } from 'react'
import type { RunBrief } from '../types'
import { deleteRun, fmtTime, listRuns } from '../api'

export function History({ onOpen }: { onOpen: (id: string) => void }) {
  const [runs, setRuns] = useState<RunBrief[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = () => listRuns().then(setRuns).catch(e => setError(e.message))
  useEffect(() => { load() }, [])
  if (error) return <div className="card"><div className="notice err">{error}</div></div>
  if (!runs) return <div className="card">Loading…</div>
  if (!runs.length) return <div className="card muted">No validations yet for this user.</div>
  return (
    <div className="card">
      <h2>Past validations</h2>
      <table className="agree hist">
        <thead><tr><th>When</th><th>Run</th><th>Media</th><th>Items</th><th>✓ Agrees</th><th>✕ Disagrees</th><th>? Inconclusive</th><th>Status</th><th /></tr></thead>
        <tbody>
          {runs.map(r => (
            <tr key={r.id} className="main" onClick={() => onOpen(r.id)}>
              <td>{fmtTime(r.created_at)}</td><td><b>{r.run_label}</b></td>
              <td>{r.media_kind}{r.media_kind === 'images' ? ` (${r.media_files.length})` : ''}</td><td>{r.items_assessed}</td>
              <td>{r.summary?.agree ?? '–'}</td><td>{r.summary?.disagree ?? '–'}</td><td>{r.summary?.inconclusive ?? '–'}</td>
              <td>{r.status}{r.error ? <div className="tiny">{r.error}</div> : null}</td>
              <td><button className="btn link" onClick={e => { e.stopPropagation(); if (confirm(`Delete "${r.run_label}" and its files?`)) deleteRun(r.id).then(load).catch(x => setError(x.message)) }}>delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
