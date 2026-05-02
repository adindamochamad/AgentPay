import { useCallback, useEffect, useState } from "react";
import { healthAPI } from "../services/api";

export function useHealth() {
  const [statusKesehatan, setStatusKesehatan] = useState("memeriksa");
  const [pesanKesalahan, setPesanKesalahan] = useState("");

  const periksaLagi = useCallback(async () => {
    setStatusKesehatan("memeriksa");
    setPesanKesalahan("");
    try {
      const data = await healthAPI.check();
      setStatusKesehatan(data.status === "ok" ? "ok" : "gagal");
    } catch (kesalahan) {
      setStatusKesehatan("gagal");
      setPesanKesalahan(kesalahan.message || "Backend tidak terjangkau");
    }
  }, []);

  useEffect(() => {
    periksaLagi();
  }, [periksaLagi]);

  return { statusKesehatan, pesanKesalahan, periksaLagi };
}
