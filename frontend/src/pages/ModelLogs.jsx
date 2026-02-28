import React, { useEffect, useState } from 'react'
import api from '../services/api'

export default function ModelLogs({ user, onNavigate }){
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)

  useEffect(()=>{ load() }, [page])
  async function load(){
    setLoading(true)
    try{
      // reuse recent-activity endpoint for per-call style listing
      const res = await api.getRecentActivity(perPage)
      setLogs(res || [])
    }catch(e){ setLogs([]) }
    setLoading(false)
  }

  if(!user || user.role !== 'admin'){
    return (
      <div>
        <div className="card">
          <h3>Access denied</h3>
          <div className="muted">Only administrators can view model logs.</div>
          <div style={{marginTop:12}}>
            <button onClick={() => onNavigate && onNavigate('dashboard')}>Back</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <h2>Model Logs</h2>
        <div>
          <button onClick={() => onNavigate && onNavigate('dashboard')}>Back</button>
        </div>
      </div>

      <div className="table-container" style={{marginTop:12}}>
        <table>
          <thead>
            <tr><th>ID</th><th>User</th><th>Model</th><th>Tokens</th><th>Cost</th><th>Timestamp</th></tr>
          </thead>
          <tbody>
            {loading ? <tr><td colSpan={6}>Loading...</td></tr> : logs.map(l=> (
              <tr key={l.id}>
                <td>{l.id}</td>
                <td>{l.user_email}</td>
                <td>{l.model_name}</td>
                <td>{l.total_tokens}</td>
                <td>{l.cost}</td>
                <td>{l.timestamp}</td>
              </tr>
            ))}
            {!loading && logs.length===0 && <tr><td colSpan={6}>No logs</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
