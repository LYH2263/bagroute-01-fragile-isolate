import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string };
type Bag = { id: number; bag_index: number; weight_kg: number; volume_l: number; kind: string; split_reason: string | null; items: { stop_name: string; is_fragile: boolean }[] };

const kindLabel = (kind: string) => kind === "fragile" ? "仅易碎" : "仅非易碎";
const splitLabel = (reason: string | null) =>
  reason === "fragile" ? "易碎隔离新开袋" : reason === "full" ? "满额开新袋" : "首袋";

export default function PackPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  async function run() {
    setMsg(""); setErr("");
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      const fragileBags = out.filter(b => b.kind === "fragile").length;
      setMsg(`完成装袋：${out.length} 袋（其中易碎袋 ${fragileBags} 个）`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋</button>
      <span className="hint">易碎与非易碎绝不混装；袋满额或易碎性切换都会新开袋</span>
    </div>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    {bags.map(b => (
      <div key={b.id} className={`bag-card bag-card--${b.kind}`}>
        <div className="mono">
          袋 {b.bag_index}
          <span className={`bag-kind bag-kind--${b.kind}`}>{kindLabel(b.kind)}</span>
          <span className="bag-split">{splitLabel(b.split_reason)}</span>
          · {b.weight_kg}kg / {b.volume_l}L
        </div>
        <div className="bag-row">{b.items.map((it, i) => (
          <div className={`bag-block${it.is_fragile ? " bag-block--fragile" : ""}`} key={i}>
            {it.is_fragile && <span className="fragile-tag">易碎</span>}{it.stop_name}
          </div>
        ))}</div>
      </div>
    ))}
  </>);
}
