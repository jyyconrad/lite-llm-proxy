import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { Box, Text, Select, Stack, Button } from '@chakra-ui/react'

function Bar({ label, value, max, highlight=false }){
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  const bg = highlight ? '#fde2e2' : '#e6eef6'
  const barColor = highlight ? '#ef4444' : '#6ee7b7'
  return (
    <Box mb={3}>
      <Box display="flex" justifyContent="space-between" fontSize="12px" color="#56667a">
        <Box>{label}</Box>
        <Box>{value}</Box>
      </Box>
      <Box height="8px" bg={bg} borderRadius="8px" overflow="hidden" mt={2}>
        <Box width={`${pct}%`} height="100%" bg={barColor} />
      </Box>
    </Box>
  )
}

export default function ModelUsage(){
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('calls')
  const [threshold, setThreshold] = useState(100)

  useEffect(()=>{ load() }, [])
  async function load(){
    setLoading(true)
    try{
      const data = await api.getModelUsageStats()
      setStats(data || [])
    }catch(e){ setStats([]) }
    setLoading(false)
  }

  const max = stats.reduce((m,s)=> Math.max(m, s.call_count || 0), 0)

  if (loading) return <div>Loading...</div>
  if (!stats.length) return <div className="muted">No model usage data</div>

  const sorted = [...stats].sort((a,b) => {
    if (sortBy === 'calls') return (b.call_count || 0) - (a.call_count || 0)
    if (sortBy === 'tokens') return (b.total_tokens || 0) - (a.total_tokens || 0)
    return a.model_name.localeCompare(b.model_name)
  })

  return (
    <Box>
      <Stack direction="row" className="font-bold text-white" spacing={3} align="center" mb={3}>
        <Text fontSize="sm">排序：</Text>
        <Select width="160px" value={sortBy} onChange={e=>setSortBy(e.target.value)}>
          <option value="calls">按调用数</option>
          <option value="tokens">按Token</option>
          <option value="name">按名称</option>
        </Select>
        <Text fontSize="sm">阈值（调用数高亮）:</Text>
        <Select width="120px" value={String(threshold)} onChange={e=>setThreshold(Number(e.target.value))}>
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="500">500</option>
          <option value="1000">1000</option>
        </Select>
        <Button size="sm" onClick={load}>刷新</Button>
      </Stack>

      {sorted.map(s=> (
        <Bar key={s.model_name} label={s.model_name} value={s.call_count || 0} max={max} highlight={(s.call_count||0) > threshold} />
      ))}
    </Box>
  )
}
