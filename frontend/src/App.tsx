import { useState } from 'react';
import { AssetsPage } from './pages/AssetsPage';
import { DashboardPage } from './pages/DashboardPage';
import { DatasetBuilderPage } from './pages/DatasetBuilderPage';
import { GenerationPage } from './pages/GenerationPage';
import { ImportPage } from './pages/ImportPage';
import { SettingsPage } from './pages/SettingsPage';
import { VersionsPage } from './pages/VersionsPage';

type PageKey = 'dashboard' | 'import' | 'assets' | 'generation' | 'builder' | 'versions' | 'settings';

const pages: Array<{ key: PageKey; label: string }> = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'import', label: 'Import Wizard' },
  { key: 'assets', label: 'Assets' },
  { key: 'generation', label: 'Generation' },
  { key: 'builder', label: 'Dataset Builder' },
  { key: 'versions', label: 'Versions / Export' },
  { key: 'settings', label: 'Settings' }
];

function renderPage(page: PageKey) {
  if (page === 'dashboard') return <DashboardPage />;
  if (page === 'import') return <ImportPage />;
  if (page === 'assets') return <AssetsPage />;
  if (page === 'generation') return <GenerationPage />;
  if (page === 'builder') return <DatasetBuilderPage />;
  if (page === 'versions') return <VersionsPage />;
  return <SettingsPage />;
}

export function App() {
  const [page, setPage] = useState<PageKey>('dashboard');
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">Wake Testset</div>
        {pages.map((item) => (
          <button key={item.key} className={`nav-item ${page === item.key ? 'active' : ''}`} onClick={() => setPage(item.key)}>
            {item.label}
          </button>
        ))}
      </aside>
      <section className="content">{renderPage(page)}</section>
    </main>
  );
}
