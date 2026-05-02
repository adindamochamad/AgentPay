import { useMemo, useState } from "react";
import { Send } from "lucide-react";
import { createSignature, generateNonce } from "../utils/crypto";
import { transactionAPI } from "../services/api";
import { useAgentStore } from "../store/agentStore";
import { formatCurrency } from "../utils/formatters";

export default function CreateTransaction() {
  const demoAgents = useAgentStore((s) => s.demoAgents);
  const tambahTransaksi = useAgentStore((s) => s.addTransaction);
  const ambilTransaksi = useAgentStore((s) => s.fetchTransactions);
  const ambilAgen = useAgentStore((s) => s.fetchAgents);

  const [idPengirim, setIdPengirim] = useState("");
  const [idPenerima, setIdPenerima] = useState("");
  const [jumlah, setJumlah] = useState("10");
  const [memuat, setMemuat] = useState(false);
  const [pesan, setPesan] = useState("");

  const agenPengirim = useMemo(
    () => demoAgents.find((a) => a.agent_id === idPengirim),
    [demoAgents, idPengirim]
  );

  const saldoNumerik = Number(agenPengirim?.balance ?? 0);
  const jumlahNumerik = Number(jumlah);

  async function tanganiKirim(event) {
    event.preventDefault();
    setPesan("");
    if (!idPengirim || !idPenerima) {
      setPesan("Pilih pengirim dan penerima.");
      return;
    }
    if (idPengirim === idPenerima) {
      setPesan("Pengirim dan penerima tidak boleh sama.");
      return;
    }
    if (!agenPengirim?.privateKey) {
      setPesan("Pengirim harus dibuat lewat form agen (ada kunci privat lokal).");
      return;
    }
    if (!Number.isFinite(jumlahNumerik) || jumlahNumerik <= 0) {
      setPesan("Jumlah harus lebih dari 0.");
      return;
    }
    if (jumlahNumerik > saldoNumerik) {
      setPesan("Saldo pengirim tidak mencukupi.");
      return;
    }
    setMemuat(true);
    try {
      const nonce = generateNonce();
      const capWaktu = new Date().toISOString();
      const muatanTanpaTanda = {
        amount: jumlahNumerik,
        from_agent: idPengirim,
        nonce,
        timestamp: capWaktu,
        to_agent: idPenerima
      };
      const tanda = createSignature(agenPengirim.privateKey, muatanTanpaTanda);
      const respons = await transactionAPI.create({ ...muatanTanpaTanda, signature: tanda });
      tambahTransaksi(respons);
      setPesan(`Transaksi dibuat: ${respons.id} (${respons.status})`);
      setJumlah("10");
      await Promise.all([ambilTransaksi(), ambilAgen()]);
    } catch (kesalahan) {
      setPesan(kesalahan.message || "Gagal membuat transaksi.");
    } finally {
      setMemuat(false);
    }
  }

  const peringatanSaldo =
    agenPengirim && Number.isFinite(jumlahNumerik) && jumlahNumerik > saldoNumerik;

  return (
    <section className="card">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
        <Send className="h-5 w-5 text-agentpay-400" aria-hidden />
        Buat pembayaran
      </h2>
      <form onSubmit={tanganiKirim} className="space-y-4">
        <div>
          <label htmlFor="pengirim" className="mb-1 block text-sm font-medium text-slate-300">
            Pengirim
          </label>
          <select
            id="pengirim"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
            value={idPengirim}
            onChange={(e) => setIdPengirim(e.target.value)}
          >
            <option value="">— pilih —</option>
            {demoAgents.map((a) => (
              <option key={a.agent_id} value={a.agent_id}>
                {a.agent_id} (${formatCurrency(a.balance)})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="penerima" className="mb-1 block text-sm font-medium text-slate-300">
            Penerima
          </label>
          <select
            id="penerima"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
            value={idPenerima}
            onChange={(e) => setIdPenerima(e.target.value)}
          >
            <option value="">— pilih —</option>
            {demoAgents
              .filter((a) => a.agent_id !== idPengirim)
              .map((a) => (
                <option key={a.agent_id} value={a.agent_id}>
                  {a.agent_id}
                </option>
              ))}
          </select>
        </div>
        <div>
          <label htmlFor="jumlah" className="mb-1 block text-sm font-medium text-slate-300">
            Jumlah (USD setara)
          </label>
          <input
            id="jumlah"
            type="number"
            min="0.00000001"
            step="any"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
            value={jumlah}
            onChange={(e) => setJumlah(e.target.value)}
          />
          {agenPengirim ? (
            <p className="mt-1 text-xs text-slate-500">
              Saldo tersedia: ${formatCurrency(agenPengirim.balance)}
            </p>
          ) : null}
          {peringatanSaldo ? (
            <p className="mt-1 text-xs text-amber-400">Jumlah melebihi saldo pengirim.</p>
          ) : null}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={memuat}>
          {memuat ? "Memproses…" : "Kirim pembayaran"}
        </button>
        {pesan ? (
          <p
            className={`text-center text-sm ${pesan.startsWith("Transaksi") ? "text-emerald-400" : "text-rose-400"}`}
            role="status"
          >
            {pesan}
          </p>
        ) : null}
      </form>
    </section>
  );
}
