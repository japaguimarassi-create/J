/// <reference types="vite/client" />

interface GoogleIdentityResponse {
  credential: string
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(config: { client_id: string; callback: (response: GoogleIdentityResponse) => void }): void
          renderButton(element: HTMLElement, options: Record<string, string | number | boolean>): void
          disableAutoSelect(): void
        }
      }
    }
  }
}

export {}
