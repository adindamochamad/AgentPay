import { lazy, Suspense, useEffect, useState } from "react";
import { Activity } from "lucide-react";
import AgentCard from "./AgentCard";
import CreateAgent from "./CreateAgent";
import CreateTransaction from "./CreateTransaction";
import TransactionList from "./TransactionList";
import { useAgentStore } from "../store/agentStore";
import { usePolling } from "../hooks/usePolling";
import { seedDemoData } from "../utils/seedDemo";

const PaymentFlow = lazy(() => import("./PaymentFlow"));
const TransactionVolumeChart = lazy(() => import("./TransactionVolumeChart"));

function JedaAlur() {
  return (
    <div className="card flex h-32 items-center justify-center text-slate-500">
      Memuat panel alur…
    </div>
  );
}

function JedaGrafik() {
  return (
    <div className="flex h-52 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-sm text-slate-500">
      Memuat grafik…
    </div>
  );
}

export default function Dashboard() {
  const [tabAktif, setTabAktif] = useState(true);

  const agents = useAgentStore((s) => s.agents);
  const transactions = useAgentStore((s) => s.transactions);
  const selectedAgent = useAgentStore((s) => s.selectedAgent);
  const selectedTransaction = useAgentStore((s) => s.selectedTransaction);
  const setSelectedAgent = useAgentStore((s) => s.setSelectedAgent);
  const setSelectedTransaction = useAgentStore((s) => s.setSelectedTransaction);
  const fetchTransactions = useAgentStore((s) => s.fetchTransactions);
  const refreshAllBalances = useAgentStore((s) => s.refreshAllBalances);
  const fetchAgents = useAgentStore((s) => s.fetchAgents);

  useEffect(() => {
    function tanganiVisibilitas() {
      setTabAktif(document.visibilityState === "visible");
    }
    tanganiVisibilitas();
    document.addEventListener("visibilitychange", tanganiVisibilitas);
    return () => document.removeEventListener("visibilitychange", tanganiVisibilitas);
  }, []);

  useEffect(() => {
    let hidup = true;
    (async () => {
      await seedDemoData();
      if (!hidup) return;
      await Promise.all([fetchAgents(), fetchTransactions()]);
    })();
    return () => {
      hidup = false;
    };
  }, [fetchAgents, fetchTransactions]);

  usePolling(
    () => {
      if (!tabAktif) return Promise.resolve();
      return fetchTransactions();
    },
    2000,
    tabAktif
  );

  usePolling(
    () => {
      if (!tabAktif) return Promise.resolve();
      return refreshAllBalances();
    },
    5000,
    tabAktif
  );

  return (
    <div className="space-y-8">
      <section className="card">
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-agentpay-400" aria-hidden />
          <h2 className="text-lg font-semibold text-white">Ringkasan volume</h2>
        </div>
        <Suspense fallback={<JedaGrafik />}>
          <TransactionVolumeChart daftarTransaksi={transactions} />
        </Suspense>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Agen & saldo</h2>
          <div className="space-y-3">
            {agents.length === 0 ? (
              <p className="text-sm text-slate-500">Belum ada agen. Buat agen atau jalankan semai demo.</p>
            ) : (
              agents.map((agen) => (
                <AgentCard
                  key={agen.agent_id}
                  agent={agen}
                  selected={selectedAgent}
                  onSelect={setSelectedAgent}
                />
              ))
            )}
          </div>
        </div>

        <div className="space-y-6">
          <CreateAgent />
          <CreateTransaction />
        </div>

        <div>
          <TransactionList
            limit={20}
            daftarTransaksi={transactions}
            transaksiTerpilih={selectedTransaction}
            onPilih={setSelectedTransaction}
          />
        </div>
      </div>

      <Suspense fallback={<JedaAlur />}>
        <PaymentFlow transaksi={selectedTransaction} />
      </Suspense>
    </div>
  );
}
