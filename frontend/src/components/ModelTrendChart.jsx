import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { Box, Text, Select, Stack, Button } from '@chakra-ui/react'

// 进度条组件，用于展示模型的调用次数和tokens数
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

export default function ModelTrendChart(){
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('calls') // 展示模式：calls 或 tokens
  const [period, setPeriod] = useState('1d') // 时间周期：1d,7d, 30d, 365d
  const [selectedUser, setSelectedUser] = useState('') // 用户筛选条件
  
  // 获取所有用户列表
  const [users, setUsers] = useState([])
  
  useEffect(() => {
    async function fetchUsers() {
      try {
        const userData = await api.getUsers(1, 1000) // 获取所有用户
        setUsers(userData.users || [])
      } catch (err) {
        console.error("获取用户列表时出错:", err)
        setUsers([])
      }
    }
    
    fetchUsers()
  }, [])
  
  // 获取模型趋势数据
  useEffect(()=>{
    load()
  }, [period, selectedUser])
  
  async function load(){
    setLoading(true)
    setError(null)
    try{
      // 根据是否选择了用户来设置userId参数
      const userId = selectedUser || null
      const modelData = await api.getModelTrend(period, 'day', userId) // 固定时间粒度为day
      // 聚合模型数据：按模型名称合并所有记录
      const aggregatedData = aggregateModelData(modelData.data || [])
      setStats(aggregatedData)
    }catch(err){
      console.error("获取模型趋势数据时出错:", err)
      setError("获取数据失败")
      setStats([])
    } finally {
      setLoading(false)
    }
  }
  
  // 聚合模型数据函数
  function aggregateModelData(data) {
    const modelMap = {}
    
    // 遍历所有数据项，按模型聚合
    data.forEach(item => {
      const modelName = item.model_name
      if (!modelMap[modelName]) {
        modelMap[modelName] = {
          model_name: modelName,
          calls: 0,
          tokens: 0
        }
      }
      modelMap[modelName].calls += item.calls || 0
      modelMap[modelName].tokens += item.tokens || 0
    })
    
    // 转换为数组并返回
    return Object.values(modelMap)
  }
  
  // 计算最大值用于进度条显示
  const maxCalls = stats.reduce((max, model) => Math.max(max, model.calls || 0), 0)
  const maxTokens = stats.reduce((max, model) => Math.max(max, model.tokens || 0), 0)
  
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
      {/* 控制面板 - 时间周期、用户筛选和展示模式 */}
      <Stack direction="row" className="font-bold text-white" spacing={2} align="center" mb={2} flexWrap="wrap">
        <Text fontSize="sm">时间周期：</Text>
        <Select size="sm" width="100px" value={period} onChange={e=>setPeriod(e.target.value)}>
          <option value="1d">近1天</option>
          <option value="7d">近7天</option>
          <option value="30d">近30天</option>
          <option value="365d">近一年</option>
        </Select>
        
        <Text fontSize="sm">用户筛选：</Text>
        <Select size="sm" width="120px" value={selectedUser} onChange={e=>setSelectedUser(e.target.value)} placeholder="所有用户">
          {users.map(user => (
            <option key={user.id} value={user.id}>{user.username}</option>
          ))}
        </Select>
        
        <Text fontSize="sm">展示模式：</Text>
        <Select size="sm" width="120px" value={viewMode} onChange={e=>setViewMode(e.target.value)}>
          <option value="calls">调用次数</option>
          <option value="tokens">Token 数量</option>
        </Select>
        
        <Button size="sm" onClick={load}>刷新</Button>
      </Stack>
      
      {/* 模型使用情况列表 */}
      <Box flex="1" overflowY="auto" pr={2}>
        {sortedStats.length > 0 ? (
          sortedStats.map(model => (
            <ProgressBar
              key={model.model_name}
              label={model.model_name}
              value={viewMode === 'calls' ? model.calls : model.tokens}
              maxValue={viewMode === 'calls' ? maxCalls : maxTokens}
              color={viewMode === 'calls' ? '#3b82f6' : '#10b981'}
            />
          ))
        ) : (
          <div className="text-gray-500 text-center py-4">暂无模型趋势数据</div>
        )}
      </Box>
      
      {/* 数据概览 */}
      <Box mt={4} pt={4} borderTop="1px solid #e2e8f0">
        <Text fontSize="sm" color="gray.600">
          共 {stats.length} 个模型 |
          总调用次数: {stats.reduce((sum, model) => sum + (model.calls || 0), 0).toLocaleString()} |
          总 Token 数: {stats.reduce((sum, model) => sum + (model.tokens || 0), 0).toLocaleString()}
        </Text>
      </Box>
    </Box>
  )
}

