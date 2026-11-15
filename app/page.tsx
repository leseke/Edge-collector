export default function HomePage() {
  return (
    <main className="legacy-shell">
      <iframe
        className="legacy-frame"
        src="/legacy/index.html"
        title="EDGE — Marché observé"
        loading="eager"
        allow="clipboard-read; clipboard-write"
      />
    </main>
  );
}
