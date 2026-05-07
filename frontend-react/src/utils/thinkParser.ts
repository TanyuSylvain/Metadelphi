import type { ThinkSegment } from '../types/messages'

export interface ParsedContent {
  segments: ThinkSegment[]
  responseContent: string
}

export function parseThinkBlocks(raw: string): ParsedContent {
  const segments: ThinkSegment[] = []
  let responseContent = raw

  const thinkRegex = /<think>([\s\S]*?)(<\/think>|$)/g
  let match: RegExpExecArray | null
  let lastIndex = 0
  let textParts: string[] = []

  // Reset lastIndex
  thinkRegex.lastIndex = 0

  while ((match = thinkRegex.exec(raw)) !== null) {
    // Text before this think block
    const before = raw.slice(lastIndex, match.index)
    if (before) textParts.push(before)

    const thinkContent = match[1]
    const closed = match[0].endsWith('</think>')
    segments.push({ thinking: thinkContent, complete: closed })

    lastIndex = match.index + match[0].length
  }

  // Remaining text after last think block
  const after = raw.slice(lastIndex)
  if (after) textParts.push(after)

  responseContent = textParts.join('').trim()

  return { segments, responseContent }
}

export function stripThinkBlocks(raw: string): string {
  return raw.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
}

export function extractCitations(raw: string): { citations: unknown[]; clean: string } {
  const citMatch = raw.match(/<!--CITATIONS_JSON([\s\S]*?)CITATIONS_JSON-->/)
  if (!citMatch) return { citations: [], clean: raw }
  try {
    const citations = JSON.parse(citMatch[1].trim())
    const clean = raw.replace(/<!--CITATIONS_JSON[\s\S]*?CITATIONS_JSON-->/, '').trim()
    return { citations, clean }
  } catch {
    return { citations: [], clean: raw }
  }
}

export function extractMetrics(raw: string): { metrics: unknown; clean: string } {
  const metMatch = raw.match(/<!--METRICS_JSON([\s\S]*?)METRICS_JSON-->/)
  if (!metMatch) return { metrics: null, clean: raw }
  try {
    const metrics = JSON.parse(metMatch[1].trim())
    const clean = raw.replace(/<!--METRICS_JSON[\s\S]*?METRICS_JSON-->/, '').trim()
    return { metrics, clean }
  } catch {
    return { metrics: null, clean: raw }
  }
}
