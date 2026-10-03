import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Renders a single chat message — user or assistant.
 * Assistant messages support markdown, sources, and tool call indicators.
 */
export default function Message({ role, content, sources = [], toolCalls = [] }) {
  const isUser = role === 'user'

  return (
    <div className={`message ${role}`}>
      {/* Avatar */}
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '70%' }}>
        {/* Main bubble */}
        <div className="message-bubble">
          {isUser ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          )}

          {/* Sources */}
          {!isUser && sources.length > 0 && (
            <div className="sources">
              <div className="sources-title">Sources</div>
              {sources.map((s, i) => (
                <a
                  key={i}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-link"
                  title={s.url}
                >
                  🔗 {s.title || s.url}
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Tool call summary (shown below bubble) */}
        {!isUser && toolCalls.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {toolCalls.map((tc, i) => (
              <div key={i} className="tool-call-card">
                <span>{tc.success ? '✓' : '✗'}</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{tc.tool_name}</span>
                <span style={{ color: tc.success ? 'var(--success)' : 'var(--error)' }}>
                  {tc.success ? 'completed' : 'failed'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
