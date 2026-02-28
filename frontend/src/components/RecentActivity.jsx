import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { Box, Text, Stack, Badge, Tag, Select } from '@chakra-ui/react'

function ActivityItem({ a, costThreshold=1.0 }){
  const isError = a.status && a.status !== 'success'
  const highCost = (Number(a.cost) || 0) > costThreshold
  return (
    <Box p={3} borderWidth={1} borderColor={isError ? 'red.100' : 'gray.100'} bg={isError ? 'red.50' : 'white'} rounded="md">
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Text fontWeight={600}>{a.model_name}</Text>
          <Text fontSize="sm" color="gray.500">{a.user_email}</Text>
        </Box>
        <Box textAlign="right">
          
          <Stack direction="row" spacing={2} mt={1} justify="flex-end">
            {isError && <Badge colorScheme="red">Error</Badge>}
            
          </Stack>
        </Box>
      </Box>
      <Box display="flex" justifyContent="space-between" mt={2} fontSize="sm" color="gray.600">
        <Box>Tokens: <Text as="span" fontWeight={600}>{a.total_tokens}</Text></Box>
        <Box><Text fontSize="sm">{new Date(a.created_at || a.timestamp).toLocaleString()}</Text></Box>
      </Box>
    </Box>
  )
}

export default function RecentActivity({ costThreshold=1.0 }){
  const [acts, setActs] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('time')

  useEffect(()=>{ load() }, [])
  async function load(){
    setLoading(true)
    try{
      const data = await api.getRecentActivity(10)
      setActs(data || [])
    }catch(e){ setActs([]) }
    setLoading(false)
  }

  if (loading) return <div>Loading...</div>
  if (!acts.length) return <div className="muted">No recent activity</div>

  const sorted = [...acts].sort((a,b) => {
    if (sortBy === 'cost') return (Number(b.cost)||0) - (Number(a.cost)||0)
    if (sortBy === 'tokens') return (Number(b.total_tokens)||0) - (Number(a.total_tokens)||0)
    return new Date(b.created_at || b.timestamp) - new Date(a.created_at || a.timestamp)
  })

  return (
    <Box>
      <Stack className="font-bold text-white" direction="row" spacing={3} align="center" mb={3}>
        <Text fontSize="sm">排序：</Text>
        <Select width="160px" value={sortBy} onChange={e=>setSortBy(e.target.value)}>
          <option value="time">按时间（新 → 旧）</option>
          <option value="cost">按成本（降序）</option>
          <option value="tokens">按 Token（降序）</option>
        </Select>
      </Stack>
      <Stack spacing={3}>
        {sorted.map(a=> <ActivityItem key={a.id} a={a} costThreshold={costThreshold} />)}
      </Stack>
    </Box>
  )
}

