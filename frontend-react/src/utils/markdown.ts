import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

// Configure marked
marked.setOptions({
  gfm: true,
  breaks: true,
})

// Syntax highlighting renderer
const renderer = new marked.Renderer()
renderer.code = ({ text, lang }) => {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  const highlighted = hljs.highlight(text, { language }).value
  return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
}
marked.use({ renderer })

function preprocessMath(text: string): string {
  // Normalize LaTeX delimiters: \[...\] → $$...$$, \(...\) → $...$
  return text
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => `$$${math}$$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => `$${math}$`)
}

function renderKatex(html: string): string {
  // Replace $$...$$ (display math) and $...$ (inline math)
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const katex = (window as any).katex
    if (!katex) return html

    html = html.replace(/\$\$([\s\S]*?)\$\$/g, (_, math) => {
      try {
        return katex.renderToString(math, { displayMode: true, throwOnError: false })
      } catch {
        return `<span class="katex-error">$$${math}$$</span>`
      }
    })

    html = html.replace(/\$([^\n$]+?)\$/g, (_, math) => {
      try {
        return katex.renderToString(math, { displayMode: false, throwOnError: false })
      } catch {
        return `<span class="katex-error">$${math}$</span>`
      }
    })
  } catch {
    // KaTeX not loaded
  }
  return html
}

export function renderMarkdown(text: string): string {
  const preprocessed = preprocessMath(text)
  const html = marked.parse(preprocessed) as string
  const withMath = renderKatex(html)
  return DOMPurify.sanitize(withMath, {
    ADD_TAGS: ['math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'annotation'],
    ADD_ATTR: ['class', 'style', 'aria-hidden', 'focusable', 'role', 'xmlns'],
  })
}

export function renderPlain(text: string): string {
  return DOMPurify.sanitize(text.replace(/\n/g, '<br>'))
}
