import React from 'react'

/**
 * ToolCall — shows a single tool invocation result inline in the chat.
 * Used inside Message.jsx to show tool_calls summary.
 */
export default function ToolCall({ toolName, success, error }) {
  return (
    <div className="tool-call-card">
      <span style={{ color: success ? 'var(--success)' : 'var(--error)' }}>
        {success ? '✓' : '✗'}
      </span>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
        {toolName}
      </span>
      {error && (
        <span style={{ color: 'var(--error)', fontSize: 11 }}>— {error}</span>
      )}
    </div>
  )
}
