"""Utilitas kriptografi Ed25519 untuk autentikasi agen."""

from __future__ import annotations

import base64
import json
from typing import Any, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def serialisasi_kanonik(muatan: dict[str, Any]) -> str:
    """Serialisasi JSON kanonik untuk penandatanganan (kunci terurut, tanpa spasi)."""
    return json.dumps(muatan, sort_keys=True, separators=(",", ":"))


class Ed25519Crypto:
    """Utilitas tanda Ed25519 untuk autentikasi agen."""

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """
        Menghasilkan pasangan kunci Ed25519 baru.

        Returns:
            Tuple (private_key_base64, public_key_base64).
        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        return (
            base64.b64encode(private_bytes).decode("utf-8"),
            base64.b64encode(public_bytes).decode("utf-8"),
        )

    @staticmethod
    def sign_message(private_key_base64: str, message: dict[str, Any]) -> str:
        """
        Menandatangani pesan dengan kunci privat.

        Args:
            private_key_base64: Kunci privat terenkode Base64.
            message: Kamus yang akan ditandatangani (akan diserialkan secara kanonik).

        Returns:
            Tanda terenkode Base64.
        """
        canonical_message = serialisasi_kanonik(message)

        private_bytes = base64.b64decode(private_key_base64)
        private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)

        signature = private_key.sign(canonical_message.encode("utf-8"))
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def verify_signature(public_key_base64: str, message: dict[str, Any], signature_base64: str) -> bool:
        """
        Memverifikasi tanda pesan.

        Args:
            public_key_base64: Kunci publik terenkode Base64.
            message: Kamus yang ditandatangani (nilai harus sama dengan saat penandatanganan).
            signature_base64: Tanda terenkode Base64.

        Returns:
            True jika tanda valid, False jika tidak.
        """
        try:
            canonical_message = serialisasi_kanonik(message)

            public_bytes = base64.b64decode(public_key_base64)
            public_key = Ed25519PublicKey.from_public_bytes(public_bytes)

            signature = base64.b64decode(signature_base64)

            public_key.verify(signature, canonical_message.encode("utf-8"))
            return True
        except Exception:
            return False
