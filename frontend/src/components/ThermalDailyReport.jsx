import {
  ThermalSeparator,
  ThermalRow,
  ThermalCenter,
  ThermalBlank,
  ThermalTableHeader,
  ThermalTableRow,
  ThermalTotalRow,
} from "./ThermalShared";

const fmt = (n) =>
  Number(n || 0)
    .toFixed(2)
    .replace(".", ",");
const fmtQty = (n) =>
  Number(n || 0)
    .toFixed(3)
    .replace(".", ",");

export default function ThermalDailyReport({ data, settings }) {
  if (!data || !settings) return null;

  const paperClass = settings.paper_width === 58 ? "paper-58" : "paper-80";
  const sizeClass = `size-${settings.font_size || 11}`;

  const counts = data.counts || {};
  const revenue = data.revenue || {};
  const items = data.items || [];
  const payments = data.payments || [];
  const advances = data.advances || [];

  return (
    <div className={`thermal-paper ${paperClass} ${sizeClass} thermal-content`}>
      {/* NASLOV */}
      <ThermalCenter bold>DNEVNI PRESEK STANJA</ThermalCenter>
      <ThermalCenter>{data.report_id}</ThermalCenter>
      <ThermalBlank size="sm" />
      <ThermalCenter>
        {settings.legal_name || "SIRIUS2010.doo Banja Luka"}
      </ThermalCenter>
      <ThermalCenter>
        {settings.store_name || settings.legal_name}
      </ThermalCenter>
      <ThermalCenter>{settings.address || ""}</ThermalCenter>
      <ThermalCenter>{settings.pos_id || "NOT APPLICABLE"}</ThermalCenter>

      <ThermalSeparator type="double" />

      {/* INFO O IZVJEŠTAJU */}
      <ThermalBlank size="sm" />
      <div className="t-info-block">
        <ThermalRow label="Vrijeme izveštaja:" value={data.time || ""} />
        <ThermalRow label="" value={data.date || ""} />
        <ThermalRow label="Kasir:" value={data.cashier || "-"} />
      </div>
      <ThermalBlank size="sm" />

      <ThermalSeparator />

      {/* BROJ IZDATIH RAČUNA */}
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
          {counts.advance_sale || 0}
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Avans</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          {counts.advance || 0}
        </span>
      </div>
      <div className="t-table-row">
        <span style={{ flex: 1 }}>Refundacija</span>
        <span style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}>
          {counts.advance_refund || 0}
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

      {/* EVIDENTIRAN PROMET */}
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

      {/* LISTA PRODATIH ARTIKALA */}
      <div className="t-section-title">Lista prodatih artikala</div>
      <div className="t-table-header t-items-table">
        <span className="t-col-name">Naziv</span>
        <span className="t-col-code">Šifra</span>
        <span className="t-col-price">Cijena</span>
        <span className="t-col-qty">Kol.</span>
        <span className="t-col-total">Promet</span>
      </div>
      {items.map((it, idx) => (
        <div key={idx}>
          <div className="t-table-row t-items-table">
            <span className="t-col-name" title={it.name}>
              {it.name}
            </span>
            <span className="t-col-code">{it.barcode}</span>
            <span className="t-col-price">{fmt(it.price)}</span>
            <span className="t-col-qty">{fmtQty(it.quantity)}</span>
            <span className="t-col-total">{fmt(it.total)}</span>
          </div>
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

      {/* AVANSNE UPLATE */}
      {advances.length > 0 && (
        <>
          <div className="t-section-title">Pregled avansnih uplata</div>
          <div className="t-table-header">
            <span style={{ flex: 1 }}>Naziv</span>
            <span
              style={{ flex: "0 0 auto", minWidth: "6em", textAlign: "right" }}
            >
              Promet
            </span>
          </div>
          {advances.map((a, i) => (
            <div key={i} className="t-table-row">
              <span style={{ flex: 1 }}>{a.name}</span>
              <span
                style={{
                  flex: "0 0 auto",
                  minWidth: "6em",
                  textAlign: "right",
                }}
              >
                {fmt(a.total)}
              </span>
            </div>
          ))}
          <ThermalSeparator />
          <div className="t-summary">
            <div className="t-summary-row t-summary-grand">
              <span>Ukupno:</span>
              <span className="t-summary-value">
                {fmt(data.advances_total)}
              </span>
            </div>
          </div>
          <ThermalSeparator type="double" />
        </>
      )}

      {/* PROMET PO VRSTAMA PLAĆANJA */}
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

      {/* KRAJ */}
      <div className="t-end-report">====== KRAJ IZVJEŠTAJA ======</div>
    </div>
  );
}
