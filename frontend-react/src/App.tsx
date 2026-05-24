import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Layout, Typography, message as antMessage } from 'antd'
import { conversationsApi, historyToMessages } from './api/conversations'
import { useAppStore } from './store/appStore'
import { useChatStore } from './store/chatStore'
import { usePrefsStore } from './store/prefsStore'
import { useDebateStore } from './store/debateStore'
import { useModels } from './hooks/useModels'
import { useConversations } from './hooks/useConversations'
import { useSmartScroll } from './hooks/useSmartScroll'
import { useSimpleStream } from './hooks/useSimpleStream'
import { useDebateStream } from './hooks/useDebateStream'
import { useCoworkingStream } from './hooks/useCoworkingStream'
import { useImageStream } from './hooks/useImageStream'
import { generateUUID } from './utils/uuid'

import { useCoworkingStore } from './store/coworkingStore'
import ConversationList from './components/sidebar/ConversationList'
import ModeSegmented from './components/header/ModeSegmented'
import ModelSelect from './components/header/ModelSelect'
import HeaderToggles from './components/header/HeaderToggles'
import MultiAgentConfigPanel from './components/config/MultiAgentConfig'
import CoworkingConfig from './components/config/CoworkingConfig'
import MessageItem from './components/chat/MessageItem'
import MessageInput from './components/input/MessageInput'
import DebatePanel from './components/debate/DebatePanel'
import CoworkingPanel from './components/coworking/CoworkingPanel'
import SettingsDrawer from './components/settings/SettingsDrawer'

const { Sider, Header, Content } = Layout

export default function App() {
  const prefs = usePrefsStore()
  const appStore = useAppStore()
  const chatStore = useChatStore()
  const debateStore = useDebateStore()
  const { workspacePath, setWorkspacePath } = useCoworkingStore()

  const { models, loading: modelsLoading } = useModels()
  const { conversations, loading: convsLoading, reload: reloadConvs, deleteConversation, deleteAll } = useConversations()

  const simpleStream = useSimpleStream()
  const debateStream = useDebateStream()
  const cwStream = useCoworkingStream()
  const imageStream = useImageStream()

  const messagesRef = useRef<HTMLDivElement>(null)
  const { scrollToBottom, resetScroll } = useSmartScroll(messagesRef)

  const resolveModelRef = useCallback((value: string) => {
    if (!value) return ''
    const exact = models.find((m) => m.model_ref === value)
    if (exact) return exact.model_ref

    const legacyMatches = models.filter((m) => m.model_id === value)
    if (legacyMatches.length === 1) return legacyMatches[0].model_ref
    return ''
  }, [models])

  // Scroll to bottom when messages change during streaming
  useEffect(() => {
    scrollToBottom()
  }, [chatStore.messages, scrollToBottom])

  // Migrate persisted legacy raw model IDs to provider-qualified refs when possible.
  useEffect(() => {
    if (models.length === 0) return

    const nextSelected = resolveModelRef(prefs.selectedModel)
    if (prefs.selectedModel && nextSelected && nextSelected !== prefs.selectedModel) {
      prefs.setSelectedModel(nextSelected)
    } else if (prefs.selectedModel && !nextSelected && !models.some((m) => m.model_ref === prefs.selectedModel)) {
      prefs.setSelectedModel('')
    }

    const nextDebateConfig = {
      moderator: resolveModelRef(prefs.multiAgentConfig.moderator),
      expert: resolveModelRef(prefs.multiAgentConfig.expert),
      critic: resolveModelRef(prefs.multiAgentConfig.critic),
    }

    if (
      (prefs.multiAgentConfig.moderator && nextDebateConfig.moderator && nextDebateConfig.moderator !== prefs.multiAgentConfig.moderator) ||
      (prefs.multiAgentConfig.expert && nextDebateConfig.expert && nextDebateConfig.expert !== prefs.multiAgentConfig.expert) ||
      (prefs.multiAgentConfig.critic && nextDebateConfig.critic && nextDebateConfig.critic !== prefs.multiAgentConfig.critic) ||
      (prefs.multiAgentConfig.moderator && !nextDebateConfig.moderator && !models.some((m) => m.model_ref === prefs.multiAgentConfig.moderator)) ||
      (prefs.multiAgentConfig.expert && !nextDebateConfig.expert && !models.some((m) => m.model_ref === prefs.multiAgentConfig.expert)) ||
      (prefs.multiAgentConfig.critic && !nextDebateConfig.critic && !models.some((m) => m.model_ref === prefs.multiAgentConfig.critic))
    ) {
      prefs.setMultiAgentConfig(nextDebateConfig)
    }
  }, [models, prefs, resolveModelRef])

  // Load first model if none selected
  useEffect(() => {
    const selectedExists = models.some((m) => m.model_ref === prefs.selectedModel)
    if ((!prefs.selectedModel || !selectedExists) && models.length > 0) {
      const first = models.find((m) => !m.is_image_model)
      if (first) prefs.setSelectedModel(first.model_ref)
    }
  }, [models, prefs])

  // Auto-switch model type when image mode toggles
  useEffect(() => {
    if (models.length === 0) return
    if (prefs.imageModeEnabled) {
      const currentIsText = models.find((m) => m.model_ref === prefs.selectedModel && !m.is_image_model)
      if (currentIsText) {
        const firstImage = models.find((m) => m.is_image_model)
        if (firstImage) prefs.setSelectedModel(firstImage.model_ref)
      }
    } else {
      const currentIsImage = models.find((m) => m.model_ref === prefs.selectedModel && m.is_image_model)
      if (currentIsImage) {
        const firstText = models.find((m) => !m.is_image_model)
        if (firstText) prefs.setSelectedModel(firstText.model_ref)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefs.imageModeEnabled, models])

  // Load conversation history when switching conversations
  const loadConversation = useCallback(async (id: string) => {
    chatStore.setConversationId(id)
    chatStore.clearMessages()
    debateStore.reset()
    try {
      const history = await conversationsApi.get(id)
      chatStore.setMessages(historyToMessages(history))
      resetScroll()
    } catch {
      chatStore.setMessages([])
    }
  }, [chatStore, debateStore, resetScroll])

  const handleNewConversation = () => {
    const id = generateUUID()
    chatStore.setConversationId(id)
    chatStore.clearMessages()
    debateStore.reset()
  }

  const handleModeChange = async (newMode: typeof prefs.chatMode) => {
    if (appStore.isProcessing) return
    prefs.setChatMode(newMode)
    try {
      await conversationsApi.switchMode(chatStore.conversationId, { target_mode: newMode })
    } catch {
      // Mode switch can fail if conversation doesn't exist yet — that's fine
    }
  }

  const handleSend = useCallback(async (text: string) => {
    if (!prefs.selectedModel && prefs.chatMode !== 'debate') {
      antMessage.warning('Please select a model first')
      return
    }

    resetScroll()

    if (prefs.chatMode === 'debate') {
      await debateStream.start({
        message: text,
        conversation_id: chatStore.conversationId,
        models: {
          moderator: prefs.multiAgentConfig.moderator || undefined,
          expert: prefs.multiAgentConfig.expert || undefined,
          critic: prefs.multiAgentConfig.critic || undefined,
        },
        max_iterations: prefs.multiAgentConfig.maxIterations,
        score_threshold: prefs.multiAgentConfig.scoreThreshold,
        thinking: prefs.multiAgentConfig.thinking,
      })
      reloadConvs()
      return
    }

    if (prefs.chatMode === 'coworking') {
      if (!workspacePath) {
        antMessage.warning('Please select a workspace directory first')
        return
      }
      await cwStream.start({
        message: text,
        conversation_id: chatStore.conversationId,
        model: prefs.selectedModel,
        workspace_path: workspacePath,
        thinking: prefs.isThinkingEnabled(prefs.selectedModel),
        web_search: prefs.webSearchEnabled,
      })
      reloadConvs()
      return
    }

    if (prefs.imageModeEnabled) {
      await imageStream.start({
        message: text,
        conversation_id: chatStore.conversationId,
        model: prefs.selectedModel,
        aspect_ratio: prefs.imageAspectRatio,
      })
      reloadConvs()
      return
    }

    await simpleStream.start({
      message: text,
      conversation_id: chatStore.conversationId,
      model: prefs.selectedModel,
      thinking: prefs.isThinkingEnabled(prefs.selectedModel),
      web_search: prefs.webSearchEnabled,
    })
    reloadConvs()
  }, [prefs, chatStore, appStore, simpleStream, debateStream, cwStream, imageStream, resetScroll, reloadConvs, workspacePath])

  // Sidebar resize
  const [sidebarDragging, setSidebarDragging] = useState(false)
  const handleSidebarDrag = useCallback((e: MouseEvent) => {
    const w = Math.max(150, Math.min(400, e.clientX))
    prefs.setSidebarWidth(w)
  }, [prefs])
  const startSidebarDrag = useCallback(() => {
    setSidebarDragging(true)
    const stop = () => { setSidebarDragging(false); window.removeEventListener('mousemove', handleSidebarDrag); window.removeEventListener('mouseup', stop) }
    window.addEventListener('mousemove', handleSidebarDrag)
    window.addEventListener('mouseup', stop)
  }, [handleSidebarDrag])

  // Panel resize
  const [panelDragging, setPanelDragging] = useState(false)
  const mainRef = useRef<HTMLDivElement>(null)
  const handlePanelDrag = useCallback((e: MouseEvent) => {
    if (!mainRef.current) return
    const rect = mainRef.current.getBoundingClientRect()
    const ratio = Math.max(0.2, Math.min(0.8, (e.clientX - rect.left) / rect.width))
    prefs.setPanelRatio(ratio)
  }, [prefs])
  const startPanelDrag = useCallback(() => {
    setPanelDragging(true)
    const stop = () => { setPanelDragging(false); window.removeEventListener('mousemove', handlePanelDrag); window.removeEventListener('mouseup', stop) }
    window.addEventListener('mousemove', handlePanelDrag)
    window.addEventListener('mouseup', stop)
  }, [handlePanelDrag])

  const showRightPanel =
    (prefs.chatMode === 'debate' && prefs.debatePanelVisible) ||
    prefs.chatMode === 'coworking'

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <>
        <Sider
          width={prefs.sidebarCollapsed ? 0 : prefs.sidebarWidth}
          theme="dark"
          className={`history-sider${prefs.sidebarCollapsed ? ' collapsed' : ''}`}
          style={{
            overflow: 'hidden',
            background: '#1a1a2e',
            flexShrink: 0,
            minWidth: 0,
            maxWidth: prefs.sidebarCollapsed ? 0 : prefs.sidebarWidth,
          }}
        >
          <div className="history-sider-inner">
            <ConversationList
              conversations={conversations}
              loading={convsLoading}
              currentId={chatStore.conversationId}
              onSelect={loadConversation}
              onNew={handleNewConversation}
              onDelete={deleteConversation}
              onDeleteAll={deleteAll}
            />
          </div>
        </Sider>
        {/* Sidebar resize handle */}
        <div
          className={`panel-resize-handle history-resize-handle${sidebarDragging ? ' dragging' : ''}${prefs.sidebarCollapsed ? ' collapsed' : ''}`}
          onMouseDown={prefs.sidebarCollapsed ? undefined : startSidebarDrag}
          style={{ background: 'transparent', zIndex: 1 }}
        />
      </>

      <Layout style={{ overflow: 'hidden' }}>
        {/* Header */}
        <Header
          style={{
            background: '#fff',
            height: 56,
            lineHeight: '56px',
            padding: '0 14px',
            borderBottom: '1px solid #e8e8e8',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flexShrink: 0,
          }}
        >
          {/* Sidebar toggle */}
          <div
            onClick={() => prefs.setSidebarCollapsed(!prefs.sidebarCollapsed)}
            style={{ cursor: 'pointer', fontSize: 16, color: '#666', padding: '0 4px' }}
          >
            {prefs.sidebarCollapsed ? '▶' : '◀'}
          </div>

          <ModeSegmented
            value={prefs.chatMode}
            onChange={handleModeChange}
            disabled={appStore.isProcessing}
          />

          {prefs.chatMode !== 'debate' && (
            <ModelSelect
              models={models}
              value={prefs.selectedModel}
              onChange={prefs.setSelectedModel}
              imageMode={prefs.imageModeEnabled}
              disabled={modelsLoading || appStore.isProcessing}
            />
          )}

          <HeaderToggles
            mode={prefs.chatMode}
            selectedModel={prefs.selectedModel}
            models={models}
            thinkingEnabled={prefs.isThinkingEnabled(prefs.selectedModel)}
            markdownEnabled={prefs.markdownEnabled}
            webSearchEnabled={prefs.webSearchEnabled}
            imageModeEnabled={prefs.imageModeEnabled}
            imageAspectRatio={prefs.imageAspectRatio}
            debatePanelVisible={prefs.debatePanelVisible}
            isProcessing={appStore.isProcessing}
            onThinkingChange={(v) => prefs.setThinkingEnabled(prefs.selectedModel, v)}
            onMarkdownChange={prefs.setMarkdownEnabled}
            onWebSearchChange={prefs.setWebSearchEnabled}
            onImageModeChange={prefs.setImageModeEnabled}
            onAspectRatioChange={prefs.setImageAspectRatio}
            onDebatePanelChange={prefs.setDebatePanelVisible}
            onSettingsClick={() => appStore.setSettingsOpen(true)}
          />
        </Header>

        {/* Debate config */}
        {prefs.chatMode === 'debate' && (
          <MultiAgentConfigPanel
            config={prefs.multiAgentConfig}
            models={models}
            onChange={prefs.setMultiAgentConfig}
          />
        )}

        {/* Coworking workspace config */}
        {prefs.chatMode === 'coworking' && (
          <CoworkingConfig
            workspacePath={workspacePath}
            onPathChange={setWorkspacePath}
          />
        )}

        {/* Main panel */}
        <Content
          ref={mainRef as React.RefObject<HTMLDivElement>}
          style={{ display: 'flex', overflow: 'hidden', flex: 1 }}
        >
          {/* Chat area */}
          <div
            style={{
              flex: showRightPanel ? prefs.panelRatio : 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              background: '#f5f5f5',
            }}
          >
            {/* Messages */}
            <div
              ref={messagesRef as React.RefObject<HTMLDivElement>}
              style={{
                flex: 1,
                overflow: 'auto',
                paddingTop: 12,
                paddingBottom: 12,
              }}
            >
              {chatStore.messages.length === 0 ? (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: '#9ca3af',
                  }}
                >
                  <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>🧠</div>
                  <Typography.Text style={{ fontSize: 16, color: '#9ca3af' }}>
                    Start a conversation
                  </Typography.Text>
                  <Typography.Text type="secondary" style={{ fontSize: 13, marginTop: 6 }}>
                    Select a model and send a message
                  </Typography.Text>
                </div>
              ) : (
                chatStore.messages.map((msg) => (
                  <MessageItem
                    key={msg.id}
                    message={msg}
                    markdownEnabled={prefs.markdownEnabled}
                    onDebateClick={(_debateId, round) => debateStore.setExpandedCard(round)}
                  />
                ))
              )}
            </div>

            {/* Input */}
            <MessageInput
              onSend={handleSend}
              onCancel={appStore.cancel}
              isProcessing={appStore.isProcessing}
              placeholder={
                prefs.chatMode === 'debate'
                  ? 'Send a question to the debate agents…'
                  : prefs.chatMode === 'coworking'
                  ? 'Describe the task for the agent…'
                  : prefs.imageModeEnabled
                  ? 'Describe the image to generate…'
                  : 'Type a message… (Enter to send)'
              }
            />
          </div>

          {/* Panel divider */}
          {showRightPanel && (
            <div
              className={`panel-resize-handle${panelDragging ? ' dragging' : ''}`}
              onMouseDown={startPanelDrag}
            />
          )}

          {/* Right panel */}
          {showRightPanel && (
            <div
              style={{
                flex: 1 - prefs.panelRatio,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {prefs.chatMode === 'debate' ? <DebatePanel /> : <CoworkingPanel />}
            </div>
          )}
        </Content>
      </Layout>

      {/* Settings drawer */}
      <SettingsDrawer
        open={appStore.settingsOpen}
        onClose={() => appStore.setSettingsOpen(false)}
      />
    </Layout>
  )
}
