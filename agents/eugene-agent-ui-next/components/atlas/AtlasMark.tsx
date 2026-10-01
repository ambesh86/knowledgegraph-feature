/**
 * Atlas brand mark — an original geometric glyph: three converging nodes
 * (ask · research · decide) over a grounded baseline. Inherits the brand red.
 */
export function AtlasMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-label="Atlas">
      <rect width="32" height="32" rx="8" fill="#e11d2a" />
      <circle cx="16" cy="9" r="3" fill="#fff" />
      <circle cx="9" cy="22" r="3" fill="#fff" fillOpacity="0.85" />
      <circle cx="23" cy="22" r="3" fill="#fff" fillOpacity="0.85" />
      <path d="M16 11.5 L10 20 M16 11.5 L22 20 M11 22.5 H21" stroke="#fff" strokeWidth="1.6"
        strokeLinecap="round" strokeOpacity="0.9" />
    </svg>
  );
}
