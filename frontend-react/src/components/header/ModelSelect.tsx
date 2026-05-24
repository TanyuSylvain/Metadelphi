import { useMemo } from 'react'
import { Select } from 'antd'
import type { Model } from '../../types/models'

interface Props {
  models: Model[]
  value: string
  onChange: (modelId: string) => void
  imageMode?: boolean
  disabled?: boolean
  configuredProviders?: string[] | null
}

export default function ModelSelect({
  models,
  value,
  onChange,
  imageMode = false,
  disabled = false,
  configuredProviders = null,
}: Props) {
  const options = useMemo(() => {
    const filtered = models.filter((m) => {
      if (imageMode && !m.is_image_model) return false
      if (!imageMode && m.is_image_model) return false
      if (configuredProviders && !configuredProviders.includes(m.provider)) return false
      return true
    })

    const byProvider: Record<string, Model[]> = {}
    for (const m of filtered) {
      if (!byProvider[m.provider_name]) byProvider[m.provider_name] = []
      byProvider[m.provider_name].push(m)
    }

    return Object.entries(byProvider).map(([providerName, providerModels]) => ({
      label: providerName,
      options: providerModels.map((m) => ({
        value: m.model_ref,
        label: m.model_name,
        title: m.description,
        searchLabel: `${m.provider_name} ${m.model_name} ${m.model_id}`,
      })),
    }))
  }, [models, imageMode, configuredProviders])

  return (
    <Select
      value={value || undefined}
      onChange={onChange}
      options={options}
      placeholder="Select a model"
      disabled={disabled}
      style={{ minWidth: 200 }}
      showSearch
      optionFilterProp="searchLabel"
      size="middle"
    />
  )
}
