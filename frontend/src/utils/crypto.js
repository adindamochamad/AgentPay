/**
 * Kriptografi Ed25519 di browser agar cocok dengan backend (app/crypto.py).
 *
 * Catatan penting: di produksi, kunci privat tidak boleh tinggal di browser;
 * gunakan wallet perangkat keras / penandatanganan sisi server. Untuk demo
 * hackathon, penandatanganan di sini memenuhi verifikasi FastAPI.
 */
import { getPublicKey, sign, utils } from "@noble/ed25519";

function bytesKeBase64(bytes) {
  let biner = "";
  bytes.forEach((byte) => {
    biner += String.fromCharCode(byte);
  });
  return btoa(biner);
}

function base64KeBytes(teksBase64) {
  const biner = atob(teksBase64);
  const keluaran = new Uint8Array(biner.length);
  for (let indeks = 0; indeks < biner.length; indeks += 1) {
    keluaran[indeks] = biner.charCodeAt(indeks);
  }
  return keluaran;
}

/** Menyalin objek dan mengurutkan kunci di setiap level (setara json.dumps sort_keys di Python). */
function urutkanObjekRekursif(nilai) {
  if (nilai === null || typeof nilai !== "object") {
    return nilai;
  }
  if (Array.isArray(nilai)) {
    return nilai.map(urutkanObjekRekursif);
  }
  const hasil = {};
  for (const kunci of Object.keys(nilai).sort()) {
    hasil[kunci] = urutkanObjekRekursif(nilai[kunci]);
  }
  return hasil;
}

/** String kanonik sama seperti Ed25519Crypto.verify_signature di backend. */
export function serialisasiKanonikKeString(muatanTanpaTanda) {
  const terurut = urutkanObjekRekursif(muatanTanpaTanda);
  /* Tanpa spasi tambahan — setara separators=(',', ':') di Python */
  return JSON.stringify(terurut);
}

/**
 * Menghasilkan pasangan kunci Ed25519 produksi (Base64 raw 32 byte, selaras backend `app/crypto.py`).
 * Menggunakan `@noble/ed25519` — kriptografi nyata, bukan placeholder.
 */
export function generateKeypair() {
  const kunciPrivat = utils.randomPrivateKey();
  const kunciPublik = getPublicKey(kunciPrivat);
  return {
    privateKey: bytesKeBase64(kunciPrivat),
    publicKey: bytesKeBase64(kunciPublik)
  };
}

/**
 * Membuat tanda Ed25519 atas muatan kanonik (tanpa field `signature`), verifikasi sama dengan backend.
 */
export function createSignature(kunciPrivatBase64, muatanTanpaTanda) {
  const teksPesan = serialisasiKanonikKeString(muatanTanpaTanda);
  const bytePesan = new TextEncoder().encode(teksPesan);
  const bytePrivat = base64KeBytes(kunciPrivatBase64);
  const byteTanda = sign(bytePesan, bytePrivat);
  return bytesKeBase64(byteTanda);
}

export function generateNonce() {
  return crypto.randomUUID();
}
