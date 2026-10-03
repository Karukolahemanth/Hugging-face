import React from 'react'

/**
 * Sidebar with conversation history, new chat button, and branding.
 */
export default function Sidebar({
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🤖</div>
          <span className="sidebar-logo-text">GAIA</span>
        </div>

        {/* New Chat */}
        <button
          id="new-chat-btn"
          className="btn-new-chat"
          onClick={onNewChat}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Task
        </button>
      </div>

      {/* History */}
      {conversations.length > 0 && (
        <>
          <div className="sidebar-section-title">History</div>
          <div className="sidebar-conversations">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conv-item ${conv.id === activeConversationId ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <span className="conv-item-title" title={conv.title}>
                  {conv.title}
                </span>
                <button
                  className="conv-item-delete"
                  title="Delete conversation"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteConversation(conv.id)
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
                    <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Footer */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--border)',
        fontSize: '11px',
        color: 'var(--text-muted)',
      }}>
        GAIA Agent v1.0 • Phase 1
      </div>
    </aside>
  )
}
