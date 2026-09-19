import { createClient } from '@supabase/supabase-js'

/**
 * Supabase client for frontend use.
 *
 * Only the PUBLISHABLE key is used here — it is safe to include in
 * client-side bundles. Never import or use the service-role key on
 * the frontend.
 *
 * Variables are injected at build time via Vite's `import.meta.env`.
 * They must be prefixed with VITE_ to be exposed to the browser.
 */
const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL as string) || ''
const supabasePublishableKey = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string) || ''

export const supabase = (() => {
  if (!supabaseUrl || !supabasePublishableKey) {
    return null
  }
  try {
    return createClient(supabaseUrl, supabasePublishableKey)
  } catch (err) {
    console.warn('[Supabase] Optional client initialization skipped:', err)
    return null
  }
})()
