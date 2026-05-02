import { useAgentStore } from "../store/agentStore";
import { createSignature, generateKeypair, generateNonce } from "./crypto";
import { agentAPI, transactionAPI } from "../services/api";

const KUNCI_SEED_DEMO = "agentpay_demo_kunci_v1";

/**
 * Menyiapkan alice, bob, charlie di backend beserta kunci lokal (disimpan sessionStorage untuk demo).
 * Transaksi contoh opsional alice→bob agar grafik tidak kosong.
 */
export async function seedDemoData() {
  const snap = useAgentStore.getState();
  const mentah = sessionStorage.getItem(KUNCI_SEED_DEMO);
  if (mentah) {
    try {
      const daftar = JSON.parse(mentah);
      for (const agen of daftar) {
        snap.addDemoAgent(agen);
      }
    } catch {
      /* abaikan JSON rusak */
    }
    return;
  }

  const definisi = [
    { idAgen: "alice", saldo: 100 },
    { idAgen: "bob", saldo: 50 },
    { idAgen: "charlie", saldo: 25 }
  ];

  const agenTersimpan = [];

  for (const baris of definisi) {
    const pasangan = generateKeypair();
    const capWaktu = new Date().toISOString();
    const muatanTanpaTanda = {
      agent_id: baris.idAgen,
      initial_balance: baris.saldo,
      public_key: pasangan.publicKey,
      timestamp: capWaktu
    };
    try {
      const tanda = createSignature(pasangan.privateKey, muatanTanpaTanda);
      const respons = await agentAPI.create({ ...muatanTanpaTanda, signature: tanda });
      const entri = {
        agent_id: respons.agent_id,
        id: respons.id,
        public_key: pasangan.publicKey,
        privateKey: pasangan.privateKey,
        balance: String(respons.balance)
      };
      agenTersimpan.push(entri);
      snap.addDemoAgent(entri);
    } catch {
      /* ID bentrok atau backend down — lewati agen ini */
    }
  }

  if (agenTersimpan.length) {
    sessionStorage.setItem(KUNCI_SEED_DEMO, JSON.stringify(agenTersimpan));
  }

  const alice = agenTersimpan.find((a) => a.agent_id === "alice");
  const bob = agenTersimpan.find((a) => a.agent_id === "bob");
  if (alice?.privateKey && bob) {
    try {
      const nonce = generateNonce();
      const capWaktu = new Date().toISOString();
      const muatanTanpaTanda = {
        amount: 5,
        from_agent: "alice",
        nonce,
        timestamp: capWaktu,
        to_agent: "bob"
      };
      const tanda = createSignature(alice.privateKey, muatanTanpaTanda);
      await transactionAPI.create({ ...muatanTanpaTanda, signature: tanda });
    } catch {
      /* saldo tidak cukup atau limit — tidak wajib */
    }
  }
}
