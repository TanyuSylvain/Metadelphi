import { useRef, useCallback, useEffect, RefObject } from 'react'

export function useSmartScroll(containerRef: RefObject<HTMLElement | null>) {
  const userScrolledUp = useRef(false)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const onWheel = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60
      if (!atBottom) userScrolledUp.current = true
    }

    const onScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60
      if (atBottom) userScrolledUp.current = false
    }

    el.addEventListener('wheel', onWheel, { passive: true })
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      el.removeEventListener('wheel', onWheel)
      el.removeEventListener('scroll', onScroll)
    }
  }, [containerRef])

  const scrollToBottom = useCallback((force = false) => {
    if (!containerRef.current) return
    if (force || !userScrolledUp.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [containerRef])

  const resetScroll = useCallback(() => {
    userScrolledUp.current = false
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [containerRef])

  return { scrollToBottom, resetScroll }
}
