import React, { useEffect, useState } from 'react'
import { Select } from '@chakra-ui/react'
import api from '../services/api'

export default function Users() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [perPage] = useState(10)
  const [total, setTotal] = useState(0)

  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'user', is_active: true })
  const [createdKey, setCreatedKey] = useState(null)

  useEffect(()=>{ load(page) }, [page])

  async function load(p = 1){
    setLoading(true)
    try{
      const res = await api.getUsers(p, perPage)
      setUsers(res.users || [])
      setTotal(res.total || 0)
      setPage(res.page || p)
    }catch(e){ setUsers([]); setTotal(0) }
    setLoading(false)
  }

  function openCreate(){
    setEditingUser(null)
    setForm({ username:'', email:'', password:'', role:'user', is_active:true })
    setShowModal(true)
  }

  function openEdit(user){
    setEditingUser(user)
    setForm({
      username: user.username,
      email: user.email,
      password:'',
      role: user.role,
      is_active: user.is_active,
      rpm_limit: user.rpm_limit,
      tpm_limit: user.tpm_limit,
      budget_limit: user.budget_limit
    })
    setShowModal(true)
  }

  async function submit(e){
    e.preventDefault()
    try{
      if(editingUser){
        // Prepare update data including rate limit fields
        const updateData = {
          username: form.username,
          email: form.email,
          role: form.role,
          is_active: form.is_active,
          rpm_limit: form.rpm_limit,
          tpm_limit: form.tpm_limit,
          budget_limit: form.budget_limit
        };
        
        await api.updateUser(editingUser.id, updateData)
        alert('用户信息已更新')
      }else{
        const res = await api.createUser({ username: form.username, email: form.email, password: form.password, role: form.role })
        if(res && res.api_key) setCreatedKey(res.api_key)
        alert('用户已创建')
      }
      setShowModal(false)
      load(page)  // 刷新用户列表以显示更新后的限制信息
    }catch(err){ alert(err.message || String(err)) }
  }

  async function doReset(u){
    const pw = prompt('输入新密码（至少6位）')
    if(!pw) return
    try{
      await api.resetUserPassword(u.id, { new_password: pw })
      alert('密码已重置')
    }catch(e){ alert(String(e)) }
  }

  async function toggleActive(u){
    try{
      if(u.is_active){
        await api.disableUser(u.id)
      } else {
        await api.enableUser(u.id)
      }
      load(page)
    }catch(e){ alert(String(e)) }
  }

  const totalPages = Math.max(1, Math.ceil((total||0)/perPage))

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">用户管理</h1>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors font-medium"
        >
          添加用户
        </button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">{editingUser? '编辑用户':'创建用户'}</h3>
            <form onSubmit={submit}>
              <div className="mb-4">
                <label className="block text-gray-400 text-sm mb-2">用户名</label>
                <input
                  value={form.username}
                  onChange={e=>setForm({...form, username: e.target.value})}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div className="mb-4">
                <label className="block text-gray-400 text-sm mb-2">邮箱</label>
                <input
                  value={form.email}
                  onChange={e=>setForm({...form, email: e.target.value})}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              {!editingUser && (
                <div className="mb-4">
                  <label className="block text-gray-400 text-sm mb-2">密码</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={e=>setForm({...form, password: e.target.value})}
                    className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              )}
              <div className="mb-6">
                <label className="block text-gray-400 text-sm mb-2">角色</label>
                <Select
                  value={form.role}
                  onChange={e=>setForm({...form, role: e.target.value})}
                  className="text-white"
                  width="full"
                >
                  <option value="user" >用户</option>
                  <option value="admin" >管理员</option>
                </Select>
              </div>
              {editingUser && (
                <>
                  <div className="mb-4">
                    <label className="block text-gray-400 text-sm mb-2">RPM限制</label>
                    <input
                      type="number"
                      value={form.rpm_limit || ''}
                      onChange={e=>setForm({...form, rpm_limit: e.target.value ? parseInt(e.target.value) : ''})}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="例如: 60"
                    />
                  </div>
                  <div className="mb-4">
                    <label className="block text-gray-400 text-sm mb-2">TPM限制</label>
                    <input
                      type="number"
                      value={form.tpm_limit || ''}
                      onChange={e=>setForm({...form, tpm_limit: e.target.value ? parseInt(e.target.value) : ''})}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="例如: 60000"
                    />
                  </div>
                  <div className="mb-4">
                    <label className="block text-gray-400 text-sm mb-2">预算限制</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.budget_limit || ''}
                      onChange={e=>setForm({...form, budget_limit: e.target.value ? parseFloat(e.target.value) : ''})}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="例如: 1000.00"
                    />
                  </div>
                </>
              )}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={()=>setShowModal(false)}
                  className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors font-medium"
                >
                  保存
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {createdKey && (
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg mb-6">
          <h3 className="text-xl font-bold text-white mb-4">创建的API密钥</h3>
          <div className="flex">
            <input
              value={createdKey}
              readOnly
              className="flex-grow bg-dark-700 border border-dark-600 rounded-l-lg px-3 py-2 text-white focus:outline-none"
            />
            <button
              onClick={() => {
                navigator.clipboard.writeText(createdKey);
                alert('已复制到剪贴板');
              }}
              className="px-4 py-2 bg-secondary-500 hover:bg-secondary-600 text-dark-950 rounded-r-lg transition-colors font-medium"
            >
              复制
            </button>
          </div>
        </div>
      )}

      <div className="bg-dark-800 rounded-xl border border-dark-700 shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-700">
              <tr>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">用户名</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">邮箱</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">角色</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">状态</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">RPM限制</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">TPM限制</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">预算限制</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-gray-400">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-primary-500"></div>
                    </div>
                  </td>
                </tr>
              ) : users.map(u => (
                <tr key={u.id} className="border-b border-dark-700 hover:bg-dark-750 transition-colors">
                  <td className="py-3 px-4 text-white">{u.username}</td>
                  <td className="py-3 px-4 text-gray-300">{u.email}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      u.role === 'admin'
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {u.role === 'admin' ? '管理员' : '用户'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      u.is_active
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {u.is_active ? '启用' : '停用'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-300">{u.rpm_limit || '-'}</td>
                  <td className="py-3 px-4 text-gray-300">{u.tpm_limit || '-'}</td>
                  <td className="py-3 px-4 text-gray-300">{u.budget_limit || '-'}</td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={()=>openEdit(u)}
                        className="px-3 py-1 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors text-sm"
                      >
                        编辑
                      </button>
                      <button
                        onClick={()=>doReset(u)}
                        className="px-3 py-1 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors text-sm"
                      >
                        重置密码
                      </button>
                      <button
                        onClick={()=>toggleActive(u)}
                        className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                          u.is_active
                            ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
                            : 'bg-green-500/20 hover:bg-green-500/30 text-green-400'
                        }`}
                      >
                        {u.is_active ? '停用' : '启用'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && users.length===0 && (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-gray-400">
                    暂无用户数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex justify-between items-center mt-6">
        <button
          onClick={()=>{ if(page>1) setPage(page-1) }}
          disabled={page<=1}
          className={`px-4 py-2 rounded-lg transition-colors ${
            page <= 1
              ? 'bg-dark-800 text-gray-600 cursor-not-allowed'
              : 'bg-dark-700 hover:bg-dark-600 text-gray-300'
          }`}
        >
          上一页
        </button>
        <div className="text-gray-400">
          第 {page} 页，共 {totalPages} 页
        </div>
        <button
          onClick={()=>{ if(page<totalPages) setPage(page+1) }}
          disabled={page>=totalPages}
          className={`px-4 py-2 rounded-lg transition-colors ${
            page >= totalPages
              ? 'bg-dark-800 text-gray-600 cursor-not-allowed'
              : 'bg-dark-700 hover:bg-dark-600 text-gray-300'
          }`}
        >
          下一页
        </button>
      </div>
    </div>
  )
}










