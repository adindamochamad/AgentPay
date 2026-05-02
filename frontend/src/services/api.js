import axios from "axios";

const dasarUrlApi = import.meta.env.VITE_API_BASE_URL || "";

const klienApi = axios.create({
  baseURL: `${dasarUrlApi}/api/v1`,
  timeout: 10000,
  headers: { "Content-Type": "application/json" }
});

klienApi.interceptors.request.use((konfigurasi) => {
  konfigurasi.params = { ...(konfigurasi.params || {}), _ts: Date.now() };
  return konfigurasi;
});

klienApi.interceptors.response.use(
  (respons) => respons,
  (kesalahan) => {
    const status = kesalahan.response?.status;
    const data = kesalahan.response?.data;
    let pesan = kesalahan.message || "Kesalahan jaringan";
    if (data?.detail) {
      pesan = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
    if (import.meta.env.DEV) {
      console.error("[api]", status, pesan, data);
    }
    const galat = new Error(pesan);
    galat.status = status;
    galat.data = data;
    return Promise.reject(galat);
  }
);

const klienMentah = axios.create({
  baseURL: dasarUrlApi,
  timeout: 10000
});

export const agentAPI = {
  async create(muatan) {
    const respons = await klienApi.post("/agents", muatan);
    return respons.data;
  },
  async getBalance(idAgen) {
    const respons = await klienApi.get(`/agents/${encodeURIComponent(idAgen)}/balance`);
    return respons.data;
  },
  async getAll() {
    try {
      const respons = await klienApi.get("/agents");
      return respons.data;
    } catch {
      /* Backend saat ini tidak mengekspos GET /agents */
      return [];
    }
  }
};

export const transactionAPI = {
  async create(muatan, kunciIdempotensi) {
    const headers = kunciIdempotensi ? { "Idempotency-Key": kunciIdempotensi } : {};
    const respons = await klienApi.post("/transactions", muatan, { headers });
    return respons.data;
  },
  async getById(idTransaksi) {
    const respons = await klienApi.get(`/transactions/${idTransaksi}`);
    return respons.data;
  },
  async list(params = {}) {
    const respons = await klienApi.get("/transactions", { params });
    return respons.data;
  },
  async accept(idTransaksi, muatan) {
    const respons = await klienApi.post(`/transactions/${idTransaksi}/accept`, muatan);
    return respons.data;
  },
  async confirm(idTransaksi, muatan) {
    const respons = await klienApi.post(`/transactions/${idTransaksi}/confirm`, muatan);
    return respons.data;
  },
  async cancel(idTransaksi, muatan) {
    const respons = await klienApi.post(`/transactions/${idTransaksi}/cancel`, muatan);
    return respons.data;
  }
};

export const healthAPI = {
  async check() {
    const respons = await klienMentah.get("/health");
    return respons.data;
  }
};

export { klienApi };
