export function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">Wake Testset</div>
        <button className="nav-item active">Dashboard</button>
        <button className="nav-item">Import Wizard</button>
        <button className="nav-item">Assets</button>
        <button className="nav-item">Dataset Builder</button>
        <button className="nav-item">Versions / Export</button>
        <button className="nav-item">Settings</button>
      </aside>
      <section className="content">
        <h1>KWS Testset Platform</h1>
        <p>React UI scaffold is ready.</p>
      </section>
    </main>
  );
}
