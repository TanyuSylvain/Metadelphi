import { useMemo, useRef, useState, useEffect } from 'react'
import { renderMarkdown, renderPlain } from '../../utils/markdown'
import type { Citation } from '../../types/messages'

interface Props {
  content: string
  markdownEnabled?: boolean
  className?: string
  citations?: Citation[]
}

interface TooltipState {
  visible: boolean
  x: number
  y: number
  title: string
  url: string
}

export default function MarkdownContent({ content, markdownEnabled = true, className, citations }: Props) {
  const html = useMemo(
    () => (markdownEnabled ? renderMarkdown(content, citations) : renderPlain(content)),
    [content, markdownEnabled, citations],
  )

  const containerRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    title: '',
    url: '',
  })
  const hideTimerRef = useRef<number | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleEnter = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.classList.contains('citation-ref')) return
      if (hideTimerRef.current != null) {
        window.clearTimeout(hideTimerRef.current)
        hideTimerRef.current = null
      }
      const rect = target.getBoundingClientRect()
      const title = target.dataset.title || ''
      const url = target.dataset.url || ''
      setTooltip({
        visible: true,
        x: rect.left + rect.width / 2,
        y: rect.top - 8,
        title,
        url,
      })
    }

    const handleLeave = () => {
      hideTimerRef.current = window.setTimeout(() => {
        setTooltip((t) => ({ ...t, visible: false }))
      }, 150)
    }

    container.addEventListener('mouseenter', handleEnter, true)
    container.addEventListener('mouseleave', handleLeave, true)

    return () => {
      container.removeEventListener('mouseenter', handleEnter, true)
      container.removeEventListener('mouseleave', handleLeave, true)
      if (hideTimerRef.current != null) window.clearTimeout(hideTimerRef.current)
    }
  }, [html])

  return (
    <>
      <div
        ref={containerRef}
        className={`md-content${className ? ` ${className}` : ''}`}
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {tooltip.visible && (
        <div
          className="citation-tooltip"
          style={{
            position: 'fixed',
            left: tooltip.x,
            top: tooltip.y,
            transform: 'translate(-50%, -100%)',
            zIndex: 1000,
          }}
        >
          {tooltip.title && <div className="citation-tooltip-title">{tooltip.title}</div>}
          <div className="citation-tooltip-url">{tooltip.url}</div>
        </div>
      )}
    </>
  )
}
