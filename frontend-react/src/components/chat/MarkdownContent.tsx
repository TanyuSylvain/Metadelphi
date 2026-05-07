import { useMemo } from 'react'
import { renderMarkdown, renderPlain } from '../../utils/markdown'

interface Props {
  content: string
  markdownEnabled?: boolean
  className?: string
}

export default function MarkdownContent({ content, markdownEnabled = true, className }: Props) {
  const html = useMemo(
    () => (markdownEnabled ? renderMarkdown(content) : renderPlain(content)),
    [content, markdownEnabled],
  )

  return (
    <div
      className={`md-content${className ? ` ${className}` : ''}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
