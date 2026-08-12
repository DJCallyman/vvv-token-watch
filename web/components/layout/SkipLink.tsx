'use client'

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only z-[100] rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
    >
      Skip to main content
    </a>
  )
}
