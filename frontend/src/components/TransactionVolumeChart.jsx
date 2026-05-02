import { useMemo } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function TransactionVolumeChart({ daftarTransaksi = [] }) {
  const dataGrafik = useMemo(() => {
    const peta = {};
    for (const txn of daftarTransaksi) {
      const s = String(txn.status || "UNKNOWN").toUpperCase();
      peta[s] = (peta[s] || 0) + 1;
    }
    return Object.entries(peta).map(([nama, jumlah]) => ({ nama, jumlah }));
  }, [daftarTransaksi]);

  if (dataGrafik.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-sm text-slate-500">
        Grafik muncul setelah ada transaksi.
      </div>
    );
  }

  return (
    <div className="h-52 w-full" aria-label="Grafik jumlah transaksi per status">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={dataGrafik} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="nama" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={{ stroke: "#334155" }} />
          <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={{ stroke: "#334155" }} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Bar dataKey="jumlah" fill="#3b82f6" radius={[6, 6, 0, 0]} name="Jumlah" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
