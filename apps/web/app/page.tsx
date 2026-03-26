// Root route — intentionally does not redirect to /workspace.
// /workspace is an internal admin tool, not exposed via the public domain.
// Public landing pages are served under /r/[slug].
export default function Home() {
  return null;
}