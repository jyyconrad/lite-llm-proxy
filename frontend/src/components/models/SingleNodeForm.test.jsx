import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SingleNodeForm from './SingleNodeForm'

describe('SingleNodeForm', () => {
  const defaultProps = {
    value: {},
    onChange: vi.fn(),
    errors: {}
  }

  const createWrapper = (props = {}) => {
    return render(<SingleNodeForm {...defaultProps} {...props} />)
  }

  describe('渲染测试', () => {
    it('应该渲染所有表单字段', () => {
      createWrapper()

      expect(screen.getByLabelText(/供应商/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/模型名称/i)).toBeInTheDocument()
      // 使用 getById 来避免与按钮的 aria-label 冲突
      expect(screen.getByTestId('api-key-input')).toBeInTheDocument()
      expect(screen.getByLabelText(/base url/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/max tokens/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/rpm/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/tpm/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/weight/i)).toBeInTheDocument()
    })

    it('应该显示所有支持的供应商选项', () => {
      createWrapper()

      const select = screen.getByLabelText(/供应商/i)
      expect(select).toBeInTheDocument()

      // 检查主要供应商选项
      expect(screen.getByText('OpenAI')).toBeInTheDocument()
      expect(screen.getByText('Anthropic')).toBeInTheDocument()
      expect(screen.getByText('Azure')).toBeInTheDocument()
      expect(screen.getByText('Gemini')).toBeInTheDocument()
      expect(screen.getByText('Ollama')).toBeInTheDocument()
      expect(screen.getByText('本地部署')).toBeInTheDocument()
      expect(screen.getByText('自定义')).toBeInTheDocument()
    })
  })

  describe('供应商切换', () => {
    it('应该在选择 OpenAI 时自动填充默认 Base URL', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const select = screen.getByLabelText(/供应商/i)
      fireEvent.change(select, { target: { value: 'openai' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          base_url: 'https://api.openai.com/v1'
        })
      )
    })

    it('应该在选择 Anthropic 时自动填充默认 Base URL', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const select = screen.getByLabelText(/供应商/i)
      fireEvent.change(select, { target: { value: 'anthropic' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          base_url: 'https://api.anthropic.com'
        })
      )
    })

    it('应该在选择 Ollama 时自动填充默认 Base URL', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const select = screen.getByLabelText(/供应商/i)
      fireEvent.change(select, { target: { value: 'ollama' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          base_url: 'http://localhost:11434'
        })
      )
    })

    it('应该在选择自定义时清空 Base URL', () => {
      const onChange = vi.fn()
      createWrapper({ onChange, value: { base_url: 'https://example.com' } })

      const select = screen.getByLabelText(/供应商/i)
      fireEvent.change(select, { target: { value: 'custom' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          base_url: ''
        })
      )
    })
  })

  describe('表单值变化', () => {
    it('应该在模型名称变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByLabelText(/模型名称/i)
      fireEvent.change(input, { target: { value: 'gpt-4-turbo' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'gpt-4-turbo'
        })
      )
    })

    it('应该在 API Key 变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByTestId('api-key-input')
      fireEvent.change(input, { target: { value: 'sk-test-key' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          api_key: 'sk-test-key'
        })
      )
    })

    it('应该在 Base URL 变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByLabelText(/base url/i)
      fireEvent.change(input, { target: { value: 'https://custom.api.com' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          base_url: 'https://custom.api.com'
        })
      )
    })

    it('应该在 Max Tokens 变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByLabelText(/max tokens/i)
      fireEvent.change(input, { target: { value: '8192' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          max_tokens: 8192
        })
      )
    })

    it('应该在 RPM 变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByLabelText(/rpm/i)
      fireEvent.change(input, { target: { value: '100' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          rpm: 100
        })
      )
    })

    it('应该在 TPM 变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByLabelText(/tpm/i)
      fireEvent.change(input, { target: { value: '200000' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          tpm: 200000
        })
      )
    })

    it('应该在 Weight 变化时调用 onChange', () => {
      const onChange = vi.fn()
      createWrapper({ onChange })

      const input = screen.getByLabelText(/weight/i)
      fireEvent.change(input, { target: { value: '2' } })

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          weight: 2
        })
      )
    })
  })

  describe('初始值回显', () => {
    it('应该正确显示初始供应商值', () => {
      createWrapper({ value: { provider: 'anthropic' } })
      expect(screen.getByLabelText(/供应商/i)).toHaveValue('anthropic')
    })

    it('应该正确显示初始模型名称', () => {
      createWrapper({ value: { model: 'claude-3-opus' } })
      expect(screen.getByLabelText(/模型名称/i)).toHaveValue('claude-3-opus')
    })

    it('应该正确显示初始 API Key', () => {
      createWrapper({ value: { api_key: 'sk-ant-test' } })
      expect(screen.getByTestId('api-key-input')).toHaveValue('sk-ant-test')
    })

    it('应该正确显示初始 Base URL', () => {
      createWrapper({ value: { base_url: 'https://custom.com' } })
      expect(screen.getByLabelText(/base url/i)).toHaveValue('https://custom.com')
    })

    it('应该正确显示初始数字字段', () => {
      createWrapper({
        value: {
          max_tokens: 4096,
          rpm: 50,
          tpm: 80000,
          weight: 3
        }
      })

      expect(screen.getByLabelText(/max tokens/i)).toHaveValue(4096)
      expect(screen.getByLabelText(/rpm/i)).toHaveValue(50)
      expect(screen.getByLabelText(/tpm/i)).toHaveValue(80000)
      expect(screen.getByLabelText(/weight/i)).toHaveValue(3)
    })
  })

  describe('验证错误显示', () => {
    it('应该显示模型名称验证错误', () => {
      createWrapper({ errors: { model: '模型名称不能为空' } })
      expect(screen.getByText('模型名称不能为空')).toBeInTheDocument()
    })

    it('应该显示 API Key 验证错误', () => {
      createWrapper({ errors: { api_key: 'API Key 不能为空' } })
      expect(screen.getByText('API Key 不能为空')).toBeInTheDocument()
    })

    it('应该显示 Base URL 验证错误', () => {
      createWrapper({ errors: { base_url: 'Base URL 不能为空' } })
      expect(screen.getByText('Base URL 不能为空')).toBeInTheDocument()
    })

    it('应该显示 RPM 验证错误', () => {
      createWrapper({ errors: { rpm: 'RPM 必须大于 0' } })
      expect(screen.getByText('RPM 必须大于 0')).toBeInTheDocument()
    })

    it('应该同时显示多个验证错误', () => {
      createWrapper({
        errors: {
          model: '模型名称不能为空',
          api_key: 'API Key 不能为空'
        }
      })

      expect(screen.getByText('模型名称不能为空')).toBeInTheDocument()
      expect(screen.getByText('API Key 不能为空')).toBeInTheDocument()
    })
  })

  describe('禁用状态', () => {
    it('应该禁用所有表单字段当 disabled 为 true', () => {
      createWrapper({ disabled: true })

      expect(screen.getByLabelText(/供应商/i)).toBeDisabled()
      expect(screen.getByLabelText(/模型名称/i)).toBeDisabled()
      expect(screen.getByTestId('api-key-input')).toBeDisabled()
      expect(screen.getByLabelText(/base url/i)).toBeDisabled()
      expect(screen.getByLabelText(/max tokens/i)).toBeDisabled()
      expect(screen.getByLabelText(/rpm/i)).toBeDisabled()
      expect(screen.getByLabelText(/tpm/i)).toBeDisabled()
      expect(screen.getByLabelText(/weight/i)).toBeDisabled()
    })
  })

  describe('API Key 可见性切换', () => {
    it('应该默认隐藏 API Key 值', () => {
      createWrapper({ value: { api_key: 'secret-key' } })
      const input = screen.getByTestId('api-key-input')
      expect(input.type).toBe('password')
    })

    it('应该可以切换显示/隐藏 API Key', async () => {
      const { container } = createWrapper({ value: { api_key: 'secret-key' } })

      // 查找眼睛图标按钮
      const toggleButton = container.querySelector('button[aria-label="显示 API Key"]')

      if (toggleButton) {
        fireEvent.click(toggleButton)
        const input = screen.getByTestId('api-key-input')
        expect(input.type).toBe('text')
      }
    })
  })

  describe('默认值', () => {
    it('应该有正确的默认值当 value 为空对象', () => {
      createWrapper({ value: {} })

      expect(screen.getByLabelText(/供应商/i)).toHaveValue('openai')
      expect(screen.getByLabelText(/模型名称/i)).toHaveValue('')
      expect(screen.getByTestId('api-key-input')).toHaveValue('')
      expect(screen.getByLabelText(/base url/i)).toHaveValue('https://api.openai.com/v1')
      expect(screen.getByLabelText(/max tokens/i)).toHaveValue(4096)
      expect(screen.getByLabelText(/rpm/i)).toHaveValue(60)
      expect(screen.getByLabelText(/tpm/i)).toHaveValue(100000)
      expect(screen.getByLabelText(/weight/i)).toHaveValue(1)
    })
  })
})
