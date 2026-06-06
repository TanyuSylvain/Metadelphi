import { useRef, useCallback, useEffect, RefObject } from 'react'

const BOTTOM_THRESHOLD_PX = 60

export function useSmartScroll(
  containerRef: RefObject<HTMLElement | null>,
  contentRef?: RefObject<HTMLElement | null>,
) {
  const autoFollow = useRef(true)
  const scrollFrame = useRef<number | null>(null)

  const isNearBottom = useCallback((el: HTMLElement) => (
    el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_THRESHOLD_PX
  ), [])

  const scrollElementToBottom = useCallback((el: HTMLElement) => {
    el.scrollTop = el.scrollHeight
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const updateAutoFollow = () => {
      scrollFrame.current = null
      autoFollow.current = isNearBottom(el)
    }

    const onScroll = () => {
      if (scrollFrame.current != null) {
        window.cancelAnimationFrame(scrollFrame.current)
      }
      scrollFrame.current = window.requestAnimationFrame(updateAutoFollow)
    }

    el.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      if (scrollFrame.current != null) {
        window.cancelAnimationFrame(scrollFrame.current)
        scrollFrame.current = null
      }
      el.removeEventListener('scroll', onScroll)
    }
  }, [containerRef, isNearBottom])

  useEffect(() => {
    const el = containerRef.current
    const content = contentRef?.current
    if (!el || !content || typeof ResizeObserver === 'undefined') return

    const observer = new ResizeObserver(() => {
      if (autoFollow.current) {
        scrollElementToBottom(el)
      }
    })

    observer.observe(content)
    return () => observer.disconnect()
  }, [containerRef, contentRef, scrollElementToBottom])

  const scrollToBottom = useCallback((force = false) => {
    const el = containerRef.current
    if (!el) return
    if (force || autoFollow.current || isNearBottom(el)) {
      autoFollow.current = true
      scrollElementToBottom(el)
    }
  }, [containerRef, isNearBottom, scrollElementToBottom])

  const resetScroll = useCallback(() => {
    autoFollow.current = true
    if (containerRef.current) {
      scrollElementToBottom(containerRef.current)
    }
  }, [containerRef, scrollElementToBottom])

  return { scrollToBottom, resetScroll }
}
