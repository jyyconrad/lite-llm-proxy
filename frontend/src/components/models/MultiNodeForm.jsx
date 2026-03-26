import React from 'react'
import SingleNodeForm, { createDefaultNode } from './SingleNodeForm'

export default function MultiNodeForm({
  value = { endpoints: [] },
  onChange,
  errors = {}
}) {
  const endpoints = value.endpoints || []

  // 添加新节点
  const addNode = () => {
    const newNode = createDefaultNode()
    onChange({
      ...value,
      endpoints: [...endpoints, newNode]
    })
  }

  // 删除节点
  const removeNode = (index) => {
    onChange({
      ...value,
      endpoints: endpoints.filter((_, i) => i !== index)
    })
  }

  // 更新节点数据
  const updateNode = (index, data) => {
    const newEndpoints = [...endpoints]
    newEndpoints[index] = { ...newEndpoints[index], ...data }
    onChange({
      ...value,
      endpoints: newEndpoints
    })
  }

  // 节点上移
  const moveNodeUp = (index) => {
    if (index === 0) return
    const newEndpoints = [...endpoints]
    const temp = newEndpoints[index]
    newEndpoints[index] = newEndpoints[index - 1]
    newEndpoints[index - 1] = temp
    onChange({
      ...value,
      endpoints: newEndpoints
    })
  }

  // 节点下移
  const moveNodeDown = (index) => {
    if (index === endpoints.length - 1) return
    const newEndpoints = [...endpoints]
    const temp = newEndpoints[index]
    newEndpoints[index] = newEndpoints[index + 1]
    newEndpoints[index + 1] = temp
    onChange({
      ...value,
      endpoints: newEndpoints
    })
  }

  return (
    <div className="space-y-4">
      {/* 节点列表 */}
      {endpoints.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <p>暂无节点</p>
          <p className="text-sm mt-1">点击下方按钮添加终端节点</p>
        </div>
      ) : (
        <div className="space-y-4">
          {endpoints.map((node, index) => {
            const nodeErrors = errors.endpoints?.[index] || {}
            const modelName = node.model || '未命名'

            return (
              <div
                key={index}
                data-testid="node-card"
                className="bg-dark-700 rounded-lg border border-dark-600 overflow-hidden"
              >
                {/* 节点标题栏 */}
                <div className="flex justify-between items-center px-4 py-3 bg-dark-800 border-b border-dark-600">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-300">
                      节点 {index + 1}
                    </span>
                    <span className="text-sm text-gray-400 truncate max-w-[200px]">
                      {modelName}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {/* 上移按钮 */}
                    {index > 0 && (
                      <button
                        type="button"
                        onClick={() => moveNodeUp(index)}
                        className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-600 rounded transition-colors"
                        title="上移"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                      </button>
                    )}
                    {/* 下移按钮 */}
                    {index < endpoints.length - 1 && (
                      <button
                        type="button"
                        onClick={() => moveNodeDown(index)}
                        className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-600 rounded transition-colors"
                        title="下移"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    )}
                    {/* 删除按钮 */}
                    <button
                      type="button"
                      onClick={() => removeNode(index)}
                      className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded transition-colors"
                      title="删除节点"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* 节点表单内容 */}
                <div className="p-4">
                  <SingleNodeForm
                    value={node}
                    onChange={(data) => updateNode(index, data)}
                    errors={nodeErrors}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 添加节点按钮 */}
      <button
        type="button"
        onClick={addNode}
        className="w-full py-3 border-2 border-dashed border-dark-600 rounded-lg text-gray-400 hover:text-white hover:border-primary-500 hover:bg-primary-500/10 transition-colors flex justify-center items-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        <span>添加节点</span>
      </button>
    </div>
  )
}
