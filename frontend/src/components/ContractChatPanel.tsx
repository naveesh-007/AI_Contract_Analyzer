import { useEffect, useRef, useState } from 'react'
import { getChatHistory, sendChatMessage } from '../services/api'
import type { ChatMessage, ChatSource } from '../types/chat'
import type { Clause } from '../types/clause'

interface ContractChatPanelProps {
  documentId: string
  clauses: Clause[]
  onSelectClause: (clause: Clause) => void
  onNavigateToPage?: (pageNumber: number) => void
}

const SUGGESTED_QUESTIONS = [
  'What are the termination conditions?',
  'Does this contract automatically renew?',
  'Are there any penalties?',
  'What payments are required?',
  'What are my obligations?',
  'What happens if I breach the agreement?',
]

export function ContractChatPanel({
  documentId,
  clauses,
  onSelectClause,
  onNavigateToPage,
}: ContractChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [inputQuestion, setInputQuestion] = useState<string>('')
  const [sending, setSending] = useState<boolean>(false)
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  // Fetch existing chat history on mount
  useEffect(() => {
    let mounted = true
    async function loadHistory() {
      try {
        setLoadingHistory(true)
        const res = await getChatHistory(documentId)
        if (mounted) {
          setSessionId(res.session_id)
          setMessages(res.messages)
        }
      } catch (err: any) {
        console.warn('Failed to load chat history:', err)
      } finally {
        if (mounted) setLoadingHistory(false)
      }
    }
    loadHistory()
    return () => {
      mounted = false
    }
  }, [documentId])

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = async (questionToSend?: string) => {
    const q = (questionToSend || inputQuestion).trim()
    if (!q || sending) return

    setInputQuestion('')
    setError(null)
    setSending(true)

    // Optimistically append user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: sessionId || '',
      role: 'user',
      message: q,
      grounded: true,
      sources: [],
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])

    try {
      const res = await sendChatMessage(documentId, q, sessionId || undefined)
      setSessionId(res.session_id)

      const assistantMsg: ChatMessage = {
        id: res.message_id,
        session_id: res.session_id,
        role: 'assistant',
        message: res.answer,
        grounded: res.grounded,
        sources: res.sources,
        created_at: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to get answer. Please try again.'
      setError(msg)
    } finally {
      setSending(false)
    }
  }

  // Handle clicking a citation source
  const handleSourceClick = (source: ChatSource) => {
    if (source.clause_id) {
      const matched = clauses.find((c) => c.id === source.clause_id)
      if (matched) {
        onSelectClause(matched)
        return
      }
    }

    // Fallback match by page or section name
    if (source.page_number) {
      onNavigateToPage?.(source.page_number)
      const pageClause = clauses.find((c) => c.page_number === source.page_number)
      if (pageClause) {
        onSelectClause(pageClause)
      }
    }
  }

  return (
    <div
      className="glass-card"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--color-bg-card)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--color-bg-secondary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>💬</span>
          <div>
            <h2
              style={{
                fontSize: '14px',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                margin: 0,
              }}
            >
              Ask this Contract
            </h2>
            <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', margin: 0 }}>
              Answers strictly grounded in document text
            </p>
          </div>
        </div>

        <span
          className="badge"
          style={{
            background: 'rgba(52, 211, 153, 0.12)',
            color: '#34d399',
            border: '1px solid rgba(52, 211, 153, 0.3)',
            fontSize: '10px',
          }}
        >
          ✓ Document Grounded
        </span>
      </div>

      {/* Suggested Question Chips (Show when few messages) */}
      {messages.length <= 1 && (
        <div
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid var(--color-border)',
            background: 'rgba(10, 13, 20, 0.4)',
          }}
        >
          <p
            style={{
              fontSize: '11px',
              fontWeight: 700,
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              marginBottom: '8px',
            }}
          >
            Suggested Questions
          </p>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '6px',
            }}
          >
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => handleSend(q)}
                disabled={sending}
                style={{
                  padding: '5px 10px',
                  borderRadius: '16px',
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-accent-light)',
                  fontSize: '11.5px',
                  cursor: sending ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s ease',
                  textAlign: 'left',
                }}
                className="btn-suggestion-chip"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message Thread */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        {loadingHistory && messages.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              color: 'var(--color-text-muted)',
              fontSize: '12px',
              padding: '24px',
            }}
          >
            Loading conversation history...
          </div>
        )}

        {messages.length === 0 && !loadingHistory && (
          <div
            style={{
              textAlign: 'center',
              padding: '32px 16px',
              color: 'var(--color-text-secondary)',
            }}
          >
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>🤖</div>
            <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Ask anything about this document
            </p>
            <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
              The assistant will answer strictly from the contract provisions and cite relevant sections.
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.role === 'user'
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
                gap: '4px',
              }}
            >
              {/* Message Bubble */}
              <div
                style={{
                  maxWidth: '88%',
                  padding: '12px 16px',
                  borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  background: isUser
                    ? 'linear-gradient(135deg, #6c8ef5 0%, #5a6fd6 100%)'
                    : 'var(--color-bg-secondary)',
                  border: isUser ? 'none' : '1px solid var(--color-border)',
                  color: isUser ? '#ffffff' : 'var(--color-text-primary)',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  wordBreak: 'break-word',
                  boxShadow: isUser
                    ? '0 4px 14px rgba(108, 142, 245, 0.25)'
                    : '0 2px 8px rgba(0,0,0,0.2)',
                }}
              >
                {msg.message}
              </div>

              {/* Citations & Grounding Indicator for Assistant */}
              {!isUser && (
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    gap: '6px',
                    marginTop: '2px',
                  }}
                >
                  {/* Grounding Verification Badge */}
                  {msg.grounded ? (
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        color: '#34d399',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '3px',
                      }}
                    >
                      ✓ Grounded
                    </span>
                  ) : (
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        color: '#fbbf24',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '3px',
                      }}
                    >
                      ⚠️ Out of scope
                    </span>
                  )}

                  {/* Clickable Source Pills */}
                  {msg.sources &&
                    msg.sources.map((src, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => handleSourceClick(src)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '2px 8px',
                          borderRadius: '10px',
                          background: 'rgba(108, 142, 245, 0.15)',
                          border: '1px solid rgba(108, 142, 245, 0.3)',
                          color: 'var(--color-accent-light)',
                          fontSize: '10.5px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                        }}
                        title="Click to view and highlight source in document"
                      >
                        <span>📄</span>
                        <span>{src.section || 'Source'}</span>
                        {src.page_number && <span>· P.{src.page_number}</span>}
                        <span>↗</span>
                      </button>
                    ))}
                </div>
              )}
            </div>
          )
        })}

        {/* Typing indicator while generating answer */}
        {sending && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              borderRadius: '12px',
              background: 'var(--color-bg-secondary)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)',
              fontSize: '12px',
              width: 'fit-content',
            }}
          >
            <span className="animate-pulse-slow">🤖 Searching document &amp; verifying facts...</span>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              background: 'rgba(248, 113, 113, 0.12)',
              border: '1px solid rgba(248, 113, 113, 0.3)',
              color: '#f87171',
              fontSize: '12px',
            }}
          >
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSend()
        }}
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--color-border)',
          background: 'var(--color-bg-secondary)',
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
        }}
      >
        <input
          id="chat-question-input"
          type="text"
          className="input-field"
          placeholder="Ask a question about this contract..."
          value={inputQuestion}
          onChange={(e) => setInputQuestion(e.target.value)}
          disabled={sending}
          style={{
            fontSize: '13px',
            height: '42px',
          }}
        />
        <button
          id="chat-send-btn"
          type="submit"
          disabled={!inputQuestion.trim() || sending}
          className="btn-primary"
          style={{
            height: '42px',
            padding: '0 16px',
            fontSize: '13px',
            opacity: !inputQuestion.trim() || sending ? 0.6 : 1,
            cursor: !inputQuestion.trim() || sending ? 'not-allowed' : 'pointer',
          }}
        >
          {sending ? '...' : 'Ask ↗'}
        </button>
      </form>
    </div>
  )
}
