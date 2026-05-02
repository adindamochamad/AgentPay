import { create } from "zustand";
import { agentAPI, transactionAPI } from "../services/api";

function gabungkanAgenUnik(daftarAgen, demoAgen, itemTransaksi) {
  const petaId = new Map();
  for (const agen of daftarAgen) {
    petaId.set(agen.agent_id, { ...agen });
  }
  for (const demo of demoAgen) {
    if (!petaId.has(demo.agent_id)) {
      petaId.set(demo.agent_id, {
        id: demo.id,
        agent_id: demo.agent_id,
        balance: demo.balance ?? "0",
        public_key: demo.public_key
      });
    } else {
      const ada = petaId.get(demo.agent_id);
      petaId.set(demo.agent_id, { ...ada, public_key: demo.public_key || ada.public_key });
    }
  }
  if (itemTransaksi) {
    for (const txn of itemTransaksi) {
      if (!petaId.has(txn.from_agent)) {
        petaId.set(txn.from_agent, {
          agent_id: txn.from_agent,
          balance: "0",
          public_key: ""
        });
      }
      if (!petaId.has(txn.to_agent)) {
        petaId.set(txn.to_agent, {
          agent_id: txn.to_agent,
          balance: "0",
          public_key: ""
        });
      }
    }
  }
  return Array.from(petaId.values());
}

export const useAgentStore = create((set, get) => ({
  agents: [],
  transactions: [],
  demoAgents: [],
  selectedAgent: null,
  selectedTransaction: null,
  loading: false,
  error: null,

  addDemoAgent: (agen) =>
    set((state) => ({
      demoAgents: [...state.demoAgents.filter((a) => a.agent_id !== agen.agent_id), agen]
    })),

  getDemoAgent: (idAgen) => get().demoAgents.find((a) => a.agent_id === idAgen),

  fetchAgents: async () => {
    const { demoAgents, transactions } = get();
    let itemTransaksi = transactions;
    if (!itemTransaksi?.length) {
      try {
        const daftar = await transactionAPI.list({ limit: 100, offset: 0 });
        itemTransaksi = daftar.items || [];
      } catch {
        itemTransaksi = [];
      }
    }
    const gabungan = gabungkanAgenUnik(get().agents, demoAgents, itemTransaksi);
    const agenTerbaru = [];
    for (const agen of gabungan) {
      try {
        const saldo = await agentAPI.getBalance(agen.agent_id);
        agenTerbaru.push({
          id: agen.id || saldo.agent_id,
          agent_id: saldo.agent_id,
          balance: saldo.balance,
          public_key: agen.public_key || ""
        });
      } catch {
        agenTerbaru.push({
          ...agen,
          balance: agen.balance ?? "?"
        });
      }
    }
    set({ agents: agenTerbaru });
  },

  fetchAgentBalance: async (idAgen) => {
    const saldo = await agentAPI.getBalance(idAgen);
    set((state) => ({
      agents: state.agents.map((a) =>
        a.agent_id === idAgen ? { ...a, balance: saldo.balance } : a
      )
    }));
    return saldo;
  },

  refreshAllBalances: async () => {
    const { agents, demoAgents } = get();
    const idUnik = new Set([
      ...agents.map((a) => a.agent_id),
      ...demoAgents.map((d) => d.agent_id)
    ]);
    const agenTerbaru = [];
    for (const idAgen of idUnik) {
      try {
        const saldo = await agentAPI.getBalance(idAgen);
        const demo = demoAgents.find((d) => d.agent_id === idAgen);
        const lama = agents.find((a) => a.agent_id === idAgen);
        agenTerbaru.push({
          id: lama?.id || saldo.agent_id,
          agent_id: saldo.agent_id,
          balance: saldo.balance,
          public_key: demo?.public_key || lama?.public_key || ""
        });
      } catch {
        const lama = agents.find((a) => a.agent_id === idAgen);
        if (lama) agenTerbaru.push(lama);
      }
    }
    if (agenTerbaru.length) set({ agents: agenTerbaru });
  },

  fetchTransactions: async (params = {}) => {
    const respons = await transactionAPI.list({ limit: params.limit ?? 50, offset: params.offset ?? 0, ...params });
    const item = respons.items || [];
    set((state) => {
      let transaksiTerpilih = state.selectedTransaction;
      if (transaksiTerpilih) {
        const cocok = item.find((t) => String(t.id) === String(transaksiTerpilih.id));
        if (cocok) transaksiTerpilih = { ...transaksiTerpilih, ...cocok };
      }
      return { transactions: item, error: null, selectedTransaction: transaksiTerpilih };
    });
    return respons;
  },

  addTransaction: (transaksi) =>
    set((state) => ({
      transactions: [transaksi, ...state.transactions.filter((t) => t.id !== transaksi.id)]
    })),

  updateTransaction: (idTransaksi, pembaruan) =>
    set((state) => ({
      transactions: state.transactions.map((t) =>
        String(t.id) === String(idTransaksi) ? { ...t, ...pembaruan } : t
      ),
      selectedTransaction:
        String(state.selectedTransaction?.id) === String(idTransaksi)
          ? { ...state.selectedTransaction, ...pembaruan }
          : state.selectedTransaction
    })),

  getTransaction: (idTransaksi) => get().transactions.find((t) => String(t.id) === String(idTransaksi)),

  setSelectedAgent: (agen) => set({ selectedAgent: agen }),
  setSelectedTransaction: (transaksi) => set({ selectedTransaction: transaksi }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  reset: () =>
    set({
      agents: [],
      transactions: [],
      demoAgents: [],
      selectedAgent: null,
      selectedTransaction: null,
      loading: false,
      error: null
    })
}));
