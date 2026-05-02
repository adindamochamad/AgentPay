import { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard";
import HealthBadge from "./components/HealthBadge";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { useHealth } from "./hooks/useHealth";

function App() {
  const { statusKesehatan, pesanKesalahan, periksaLagi } = useHealth();
  const [siap, setSiap] = useState(false);

  useEffect(() => {
    const id = window.requestAnimationFrame(() => setSiap(true));
    return () => window.cancelAnimationFrame(id);
  }, []);

  if (!siap) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Memuat AgentPay…
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-agentpay-950/30">
        <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-agentpay-600 font-bold text-white shadow-lg shadow-agentpay-900/50">
                AP
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-white">AgentPay</h1>
                <p className="text-xs text-slate-400">Infrastruktur pembayaran untuk agen AI — NandaHack 2026</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <HealthBadge status={statusKesehatan} />
              {statusKesehatan === "gagal" ? (
                <button type="button" className="btn-secondary text-sm" onClick={periksaLagi} aria-label="Coba sambungkan lagi ke API">
                  Coba lagi
                </button>
              ) : null}
            </div>
          </div>
        </header>

        {pesanKesalahan && statusKesehatan === "gagal" ? (
          <div
            className="border-b border-amber-900/40 bg-amber-950/50 px-4 py-3 text-center text-sm text-amber-200"
            role="alert"
          >
            {pesanKesalahan}
          </div>
        ) : null}

        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <Dashboard />
        </main>

        <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
          NandaHack 2026 · MIT Media Lab + HCLTech · AgentPay demo
        </footer>
      </div>
    </ErrorBoundary>
  );
}

export default App;
