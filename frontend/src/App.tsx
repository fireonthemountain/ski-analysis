import { useEffect, useState } from 'react'
import type { Catalog } from './types'
import { fetchCatalog, getUser, setUser } from './api'
import { AssessmentForm } from './components/AssessmentForm'
import { ResultsView } from './components/ResultsView'
import { History } from './components/History'

type Page = { name: 'new' } | { name: 'history' } | { name: 'run'; id: string }

function pageFromHash(): Page {
  const h = window.location.hash.replace(/^#\/?/, '')
  if (h.startsWith('run/')) return { name: 'run', id: h.slice(4) }
  return h === 'history' ? { name: 'history' } : { name: 'new' }
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [user, setU] = useState(getUser())

  useEffect(() => { fetchCatalog().then(setCatalog).catch(e => setError(`Cannot reach the API (${e.message}). Start the backend: scripts/run_dev.sh`)) }, [])
  useEffect(() => {
    const on = () => setPage(pageFromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = (p: Page) => { window.location.hash = p.name === 'run' ? `/run/${p.id}` : `/${p.name}` }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Ski assessment validation</h1>
          <div className="sub">Rate what you saw. The video or screenshots are measured, and each rating comes back as agrees, disagrees or inconclusive.</div>
        </div>
        <nav className="tabs">
          <button className={`tab ${page.name === 'new' ? 'on' : ''}`} onClick={() => go({ name: 'new' })}>New validation</button>
          <button className={`tab ${page.name === 'history' ? 'on' : ''}`} onClick={() => go({ name: 'history' })}>History</button>
        </nav>
        <label className="user" title="Sent as the X-User-Id header; runs are listed per user. Not a login.">
          User <input type="text" value={user} onChange={e => setU(e.target.value)}
            onBlur={() => { const u = user.trim() || 'anonymous'; setU(u); setUser(u) }} />
        </label>
      </header>
      {error && <div className="notice err">{error}</div>}
      {page.name === 'new' && catalog && <AssessmentForm catalog={catalog} onSubmitted={id => go({ name: 'run', id })} />}
      {page.name === 'history' && <History key={user} onOpen={id => go({ name: 'run', id })} />}
      {page.name === 'run' && <ResultsView key={page.id} id={page.id} onBack={() => go({ name: 'new' })} />}
    </div>
  )
}
