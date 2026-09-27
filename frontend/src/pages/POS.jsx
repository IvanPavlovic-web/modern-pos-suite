import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import api from "../api";
import useWebSocket from "../hooks/useWebSocket";

const TERMINAL_ID =
  localStorage.getItem("terminal_id") ||
  `terminal-${Math.floor(Math.random() * 1000)}`;
localStorage.setItem("terminal_id", TERMINAL_ID);

function SearchIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="4" width="4" height="16" rx="1" />
      <rect x="14" y="4" width="4" height="16" rx="1" />
    </svg>
  );
}

export default function POS() {
  const [products, setProducts] = useState([]);
  const [openSales, setOpenSales] = useState([]);
  const [activeSaleId, setActiveSaleId] = useState(null);
  const [barcode, setBarcode] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [payment, setPayment] = useState("CASH");
  const [message, setMessage] = useState("");
  const [stockFlash, setStockFlash] = useState({});
  const [isMobileCartOpen, setIsMobileCartOpen] = useState(false);
  const [discountOpen, setDiscountOpen] = useState(false);
  const [discountPercent, setDiscountPercent] = useState(0);
  const [splitOpen, setSplitOpen] = useState(false);
  const [splitCash, setSplitCash] = useState(0);
  const [splitCard, setSplitCard] = useState(0);
  const searchInputRef = useRef(null);
  const barcodeInputRef = useRef(null);

  const activeSale = openSales.find((s) => s.id === activeSaleId);

  const categories = useMemo(() => {
    const cats = new Set(products.map((p) => p.category_name).filter(Boolean));
    return ["all", ...Array.from(cats).sort()];
  }, [products]);

  const filteredProducts = useMemo(() => {
    let result = products;
    if (selectedCategory !== "all") {
      result = result.filter((p) => p.category_name === selectedCategory);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.barcode && p.barcode.includes(q)),
      );
    }
    return result;
  }, [products, searchQuery, selectedCategory]);

  const loadProducts = async () => {
    const res = await api.get("/products/?page_size=1000");
    setProducts(res.data.results || res.data);
  };

  const loadOpenSales = async () => {
    const res = await api.get("/sales/open/");
    setOpenSales(res.data);
    if (res.data.length > 0 && !activeSaleId) {
      setActiveSaleId(res.data[0].id);
    }
  };

  useEffect(() => {
    loadProducts();
    loadOpenSales();
  }, []);

  useEffect(() => {
    const handleKey = (e) => {
      const isInInput =
        e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA";
      const isFunctionKey = e.key.startsWith("F") && e.key.length <= 3;
      if (isInInput && !isFunctionKey && e.key !== "Escape") return;

      if (e.key === "F1") {
        e.preventDefault();
        barcodeInputRef.current?.focus();
      } else if (e.key === "F2") {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === "F3") {
        e.preventDefault();
        setPayment("CASH");
        finishSaleDirect("CASH");
      } else if (e.key === "F4") {
        e.preventDefault();
        setPayment("CARD");
        finishSaleDirect("CARD");
      } else if (e.key === "F5") {
        e.preventDefault();
        createNewSale();
      } else if (e.key === "F6") {
        e.preventDefault();
        setDiscountOpen(true);
      } else if (e.key === "F7") {
        e.preventDefault();
        openSplit();
      } else if (e.key === "F8") {
        e.preventDefault();
        holdSale();
      } else if (e.key === "Escape") {
        e.preventDefault();
        setDiscountOpen(false);
        setSplitOpen(false);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
    // eslint-disable-next-line
  }, [activeSaleId, activeSale]);

  useWebSocket("/ws/inventory/", (data) => {
    if (!data.product_id) return;
    setProducts((prev) =>
      prev.map((p) =>
        p.id === data.product_id ? { ...p, stock: data.new_stock } : p,
      ),
    );
    setStockFlash((s) => ({ ...s, [data.product_id]: true }));
    setTimeout(
      () => setStockFlash((s) => ({ ...s, [data.product_id]: false })),
      900,
    );
  });

  useWebSocket("/ws/sales/", (data) => {
    if (!data.sale_id) return;
    if (
      data.action === "deleted" ||
      data.status === "COMPLETED" ||
      data.status === "REFUNDED"
    ) {
      setOpenSales((prev) => {
        const filtered = prev.filter((s) => s.id !== data.sale_id);
        if (activeSaleId === data.sale_id) {
          setActiveSaleId(filtered[0]?.id || null);
        }
        return filtered;
      });
      return;
    }
    loadOpenSales();
  });

  const createNewSale = useCallback(async () => {
    const res = await api.post("/sales/open-new/", {
      terminal_id: TERMINAL_ID,
    });
    setOpenSales((prev) => [...prev, res.data]);
    setActiveSaleId(res.data.id);
    setIsMobileCartOpen(true);
    return res.data;
  }, []);

  const switchToSale = (id) => setActiveSaleId(id);

  const cancelSale = async (id) => {
    if (!confirm("Otkazati ovaj račun?")) return;
    try {
      await api.post(`/sales/${id}/cancel/`);
      setOpenSales((prev) => {
        const filtered = prev.filter((s) => s.id !== id);
        if (activeSaleId === id) setActiveSaleId(filtered[0]?.id || null);
        return filtered;
      });
    } catch (e) {
      setMessage("Greška pri otkazivanju.");
    }
  };

  const holdSale = async () => {
    if (!activeSaleId) return;
    try {
      const res = await api.post(`/sales/${activeSaleId}/hold/`);
      setOpenSales((prev) =>
        prev.map((s) => (s.id === activeSaleId ? res.data : s)),
      );
      setMessage("Račun zadržan.");
      setTimeout(() => setMessage(""), 1500);
    } catch (e) {
      setMessage("Greška.");
    }
  };

  const resumeSale = async (id) => {
    try {
      const res = await api.post(`/sales/${id}/resume/`);
      setOpenSales((prev) => prev.map((s) => (s.id === id ? res.data : s)));
      setActiveSaleId(id);
    } catch (e) {
      setMessage("Greška.");
    }
  };

  const addProduct = async (product, quantity = 1) => {
    let saleId = activeSaleId;
    if (!saleId) {
      const newSale = await createNewSale();
      saleId = newSale.id;
    }
    try {
      const res = await api.post(`/sales/${saleId}/add-item/`, {
        product_id: product.id,
        quantity,
      });
      setOpenSales((prev) => prev.map((s) => (s.id === saleId ? res.data : s)));
    } catch (err) {
      setMessage(err.response?.data?.detail || "Greška pri dodavanju.");
      setTimeout(() => setMessage(""), 2000);
    }
  };

  const removeItem = async (itemId) => {
    if (!activeSaleId) return;
    const res = await api.post(`/sales/${activeSaleId}/remove-item/`, {
      item_id: itemId,
    });
    setOpenSales((prev) =>
      prev.map((s) => (s.id === activeSaleId ? res.data : s)),
    );
  };

  const updateItemQty = async (itemId, quantity) => {
    if (!activeSaleId) return;
    if (quantity <= 0) return removeItem(itemId);
    const res = await api.post(`/sales/${activeSaleId}/update-item/`, {
      item_id: itemId,
      quantity,
    });
    setOpenSales((prev) =>
      prev.map((s) => (s.id === activeSaleId ? res.data : s)),
    );
  };

  const applyDiscount = async () => {
    if (!activeSaleId) return;
    try {
      const res = await api.post(`/sales/${activeSaleId}/set-discount/`, {
        percent: discountPercent,
      });
      setOpenSales((prev) =>
        prev.map((s) => (s.id === activeSaleId ? res.data : s)),
      );
      setDiscountOpen(false);
      setMessage(`Popust ${discountPercent}% primijenjen.`);
      setTimeout(() => setMessage(""), 1500);
    } catch (err) {
      setMessage(err.response?.data?.detail || "Greška.");
      setTimeout(() => setMessage(""), 2000);
    }
  };

  const handleBarcode = async (e) => {
    e.preventDefault();
    if (!barcode) return;
    try {
      const res = await api.get(`/products/by-barcode/${barcode}/`);
      await addProduct(res.data, 1);
      setBarcode("");
    } catch {
      setMessage("Proizvod nije nađen.");
      setTimeout(() => setMessage(""), 1500);
    }
    barcodeInputRef.current?.focus();
  };

  const openSplit = () => {
    if (!activeSale) return;
    setSplitCash(parseFloat(activeSale.total));
    setSplitCard(0);
    setSplitOpen(true);
  };

  const finishSaleDirect = async (paymentMethod = null) => {
    const method = paymentMethod || payment;
    if (!activeSaleId || !activeSale?.items?.length) return;

    let payment_splits = null;
    if (method === "SPLIT") {
      if (
        Math.abs(splitCash + splitCard - parseFloat(activeSale.total)) > 0.01
      ) {
        setMessage("Suma split plaćanja ne odgovara ukupnom iznosu.");
        setTimeout(() => setMessage(""), 2500);
        return;
      }
      payment_splits = [
        { method: "CASH", amount: parseFloat(splitCash) },
        { method: "CARD", amount: parseFloat(splitCard) },
      ];
    }

    let res;
    try {
      res = await api.post(`/sales/${activeSaleId}/checkout/`, {
        payment_method: method,
        payment_splits,
      });
    } catch (err) {
      setMessage(
        err.response?.data?.detail || "Greška pri završavanju prodaje.",
      );
      setTimeout(() => setMessage(""), 2500);
      return;
    }

    const saleId = res.data.id;
    const receiptNo = res.data.receipt_number;
    setOpenSales((prev) => {
      const filtered = prev.filter((s) => s.id !== saleId);
      setActiveSaleId(filtered[0]?.id || null);
      return filtered;
    });
    setSplitOpen(false);
    setMessage(`Prodaja završena! Račun #${receiptNo}`);
    try {
      await downloadReceipt(saleId);
    } catch {
      setMessage(`Prodaja završena! PDF računa #${receiptNo} nije preuzet.`);
    }
    setTimeout(() => setMessage(""), 2500);
  };

  const finishSale = () => finishSaleDirect();

  const downloadReceipt = async (saleId) => {
    const token = localStorage.getItem("access_token");
    const pdfRes = await fetch(
      `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/sales/${saleId}/receipt/`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!pdfRes.ok) throw new Error("PDF računa nije dostupan.");
    const blob = await pdfRes.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `racun-${saleId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearSearch = () => {
    setSearchQuery("");
    searchInputRef.current?.focus();
  };

  const cartItems = activeSale?.items || [];
  const total = parseFloat(activeSale?.total || 0);
  const discountAmount = parseFloat(activeSale?.discount_amount || 0);

  return (
    <div className="pos-wrap">
      {/* TABS */}
      <div className="tabs-bar">
        <div className="tabs-scroll">
          {openSales.map((s, idx) => (
            <div
              key={s.id}
              className={`tab ${s.id === activeSaleId ? "active" : ""} ${s.status === "HELD" ? "held" : ""}`}
              onClick={() => switchToSale(s.id)}
              onDoubleClick={() => s.status === "HELD" && resumeSale(s.id)}
            >
              <span className="tab-label">
                {s.status === "HELD" && <PauseIcon />}
                {s.receipt_number || `Račun ${idx + 1}`}
              </span>
              <span className="tab-total">
                {parseFloat(s.total).toFixed(2)}
              </span>
              <button
                className="tab-close"
                onClick={(e) => {
                  e.stopPropagation();
                  cancelSale(s.id);
                }}
                title="Otkaži"
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <button className="tab-new" onClick={createNewSale}>
          + Novi
        </button>
      </div>

      <div className="pos-body">
        <div className="pos-left">
          <div className="pos-search-row">
            <form className="barcode-bar" onSubmit={handleBarcode}>
              <input
                ref={barcodeInputRef}
                autoFocus
                placeholder="Skeniraj barkod [F1]"
                value={barcode}
                onChange={(e) => setBarcode(e.target.value)}
                inputMode="numeric"
              />
              <button type="submit">Dodaj</button>
            </form>

            <div className="search-bar">
              <span className="search-icon">
                <SearchIcon />
              </span>
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Pretraži proizvod [F2]"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoComplete="off"
              />
              {searchQuery && (
                <button className="search-clear" onClick={clearSearch}>
                  ×
                </button>
              )}
            </div>
          </div>

          {/* CATEGORIES */}
          <div className="categories-bar">
            {categories.map((cat) => (
              <button
                key={cat}
                className={`category-chip ${selectedCategory === cat ? "active" : ""}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat === "all" ? "Sve" : cat}
              </button>
            ))}
          </div>

          {message && <div className="toast">{message}</div>}

          <div className="products-info">
            Prikazano: {filteredProducts.length}
            {searchQuery && ` | "${searchQuery}"`}
          </div>

          {/* PRODUCTS */}
          <div className="product-grid">
            {filteredProducts.length === 0 && (
              <div className="no-products">
                Nema proizvoda za "{searchQuery}"
              </div>
            )}
            {filteredProducts.map((p) => (
              <button
                key={p.id}
                className={`product-tile ${stockFlash[p.id] ? "flash" : ""}`}
                onClick={() => addProduct(p, 1)}
                disabled={p.stock <= 0}
                title={p.name}
              >
                <div className="pt-name">{p.name}</div>
                <div className="pt-price">{p.final_price}</div>
                <div className="pt-stock">Stanje: {p.stock}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="pos-right">
          <div className="cart-header">
            <h3>Korpa: {activeSale?.receipt_number || "Novi račun"}</h3>
            <button
              className="mobile-toggle"
              onClick={() => setIsMobileCartOpen((v) => !v)}
            >
              {isMobileCartOpen ? "▼" : "▲"}
            </button>
          </div>

          <div className={`cart-list ${isMobileCartOpen ? "open" : ""}`}>
            {cartItems.length === 0 && (
              <div className="empty">Prazna korpa</div>
            )}
            {cartItems.map((i) => (
              <div key={i.id} className="cart-item">
                <div className="cart-item-header">
                  <b>{i.product_name}</b>
                  <button
                    className="remove-btn"
                    onClick={() => removeItem(i.id)}
                    title="Ukloni"
                  >
                    ×
                  </button>
                </div>
                <div className="cart-item-body">
                  <div className="qty-controls">
                    <button onClick={() => updateItemQty(i.id, i.quantity - 1)}>
                      −
                    </button>
                    <span>{i.quantity}</span>
                    <button onClick={() => updateItemQty(i.id, i.quantity + 1)}>
                      +
                    </button>
                  </div>
                  <div className="cart-item-total">
                    {parseFloat(i.line_total).toFixed(2)} KM
                  </div>
                </div>
              </div>
            ))}
          </div>

          {discountAmount > 0 && (
            <div className="discount-info">
              Popust {activeSale?.discount_percent}% −{" "}
              {discountAmount.toFixed(2)} KM
            </div>
          )}

          <div className="action-buttons">
            <button
              className="action-btn"
              onClick={() => setDiscountOpen(true)}
              title="F6"
            >
              Popust
            </button>
            <button className="action-btn" onClick={openSplit} title="F7">
              Split
            </button>
            <button className="action-btn" onClick={holdSale} title="F8">
              Zadrži
            </button>
          </div>

          <div className="payment-row">
            <label>Plaćanje</label>
            <select
              value={payment}
              onChange={(e) => setPayment(e.target.value)}
            >
              <option value="CASH">Gotovina [F3]</option>
              <option value="CARD">Kartica [F4]</option>
            </select>
          </div>

          <div className="total-bar">
            <span>Ukupno</span>
            <b>{total.toFixed(2)} KM</b>
          </div>

          <button
            className="finish-btn"
            onClick={finishSale}
            disabled={cartItems.length === 0}
          >
            Završi prodaju
          </button>
        </div>
      </div>

      {/* MODAL: POPUST */}
      {discountOpen && (
        <div className="modal-overlay" onClick={() => setDiscountOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Popust na račun</h3>
            <div className="modal-body">
              <label>Procenat</label>
              <input
                type="number"
                min="0"
                max="100"
                value={discountPercent}
                onChange={(e) => setDiscountPercent(e.target.value)}
                autoFocus
              />
              <div className="quick-discounts">
                {[5, 10, 15, 20, 25, 30].map((p) => (
                  <button key={p} onClick={() => setDiscountPercent(p)}>
                    {p}%
                  </button>
                ))}
              </div>
              <p className="hint">
                Popust veći od 20% zahteva manager ovlašćenje.
              </p>
            </div>
            <div className="modal-actions">
              <button onClick={applyDiscount}>Primeni</button>
              <button
                onClick={() => setDiscountOpen(false)}
                className="secondary"
              >
                Otkaži
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SPLIT */}
      {splitOpen && (
        <div className="modal-overlay" onClick={() => setSplitOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Split plaćanje</h3>
            <div className="modal-body">
              <p>
                Ukupno: <b>{total.toFixed(2)} KM</b>
              </p>
              <label>Gotovina (KM)</label>
              <input
                type="number"
                step="0.01"
                value={splitCash}
                onChange={(e) => {
                  const v = parseFloat(e.target.value) || 0;
                  setSplitCash(v);
                  setSplitCard(parseFloat((total - v).toFixed(2)));
                }}
              />
              <label>Kartica (KM)</label>
              <input
                type="number"
                step="0.01"
                value={splitCard}
                onChange={(e) => {
                  const v = parseFloat(e.target.value) || 0;
                  setSplitCard(v);
                  setSplitCash(parseFloat((total - v).toFixed(2)));
                }}
              />
              <p
                className={
                  Math.abs(splitCash + splitCard - total) < 0.01
                    ? "ok"
                    : "error"
                }
              >
                Zbir: {(splitCash + splitCard).toFixed(2)} / {total.toFixed(2)}{" "}
                KM
              </p>
            </div>
            <div className="modal-actions">
              <button onClick={() => finishSaleDirect("SPLIT")}>Završi</button>
              <button onClick={() => setSplitOpen(false)} className="secondary">
                Otkaži
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
