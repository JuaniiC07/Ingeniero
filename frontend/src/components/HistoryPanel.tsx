import { formatLap } from "../labels";
import type { AnalysisListItem } from "../types";

interface Props {
  open: boolean;
  loading: boolean;
  items: AnalysisListItem[];
  onClose: () => void;
  onOpen: (id: number) => void;
}

function statusChip(item: AnalysisListItem) {
  if (item.status === "saved") return <span className="chip ok">Guardado</span>;
  return <span className="chip">Propuesto</span>;
}

export function HistoryPanel({ open, loading, items, onClose, onOpen }: Props) {
  if (!open) return null;
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <div className="card-title">Historial de análisis</div>
            <div className="card-sub">Todo queda local en tu equipo.</div>
          </div>
          <button className="btn small ghost" onClick={onClose}>
            Cerrar ✕
          </button>
        </div>
        <div className="drawer-body">
          {loading ? <div className="empty">Cargando…</div> : null}
          {!loading && items.length === 0 ? (
            <div className="empty">Todavía no generaste ningún análisis.</div>
          ) : null}
          {items.map((item) => (
            <button className="hist-item" key={item.id} onClick={() => onOpen(item.id)}>
              <div className="hi-top">
                <span className="hi-name">
                  {item.setup_name} · {item.track_name}
                </span>
                {statusChip(item)}
              </div>
              <div className="hi-meta">
                #{item.id} · {item.car_name} · {new Date(item.created_at).toLocaleString("es-AR")}
                {item.result && typeof item.result.best_lap_ms === "number"
                  ? ` · mejor vuelta ${formatLap(item.result.best_lap_ms as number)}`
                  : ""}
              </div>
              {item.summary ? <div className="hi-meta">{item.summary}</div> : null}
              {item.changes.length > 0 ? (
                <div className="hi-changes">{item.changes.slice(0, 3).join(" · ")}</div>
              ) : null}
              {item.saved_path ? <div className="hi-changes">→ {item.saved_path}</div> : null}
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
