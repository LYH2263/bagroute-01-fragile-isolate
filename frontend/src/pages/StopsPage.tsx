import { useEffect, useState } from "react";
import { api } from "../api/client";
type S = { id: number; route_id: number; seq: number; name: string; weight_kg: number; volume_l: number; is_fragile: boolean };
type R = { id: number; name: string };
export default function StopsPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [rows, setRows] = useState<S[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  useEffect(() => {
    if (rid === "") return;
    api<S[]>(`/stops?route_id=${rid}`).then(setRows);
  }, [rid]);
  async function toggle(s: S) {
    setBusyId(s.id); setErr("");
    try {
      const next = !s.is_fragile;
      // 标记落库；再次进入站点页仍从库中读回
      await api<S>(`/stops/${s.id}`, { method: "PATCH", body: JSON.stringify({ is_fragile: next }) });
      setRows(rs => rs.map(r => r.id === s.id ? { ...r, is_fragile: next } : r));
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusyId(null); }
  }
  return (<>
    <h2>订户点</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <span className="hint">勾选「易碎」后落库，装袋时易碎站点与非易碎站点分袋</span>
    </div>
    {err && <div className="err">{err}</div>}
    <div className="route-strip">
      {rows.map(s => (
        <div className={`stop-chip${s.is_fragile ? " stop-chip--fragile" : ""}`} key={s.id}>
          <span className="seq">#{s.seq}</span>
          <strong>{s.name}</strong>
          <span className="mono">{s.weight_kg}kg · {s.volume_l}L</span>
          <label className="fragile-toggle">
            <input type="checkbox" checked={s.is_fragile} disabled={busyId === s.id} onChange={() => toggle(s)} />
            易碎
          </label>
        </div>
      ))}
    </div>
  </>);
}
