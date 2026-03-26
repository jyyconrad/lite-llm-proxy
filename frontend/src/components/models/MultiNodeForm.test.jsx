import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import MultiNodeForm from './MultiNodeForm'

// Mock SingleNodeForm
vi.mock('./SingleNodeForm', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    default: function MockSingleNodeForm({ value, onChange, errors, disabled }) {
      return (
        <div data-testid="single-node-form" data-provider={value?.provider || 'openai'}>
          <input
            data-testid="node-provider"
            value={value?.provider || 'openai'}
            onChange={(e) => onChange?.({ ...value, provider: e.target.value })}
            disabled={disabled}
            aria-label="provider"
          />
          <input
            data-testid="node-model"
            value={value?.model || ''}
            onChange={(e) => onChange?.({ ...value, model: e.target.value })}
            disabled={disabled}
            aria-label="model"
          />
          <input
            data-testid="node-api-key"
            value={value?.api_key || ''}
            onChange={(e) => onChange?.({ ...value, api_key: e.target.value })}
            disabled={disabled}
            aria-label="api-key"
          />
          <input
            data-testid="node-base-url"
            value={value?.base_url || ''}
            onChange={(e) => onChange?.({ ...value, base_url: e.target.value })}
            disabled={disabled}
            aria-label="base-url"
          />
          <input
            data-testid="node-max-tokens"
            type="number"
            value={value?.max_tokens || 4096}
            onChange={(e) => onChange?.({ ...value, max_tokens: parseInt(e.target.value) || 4096 })}
            disabled={disabled}
            aria-label="max-tokens"
          />
          <input
            data-testid="node-rpm"
            type="number"
            value={value?.rpm || 60}
            onChange={(e) => onChange?.({ ...value, rpm: parseInt(e.target.value) || 60 })}
            disabled={disabled}
            aria-label="rpm"
          />
          <input
            data-testid="node-tpm"
            type="number"
            value={value?.tpm || 100000}
            onChange={(e) => onChange?.({ ...value, tpm: parseInt(e.target.value) || 100000 })}
            disabled={disabled}
            aria-label="tpm"
          />
          <input
            data-testid="node-weight"
            type="number"
            value={value?.weight || 1}
            onChange={(e) => onChange?.({ ...value, weight: parseInt(e.target.value) || 1 })}
            disabled={disabled}
            aria-label="weight"
          />
          {errors && Object.entries(errors).map(([key, value]) => (
            <div key={key} data-testid={`error-${key}`}>{value}</div>
          ))}
        </div>
      )
    }
  }
})

describe('MultiNodeForm', () => {
  const defaultProps = {
    value: { endpoints: [] },
    onChange: vi.fn(),
    errors: {}
  }

  const createWrapper = (props = {}) => {
    return render(<MultiNodeForm {...defaultProps} {...props} />)
  }

  describe('渲染测试', () => {
    it('应该渲染添加节点按钮', () => {
      createWrapper()
      expect(screen.getByText(/添加节点/i)).toBeInTheDocument()
    })

    it('应该渲染空状态提示当没有节点时', () => {
      createWrapper()
      expect(screen.getByText(/暂无节点/i)).toBeInTheDocument()
    })

    it('应该渲染现有节点', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com' },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com' }
      ]
      createWrapper({ value: { endpoints } })

      const forms = screen.getAllByTestId('single-node-form')
      expect(forms).toHaveLength(2)
    })
  })

  describe('添加节点', () => {
    it('应该添加一个新节点当点击添加按钮', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const addButton = screen.getByText(/添加节点/i)
      fireEvent.click(addButton)

      expect(onChange).toHaveBeenCalledWith({
        endpoints: [expect.objectContaining({
          provider: 'openai',
          weight: 1
        })]
      })
    })

    it('应该在现有节点基础上添加新节点', () => {
      const onChange = vi.fn()
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints }, onChange })

      const addButton = screen.getByText(/添加节点/i)
      fireEvent.click(addButton)

      expect(onChange).toHaveBeenCalledWith({
        endpoints: [
          expect.objectContaining({ provider: 'openai', model: 'gpt-4' }),
          expect.objectContaining({ provider: 'openai', weight: 1 })
        ]
      })
    })
  })

  describe('删除节点', () => {
    it('应该显示删除按钮当有节点时', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints } })

      expect(screen.getAllByTitle(/删除节点/i)).toHaveLength(1)
    })

    it('应该删除指定节点当点击删除按钮', () => {
      const onChange = vi.fn()
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints }, onChange })

      const deleteButtons = screen.getAllByTitle(/删除节点/i)
      fireEvent.click(deleteButtons[0])

      expect(onChange).toHaveBeenCalledWith({
        endpoints: [
          expect.objectContaining({ provider: 'anthropic', model: 'claude-3' })
        ]
      })
    })
  })

  describe('节点排序', () => {
    it('应该显示上移/下移按钮当有多个节点时', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints } })

      // 第一个节点应该有下移按钮
      expect(screen.getAllByTitle(/下移/i)).toHaveLength(1)
      // 第二个节点应该有上移按钮
      expect(screen.getAllByTitle(/上移/i)).toHaveLength(1)
    })

    it('应该上移节点当点击上移按钮', () => {
      const onChange = vi.fn()
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints }, onChange })

      const upButtons = screen.getAllByTitle(/上移/i)
      fireEvent.click(upButtons[0])

      expect(onChange).toHaveBeenCalledWith({
        endpoints: [
          expect.objectContaining({ provider: 'anthropic', model: 'claude-3' }),
          expect.objectContaining({ provider: 'openai', model: 'gpt-4' })
        ]
      })
    })

    it('应该下移节点当点击下移按钮', () => {
      const onChange = vi.fn()
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints }, onChange })

      const downButtons = screen.getAllByTitle(/下移/i)
      fireEvent.click(downButtons[0])

      expect(onChange).toHaveBeenCalledWith({
        endpoints: [
          expect.objectContaining({ provider: 'anthropic', model: 'claude-3' }),
          expect.objectContaining({ provider: 'openai', model: 'gpt-4' })
        ]
      })
    })

    it('第一个节点不应该有上移按钮', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 1 }
      ]
      const { container } = createWrapper({ value: { endpoints } })

      // 查找第一个节点卡片
      const cards = container.querySelectorAll('[data-testid="node-card"]')
      if (cards.length > 0) {
        // 第一个节点不应该有上移按钮
        const firstCardUpButton = cards[0].querySelector('[title*="上移"]')
        expect(firstCardUpButton).not.toBeInTheDocument()
      }
    })

    it('最后一个节点不应该有下移按钮', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 1 }
      ]
      const { container } = createWrapper({ value: { endpoints } })

      const cards = container.querySelectorAll('[data-testid="node-card"]')
      if (cards.length > 1) {
        // 最后一个节点不应该有下移按钮
        const lastCardDownButton = cards[cards.length - 1].querySelector('[title*="下移"]')
        expect(lastCardDownButton).not.toBeInTheDocument()
      }
    })
  })

  describe('节点数据更新', () => {
    it('应该更新指定节点的数据', () => {
      const onChange = vi.fn()
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints }, onChange })

      const modelInput = screen.getByTestId('node-model')
      fireEvent.change(modelInput, { target: { value: 'gpt-4-turbo' } })

      expect(onChange).toHaveBeenCalledWith({
        endpoints: [
          expect.objectContaining({ provider: 'openai', model: 'gpt-4-turbo' })
        ]
      })
    })
  })

  describe('初始值回显', () => {
    it('应该正确回显多个节点数据', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 },
        { provider: 'anthropic', model: 'claude-3', api_key: 'key2', base_url: 'https://api.anthropic.com', weight: 2 }
      ]
      createWrapper({ value: { endpoints } })

      const forms = screen.getAllByTestId('single-node-form')
      expect(forms[0]).toHaveAttribute('data-provider', 'openai')
      expect(forms[1]).toHaveAttribute('data-provider', 'anthropic')
    })
  })

  describe('节点标题显示', () => {
    it('应该显示节点序号和模型名称', () => {
      const endpoints = [
        { provider: 'openai', model: 'gpt-4-turbo', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints } })

      expect(screen.getByText('节点 1')).toBeInTheDocument()
      expect(screen.getByText('gpt-4-turbo')).toBeInTheDocument()
    })

    it('应该显示未命名当模型名称为空时', () => {
      const endpoints = [
        { provider: 'openai', model: '', api_key: 'key1', base_url: 'https://api.openai.com', weight: 1 }
      ]
      createWrapper({ value: { endpoints } })

      expect(screen.getByText('节点 1')).toBeInTheDocument()
      expect(screen.getByText('未命名')).toBeInTheDocument()
    })
  })
})
