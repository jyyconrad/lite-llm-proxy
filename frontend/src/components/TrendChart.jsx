import React, { useMemo, useState } from 'react'
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts'

function defaultColor(name){
  // simple hash to pick color
  const palette = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#84cc16']
  let h = 0
  for(let i=0;i<name.length;i++) h = (h<<5) - h + name.charCodeAt(i)
  return palette[Math.abs(h) % palette.length]
}

function formatNumber(v, isTokens = false){
  if (v === null || v === undefined) return '-'
  
  // 对于 tokens 数据且数值较大时，使用简化格式
  if (isTokens && v >= 10000) {
    return (v / 10000).toFixed(v % 10000 === 0 ? 0 : 1) + '万'
  }
  
  return Number(v).toLocaleString()
}

export default function TrendChart({ data = [], series = ['calls','tokens'], height = 240, thresholds = {} }){
  if (!data || !data.length) return <div className="muted">暂无趋势数据</div>

  // Ensure numeric values for all series keys
  const formatted = useMemo(() => data.map(d => {
    const out = { ...d }
    for(const s of series){ out[s] = Number(out[s]||0) }
    return out
  }), [data, series])

  const [hidden, setHidden] = useState(new Set())

  const colors = useMemo(()=> {
    const map = {}
    series.forEach(s => { map[s] = defaultColor(s) })
    return map
  }, [series])

  const handleLegendClick = (o) => {
    const key = o.dataKey || o.value
    setHidden(prevHidden => {
      const next = new Set(prevHidden)
      if(next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if(!active || !payload) return null
    return (
      <div className="tooltip" style={{background:'#fff',padding:8,borderRadius:6,border:'1px solid #eee'}}>
        <div style={{fontWeight:600,marginBottom:6}}>{label}</div>
        {payload.map(p => (
          <div key={p.dataKey} style={{display:'flex',justifyContent:'space-between',gap:8}}>
            <div style={{display:'flex',alignItems:'center',gap:8}}>
              <span style={{width:10,height:10,background:colors[p.dataKey],display:'inline-block',borderRadius:2}} />
              <div style={{fontSize:12}}>{p.name === 'calls' ? '调用次数' : p.name === 'tokens' ? 'tokens数量' : (p.name || p.dataKey)}</div>
            </div>
            <div style={{fontSize:12}}>{formatNumber(p.value, p.dataKey === 'tokens')}</div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={{width:'100%', height}}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={formatted} margin={{ top: 10, right: 24, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{fontSize:12}} />
          <YAxis yAxisId="left" orientation="left" tickFormatter={(v) => formatNumber(v, true)} />
          <YAxis yAxisId="right" orientation="right" tickFormatter={formatNumber} />
          <Tooltip content={<CustomTooltip/>} />
          <Legend onClick={handleLegendClick} />
          {series.map((s, idx) => (
            s === 'calls' ? (
              <Bar
                key={s}
                yAxisId="right"
                dataKey={s}
                name={s === 'calls' ? '调用次数' : s === 'tokens' ? 'tokens数量' : s}
                fill={colors[s]}
                opacity={0.7}
                hide={hidden.has(s)}
              />
            ) : (
              <Line
                key={s}
                yAxisId="left"
                type="monotone"
                dataKey={s}
                name={s === 'calls' ? '调用次数' : s === 'tokens' ? 'tokens数量' : s}
                stroke={colors[s]}
                strokeWidth={2}
                dot={props => {
                  const val = props.payload ? Number(props.payload[s]||0) : null
                  const th = thresholds && thresholds[s]
                  const color = (th !== undefined && val !== null && val > th) ? '#ef4444' : colors[s]
                  return (
                    <circle key={`${s}-${props.index}`} cx={props.cx} cy={props.cy} r={3} fill={color} stroke="white" strokeWidth={0.5} />
                  )
                }}
                hide={hidden.has(s)}
              />
            )
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}









