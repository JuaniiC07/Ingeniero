import type { SessionSummary } from "../types";

interface Props {
  open: boolean;
  loading: boolean;
  items: SessionSummary[];
  onClose: () => void;
  onOpen: (id: number) => void;
  onCreate: () => void;
}

export function SessionPanel({ open, loading, items, onClose, onOpen, onCreate }: Props) {
  if (!open) return null;
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <div className="card-title">Sesiones de desarrollo</div>
            <div className="card-sub">Varios ajustes seguidos sobre el mismo coche/circuito.</div>
          </div>
          <button className="btn small primary" onClick={onCreate}>
            + Nueva
          </button>
          <button className="btn small ghost" onClick={onClose}>
            Cerrar ✕
          </button>
        </div>
        <div className="drawer-body">
          {loading ? <div className="empty">Cargando…</div> : null}
          {!loading && items.length === 0 ? (
            <div className="empty">Todavía no hay sesiones. Creá una desde un setup cargado.</div>
          ) : null}
          {items.map((item) => (
            <button className="hist-item" key={item.id} onClick={() => onOpen(item.id)}>
              <div className="hi-top">
                <span className="hi-name">
                  {item.name || `${item.car_name} · ${item.track_name}`}
                </span>
                <span className={`chip ${item.status === "active" ? "ok" : ""}`}>{item.status}</span>
              </div>
              <div className="hi-meta">
                #{item.id} · {item.car_name} · {item.track_name} · {item.analysis_count} ajuste(s)
              </div>
              {item.current_setup_path ? (
                <div className="hi-changes">→ {item.current_setup_path.split(/[\\/]/).pop()}</div>
              ) : null}
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
