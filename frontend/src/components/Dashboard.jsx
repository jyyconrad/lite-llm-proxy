import React, { useEffect, useState } from 'react'
import { Select, Progress } from '@chakra-ui/react'
import api from '../services/api'
import ModelUsage from './ModelUsage'
import TrendChart from './TrendChart'
import RecentActivity from './RecentActivity'
import UserTrendChart from './UserTrendChart'
import ModelTrendChart from './ModelTrendChart'

export default function Dashboard({ user, onNavigate }) {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modelTrend, setModelTrend] = useState({ data: [], series: ['calls', 'tokens'] })
  const [userTrend, setUserTrend] = useState({ data: [], series: ['calls', 'tokens'] })
  const [models, setModels] = useState([])
  const [users, setUsers] = useState([])
  const [selectedModels, setSelectedModels] = useState([])
  const [selectedUsers, setSelectedUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [period, setPeriod] = useState('7d')
  const [granularity, setGranularity] = useState('day')
  const [costThreshold, setCostThreshold] = useState(1.0)
  const [concurrentStats, setConcurrentStats] = useState({ global_concurrent: 0, model_concurrent: {}, total_concurrent: 0 })
  const [budgetUsage, setBudgetUsage] = useState({ budget_used: 0, budget_limit: 0 })
  
  // 用户使用对比卡片的独立筛选条件
  const [userTrendPeriod, setUserTrendPeriod] = useState('7d')
  const [userTrendModel, setUserTrendModel] = useState('')
  const [userTrendGranularity, setUserTrendGranularity] = useState('day')
  
  // 模型调用对比卡片的独立筛选条件
  const [modelTrendPeriod, setModelTrendPeriod] = useState('7d')
  const [modelTrendUser, setModelTrendUser] = useState('')
  const [modelTrendGranularity, setModelTrendGranularity] = useState('day')

  // 获取并发统计和预算使用情况
  useEffect(() => {
    async function fetchRealtimeStats() {
      try {
        // 获取并发统计
        const concurrent = await api.getConcurrentStats()
        setConcurrentStats(concurrent)
      } catch (e) {
        console.error("获取并发统计失败:", e)
      }
    }

    // 获取预算使用情况
    async function fetchBudgetUsage() {
      try {
        const usage = await api.getStatsOverview()
        // 从 stats/usage 获取预算信息
        const usageData = await api.request('/admin/stats/usage')
        if (usageData) {
          setBudgetUsage({
            budget_used: usageData.budget_used || 0,
            budget_limit: usageData.budget_limit || 0
          })
        }
      } catch (e) {
        console.error("获取预算使用失败:", e)
      }
    }

    fetchRealtimeStats()
    fetchBudgetUsage()

    // 每 10 秒刷新一次并发数据
    const interval = setInterval(fetchRealtimeStats, 10000)
    return () => clearInterval(interval)
  }, [])

  function computeTotals(series, data){
    const totals = {}
    for(const s of series || []) totals[s] = 0
    for(const row of (data || [])){
      for(const s of series || []){
        totals[s] += Number(row[s] || 0)
      }
    }
    return totals
  }

  useEffect(() => {
    async function fetchOverview() {
      try {
        // 获取统计数据时应用筛选条件
        const data = await api.getStatsOverview()
        setOverview(data)
        try{
          const m = await api.getModels()
          setModels(m.models || [])
          setSelectedModels([])
        }catch(e){ setModels([]) }
        try{
          if(user && user.role === 'admin'){
            const u = await api.getUsers(1, 100)
            setUsers(u.users || [])
          }
          if(user && user.role !== 'admin') setSelectedUsers([user.id])
        }catch(e){ setUsers([]) }
      } catch (e) {
        setOverview(null)
      } finally {
        setLoading(false)
      }
    }
    fetchOverview()
  }, [user])

  // 当筛选条件变化时，重新获取统计数据
  useEffect(() => {
    async function fetchFilteredData() {
      if (!period) return;
      
      try {
        // 获取趋势数据时应用筛选条件
        const userId = user && user.role !== 'admin' ? user.id : selectedUser || null;
        const model = selectedModel || null;
        
        // 获取模型趋势数据
        const modelTrendData = await api.getUsageTrend(period, granularity, model, userId);
        setModelTrend({ data: modelTrendData.data || [], series: ['calls','tokens'] });
        
        // 获取用户趋势数据
        const userTrendData = await api.getUsageTrend(period, granularity, model, userId);
        setUserTrend({ data: userTrendData.data || [], series: ['calls','tokens'] });
        
        // 重新计算统计数据
        const totals = computeTotals(['calls', 'tokens'], modelTrendData.data);
        const filteredOverview = {
          ...overview,
          total_calls: totals.calls,
          total_tokens: totals.tokens,
          model_count: model ? 1 : (overview?.model_count || models.length || 0)
        };
        
        setOverview(filteredOverview);
      } catch (e) {
        console.error("获取筛选数据时出错:", e);
      }
    }
    
    fetchFilteredData();
  }, [selectedUser, selectedModel, period, granularity, user]);

  // 获取用户使用对比数据
  useEffect(() => {
    async function fetchUserTrendData() {
      try {
        const model = userTrendModel || null;
        const userData = await api.getUserTrend(userTrendPeriod, userTrendGranularity, model);
        
        // 直接使用API返回的数据，包含时间粒度信息
        setUserTrend({
          data: userData.data || [],
          series: ['calls', 'tokens']
        });
      } catch (e) {
        console.error("获取用户趋势数据时出错:", e);
        setUserTrend({ data: [], series: [] });
      }
    }
    
    fetchUserTrendData();
  }, [userTrendModel, userTrendPeriod, userTrendGranularity]);

  // 获取模型调用对比数据
  useEffect(() => {
    async function fetchModelTrendData() {
      try {
        const userId = user && user.role !== 'admin' ? user.id : modelTrendUser || null;
        const modelData = await api.getModelTrend(modelTrendPeriod, modelTrendGranularity, userId);
        
        // 直接使用API返回的数据，包含时间粒度信息
        setModelTrend({
          data: modelData.data || [],
          series: ['calls', 'tokens']
        });
      } catch (e) {
        console.error("获取模型趋势数据时出错:", e);
        setModelTrend({ data: [], series: [] });
      }
    }
    
    fetchModelTrendData();
  }, [modelTrendUser, modelTrendPeriod, modelTrendGranularity, user]);

  useEffect(()=>{
    async function loadModel(){
      try{
        if(!selectedModels || selectedModels.length === 0){
          const r = await api.getUsageTrend(period, 'day', null, null)
          setModelTrend({ data: r.data || [], series: ['calls','tokens'] })
        } else {
          const map = {}
          const series = []
          for(const m of selectedModels){
            try{
              const r = await api.getUsageTrend(period, 'day', m, null)
              const arr = r.data || []
              for(const d of arr){
                const date = d.date
                if(!map[date]) map[date] = { date }
                map[date][`${m}_calls`] = Number(d.calls||0)
                map[date][`${m}_tokens`] = Number(d.tokens||0)
              }
              series.push(`${m}_calls`)
              series.push(`${m}_tokens`)
            }catch(e){ }
          }
          const merged = Object.values(map).sort((a,b)=> (a.date||'').localeCompare(b.date||''))
          setModelTrend({ data: merged, series })
        }
      }catch(e){ setModelTrend({ data: [], series: [] }) }
    }
    loadModel()
  }, [selectedModels, period])

  useEffect(()=>{
    async function loadUser(){
      try{
        const admin = user && user.role === 'admin'
        if(admin && selectedUsers && selectedUsers.length > 0){
          const map = {}
          const series = []
          for(const uid of selectedUsers){
            try{
              const r = await api.getUsageTrend(period, 'day', null, uid)
              const arr = r.data || []
              const name = (users.find(u=>u.id===uid)?.username) || uid
              for(const d of arr){
                const date = d.date
                if(!map[date]) map[date] = { date }
                map[date][`${name}_calls`] = Number(d.calls||0)
                map[date][`${name}_tokens`] = Number(d.tokens||0)
              }
              series.push(`${name}_calls`)
              series.push(`${name}_tokens`)
            }catch(e){ }
          }
          const merged = Object.values(map).sort((a,b)=> (a.date||'').localeCompare(b.date||''))
          setUserTrend({ data: merged, series })
        } else {
          const uid = user && user.role === 'admin' ? null : (user && user.id)
          const r = await api.getUsageTrend(period, 'day', null, uid)
          setUserTrend({ data: r.data || [], series: ['calls','tokens'] })
        }
      }catch(e){ setUserTrend({ data: [], series: [] }) }
    }
    loadUser()
  }, [selectedUsers, period, user, users])

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }
  function formatNumber(v){
  if (v === null || v === undefined) return '-'
  const num = Number(v)
  if (isNaN(num)) return '-'

  // 百万以上使用 M 格式
  if (num >= 1000000) {
    return (num / 1000000).toFixed(num % 1000000 === 0 ? 0 : 1) + 'M'
  }
  // 万以上使用万格式
  if (num >= 10000) {
    return (num / 10000).toFixed(num % 10000 === 0 ? 0 : 1) + '万'
  }

  return num.toLocaleString()
}

// 计算平均 tokens（使用原始数字计算后再格式化显示）
  const rawTotalCalls = overview ? Number(overview.total_calls || 0) : 0
  const rawTotalTokens = overview ? Number(overview.total_tokens || 0) : 0
  const modelCount = overview ? formatNumber(overview.model_count || (models.length || 0)) : '-'
  const totalCalls = formatNumber(rawTotalCalls)
  const totalTokens = formatNumber(rawTotalTokens)
  const avgTokensPerCall = (rawTotalCalls > 0 && rawTotalTokens > 0)
    ? formatNumber(Math.round(rawTotalTokens / rawTotalCalls))
    : '-'

  return (
    <div className="mx-auto px-4 py-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">模型用量</h1>
          <p className="text-gray-400">概览 · 用量统计</p>
        </div>

        <div className="flex gap-3 items-center">
          {/* 用户筛选 */}
          {user && user.role === 'admin' && (
            <Select
              placeholder="选择用户"
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              borderRadius="lg"
              borderColor="dark.700"
              _focus={{ borderColor: 'primary.500', boxShadow: '0 0 0 1px var(--chakra-colors-primary-500)' }}
              maxWidth="200px"
            >
              {users.map((u) => (
                <option key={u.id} value={u.id} >
                  {u.username}
                </option>
              ))}
            </Select>
          )}
          
          {/* 模型筛选 */}
          <Select
            placeholder="选择模型"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            borderRadius="lg"
            borderColor="dark.700"
            _focus={{ borderColor: 'primary.500', boxShadow: '0 0 0 1px var(--chakra-colors-primary-500)' }}
            maxWidth="200px"
          >
            {models.map((model) => (
              <option key={model} value={model} >
                {model}
              </option>
            ))}
          </Select>
          
          <Select
            value={period}
            onChange={e=>setPeriod(e.target.value)}
            // bg="dark.800"
            // color="white"
            borderRadius="lg"
            borderColor="dark.700"
            _focus={{ borderColor: 'primary.500', boxShadow: '0 0 0 1px var(--chakra-colors-primary-500)' }}
          >
            <option value="7d" >最近7天</option>
            <option value="30d" >最近30天</option>
          </Select>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-6">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <p className="text-gray-400 text-sm mb-1">调用模型数</p>
          <h3 className="text-2xl font-bold text-white">{modelCount}</h3>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <p className="text-gray-400 text-sm mb-1">调用总次数</p>
          <h3 className="text-2xl font-bold text-white">{totalCalls}</h3>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <p className="text-gray-400 text-sm mb-1">Token 总数</p>
          <h3 className="text-2xl font-bold text-white">{totalTokens}</h3>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <p className="text-gray-400 text-sm mb-1">平均单次请求 Token 量</p>
          <h3 className="text-2xl font-bold text-white">{avgTokensPerCall}</h3>
        </div>

        {/* 并发监控卡片 */}
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <p className="text-gray-400 text-sm mb-1">当前并发请求</p>
          <h3 className="text-2xl font-bold text-white">{concurrentStats.global_concurrent || 0}</h3>
          <p className="text-gray-500 text-xs mt-1">实时活跃请求数</p>
        </div>
      </div>

      {/* 预算使用进度条 */}
      {budgetUsage.budget_limit > 0 && (
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg mb-6">
          <div className="flex justify-between items-center mb-2">
            <p className="text-gray-400 text-sm">预算使用</p>
            <p className="text-white text-sm font-medium">
              {formatNumber(budgetUsage.budget_used)} / {formatNumber(budgetUsage.budget_limit)}
            </p>
          </div>
          <Progress
            value={Math.min((budgetUsage.budget_used / budgetUsage.budget_limit) * 100, 100)}
            size="lg"
            borderRadius="full"
            bg="dark.700"
            sx={{
              '& > div': {
                backgroundColor: budgetUsage.budget_used / budgetUsage.budget_limit > 0.9
                  ? 'red.400'
                  : budgetUsage.budget_used / budgetUsage.budget_limit > 0.7
                    ? 'orange.400'
                    : 'green.400'
              }
            }}
          />
          <p className="text-gray-500 text-xs mt-2">
            已使用 {((budgetUsage.budget_used / budgetUsage.budget_limit) * 100).toFixed(1)}%
          </p>
        </div>
      )}

      {/* Chart Section */}
      <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg mb-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-white">总调用次数分布</h2>
            <p className="text-gray-400 text-sm">单位：次数</p>
          </div>
          <button className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors">
            下载报告
          </button>
        </div>
        <div className="h-80">
          <TrendChart data={modelTrend.data || []} series={modelTrend.series || ['calls','tokens']} />
        </div>
      </div>

      {/* New Trend Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* User Trend Card */}
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">用户使用对比</h2>
              <p className="text-gray-400 text-sm">按用户展示调用次数和Token使用量</p>
            </div>
          </div>
          <div className="h-80">
            <UserTrendChart />
          </div>
        </div>

        {/* Model Trend Card */}
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">模型调用对比</h2>
              <p className="text-gray-400 text-sm">按模型展示调用次数和Token使用量</p>
            </div>
          </div>
          <div className="h-80">
            <ModelTrendChart data={modelTrend.data || []} series={modelTrend.series || ['calls','tokens']} />
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg lg:col-span-2">
          <h2 className="text-xl font-bold text-white mb-6">总调用成功次数 Top 模型</h2>
          <div className="overflow-x-auto">
            <ModelUsage compact data={overview && overview.top_models} />
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
            <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white mb-6">最近活动</h2>
          <button onClick={() => onNavigate('modelLogs')} className="mb-2 px-2 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors">
            查看全部活动
          </button>
        </div>
          <div className="max-h-96 overflow-y-auto">
            <RecentActivity costThreshold={costThreshold} />
          </div>
        </div>
      </div>
    </div>
  )
}








