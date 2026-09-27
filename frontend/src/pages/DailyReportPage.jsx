import { useEffect, useState } from "react";
import api from "../api";
import ThermalDailyReport from "../components/ThermalDailyReport";

function formatLocalDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export default function DailyReportPage() {
  const [date, setDate] = useState(() => formatLocalDate(new Date()));
  const [cashier, setCashier] = useState("");
  const [data, setData] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/receipt-settings/").then((r) => setSettings(r.data));
  }, []);

  const load = async () => {
    setLoading(true);
    try {
      const params = { date };
      if (cashier) params.cashier = cashier;
      const res = await api.get("/reports/daily/", { params });
      setData(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (settings) load();
  }, [settings]);

  const print = () => {
    document.body.classList.add(`print-${settings.paper_width}`);
    setTimeout(() => {
      window.print();
      setTimeout(
        () => document.body.classList.remove(`print-${settings.paper_width}`),
        500,
      );
    }, 100);
  };

  if (!settings) return <div className="loading">Učitavanje...</div>;

  return (
    <div className="report-page">
      <div className="report-header no-print">
        <h2>Dnevni presek stanja</h2>
        <div className="report-filters">
          <label>
            Datum{" "}
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <label>
            Kasir{" "}
            <input
              value={cashier}
              onChange={(e) => setCashier(e.target.value)}
              placeholder="svi"
            />
          </label>
          <button onClick={load}>Prikaži</button>
          <button onClick={print}>Print</button>
        </div>
      </div>

      {loading && <div className="loading">Učitavanje...</div>}

      {data && (
        <div className="thermal-preview-wrapper">
          <div className={`thermal-print-zone print-${settings.paper_width}`}>
            <ThermalDailyReport data={data} settings={settings} />
          </div>
        </div>
      )}
    </div>
  );
}
