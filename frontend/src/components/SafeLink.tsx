// Renders as a clickable link only for http(s) URLs. Any other scheme
// (javascript:, data:, vbscript:, ...) renders as inert text instead —
// last line of defense against a stored non-http(s) URL (e.g. a
// javascript: URI that slipped past backend validation) turning into
// script execution when a user clicks it.
function isHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value, window.location.href);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export default function SafeLink({
  href,
  children,
  className,
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  if (!isHttpUrl(href)) {
    return <span className={className}>{children}</span>;
  }
  return (
    <a href={href} target="_blank" rel="noreferrer" className={className}>
      {children}
    </a>
  );
}
