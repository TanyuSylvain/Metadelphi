import { useState, useEffect, useCallback } from 'react'
import { conversationsApi } from '../api/conversations'
import type { ConversationInfo } from '../types/models'

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationInfo[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await conversationsApi.list()
      setConversations(res.conversations)
    } catch {
      setConversations([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const deleteConversation = useCallback(async (id: string) => {
    await conversationsApi.delete(id)
    setConversations((prev) => prev.filter((c) => c.id !== id))
  }, [])

  const deleteAll = useCallback(async () => {
    await conversationsApi.deleteAll()
    setConversations([])
  }, [])

  return { conversations, loading, reload: load, deleteConversation, deleteAll }
}
