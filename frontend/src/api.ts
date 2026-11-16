import type { Catalog, RunBrief, RunDetail } from './types'

// Relative URLs: Vite proxies /api to the backend in dev; the backend serves the built UI in prod.
const BASE = (import.meta.env.VITE_API_URL as string | undefined) || '/api/v1'

export function getUser(): string {
  try { return localStorage.getItem('ski-user') || 'anonymous' } catch { return 'anonymous' }
}
export function setUser(u: string) {
  try { localStorage.setItem('ski-user', u) } catch { /* private mode */ }
}
const headers = () => ({ 'X-User-Id': getUser() })

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const b = await r.json()
      msg = typeof b.detail === 'string' ? b.detail : (b.detail || []).map((d: { loc?: string[]; msg: string }) => `${(d.loc || []).join('.')}: ${d.msg}`).join('; ')
    } catch { /* not json */ }
    throw new Error(msg)
  }
  return r.json()
}

export const fetchCatalog = () => fetch(`${BASE}/assessment/catalog`).then(r => json<Catalog>(r))
export const listRuns = () => fetch(`${BASE}/validations`, { headers: headers() }).then(r => json<{ validations: RunBrief[] }>(r)).then(b => b.validations)
export const getRun = (id: string) => fetch(`${BASE}/validations/${id}`, { headers: headers() }).then(r => json<RunDetail>(r))
export const deleteRun = (id: string) => fetch(`${BASE}/validations/${id}`, { method: 'DELETE', headers: headers() }).then(r => { if (!r.ok) throw new Error('Delete failed') })
export const fileUrl = (id: string, path: string) => `${BASE}/validations/${id}/files/${path}`

export function submitRun(assessment: object, files: File[], onProgress: (pct: number) => void): Promise<{ id: string }> {
  return new Promise((resolve, reject) => {
    const fd = new FormData()
    fd.append('assessment', JSON.stringify(assessment))
    files.forEach(f => fd.append('files', f, f.name))
    const xhr = new XMLHttpRequest()
    xhr.upload.onprogress = e => { if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100)) }
    xhr.onload = () => {
      let body: any = {}
      try { body = JSON.parse(xhr.responseText) } catch { /* ignore */ }
      if (xhr.status === 202) resolve(body)
      else reject(new Error(typeof body.detail === 'string' ? body.detail
        : Array.isArray(body.detail) ? body.detail.map((d: any) => d.msg).join('; ') : `Upload failed (${xhr.status})`))
    }
    xhr.onerror = () => reject(new Error('Network error - is the backend running on port 8003?'))
    xhr.open('POST', `${BASE}/validations`)
    xhr.setRequestHeader('X-User-Id', getUser())
    xhr.send(fd)
  })
}

/** 12-hour local time, e.g. "Nov 15, 5:42 PM" */
export function fmtTime(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })
}
export function fmtNum(v: number | null | undefined, unit = ''): string {
  if (v === null || v === undefined) return '-'
  if (Object.is(v, -0) || Math.abs(v) < 0.005) v = 0
  const a = Math.abs(v)
  const s = a >= 10 || unit === 'deg' || unit === '%' ? v.toFixed(0) : v.toFixed(2)
  return unit === 'deg' ? `${s}°` : unit === '%' ? `${s}%` : unit ? `${s} ${unit}` : s
}
