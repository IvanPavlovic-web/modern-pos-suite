import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, Line, Pie, Doughnut } from "react-chartjs-2";
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import api from "../api";

Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#f97316",
  "#14b8a6",
];

export default function Reports() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [daily, setDaily] = useState([]);
  const [top, setTop] = useState([]);
  const [cashiers, setCashiers] = useState([]);
  const [cats, setCats] = useState([]);
  const [hours, setHours] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [avgBasket, setAvgBasket] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [s, c, d, t, ca, cat, h, ls, ab] = await Promise.all([
          api.get("/reports/summary/"),
          api.get("/reports/comparison/"),
          api.get("/reports/revenue-per-day/"),
          api.get("/reports/top-products/"),
          api.get("/reports/revenue-per-cashier/"),
          api.get("/reports/revenue-per-category/"),
          api.get("/reports/revenue-per-hour/"),
          api.get("/reports/low-stock/"),
          api.get("/reports/average-basket/"),
        ]);
        setSummary(s.data);
        setComparison(c.data);
        setDaily(d.data);
        setTop(t.data);
        setCashiers(ca.data);
        setCats(cat.data);
        setHours(h.data);
        setLowStock(ls.data);
        setAvgBasket(ab.data);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading || !summary) return <div className="loading">Učitavanje...</div>;

  const dailyData = {
    labels: daily.map((r) => r.date),
    datasets: [
      {
        label: "Promet (KM)",
        data: daily.map((r) => r.total),
        backgroundColor: "rgba(54, 162, 235, 0.5)",
        borderColor: "rgb(54, 162, 235)",
        borderWidth: 2,
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const topData = {
    labels: top.map((r) => r.name),
    datasets: [
      {
        label: "Prodano komada",
        data: top.map((r) => r.total_sold),
        backgroundColor: "rgba(255, 99, 132, 0.6)",
      },
    ],
  };

  const cashierData = {
    labels: cashiers.map((r) => r.cashier),
    datasets: [
      {
        label: "Promet (KM)",
        data: cashiers.map((r) => r.total),
        backgroundColor: "rgba(75, 192, 192, 0.6)",
      },
    ],
  };

  const catData = {
    labels: cats.map((r) => r.category),
    datasets: [
      {
        label: "Promet po kategoriji",
        data: cats.map((r) => r.total),
        backgroundColor: COLORS,
      },
    ],
  };

  const hourData = {
    labels: hours.map((r) => r.hour),
    datasets: [
      {
        label: "Promet po satu",
        data: hours.map((r) => r.total),
        backgroundColor: "rgba(139, 92, 246, 0.6)",
      },
    ],
  };

  const todayVsYesterday = comparison && {
    labels: ["Danas", "Juče"],
    datasets: [
      {
        label: "Promet (KM)",
        data: [comparison.today, comparison.yesterday],
        backgroundColor: ["#2563eb", "#94a3b8"],
      },
    ],
  };

  return (
    <div className="reports-wrap">
      <h2>Izvještaji</h2>

      {/* TERMALNI IZVJEŠTAJI - DUGMAD */}
      <div className="report-actions no-print">
        <h3>Termalni izvještaji</h3>
        <button onClick={() => navigate("/reports/daily")}>
          Dnevni presek stanja
        </button>
        <button onClick={() => navigate("/reports/periodic")}>
          Periodični izvještaj
        </button>
        <button onClick={() => navigate("/settings/receipt")}>
          Podešavanja računa
        </button>
      </div>

      <div className="kpi-row">
        <div className="kpi">
          <div className="kpi-label">Ukupan promet</div>
          <div className="kpi-val">{summary.total_revenue.toFixed(2)} KM</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Broj prodaja</div>
          <div className="kpi-val">{summary.total_sales}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Prodano artikala</div>
          <div className="kpi-val">{summary.total_items}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Prosečna korpa</div>
          <div className="kpi-val">
            {avgBasket ? avgBasket.average.toFixed(2) : "0.00"} KM
          </div>
        </div>
      </div>

      {comparison && (
        <div className="chart-card">
          <h3>Poređenje dana</h3>
          <div className="comparison-row">
            <div className="comp-item">
              <div className="comp-label">Danas</div>
              <div className="comp-val">{comparison.today.toFixed(2)} KM</div>
            </div>
            <div className="comp-item">
              <div className="comp-label">Juče</div>
              <div className="comp-val">
                {comparison.yesterday.toFixed(2)} KM
              </div>
              <div
                className={`comp-diff ${comparison.today >= comparison.yesterday ? "up" : "down"}`}
              >
                {comparison.yesterday > 0
                  ? `${(((comparison.today - comparison.yesterday) / comparison.yesterday) * 100).toFixed(1)}%`
                  : "-"}
              </div>
            </div>
            <div className="comp-item">
              <div className="comp-label">Poslednjih 7 dana</div>
              <div className="comp-val">
                {comparison.last_7_days.toFixed(2)} KM
              </div>
            </div>
            <div className="comp-item">
              <div className="comp-label">Poslednjih 30 dana</div>
              <div className="comp-val">
                {comparison.last_30_days.toFixed(2)} KM
              </div>
            </div>
          </div>
          <Bar
            data={todayVsYesterday}
            options={{
              responsive: true,
              plugins: { legend: { display: false } },
            }}
          />
        </div>
      )}

      <div className="chart-card">
        <h3>Promet po danu</h3>
        <Line data={dailyData} />
      </div>

      <div className="two-cols">
        <div className="chart-card">
          <h3>Top 10 proizvoda</h3>
          <Bar data={topData} />
        </div>
        <div className="chart-card">
          <h3>Promet po kategoriji</h3>
          <Pie data={catData} />
        </div>
      </div>

      <div className="two-cols">
        <div className="chart-card">
          <h3>Promet po kasiru</h3>
          <Bar data={cashierData} />
        </div>
        <div className="chart-card">
          <h3>Promet po satu</h3>
          <Doughnut data={hourData} />
        </div>
      </div>

      {lowStock.length > 0 && (
        <div className="chart-card">
          <h3>Zalihe ispod minimuma ({lowStock.length})</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Proizvod</th>
                <th>Kategorija</th>
                <th>Stanje</th>
                <th>Min</th>
              </tr>
            </thead>
            <tbody>
              {lowStock.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.category}</td>
                  <td className="low-stock">{p.stock}</td>
                  <td>{p.min_stock}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
