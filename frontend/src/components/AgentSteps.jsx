import React from 'react'

/**
 * Displays the agent activity panel — steps taken during reasoning.
 * Shows only safe high-level labels (no chain-of-thought).
 */
export default function AgentSteps({ steps, isThinking }) {
  if (!steps?.length && !isThinking) return null

  return (
    <div className="activity-panel">
      <div className="activity-header">Agent Activity</div>

      {steps.map((step, i) => (
        <div key={i} className="step-item">
          <div className={`step-icon ${step.status}`}>
            {step.status === 'done'    && '✓'}
            {step.status === 'error'   && '✗'}
            {step.status === 'pending' && '○'}
            {step.status === 'running' && <div className="step-spinner" />}
          </div>
          <span className="step-label">{step.label}</span>
        </div>
      ))}

      {isThinking && (
        <div className="step-item">
          <div className="step-icon running">
            <div className="step-spinner" />
          </div>
          <span className="step-label">Thinking...</span>
        </div>
      )}
    </div>
  )
}
