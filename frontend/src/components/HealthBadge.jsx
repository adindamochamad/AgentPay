export default function HealthBadge({ status }) {
  const sehat = status === "ok";
  const memuat = status === "memeriksa";
  const kelasWarna = sehat ? "bg-emerald-600" : memuat ? "bg-amber-600" : "bg-rose-600";
  const teks = sehat ? "API OK" : memuat ? "Memeriksa…" : "API offline";
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold text-white ${kelasWarna}`}
      role="status"
      aria-live="polite"
    >
      {teks}
    </span>
  );
}
