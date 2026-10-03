import React, { useState, useRef, useEffect, useCallback } from 'react'
import { streamChat } from '../api/client'
import Message from './Message'
import AgentSteps from './AgentSteps'
import FileUpload from './FileUpload'

const EXAMPLES = [
  '🧮 Calculate (250 × 18) / 5 and show the steps',
  '🔎 Search for the latest AI news and summarize key trends',
  '📊 What is the square root of 1764 and what is 2^15?',
  '🌍 Compare the GDP of USA and China in 2023 and calculate the ratio',
]

/**
 * Main chat interface — handles message flow, streaming, and file attachments.
 */
export default function Chat({ conversationId, onConversationCreated }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [steps, setSteps] = useState([])
  const [attachedFiles, setAttachedFiles] = useState([])  // [{filename, originalName}]
  const [errorMsg, setErrorMsg] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)

  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, steps])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'
  }, [input])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isLoading) return

    setInput('')
    setErrorMsg(null)
    setIsLoading(true)
    setSteps([])

    // Add user message immediately
    const userMsg = { role: 'user', content: text, id: Date.now() }
    setMessages((prev) => [...prev, userMsg])

    // Placeholder for assistant
    const assistantId = Date.now() + 1
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', sources: [], toolCalls: [], id: assistantId, loading: true },
    ])

    const fileNames = attachedFiles.map((f) => f.filename)
    setAttachedFiles([])

    // Stream the response
    const abort = streamChat(
      text,
      conversationId,
      fileNames,
      (event) => {
        if (event.event === 'status') {
          setStreamStatus(event.data?.message || '')
        }

        if (event.event === 'tool_started') {
          setSteps((prev) => [
            ...prev,
            { label: event.data.label, status: 'running' },
          ])
        }

        if (event.event === 'tool_completed') {
          setSteps((prev) =>
            prev.map((s, i) =>
              i === prev.length - 1
                ? { ...s, status: event.data.success ? 'done' : 'error' }
                : s
            )
          )
        }

        if (event.event === 'final_answer') {
          const { answer, sources, steps: finalSteps, tool_calls } = event.data

          // Notify parent of new conversation ID if created
          if (!conversationId && onConversationCreated) {
            // We'll get it from the conversation list refresh
            onConversationCreated()
          }

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: answer || 'No answer returned.',
                    sources: sources || [],
                    toolCalls: tool_calls || [],
                    loading: false,
                  }
                : m
            )
          )

          if (finalSteps) {
            setSteps(finalSteps.map((s) => ({ label: s.label, status: s.status })))
          }

          setIsLoading(false)
          setStreamStatus(null)
        }

        if (event.event === 'error') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: `❌ Error: ${event.data?.error || 'Unknown error'}`,
                    loading: false,
                  }
                : m
            )
          )
          setIsLoading(false)
          setStreamStatus(null)
        }

        if (event.event === 'done') {
          setIsLoading(false)
          setStreamStatus(null)
        }
      }
    )

    abortRef.current = abort
  }, [input, isLoading, conversationId, attachedFiles, onConversationCreated])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleExampleClick = (example) => {
    // Strip emoji prefix
    const text = example.replace(/^[^\s]+ /, '')
    setInput(text)
    textareaRef.current?.focus()
  }

  const handleFileUploaded = (filename, originalName, mimeType) => {
    setAttachedFiles((prev) => [...prev, { filename, originalName, mimeType }])
  }

  const handleFileError = (msg) => {
    setErrorMsg(`Upload error: ${msg}`)
    setTimeout(() => setErrorMsg(null), 4000)
  }

  const removeFile = (filename) => {
    setAttachedFiles((prev) => prev.filter((f) => f.filename !== filename))
  }

  const isEmpty = messages.length === 0

  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
      {/* Messages column */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        {/* Message list or Welcome screen */}
        <div className="chat-messages">
          {isEmpty ? (
            <div className="welcome">
              <div className="welcome-icon">🤖</div>
              <h1>GAIA Agent</h1>
              <p>
                A general-purpose AI agent that reasons, plans, searches the web,
                reads documents, and provides verified answers with sources.
              </p>
              <div className="welcome-examples">
                {EXAMPLES.map((ex, i) => (
                  <button
                    key={i}
                    className="example-card"
                    onClick={() => handleExampleClick(ex)}
                    id={`example-${i}`}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              msg.loading ? (
                <div key={msg.id} className="thinking" style={{ marginLeft: '44px' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {streamStatus || 'Thinking...'}
                  </span>
                  <div className="thinking-dots">
                    <div className="thinking-dot" />
                    <div className="thinking-dot" />
                    <div className="thinking-dot" />
                  </div>
                </div>
              ) : (
                <Message
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  toolCalls={msg.toolCalls}
                />
              )
            ))
          )}

          {/* Error banner */}
          {errorMsg && (
            <div style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 14px',
              fontSize: 13,
              color: 'var(--error)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              ⚠️ {errorMsg}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="input-area">
          {/* Attached files */}
          {attachedFiles.length > 0 && (
            <div className="uploaded-files">
              {attachedFiles.map((f) => (
                <div key={f.filename} className="file-badge">
                  <span>{f.mimeType?.startsWith('image/') ? '🖼️' : '📎'}</span>
                  <span>{f.originalName}</span>
                  <button
                    className="file-badge-remove"
                    onClick={() => removeFile(f.filename)}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="input-box">
            <textarea
              ref={textareaRef}
              id="chat-input"
              className="input-textarea"
              placeholder="Ask anything... (Shift+Enter for newline)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
            />

            <div className="input-actions">
              {/* File attach */}
              <FileUpload
                onUpload={handleFileUploaded}
                onError={handleFileError}
              />

              {/* Send */}
              <button
                id="send-btn"
                className="btn-send"
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                title="Send message"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Activity Panel */}
      <AgentSteps steps={steps} isThinking={isLoading && steps.length === 0} />
    </div>
  )
}
