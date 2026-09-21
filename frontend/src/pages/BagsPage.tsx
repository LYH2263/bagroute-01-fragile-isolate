import { useEffect, useState } from "react";
import { api } from "../api/client";
type Bag = { id: number; route_id: number; bag_index: number; weight_kg: number; volume_l: number; kind: string; split_reason: string | null; items: { stop_name: string; weight_kg: number; volume_l: number; is_fragile: boolean }[] };

const splitText = (reason: string | null) =>
  reason === "fragile" ? "易碎隔离新开袋" : reason === "full" ? "满额开新袋" : reason === "start" ? "首袋" : "";

export default function BagsPage() {
  const [rows, setRows] = useState<Bag[]>([]);
  useEffect(() => { api<Bag[]>("/bags").then(setRows); }, []);
  return (<>
    <h2>袋明细</h2>
    <table className="table"><thead><tr><th>路线</th><th>袋号</th><th>袋类型</th><th>新开袋原因</th><th>重量</th><th>体积</th><th>订户</th></tr></thead>
    <tbody>{rows.map(b => <tr key={b.id} className={`bag-row--${b.kind}`}>
      <td>{b.route_id}</td>
      <td>{b.bag_index}</td>
      <td><span className={`bag-kind bag-kind--${b.kind}`}>{b.kind === "fragile" ? "仅易碎" : "仅非易碎"}</span></td>
      <td>{splitText(b.split_reason)}</td>
      <td className="mono">{b.weight_kg}</td>
      <td className="mono">{b.volume_l}</td>
      <td>{b.items.map((i, idx) => (
        <span className="bag-name-item" key={idx}>
          {idx > 0 && " → "}
          {i.is_fragile && <span className="fragile-tag">易碎</span>}{i.stop_name}
        </span>
      ))}</td>
    </tr>)}
      {!rows.length && <tr><td colSpan={7}>尚无装袋结果，请先执行装袋</td></tr>}
    </tbody></table>
  </>);
}
