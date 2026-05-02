import { memo } from "react";
import { ArrowRight, CheckCircle, Clock, XCircle } from "lucide-react";
import { formatCurrency, formatRelativeTime } from "../utils/formatters";
import StatusBadge from "./StatusBadge";

function ikonStatus(status) {
  const s = String(status || "").toUpperCase();
  if (s === "SETTLED") return <CheckCircle className="h-5 w-5 text-emerald-400" aria-hidden />;
  if (s === "FAILED" || s === "EXPIRED" || s === "ROLLED_BACK") {
    return <XCircle className="h-5 w-5 text-rose-400" aria-hidden />;
  }
  return <Clock className="h-5 w-5 text-amber-400" aria-hidden />;
}

const BarisTransaksi = memo(function BarisTransaksi({ transaksi, dipilih, onPilih }) {
  return (
    <button
      type="button"
      onClick={() => onPilih(transaksi)}
      aria-label={`Transaksi ${transaksi.id} status ${transaksi.status}`}
      className={`flex w-full flex-col gap-2 border-b border-slate-800/80 px-3 py-3 text-left transition hover:bg-slate-800/50 sm:flex-row sm:items-center sm:justify-between ${
        dipilih ? "bg-agentpay-950/40" : ""
      }`}
    >
      <div className="flex items-center gap-3">
        {ikonStatus(transaksi.status)}
        <div>
          <p className="flex flex-wrap items-center gap-2 font-mono text-sm text-slate-200">
            <span>{transaksi.from_agent}</span>
            <ArrowRight className="inline h-4 w-4 text-slate-500" aria-hidden />
            <span>{transaksi.to_agent}</span>
          </p>
          <p className="text-xs text-slate-500">{formatRelativeTime(transaksi.created_at)}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 pl-8 sm:pl-0">
        <span className="font-semibold text-white">${formatCurrency(transaksi.amount)}</span>
        <StatusBadge status={transaksi.status} />
      </div>
    </button>
  );
});

export default function TransactionList({ limit = 10, daftarTransaksi = [], transaksiTerpilih, onPilih }) {
  const potong = daftarTransaksi.slice(0, limit);

  return (
    <section className="card flex max-h-[480px] flex-col">
      <header className="mb-3 flex items-center justify-between border-b border-slate-800 pb-3">
        <h2 className="text-lg font-semibold text-white">Transaksi terbaru</h2>
        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
          {daftarTransaksi.length} total
        </span>
      </header>
      <div className="scrollbar-slim min-h-0 flex-1 overflow-y-auto rounded-lg border border-slate-800/60 bg-slate-950/40">
        {potong.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">Belum ada transaksi. Buat pembayaran untuk melihat riwayat.</p>
        ) : (
          potong.map((txn) => (
            <BarisTransaksi
              key={txn.id}
              transaksi={txn}
              dipilih={String(transaksiTerpilih?.id) === String(txn.id)}
              onPilih={onPilih}
            />
          ))
        )}
      </div>
    </section>
  );
}
