class AgentNotFoundException(Exception):
    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent dengan agent_id '{agent_id}' tidak ditemukan")


class InsufficientBalanceException(Exception):
    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Saldo agent '{agent_id}' tidak mencukupi")


class InvalidTransactionStateException(Exception):
    def __init__(self, status_saat_ini: str, status_diharapkan: str) -> None:
        super().__init__(
            f"Status transaksi '{status_saat_ini}' tidak valid, harus '{status_diharapkan}'"
        )


class DuplicateAgentException(Exception):
    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent dengan agent_id '{agent_id}' sudah ada")


class InvalidStateTransition(Exception):
    """Dipakai ketika transisi status transaksi tidak diizinkan oleh mesin status."""

    def __init__(self, dari_status: str, ke_status: str) -> None:
        super().__init__(
            f"Transisi status tidak valid: '{dari_status}' → '{ke_status}' tidak diizinkan"
        )


class TransactionExpiredException(Exception):
    def __init__(self, id_transaksi: str) -> None:
        super().__init__(f"Transaksi '{id_transaksi}' sudah kedaluwarsa (timeout)")


class RateLimitExceededException(Exception):
    def __init__(self, agent_id: str, batas_per_jam: int) -> None:
        super().__init__(
            f"Agent '{agent_id}' melebihi batas {batas_per_jam} transaksi per jam"
        )


class InvalidAmountException(Exception):
    def __init__(self, pesan: str) -> None:
        super().__init__(pesan)


class SelfPaymentNotAllowedException(Exception):
    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Pembayaran ke diri sendiri tidak diizinkan untuk agent '{agent_id}'")
