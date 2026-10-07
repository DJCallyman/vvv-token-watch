import '@testing-library/jest-dom'

// Some tests opt into the `node` jest environment (e.g. session.test.ts)
// where `window` is undefined. Only register DOM-dependent polyfills when
// a window is present.
if (typeof window !== 'undefined') {
  // Mock matchMedia for ThemeProvider (used in tests via renderWithProviders)
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(), // deprecated
      removeListener: jest.fn(), // deprecated
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  })

  // Recharts' ResponsiveContainer requires ResizeObserver in jsdom.
  if (!('ResizeObserver' in window)) {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    Object.defineProperty(window, 'ResizeObserver', {
      writable: true,
      configurable: true,
      value: ResizeObserverMock,
    })
    ;(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverMock
  }
}
