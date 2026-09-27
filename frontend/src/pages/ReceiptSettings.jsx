import { useEffect, useState } from "react";
import api from "../api";
import ThermalReceipt from "../components/ThermalReceipt";

const DEMO_SALE = {
  id: 1,
  receipt_number: "R-20261015-00001",
  eo_number: "00001",
  created_at: new Date().toISOString(),
  cashier_name: "prodavac1",
  cashier_full: "Prodavac 1",
  payment_method: "CASH",
  total: 4.0,
  total_tax: 0.58,
  discount_amount: 0,
  amount_paid: 4.0,
  change_amount: 0,
  items: [
    {
      product_name: "NES CAFA - JACOBS",
      quantity: 1,
      unit_price: 2.0,
      line_total: 2.0,
      tax_amount: 0.29,
      product_tax_rate: 17,
    },
    {
      product_name: "KAFA",
      quantity: 1,
      unit_price: 2.0,
      line_total: 2.0,
      tax_amount: 0.29,
      product_tax_rate: 17,
    },
  ],
};

export default function ReceiptSettings() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    (async () => {
      const res = await api.get("/receipt-settings/");
      setSettings(res.data);
    })();
  }, []);

  const update = (key, value) => setSettings((s) => ({ ...s, [key]: value }));

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.post("/receipt-settings/", settings);
      setSettings(res.data);
      setMessage("Sačuvano!");
      setTimeout(() => setMessage(""), 2000);
    } catch (e) {
      setMessage("Greška: " + JSON.stringify(e.response?.data));
    } finally {
      setSaving(false);
    }
  };

  const testPrint = () => {
    document.body.classList.add(`print-${settings.paper_width}`);
    document.body.classList.add("printing-receipt");
    setTimeout(() => {
      window.print();
      setTimeout(() => {
        document.body.classList.remove(`print-${settings.paper_width}`);
        document.body.classList.remove("printing-receipt");
      }, 500);
    }, 100);
  };

  if (!settings) return <div className="loading">Učitavanje...</div>;

  return (
    <div className="settings-page">
      <div className="settings-header no-print">
        <h2>Podešavanja računa</h2>
        <div className="header-actions">
          <button onClick={testPrint} className="btn-secondary">
            Test Print
          </button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Čuvanje..." : "Sačuvaj"}
          </button>
        </div>
      </div>

      {message && <div className="toast no-print">{message}</div>}

      <div className="settings-body">
        <div className="settings-form no-print">
          {/* BUSINESS INFO */}
          <fieldset className="settings-fieldset settings-company">
            <legend>Podaci o firmi</legend>
            <label>
              Naziv (kratki){" "}
              <input
                value={settings.business_name}
                onChange={(e) => update("business_name", e.target.value)}
              />
            </label>
            <label>
              Puni naziv{" "}
              <input
                value={settings.legal_name}
                onChange={(e) => update("legal_name", e.target.value)}
              />
            </label>
            <label>
              Adresa{" "}
              <input
                value={settings.address}
                onChange={(e) => update("address", e.target.value)}
              />
            </label>
            <label>
              Grad{" "}
              <input
                value={settings.city}
                onChange={(e) => update("city", e.target.value)}
              />
            </label>
            <label>
              Poštanski broj{" "}
              <input
                value={settings.postal_code}
                onChange={(e) => update("postal_code", e.target.value)}
              />
            </label>
            <label>
              Telefon{" "}
              <input
                value={settings.phone}
                onChange={(e) => update("phone", e.target.value)}
              />
            </label>
            <label>
              Email{" "}
              <input
                value={settings.email}
                onChange={(e) => update("email", e.target.value)}
              />
            </label>
            <label>
              JIB{" "}
              <input
                value={settings.jib}
                onChange={(e) => update("jib", e.target.value)}
              />
            </label>
            <label>
              PIB{" "}
              <input
                value={settings.pib}
                onChange={(e) => update("pib", e.target.value)}
              />
            </label>
            <label>
              MB{" "}
              <input
                value={settings.mb}
                onChange={(e) => update("mb", e.target.value)}
              />
            </label>
            <label>
              ID poslovne jedinice{" "}
              <input
                value={settings.business_unit_id}
                onChange={(e) => update("business_unit_id", e.target.value)}
              />
            </label>
            <label>
              ID kase{" "}
              <input
                value={settings.pos_id}
                onChange={(e) => update("pos_id", e.target.value)}
              />
            </label>
            <label>
              Naziv prodajnog mjesta{" "}
              <input
                value={settings.store_name}
                onChange={(e) => update("store_name", e.target.value)}
              />
            </label>
          </fieldset>

          <fieldset className="settings-fieldset settings-receipt">
            <legend>Račun</legend>
            <label>
              Tip računa{" "}
              <input
                value={settings.receipt_type}
                onChange={(e) => update("receipt_type", e.target.value)}
              />
            </label>
            <label>
              Header text{" "}
              <input
                value={settings.header_text}
                onChange={(e) => update("header_text", e.target.value)}
              />
            </label>
            <label>
              Footer text{" "}
              <textarea
                rows={3}
                value={settings.footer_text}
                onChange={(e) => update("footer_text", e.target.value)}
              />
            </label>
          </fieldset>

          <fieldset className="settings-fieldset settings-appearance">
            <legend>Izgled</legend>
            <label>
              Širina papira
              <select
                value={settings.paper_width}
                onChange={(e) =>
                  update("paper_width", parseInt(e.target.value))
                }
              >
                <option value={58}>58 mm</option>
                <option value={80}>80 mm</option>
              </select>
            </label>
            <label>
              Font{" "}
              <input
                value={settings.font_family}
                onChange={(e) => update("font_family", e.target.value)}
              />
            </label>
            <label>
              Veličina fonta (px)
              <input
                type="number"
                min="8"
                max="16"
                value={settings.font_size}
                onChange={(e) => update("font_size", parseInt(e.target.value))}
              />
            </label>
            <label>
              Line height{" "}
              <input
                type="number"
                step="0.05"
                value={settings.line_height}
                onChange={(e) => update("line_height", e.target.value)}
              />
            </label>
            <label>
              Letter spacing{" "}
              <input
                type="number"
                step="0.1"
                value={settings.letter_spacing}
                onChange={(e) => update("letter_spacing", e.target.value)}
              />
            </label>
          </fieldset>

          <fieldset className="settings-fieldset settings-display">
            <legend>Prikaz polja</legend>
            {[
              "show_logo",
              "show_address",
              "show_phone",
              "show_email",
              "show_jib",
              "show_pib",
              "show_operator",
              "show_payment_method",
              "show_tax",
              "show_qr",
              "show_barcode",
            ].map((k) => (
              <label key={k} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={settings[k]}
                  onChange={(e) => update(k, e.target.checked)}
                />
                {k.replace("show_", "").toUpperCase()}
              </label>
            ))}
          </fieldset>
        </div>

        <div className="settings-preview">
          <div className="preview-label no-print">LIVE PREVIEW</div>
          <div className="thermal-preview-wrapper">
            <ThermalReceipt sale={DEMO_SALE} settings={settings} demo />
          </div>
        </div>
      </div>

      {/* PRINT ZONE (skrivena na ekranu, vidljiva pri printu) */}
      <div
        className={`thermal-print-zone print-${settings.paper_width}`}
        style={{ display: "none" }}
      >
        <ThermalReceipt sale={DEMO_SALE} settings={settings} demo />
      </div>
    </div>
  );
}
