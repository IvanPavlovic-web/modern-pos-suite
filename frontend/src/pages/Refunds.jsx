import { useState } from "react";
import api from "../api";

export default function Refunds() {
  const [receipt, setReceipt] = useState("");
  const [sale, setSale] = useState(null);
  const [selectedItems, setSelectedItems] = useState({});
  const [reason, setReason] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("CASH");
  const [message, setMessage] = useState("");
  const [recentRefunds, setRecentRefunds] = useState([]);

  const findSale = async (e) => {
    e.preventDefault();
    setMessage("");
    setSale(null);
    try {
      const res = await api.get(`/refunds/find-sale/?receipt=${receipt}`);
      setSale(res.data);
      const initial = {};
      res.data.items.forEach((i) => {
        initial[i.id] = 0;
      });
      setSelectedItems(initial);
    } catch (err) {
      setMessage(err.response?.data?.detail || "Račun nije nađen.");
    }
  };

  const updateQty = (itemId, qty) => {
    setSelectedItems((prev) => ({ ...prev, [itemId]: Math.max(0, qty) }));
  };

  const totalRefund = () => {
    if (!sale) return 0;
    return sale.items.reduce((sum, i) => {
      const qty = selectedItems[i.id] || 0;
      const unitPrice = parseFloat(i.unit_price);
      const itemDiscount = parseFloat(i.item_discount_percent || 0);
      const saleDiscount = parseFloat(sale.discount_percent || 0);
      const refundUnitPrice =
        Math.round(
          unitPrice * (1 - itemDiscount / 100) * (1 - saleDiscount / 100) * 100,
        ) / 100;
      return sum + refundUnitPrice * qty;
    }, 0);
  };

  const processRefund = async () => {
    if (!sale) return;
    const items = Object.entries(selectedItems)
      .filter(([_, qty]) => qty > 0)
      .map(([id, qty]) => ({ sale_item_id: parseInt(id), quantity: qty }));

    if (items.length === 0) {
      setMessage("Odaberi bar jedan artikal za refundaciju.");
      return;
    }

    if (!confirm(`Refundirati ${totalRefund().toFixed(2)} KM?`)) return;

    let res;
    try {
      res = await api.post("/refunds/", {
        sale_id: sale.id,
        reason,
        payment_method: paymentMethod,
        items,
      });
    } catch (err) {
      setMessage(err.response?.data?.detail || "Greška pri refundaciji.");
      return;
    }

    setMessage(`Refundacija uspešna! Broj: ${res.data.receipt_number}`);
    setRecentRefunds((prev) => [res.data, ...prev]);
    setSale(null);
    setReceipt("");
    setReason("");

    try {
      const token = localStorage.getItem("access_token");
      const pdfRes = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/refunds/${res.data.id}/receipt/`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!pdfRes.ok) throw new Error("PDF storno računa nije dostupan.");
      const blob = await pdfRes.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `storno-${res.data.receipt_number}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setMessage(
        "Refundacija je uspješna, ali PDF storno računa nije preuzet.",
      );
    }
  };

  return (
    <div className="refunds-wrap">
      <h2>Refundacije / Storniranje</h2>

      <div className="refund-search">
        <form onSubmit={findSale}>
          <input
            type="text"
            placeholder="Unesi broj računa (npr. R-20260927-00042)"
            value={receipt}
            onChange={(e) => setReceipt(e.target.value)}
          />
          <button type="submit">Nađi račun</button>
        </form>
      </div>

      {message && (
        <div
          className={message.includes("uspešna") ? "toast success" : "toast"}
        >
          {message}
        </div>
      )}

      {sale && (
        <div className="refund-sale">
          <h3>Račun {sale.receipt_number}</h3>
          <p>
            Datum: {new Date(sale.created_at).toLocaleString()} | Kasir:{" "}
            {sale.cashier_name} | Ukupno: {sale.total} KM | Status:{" "}
            {sale.status}
          </p>

          <table className="table">
            <thead>
              <tr>
                <th>Artikal</th>
                <th>Cijena</th>
                <th>Prodano</th>
                <th>Refundirano</th>
                <th>Dostupno</th>
                <th>Refundiraj</th>
              </tr>
            </thead>
            <tbody>
              {sale.items.map((i) => (
                <tr key={i.id}>
                  <td>{i.product_name}</td>
                  <td>{parseFloat(i.unit_price).toFixed(2)} KM</td>
                  <td>{i.quantity}</td>
                  <td>{i.refunded_quantity}</td>
                  <td>{i.available_for_refund}</td>
                  <td>
                    <div className="qty-controls">
                      <button
                        onClick={() =>
                          updateQty(i.id, (selectedItems[i.id] || 0) - 1)
                        }
                      >
                        −
                      </button>
                      <span>{selectedItems[i.id] || 0}</span>
                      <button
                        onClick={() =>
                          updateQty(
                            i.id,
                            Math.min(
                              i.available_for_refund,
                              (selectedItems[i.id] || 0) + 1,
                            ),
                          )
                        }
                      >
                        +
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="refund-form">
            <label>
              Razlog:
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
              />
            </label>
            <label>
              Način povrata:
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                <option value="CASH">Gotovina</option>
                <option value="CARD">Kartica</option>
              </select>
            </label>
            <div className="refund-total">
              Za refundaciju: <b>{totalRefund().toFixed(2)} KM</b>
            </div>
            <button className="refund-btn" onClick={processRefund}>
              Izvrši refundaciju
            </button>
          </div>
        </div>
      )}

      {recentRefunds.length > 0 && (
        <div className="recent-refunds">
          <h3>U ovoj sesiji refundirano:</h3>
          <ul>
            {recentRefunds.map((r) => (
              <li key={r.id}>
                {r.receipt_number} | {r.total} KM | original:{" "}
                {r.original_receipt}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
