import React, { useState, useEffect, useCallback } from 'react'
import { api } from './api/client'
import Sidebar from './components/Sidebar'
import Chat from './components/Chat'

export default function App() {
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [chatKey, setChatKey] = useState(0)   // Force re-mount Chat on new conversation
  const [backendStatus, setBackendStatus] = useState('connecting')

  // Check backend health
  useEffect(() => {
    api.health()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'))
  }, [])

  // Load conversation history
  const refreshConversations = useCallback(async () => {
    try {
      const list = await api.listConversations()
      setConversations(list)
      if (list.length > 0 && !activeConversationId) {
        // Don't auto-select — let user choose or start fresh
      }
    } catch {
      // Backend might not be ready yet
    }
  }, [activeConversationId])

  useEffect(() => {
    refreshConversations()
    const interval = setInterval(refreshConversations, 10000)
    return () => clearInterval(interval)
  }, [refreshConversations])

  const handleNewChat = () => {
    setActiveConversationId(null)
    setChatKey((k) => k + 1)
  }

  const handleSelectConversation = (id) => {
    setActiveConversationId(id)
    setChatKey((k) => k + 1)
  }

  const handleDeleteConversation = async (id) => {
    await api.deleteConversation(id).catch(() => {})
    setConversations((prev) => prev.filter((c) => c.id !== id))
    if (activeConversationId === id) {
      setActiveConversationId(null)
      setChatKey((k) => k + 1)
    }
  }

  const handleConversationCreated = () => {
    setTimeout(refreshConversations, 1500)
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
      />

      <div className="main">
        {/* Top bar */}
        <div className="topbar">
          <span className="topbar-title">
            {activeConversationId
              ? conversations.find((c) => c.id === activeConversationId)?.title || 'Conversation'
              : 'New Task'
            }
          </span>
          <div className="status-badge">
            <div
              className="status-dot"
              style={{
                background: backendStatus === 'online'
                  ? 'var(--success)'
                  : backendStatus === 'offline'
                  ? 'var(--error)'
                  : 'var(--warning)',
              }}
            />
            {backendStatus === 'online' ? 'Agent Online' : backendStatus === 'offline' ? 'Agent Offline' : 'Connecting...'}
          </div>
        </div>

        {/* Chat */}
        <div className="chat-area">
          {backendStatus === 'offline' ? (
            <div className="welcome">
              <div className="welcome-icon" style={{ animation: 'none' }}>⚠️</div>
              <h1 style={{ fontSize: 22 }}>Backend Offline</h1>
              <p>
                The GAIA Agent backend is not running. Please start it with:
              </p>
              <code style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                padding: '12px 20px',
                borderRadius: 'var(--radius-md)',
                fontSize: 13,
                fontFamily: 'JetBrains Mono, monospace',
              }}>
                uvicorn backend.main:app --reload
              </code>
            </div>
          ) : (
            <Chat
              key={chatKey}
              conversationId={activeConversationId}
              onConversationCreated={handleConversationCreated}
            />
          )}
        </div>
      </div>
    </div>
  )
}
