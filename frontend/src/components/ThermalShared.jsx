// Zajedničke termalne komponente

export function ThermalSeparator({ type = "single" }) {
  const cls =
    type === "double"
      ? "t-sep-double"
      : type === "thick"
        ? "t-sep-thick"
        : "t-sep";
  return <div className={cls} />;
}

export function ThermalRow({ label, value, bold = false }) {
  return (
    <div className={`t-row ${bold ? "t-bold" : ""}`}>
      <span className="t-row-label">{label}</span>
      <span className="t-row-value">{value}</span>
    </div>
  );
}

export function ThermalCenter({ children, bold = false }) {
  return <div className={`t-center ${bold ? "t-bold" : ""}`}>{children}</div>;
}

export function ThermalBlank({ size = "normal" }) {
  const cls =
    size === "sm" ? "t-blank-sm" : size === "lg" ? "t-blank-lg" : "t-blank";
  return <div className={cls} />;
}

export function ThermalItem({
  name,
  code,
  quantity,
  unit,
  unitPrice,
  lineTotal,
  currency = "E",
}) {
  const fmt = (n) => Number(n).toFixed(2).replace(".", ",");
  return (
    <div className="t-item">
      <div className="t-item-name">{name}</div>
      <div className="t-item-line">
        <span className="t-item-qty">{quantity}x</span>
        <span className="t-item-price">{fmt(unitPrice)}</span>
        <span className="t-item-total">
          {fmt(lineTotal)} {currency}
        </span>
      </div>
    </div>
  );
}

export function ThermalTableHeader({ columns }) {
  return (
    <div className="t-table-header t-items-table">
      {columns.map((c, i) => (
        <span key={i} className={`t-col-${c.key}`}>
          {c.label}
        </span>
      ))}
    </div>
  );
}

export function ThermalTableRow({ values }) {
  return (
    <div className="t-table-row t-items-table">
      {values.map((v, i) => (
        <span key={i} className={`t-col-${v.key}`} title={v.value}>
          {v.value}
        </span>
      ))}
    </div>
  );
}

export function ThermalTotalRow({ label, value, grand = false }) {
  return (
    <div className={`t-total-row ${grand ? "t-total-grand" : ""}`}>
      <span className="t-total-label">{label}</span>
      <span className="t-total-value">{value}</span>
    </div>
  );
}

export function ThermalBarcode({ value }) {
  return <div className="t-barcode">*{value}*</div>;
}
