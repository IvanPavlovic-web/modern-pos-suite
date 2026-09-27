import {
  ThermalSeparator,
  ThermalRow,
  ThermalCenter,
  ThermalBlank,
  ThermalItem,
  ThermalTotalRow,
  ThermalBarcode,
} from "./ThermalShared";

const fmt = (n) =>
  Number(n || 0)
    .toFixed(2)
    .replace(".", ",");

export default function ThermalReceipt({ sale, settings, demo = false }) {
  if (!settings) settings = {};
  if (!sale) sale = {};

  const currency = "E"; // može i 'KM'
  const paperClass = settings.paper_width === 58 ? "paper-58" : "paper-80";
  const sizeClass = `size-${settings.font_size || 11}`;
  const paperStyle = {
    fontFamily: settings.font_family || "var(--thermal-font)",
    fontSize: `${settings.font_size || 11}px`,
    lineHeight: settings.line_height || 1.35,
    letterSpacing: `${settings.letter_spacing ?? 0.4}px`,
  };

  const items = sale.items || [];
  const total = parseFloat(sale.total || 0);
  const totalTax = parseFloat(sale.total_tax || 0);
  const discount = parseFloat(sale.discount_amount || 0);
  const amountPaid = parseFloat(sale.amount_paid || sale.total || 0);
  const change = parseFloat(sale.change_amount || amountPaid - total || 0);

  // Grupisi poreze po stopi
  const taxGroups = {};
  items.forEach((i) => {
    const rate = parseFloat(i.product_tax_rate || 17);
    const lineTotal = parseFloat(
      i.line_total || i.unit_price * i.quantity || 0,
    );
    const taxAmt = parseFloat(
      i.tax_amount || (lineTotal * rate) / (100 + rate) || 0,
    );
    if (!taxGroups[rate]) taxGroups[rate] = { base: 0, tax: 0, total: 0 };
    taxGroups[rate].total += lineTotal;
    taxGroups[rate].tax += taxAmt;
    taxGroups[rate].base += lineTotal - taxAmt;
  });

  const dateStr = sale.created_at
    ? new Date(sale.created_at)
        .toLocaleString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
        .replace(",", "")
    : "-";

  const cashierName = sale.cashier_full || sale.cashier_name || "-";

  return (
    <div
      className={`thermal-paper ${paperClass} ${sizeClass} thermal-content`}
      style={paperStyle}
    >
      {/* HEADER - naziv gore desno */}
      <div className="t-header">
        <span className="t-header-name">{settings.business_name || "SUR"}</span>
      </div>

      <ThermalBlank size="sm" />

      {/* Polja firme: samo ako su popunjena */}
      {(settings.show_jib || settings.show_pib || settings.show_address) && (
        <div className="t-info-block">
          {settings.show_jib && (
            <div className="t-info-line">
              <span>IBBO:</span>
              <span>{settings.jib || ""}</span>
            </div>
          )}
          {settings.show_pib && (
            <div className="t-info-line">
              <span>IIDO:</span>
              <span>{settings.pib || ""}</span>
            </div>
          )}
          {settings.show_address && (
            <div className="t-info-line">
              <span>BBOI:</span>
              <span>{settings.mb || ""}</span>
            </div>
          )}
        </div>
      )}

      <ThermalSeparator />

      {/* Naslov */}
      <div className="t-title">
        {(settings.receipt_type || "MALOPRODAJNI FISKALNI RAČUN")
          .split(" ")
          .slice(0, 1)
          .join(" ")}
        <br />
        {(settings.receipt_type || "MALOPRODAJNI FISKALNI RAČUN")
          .split(" ")
          .slice(1)
          .join(" ")}
      </div>

      <ThermalSeparator />

      {/* ARTIKLI */}
      <div>
        {items.map((item, idx) => (
          <ThermalItem
            key={idx}
            name={item.product_name || item.name || "Artikal"}
            code={item.product_barcode || ""}
            quantity={item.quantity}
            unitPrice={item.unit_price}
            lineTotal={item.line_total || item.unit_price * item.quantity}
            currency={currency}
          />
        ))}
      </div>

      <ThermalSeparator />

      {/* POREZI */}
      {settings.show_tax && Object.keys(taxGroups).length > 0 && (
        <div>
          {Object.entries(taxGroups).map(([rate, t]) => (
            <div key={rate}>
              <div className="t-row">
                <span>
                  CE: {parseFloat(rate).toFixed(2).replace(".", ",")}%
                </span>
              </div>
              <ThermalRow label="PE:" value={fmt(t.base)} />
              <ThermalRow label="PN:" value={fmt(t.tax)} />
              <ThermalRow label="EE:" value={fmt(t.total)} />
              <ThermalRow label="EY:" value={fmt(t.total - t.tax)} />
              <ThermalRow label="EG:" value={fmt(t.base)} />
            </div>
          ))}
        </div>
      )}

      <ThermalSeparator />

      {/* UKUPNO */}
      <div className="t-totals">
        <ThermalTotalRow label="ZA UPLATU:" value={fmt(total)} />
        {settings.show_payment_method && (
          <ThermalTotalRow
            label={sale.payment_method === "CARD" ? "KARTICA:" : "GOTOVINA:"}
            value={fmt(total)}
          />
        )}
        <ThermalTotalRow label="PLAĆENO:" value={fmt(amountPaid)} />
        <ThermalTotalRow label="POVRAT:" value={fmt(change)} />
      </div>

      <div className="t-info-block">
        <div className="t-info-line">
          <span>Datum:</span>
          <span>{dateStr}</span>
        </div>
        <div className="t-info-line">
          <span>EO:</span>
          <span>{sale.eo_number || sale.receipt_number || "-"}</span>
        </div>
      </div>

      <ThermalSeparator />

      {/* FOOTER */}
      <div className="t-footer">
        {(settings.footer_text || "HVALA NA POSJETI !\nPOS")
          .split("\n")
          .map((line, i) => (
            <div key={i} className="t-footer-line">
              {line}
            </div>
          ))}
      </div>
      <div className="t-footer-right">
        # {String(sale.id || 1).padStart(2, "0")}
      </div>

      {/* BARCODE */}
      {settings.show_barcode && (
        <ThermalBarcode
          value={String(sale.receipt_number || "00000001")
            .replace(/\D/g, "")
            .slice(-8)
            .padStart(8, "0")}
        />
      )}
    </div>
  );
}
