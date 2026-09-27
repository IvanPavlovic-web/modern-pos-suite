import ThermalDailyReport from "./ThermalDailyReport";

export default function ThermalPeriodicReport({ data, settings }) {
  if (!data || !settings) return null;

  // Isti template kao dnevni, samo drugi naslov i dodat "Za dan"
  const modifiedData = {
    ...data,
    report_type: "PERIODIČNI IZVJEŠTAJ PROMETA",
    // Dodajemo "Za dan" info
  };

  // Koristimo isti render, ali sa izmjenama za header
  return (
    <div className="thermal-periodic-wrapper">
      <PeriodicRender data={modifiedData} settings={settings} />
    </div>
  );
}

function PeriodicRender({ data, settings }) {
  // Reuse logike iz DailyReport-a preko props-a
  return (
    <ThermalDailyReportInternal data={data} settings={settings} periodic />
  );
}

// Interna varijanta koja prima `periodic` flag
function ThermalDailyReportInternal({ data, settings, periodic = false }) {
  const {
    ThermalSeparator,
    ThermalRow,
    ThermalCenter,
    ThermalBlank,
    ThermalTableHeader,
    ThermalTableRow,
  } = require("./ThermalShared");

  const fmt = (n) =>
    Number(n || 0)
      .toFixed(2)
      .replace(".", ",");
  const fmtQty = (n) =>
    Number(n || 0)
      .toFixed(3)
      .replace(".", ",");

  const paperClass = settings.paper_width === 58 ? "paper-58" : "paper-80";
  const sizeClass = `size-${settings.font_size || 11}`;

  const counts = data.counts || {};
  const revenue = data.revenue || {};
  const items = data.items || [];
  const payments = data.payments || [];
  const advances = data.advances || [];

  const title = periodic
    ? "PERIODIČNI IZVJEŠTAJ PROMETA"
    : "DNEVNI PRESEK STANJA";

  return (
    <div className={`thermal-paper ${paperClass} ${sizeClass} thermal-content`}>
      <ThermalCenter bold>{title}</ThermalCenter>
      <ThermalCenter>{data.report_id}</ThermalCenter>
      <ThermalBlank size="sm" />
      <ThermalCenter>{settings.legal_name}</ThermalCenter>
      <ThermalCenter>{settings.store_name}</ThermalCenter>
      <ThermalCenter>{settings.address}</ThermalCenter>
      <ThermalCenter>{settings.pos_id}</ThermalCenter>

      <ThermalSeparator type="double" />

      <ThermalBlank size="sm" />
      <div className="t-info-block">
        <ThermalRow label="Vrijeme izveštaja:" value={data.time} />
        <ThermalRow label="" value={data.date || ""} />
        {periodic && (
          <>
            <ThermalRow label="Za dan:" value={data.date_from || ""} />
          </>
        )}
        <ThermalRow label="Kasir:" value={data.cashier} />
      </div>
      <ThermalBlank size="sm" />
      <ThermalSeparator />

      <div className="t-section-title">Broj izdatih računa</div>
      <div className="t-table-header">
        <span style={{ flex: 1 }}>Tip računa</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          Izdato računa
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Promet Prodaja</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          {counts.sale_count || 0}
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Promet</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          0
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Refundacija</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          {counts.refund_count || 0}
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Avans Prodaja</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          0
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Avans</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          0
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Refundacija</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          0
        </span>
      </div>

      <ThermalSeparator />
      <div className="t-summary">
        <div className="t-summary-row t-summary-grand">
          <span>Ukupno:</span>
          <span className="t-summary-value">{counts.total_count || 0}</span>
        </div>
      </div>

      <ThermalSeparator type="double" />

      <div className="t-section-title">Evidentiran promet</div>
      <div className="t-summary">
        <div className="t-summary-row">
          <span>Ukupno Prodaja</span>
          <span className="t-summary-value">{fmt(revenue.total_sales)}</span>
        </div>
        <div className="t-summary-row">
          <span>Ukupno Refundacija</span>
          <span className="t-summary-value">-{fmt(revenue.total_refunds)}</span>
        </div>
        <div className="t-summary-row t-summary-grand">
          <span>Ukupno</span>
          <span className="t-summary-value">{fmt(revenue.net_total)}</span>
        </div>
      </div>

      <ThermalSeparator type="double" />

      <div className="t-section-title">Lista prodatih artikala</div>
      <div className="t-table-header t-items-table">
        <span className="t-col-name">Naziv</span>
        <span className="t-col-code">Šifra</span>
        <span className="t-col-price">Cijena</span>
        <span className="t-col-qty">Kol.</span>
        <span className="t-col-total">Promet</span>
      </div>
      {items.map((it, idx) => (
        <div key={idx} className="t-table-row t-items-table">
          <span className="t-col-name" title={it.name}>
            {it.name}
          </span>
          <span className="t-col-code">{it.barcode}</span>
          <span className="t-col-price">{fmt(it.price)}</span>
          <span className="t-col-qty">{fmtQty(it.quantity)}</span>
          <span className="t-col-total">{fmt(it.total)}</span>
        </div>
      ))}

      <ThermalSeparator />
      <div className="t-summary">
        <div className="t-summary-row t-summary-grand">
          <span>Ukupno:</span>
          <span className="t-summary-value">{fmt(data.items_total)}</span>
        </div>
      </div>

      <ThermalSeparator type="double" />

      <div className="t-section-title">Promet po vrstama plaćanja</div>
      <div className="t-table-header">
        <span style={{ flex: 1 }}>Vrsta plaćanja</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          Iznos
        </span>
      </div>
      {payments.map((p, i) => (
        <div key={i} className="t-table-row">
          <span style={{ flex: 1 }}>{p.method}</span>
          <span
            style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}
          >
            {fmt(p.total)}
          </span>
        </div>
      ))}

      <div className="t-end-report">====== KRAJ IZVJEŠTAJA ======</div>
    </div>
  );
}
