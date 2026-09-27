import { useEffect, useState } from "react";
import api from "../api";

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [actionFilter, setActionFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (actionFilter) params.action = actionFilter;
      if (userFilter) params.user = userFilter;
      const res = await api.get("/audit-log/", { params });
      setLogs(res.data.results || res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [actionFilter, userFilter]);

  const actions = [
    ["", "Sve akcije"],
    ["LOGIN", "Login"],
    ["SALE_CREATE", "Kreiranje prodaje"],
    ["SALE_CHECKOUT", "Završetak prodaje"],
    ["SALE_CANCEL", "Otkazivanje"],
    ["SALE_REFUND", "Refundacija"],
    ["SALE_DISCOUNT", "Popust"],
    ["PRODUCT_CREATE", "Novi proizvod"],
    ["PRODUCT_UPDATE", "Izmjena proizvoda"],
    ["PRODUCT_DELETE", "Brisanje proizvoda"],
    ["PRICE_CHANGE", "Izmjena cijene"],
    ["STOCK_CHANGE", "Izmjena stanja"],
  ];

  return (
    <div className="audit-wrap">
      <h2>Audit log: istorija akcija</h2>

      <div className="audit-filters">
        <label>
          Akcija:
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          >
            {actions.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          Korisnik:
          <input
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            placeholder="username"
          />
        </label>
        <button onClick={load}>Osvježi</button>
      </div>

      {loading && <div className="loading">Učitavanje...</div>}

      {!loading && (
        <table className="table">
          <thead>
            <tr>
              <th>Vrijeme</th>
              <th>Korisnik</th>
              <th>Akcija</th>
              <th>Meta</th>
              <th>Detalji</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  Nema zapisa.
                </td>
              </tr>
            )}
            {logs.map((l) => (
              <tr key={l.id}>
                <td>{new Date(l.created_at).toLocaleString()}</td>
                <td>{l.user_name || "-"}</td>
                <td>
                  <span
                    className={`action-badge action-${l.action.toLowerCase()}`}
                  >
                    {l.action}
                  </span>
                </td>
                <td>
                  {l.target_type} {l.target_id && `#${l.target_id}`}
                </td>
                <td className="details-cell">
                  {l.details && Object.keys(l.details).length > 0 && (
                    <code>{JSON.stringify(l.details)}</code>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
