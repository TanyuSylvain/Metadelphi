import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import katex from 'katex'

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

interface MathPlaceholders {
  values: string[]
}

function preprocessMath(text: string): { text: string; placeholders: MathPlaceholders } {
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

export function renderMarkdown(text: string): string {
  const { text: preprocessed, placeholders } = preprocessMath(text)
  const html = marked.parse(preprocessed) as string
  const withMath = restoreMath(html, placeholders)
  return DOMPurify.sanitize(withMath, {
    ADD_TAGS: ['math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'annotation'],
    ADD_ATTR: ['class', 'style', 'aria-hidden', 'focusable', 'role', 'xmlns'],
  })
}

export function renderPlain(text: string): string {
  return DOMPurify.sanitize(text.replace(/\n/g, '<br>'))
}
