import { useState } from "react";
import { KeyRound, UserPlus } from "lucide-react";
import { createSignature, generateKeypair } from "../utils/crypto";
import { agentAPI } from "../services/api";
import { useAgentStore } from "../store/agentStore";

export default function CreateAgent() {
  const [idAgen, setIdAgen] = useState("");
  const [saldoAwal, setSaldoAwal] = useState("100");
  const [kunciPublik, setKunciPublik] = useState("");
  const [kunciPrivat, setKunciPrivat] = useState("");
  const [memuat, setMemuat] = useState(false);
  const [pesan, setPesan] = useState("");

  const tambahDemoAgen = useAgentStore((s) => s.addDemoAgent);
  const ambilDaftarAgen = useAgentStore((s) => s.fetchAgents);

  function tanganiPasanganKunci() {
    const pasangan = generateKeypair();
    setKunciPublik(pasangan.publicKey);
    setKunciPrivat(pasangan.privateKey);
    setPesan("");
  }

  async function tanganiKirim(event) {
    event.preventDefault();
    setPesan("");
    if (!idAgen.trim()) {
      setPesan("ID agen wajib diisi.");
      return;
    }
    const angkaSaldo = Number(saldoAwal);
    if (!Number.isFinite(angkaSaldo) || angkaSaldo <= 0) {
      setPesan("Saldo awal harus lebih dari 0.");
      return;
    }
    if (!kunciPrivat || !kunciPublik) {
      setPesan("Klik «Hasilkan pasangan kunci» terlebih dahulu.");
      return;
    }
    setMemuat(true);
    try {
      const capWaktu = new Date().toISOString();
      const muatanTanpaTanda = {
        agent_id: idAgen.trim(),
        initial_balance: angkaSaldo,
        public_key: kunciPublik,
        timestamp: capWaktu
      };
      const tanda = createSignature(kunciPrivat, muatanTanpaTanda);
      const respons = await agentAPI.create({ ...muatanTanpaTanda, signature: tanda });
      tambahDemoAgen({
        agent_id: respons.agent_id,
        id: respons.id,
        public_key: kunciPublik,
        privateKey: kunciPrivat,
        balance: String(respons.balance)
      });
      setPesan(`Agen «${respons.agent_id}» berhasil dibuat.`);
      setIdAgen("");
      setSaldoAwal("100");
      setKunciPublik("");
      setKunciPrivat("");
      await ambilDaftarAgen();
    } catch (kesalahan) {
      setPesan(kesalahan.message || "Gagal membuat agen.");
    } finally {
      setMemuat(false);
    }
  }

  return (
    <section className="card">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
        <UserPlus className="h-5 w-5 text-agentpay-400" aria-hidden />
        Buat agen
      </h2>
      <form onSubmit={tanganiKirim} className="space-y-4">
        <div>
          <label htmlFor="id-agen" className="mb-1 block text-sm font-medium text-slate-300">
            ID agen
          </label>
          <input
            id="id-agen"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white focus:border-agentpay-500 focus:outline-none focus:ring-1 focus:ring-agentpay-500"
            value={idAgen}
            onChange={(e) => setIdAgen(e.target.value)}
            placeholder="mis. alice"
            autoComplete="off"
          />
        </div>
        <div>
          <label htmlFor="saldo-awal" className="mb-1 block text-sm font-medium text-slate-300">
            Saldo awal
          </label>
          <input
            id="saldo-awal"
            type="number"
            min="0.00000001"
            step="any"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-agentpay-500 focus:outline-none focus:ring-1 focus:ring-agentpay-500"
            value={saldoAwal}
            onChange={(e) => setSaldoAwal(e.target.value)}
          />
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
          <p className="mb-2 text-xs text-slate-500">
            Kunci publik ditampilkan; kunci privat hanya dipakai di browser untuk menandatangani permintaan (demo).
          </p>
          <button
            type="button"
            className="btn-secondary w-full text-sm"
            onClick={tanganiPasanganKunci}
            aria-label="Hasilkan pasangan kunci Ed25519"
          >
            <KeyRound className="h-4 w-4" aria-hidden />
            Hasilkan pasangan kunci
          </button>
          {kunciPublik ? (
            <p className="mt-2 break-all font-mono text-xs text-agentpay-200" title={kunciPublik}>
              Pub: {kunciPublik.slice(0, 24)}…
            </p>
          ) : null}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={memuat} aria-busy={memuat}>
          {memuat ? "Menyimpan…" : "Buat agen"}
        </button>
        {pesan ? (
          <p
            className={`text-center text-sm ${pesan.startsWith("Agen") ? "text-emerald-400" : "text-rose-400"}`}
            role="status"
          >
            {pesan}
          </p>
        ) : null}
      </form>
    </section>
  );
}
