import { format, formatDistanceToNow } from "date-fns";

/**
 * Memformat angka desimal sebagai string mata uang sederhana (tanpa simbol).
 */
export function formatCurrency(jumlah, desimal = 2) {
  const angka = Number(jumlah);
  if (Number.isNaN(angka)) return "0.00";
  return angka.toFixed(desimal);
}

export function formatStatus(status) {
  if (!status) return "";
  const hurufKecil = status.toLowerCase().replace(/_/g, " ");
  return hurufKecil.replace(/\b\w/g, (huruf) => huruf.toUpperCase());
}

export function formatDateTime(isoString) {
  if (!isoString) return "—";
  try {
    return format(new Date(isoString), "MMM d, yyyy, h:mm:ss a");
  } catch {
    return String(isoString);
  }
}

export function formatRelativeTime(isoString) {
  if (!isoString) return "—";
  try {
    return formatDistanceToNow(new Date(isoString), { addSuffix: true });
  } catch {
    return String(isoString);
  }
}

export function truncate(teks, panjangMaks = 12) {
  if (!teks || teks.length <= panjangMaks) return teks || "";
  return `${teks.slice(0, panjangMaks)}…`;
}

export function getStatusColor(status) {
  if (!status) return "status-unknown";
  const normal = String(status).toUpperCase().replace(/-/g, "_");
  const peta = {
    INITIATED: "status-initiated",
    PENDING: "status-pending",
    CONFIRMED: "status-confirmed",
    SETTLED: "status-settled",
    FAILED: "status-failed",
    EXPIRED: "status-expired",
    ROLLED_BACK: "status-rolled_back"
  };
  return peta[normal] || "status-unknown";
}
