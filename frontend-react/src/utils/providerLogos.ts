import deepseekLogo from '../../../frontend/src/assets/logos/deepseek.png'
import geminiLogo from '../../../frontend/src/assets/logos/gemini.png'
import minimaxLogo from '../../../frontend/src/assets/logos/minimax.png'
import mistralLogo from '../../../frontend/src/assets/logos/mistral.png'
import openaiLogo from '../../../frontend/src/assets/logos/openai.png'
import qwenLogo from '../../../frontend/src/assets/logos/qwen.png'
import zhipuLogo from '../../../frontend/src/assets/logos/zhipu.png'

const PROVIDER_LOGOS: Record<string, string> = {
  deepseek: deepseekLogo,
  gemini: geminiLogo,
  minimax: minimaxLogo,
  mistral: mistralLogo,
  openai: openaiLogo,
  qwen: qwenLogo,
  zhipu: zhipuLogo,
}

export function getProviderKey(modelId: string): string | null {
  const lower = modelId.toLowerCase()
  if (lower.includes('deepseek')) return 'deepseek'
  if (lower.includes('gemini')) return 'gemini'
  if (lower.includes('minimax')) return 'minimax'
  if (lower.includes('mistral')) return 'mistral'
  if (lower.includes('gpt') || lower.includes('openai')) return 'openai'
  if (lower.includes('qwen') || lower.includes('dashscope')) return 'qwen'
  if (lower.includes('glm') || lower.includes('chatglm') || lower.includes('zhipu')) return 'zhipu'
  return null
}

export function getProviderLogoSrc(modelId: string): string | null {
  const providerKey = getProviderKey(modelId)
  return providerKey ? PROVIDER_LOGOS[providerKey] ?? null : null
}
