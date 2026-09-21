import { useEffect, useState } from "react";
import { api } from "../api/client";
type Rj = { id: number; route_id: number; stop_name: string; reason: string; reason_code: string; created_at: string };
type Bag = { id: number; route_id: number; bag_index: number; kind: string; split_reason: string | null };

const splitText = (reason: string | null) =>
  reason === "fragile" ? "易碎隔离新开袋" : reason === "full" ? "满额开新袋" : reason === "start" ? "首袋" : "";

export default function RejectsPage() {
  const [rows, setRows] = useState<Rj[]>([]);
  const [bags, setBags] = useState<Bag[]>([]);
  useEffect(() => {
    api<Rj[]>("/rejects").then(setRows);
    api<Bag[]>("/bags").then(setBags);
  }, []);
  const splits = bags.filter(b => b.split_reason === "full" || b.split_reason === "fragile");
  return (<>
    <h2>拒收</h2>
    <p className="hint">下表为「单站自身超路线限额」的现网拒收；满额/易碎隔离开新袋不是拒收，列于下方以便区分。</p>
    <table className="table"><thead><tr><th>时间</th><th>路线</th><th>订户</th><th>类型</th><th>原因</th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id} className="reject-row">
      <td className="mono">{new Date(r.created_at).toLocaleString()}</td>
      <td>{r.route_id}</td>
      <td>{r.stop_name}</td>
      <td><span className="reject-badge">超限拒收</span></td>
      <td className="err">{r.reason}</td>
    </tr>)}
      {!rows.length && <tr><td colSpan={5}>暂无拒收</td></tr>}
    </tbody></table>

    <h2 className="split-heading">开新袋记录（非拒收）</h2>
    <table className="table"><thead><tr><th>路线</th><th>袋号</th><th>袋类型</th><th>新开袋原因</th></tr></thead>
    <tbody>{splits.map(b => <tr key={b.id}>
      <td>{b.route_id}</td>
      <td>{b.bag_index}</td>
      <td><span className={`bag-kind bag-kind--${b.kind}`}>{b.kind === "fragile" ? "仅易碎" : "仅非易碎"}</span></td>
      <td>{splitText(b.split_reason)}</td>
    </tr>)}
      {!splits.length && <tr><td colSpan={4}>暂无因满额或易碎隔离而新开的袋</td></tr>}
    </tbody></table>
  </>);
}
