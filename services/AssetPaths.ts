/**
 * Resolves a file from `public/` against Vite's configured base path.
 *
 * Root-absolute URLs ("/models/…") 404 whenever the app is hosted under a
 * sub-path (GitHub Pages project sites, reverse-proxied prefixes). Using
 * import.meta.env.BASE_URL keeps every asset resolvable in both setups.
 */
export function assetUrl(relativePath: string): string {
  const base = import.meta.env.BASE_URL || '/';
  return `${base.replace(/\/+$/, '')}/${relativePath.replace(/^\/+/, '')}`;
}
