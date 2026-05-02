import { formatStatus, getStatusColor } from "../utils/formatters";

export default function StatusBadge({ status }) {
  const kelasTambahan = getStatusColor(status);
  return <span className={`status-badge ${kelasTambahan}`}>{formatStatus(status)}</span>;
}
