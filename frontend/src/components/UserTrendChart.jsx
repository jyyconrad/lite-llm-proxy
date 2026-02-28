import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { Box, Text, Select, Stack, Button } from '@chakra-ui/react'

// 进度条组件，用于展示用户的调用次数和tokens数
function ProgressBar({ label, value, maxValue, highlight=false, color }){
  const pct = maxValue > 0 ? Math.round((value / maxValue) * 100) : 0
  const bg = highlight ? '#fde2e2' : '#e6eef6'
  const barColor = color || (highlight ? '#ef4444' : '#6ee7b7')
  
  return (
    <Box mb={3}>
      <Box display="flex" justifyContent="space-between" fontSize="12px" color="#56667a">
        <Box>{label}</Box>
        <Box>{value.toLocaleString()}</Box>
      </Box>
      <Box height="8px" bg={bg} borderRadius="8px" overflow="hidden" mt={2}>
        <Box width={`${pct}%`} height="100%" bg={barColor} />
      </Box>
    </Box>
  )
}

export default function UserTrendChart(){
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('calls') // 展示模式：calls 或 tokens
  const [period, setPeriod] = useState('7d') // 时间周期：1d,7d, 30d, 365d
  const [selectedModel, setSelectedModel] = useState('') // 模型筛选条件
  
  // 获取所有模型列表
  const [models, setModels] = useState([])
  
  useEffect(() => {
    async function fetchModels() {
      try {
        // 从统计数据中提取模型列表
        const modelData = await api.getModels()
        setModels(modelData.models || [])
      } catch (err) {
        console.error("获取模型列表时出错:", err)
        setModels([])
      }
    }
    
    fetchModels()
  }, [])
  
  // 获取用户趋势数据
  useEffect(()=>{
    load()
  }, [period, selectedModel])
  
  async function load(){
    setLoading(true)
    setError(null)
    try{
      // 根据是否选择了模型来设置model参数
      const model = selectedModel || null
      const userData = await api.getUserTrend(period, 'day', model) // 固定时间粒度为day
      // 聚合用户数据：按用户ID合并所有记录
      const aggregatedData = aggregateUserData(userData.data || [])
      setStats(aggregatedData)
    }catch(err){
      console.error("获取用户趋势数据时出错:", err)
      setError("获取数据失败")
      setStats([])
    } finally {
      setLoading(false)
    }
  }
  
  // 移除没有数据时不显示筛选条件的限制
  // 始终显示筛选条件，即使没有数据
  
  // 聚合用户数据函数
  function aggregateUserData(data) {
    const userMap = {}
    
    // 遍历所有数据项，按用户聚合
    data.forEach(item => {
      const userId = item.user_id
      if (!userMap[userId]) {
        userMap[userId] = {
          user_id: userId,
          username: item.username,
          calls: 0,
          tokens: 0
        }
      }
      userMap[userId].calls += item.calls || 0
      userMap[userId].tokens += item.tokens || 0
    })
    
    // 转换为数组并返回
    return Object.values(userMap)
  }
  
  // 计算最大值用于进度条显示
  const maxCalls = stats.reduce((max, user) => Math.max(max, user.calls || 0), 0)
  const maxTokens = stats.reduce((max, user) => Math.max(max, user.tokens || 0), 0)
  
  // 默认按调用次数或token数量排序（取决于展示模式）
  const sortedStats = [...stats].sort((a, b) => {
    if (viewMode === 'calls') return (b.calls || 0) - (a.calls || 0)
    return (b.tokens || 0) - (a.tokens || 0)
  })
  
  if (loading) return <div className="flex justify-center items-center h-full">加载中...</div>
  if (error) return <div className="text-red-500 text-center py-4">{error}</div>
  
  // 即使没有数据也显示完整的界面
  return (
    <Box height="100%" display="flex" flexDirection="column">
      {/* 控制面板 - 时间周期、模型筛选和展示模式 */}
      <Stack direction="row" className="font-bold text-white" spacing={2} align="center" mb={2} flexWrap="wrap">
        <Text fontSize="sm">时间周期：</Text>
        <Select size="sm" width="100px" value={period} onChange={e=>setPeriod(e.target.value)}>
          <option value="1d">近1天</option>
          <option value="7d">近7天</option>
          <option value="30d">近30天</option>
          <option value="365d">近一年</option>
        </Select>
        
        <Text fontSize="sm">模型筛选：</Text>
        <Select size="sm" width="120px" value={selectedModel} onChange={e=>setSelectedModel(e.target.value)} placeholder="所有模型">
          {models.map(model => (
            <option key={model} value={model}>{model}</option>
          ))}
        </Select>
        
        <Text fontSize="sm">展示模式：</Text>
        <Select size="sm" width="120px" value={viewMode} onChange={e=>setViewMode(e.target.value)}>
          <option value="calls">调用次数</option>
          <option value="tokens">Token 数量</option>
        </Select>
        
        <Button size="sm" onClick={load}>刷新</Button>
      </Stack>
      
      {/* 用户使用情况列表 */}
      <Box flex="1" overflowY="auto" pr={2}>
        {sortedStats.length > 0 ? (
          sortedStats.map(user => (
            <ProgressBar
              key={user.user_id}
              label={user.username}
              value={viewMode === 'calls' ? user.calls : user.tokens}
              maxValue={viewMode === 'calls' ? maxCalls : maxTokens}
              color={viewMode === 'calls' ? '#3b82f6' : '#10b981'}
            />
          ))
        ) : (
          <div className="text-gray-500 text-center py-4">暂无用户趋势数据</div>
        )}
      </Box>
      
      {/* 数据概览 */}
      <Box mt={4} pt={4} borderTop="1px solid #e2e8f0">
        <Text fontSize="sm" color="gray.600">
          共 {stats.length} 个用户 |
          总调用次数: {stats.reduce((sum, user) => sum + (user.calls || 0), 0).toLocaleString()} |
          总 Token 数: {stats.reduce((sum, user) => sum + (user.tokens || 0), 0).toLocaleString()}
        </Text>
      </Box>
    </Box>
  )
}










