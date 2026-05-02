import { useCallback, useEffect, useState } from "react";
import { Check, Circle, Loader2 } from "lucide-react";
import { createSignature, generateNonce } from "../utils/crypto";
import { transactionAPI } from "../services/api";
import { useAgentStore } from "../store/agentStore";
import { formatCurrency, formatStatus } from "../utils/formatters";
import StatusBadge from "./StatusBadge";

const langkahAlur = [
  { kunci: "INITIATED", judul: "Dibuat", deskripsi: "Dana pengirim dikunci" },
  { kunci: "PENDING", judul: "Diterima", deskripsi: "Penerima menyetujui escrow" },
  { kunci: "CONFIRMED", judul: "Dikonfirmasi", deskripsi: "Pengirim mengonfirmasi" },
  { kunci: "SETTLED", judul: "Selesai", deskripsi: "Dana ditransfer ke penerima" }
];

function indeksStatus(status) {
  const s = String(status || "").toUpperCase();
  if (s === "SETTLED") return 3;
  if (s === "CONFIRMED") return 2;
  if (s === "PENDING") return 1;
  if (s === "INITIATED") return 0;
  return -1;
}

export default function PaymentFlow({ transaksi }) {
  const [detail, setDetail] = useState(transaksi);
  const [memuat, setMemuat] = useState(false);
  const [pesanGalat, setPesanGalat] = useState("");

  const demoAgents = useAgentStore((s) => s.demoAgents);
  const perbaruiTransaksi = useAgentStore((s) => s.updateTransaction);
  const ambilTransaksi = useAgentStore((s) => s.fetchTransactions);
  const ambilAgen = useAgentStore((s) => s.fetchAgents);
  const setTransaksiTerpilih = useAgentStore((s) => s.setSelectedTransaction);

  const muatDetail = useCallback(async () => {
    if (!transaksi?.id) return;
    try {
      const data = await transactionAPI.getById(transaksi.id);
      setDetail(data);
      perbaruiTransaksi(transaksi.id, data);
      setTransaksiTerpilih(data);
    } catch {
      setDetail(transaksi);
    }
  }, [transaksi, perbaruiTransaksi, setTransaksiTerpilih]);

  useEffect(() => {
    setDetail(transaksi);
  }, [transaksi]);

  useEffect(() => {
    if (!transaksi?.id) return undefined;
    const idTimer = window.setInterval(() => {
      muatDetail();
    }, 2500);
    return () => window.clearInterval(idTimer);
  }, [transaksi?.id, muatDetail]);

  if (!transaksi?.id) {
    return (
      <section className="card border-dashed border-slate-700 text-center text-slate-500">
        Pilih sebuah transaksi di daftar untuk menjalankan alur pembayaran.
      </section>
    );
  }

  const statusAtas = String(detail?.status || "").toUpperCase();
  const indeksAktif = indeksStatus(statusAtas);
  const agenPenerima = demoAgents.find((a) => a.agent_id === detail.to_agent);
  const agenPengirim = demoAgents.find((a) => a.agent_id === detail.from_agent);

  async function tandaTanganDanKirim(peran) {
    setPesanGalat("");
    setMemuat(true);
    try {
      const nonce = generateNonce();
      const capWaktu = new Date().toISOString();
      const idAgen = peran === "penerima" ? detail.to_agent : detail.from_agent;
      const agen = peran === "penerima" ? agenPenerima : agenPengirim;
      if (!agen?.privateKey) {
        throw new Error(
          `Kunci privat ${idAgen} tidak ada di sesi ini — buat ulang agen atau impor demo.`
        );
      }
      const muatanTanpaTanda = {
        agent_id: idAgen,
        nonce,
        timestamp: capWaktu,
        transaction_id: detail.id
      };
      const tanda = createSignature(agen.privateKey, muatanTanpaTanda);
      const tubuh = { ...muatanTanpaTanda, signature: tanda };
      let respons;
      if (peran === "penerima") {
        respons = await transactionAPI.accept(detail.id, tubuh);
      } else {
        respons = await transactionAPI.confirm(detail.id, tubuh);
      }
      setDetail(respons);
      perbaruiTransaksi(detail.id, respons);
      setTransaksiTerpilih(respons);
      await Promise.all([ambilTransaksi(), ambilAgen()]);
    } catch (kesalahan) {
      setPesanGalat(kesalahan.message || "Aksi gagal.");
    } finally {
      setMemuat(false);
    }
  }

  async function tanganiBatal() {
    setPesanGalat("");
    const agen =
      agenPengirim?.privateKey ? agenPengirim : agenPenerima?.privateKey ? agenPenerima : null;
    if (!agen?.privateKey) {
      setPesanGalat("Butuh kunci privat pengirim atau penerima di browser.");
      return;
    }
    setMemuat(true);
    try {
      const nonce = generateNonce();
      const capWaktu = new Date().toISOString();
      const muatanTanpaTanda = {
        agent_id: agen.agent_id,
        nonce,
        reason: "Dibatalkan dari dashboard demo",
        timestamp: capWaktu,
        transaction_id: detail.id
      };
      const tanda = createSignature(agen.privateKey, muatanTanpaTanda);
      const respons = await transactionAPI.cancel(detail.id, { ...muatanTanpaTanda, signature: tanda });
      setDetail(respons);
      perbaruiTransaksi(detail.id, respons);
      await Promise.all([ambilTransaksi(), ambilAgen()]);
    } catch (kesalahan) {
      setPesanGalat(kesalahan.message || "Batal gagal.");
    } finally {
      setMemuat(false);
    }
  }

  const bisaTerima = statusAtas === "INITIATED";
  const bisaKonfirmasi = statusAtas === "PENDING";
  const selesai = statusAtas === "SETTLED";
  const terminalBatal = ["SETTLED", "FAILED", "EXPIRED", "ROLLED_BACK"].includes(statusAtas);

  return (
    <section className="card">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Alur pembayaran</h2>
          <p className="font-mono text-xs text-slate-500">{String(detail.id)}</p>
        </div>
        <StatusBadge status={detail.status} />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
        {langkahAlur.map((langkah, indeks) => {
          const selesaiLangkah = indeksAktif > indeks || (indeks === 3 && statusAtas === "SETTLED");
          const aktif = indeks === indeksAktif && !selesai;
          return (
            <div
              key={langkah.kunci}
              className={`relative rounded-lg border p-3 ${
                selesaiLangkah
                  ? "border-emerald-600/50 bg-emerald-950/30"
                  : aktif
                    ? "border-agentpay-500 bg-agentpay-950/40"
                    : "border-slate-800 bg-slate-950/40"
              }`}
            >
              <div className="mb-1 flex items-center gap-2">
                {selesaiLangkah ? (
                  <Check className="h-4 w-4 text-emerald-400" aria-hidden />
                ) : (
                  <Circle
                    className={`h-4 w-4 ${aktif ? "text-agentpay-400" : "text-slate-600"}`}
                    aria-hidden
                  />
                )}
                <span className="font-medium text-white">{langkah.judul}</span>
              </div>
              <p className="text-xs text-slate-400">{langkah.deskripsi}</p>
            </div>
          );
        })}
      </div>

      <div className="mb-6 grid gap-2 rounded-lg bg-slate-950/50 p-4 font-mono text-sm text-slate-300">
        <p>
          <span className="text-slate-500">Dari</span> {detail.from_agent}
        </p>
        <p>
          <span className="text-slate-500">Ke</span> {detail.to_agent}
        </p>
        <p>
          <span className="text-slate-500">Jumlah</span> ${formatCurrency(detail.amount)}
        </p>
        <p>
          <span className="text-slate-500">Status</span> {formatStatus(detail.status)}
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        {bisaTerima ? (
          <button
            type="button"
            className="btn-success"
            disabled={memuat}
            onClick={() => tandaTanganDanKirim("penerima")}
            aria-label="Terima pembayaran sebagai penerima"
          >
            {memuat ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            Terima (penerima)
          </button>
        ) : null}
        {bisaKonfirmasi ? (
          <button
            type="button"
            className="btn-primary"
            disabled={memuat}
            onClick={() => tandaTanganDanKirim("pengirim")}
            aria-label="Konfirmasi sebagai pengirim"
          >
            {memuat ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            Konfirmasi (pengirim)
          </button>
        ) : null}
        {!terminalBatal && (bisaTerima || bisaKonfirmasi) ? (
          <button
            type="button"
            className="btn-danger"
            disabled={memuat}
            onClick={tanganiBatal}
            aria-label="Batalkan transaksi"
          >
            Batalkan
          </button>
        ) : null}
        {selesai ? (
          <span className="btn btn-secondary cursor-default opacity-80">Selesai</span>
        ) : null}
      </div>

      {pesanGalat ? (
        <p className="mt-3 text-sm text-rose-400" role="alert">
          {pesanGalat}
        </p>
      ) : null}
    </section>
  );
}
