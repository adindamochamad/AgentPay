import { useState } from "react";
import { RefreshCw, User, Wallet } from "lucide-react";
import { formatCurrency, truncate } from "../utils/formatters";
import { useAgentStore } from "../store/agentStore";

export default function AgentCard({ agent, onSelect, selected }) {
  const [memuatSaldo, setMemuatSaldo] = useState(false);
  const ambilSaldo = useAgentStore((s) => s.fetchAgentBalance);

  async function tanganiSegarkan(event) {
    event.stopPropagation();
    setMemuatSaldo(true);
    try {
      await ambilSaldo(agent.agent_id);
    } finally {
      setMemuatSaldo(false);
    }
  }

  const dipilih = selected?.agent_id === agent.agent_id;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(agent)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect?.(agent);
        }
      }}
      aria-label={`Pilih agen ${agent.agent_id}`}
      className={`card card-hover w-full cursor-pointer text-left ${dipilih ? "ring-2 ring-agentpay-500" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-agentpay-600/30 text-agentpay-200">
            <User className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <p className="font-mono text-lg font-bold text-white">{agent.agent_id}</p>
            <p className="mt-0.5 font-mono text-xs text-slate-400" title={agent.public_key}>
              {truncate(agent.public_key || "—", 20)}
            </p>
          </div>
        </div>
        <button
          type="button"
          className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
          onClick={tanganiSegarkan}
          disabled={memuatSaldo}
          aria-label={`Segarkan saldo ${agent.agent_id}`}
        >
          <RefreshCw className={`h-4 w-4 ${memuatSaldo ? "animate-spin" : ""}`} aria-hidden />
        </button>
      </div>
      <div className="mt-4 flex items-center gap-2 border-t border-slate-800 pt-4">
        <Wallet className="h-5 w-5 text-agentpay-400" aria-hidden />
        <span className="text-2xl font-bold tracking-tight text-white">
          ${formatCurrency(agent.balance)}
        </span>
      </div>
    </div>
  );
}
