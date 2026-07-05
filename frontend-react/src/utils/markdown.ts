import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import katex from 'katex'
import type { Citation } from '../types/messages'

// Configure marked
marked.setOptions({
  gfm: true,
  breaks: true,
})

// Syntax highlighting renderer
const renderer = new marked.Renderer()
renderer.code = (codeOrToken) => {
  // marked v13 passes { text, lang, escaped }; older versions pass raw arguments.
  const token = (typeof codeOrToken === 'object' && codeOrToken !== null)
    ? (codeOrToken as { text?: unknown; lang?: unknown })
    : { text: codeOrToken as unknown, lang: undefined }

  const text = typeof token.text === 'string' ? token.text : ''
  const lang = typeof token.lang === 'string' ? token.lang : ''

  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  const highlighted = hljs.highlight(text, { language }).value
  return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
}
marked.use({ renderer })

interface MathPlaceholders {
  values: string[]
}

function preprocessMath(text: string): { text: string; placeholders: MathPlaceholders } {
  if (typeof text !== 'string') {
    text = String(text ?? '')
  }

  const placeholders: MathPlaceholders = { values: [] }

  const addPlaceholder = (math: string, displayMode: boolean, fallback: string) => {
    try {
      const rendered = katex.renderToString(math.trim(), {
        displayMode,
        throwOnError: false,
      })
      const token = `@@KATEX_${placeholders.values.length}@@`
      placeholders.values.push(rendered)
      return token
    } catch {
      return fallback
    }
  }

  text = text
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => `$$${math}$$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => `$${math}$`)

  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (match, math) =>
    addPlaceholder(math, true, match),
  )

  text = text.replace(/\$([^$\n]+?)\$/g, (match, math) => addPlaceholder(math, false, match))

  return { text, placeholders }
}

function restoreMath(html: string, placeholders: MathPlaceholders): string {
  return placeholders.values.reduce(
    (result, rendered, index) => result.split(`@@KATEX_${index}@@`).join(rendered),
    html,
  )
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderCitations(text: string, citations?: Citation[]): string {
  if (!citations?.length) return text
  const map = new Map(citations.map((c) => [c.index, c]))
  return text.replace(/\[(\d+)\]/g, (match, num) => {
    const c = map.get(Number(num))
    if (!c) return match
    const titleAttr = escapeHtml(c.title || '')
    const urlAttr = escapeHtml(c.url)
    return `<a class="citation-ref" href="${c.url}" target="_blank" rel="noopener noreferrer" data-url="${urlAttr}" data-title="${titleAttr}">[${num}]</a>`
  })
}

export function renderMarkdown(text: string, citations?: Citation[]): string {
  if (typeof text !== 'string') {
    text = String(text ?? '')
  }

  const { text: preprocessed, placeholders } = preprocessMath(text)
  const withCitations = renderCitations(preprocessed, citations)
  let html: string
  try {
    html = marked.parse(withCitations) as string
  } catch (error) {
    console.error('Error parsing markdown:', error)
    html = escapeHtml(text).replace(/\n/g, '<br>')
  }
  const withMath = restoreMath(html, placeholders)
  return DOMPurify.sanitize(withMath, {
    ADD_TAGS: [
      'math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'annotation',
      'a',
    ],
    ADD_ATTR: [
      'class', 'style', 'aria-hidden', 'focusable', 'role', 'xmlns',
      'href', 'target', 'rel',
    ],
  })
}

export function renderPlain(text: string): string {
  if (typeof text !== 'string') {
    text = String(text ?? '')
  }
  return DOMPurify.sanitize(text.replace(/\n/g, '<br>'))
}
