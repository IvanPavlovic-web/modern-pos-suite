import { useEffect, useState } from "react";
import api from "../api";

export default function Admin() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: "",
    barcode: "",
    price: "",
    stock: "",
    tax_rate: 20,
    discount_percent: 0,
    category: "",
  });

  const load = async () => {
    const [p, c] = await Promise.all([
      api.get("/products/?page_size=1000"),
      api.get("/categories/"),
    ]);
    setProducts(p.data.results || p.data);
    setCategories(c.data.results || c.data);
  };

  useEffect(() => {
    load();
  }, []);

  const startEdit = (p) => {
    setEditing(p.id);
    setForm({
      name: p.name,
      barcode: p.barcode || "",
      price: p.price,
      stock: p.stock,
      tax_rate: p.tax_rate,
      discount_percent: p.discount_percent,
      category: p.category || "",
    });
  };

  const startCreate = () => {
    setEditing("new");
    setForm({
      name: "",
      barcode: "",
      price: "",
      stock: "",
      tax_rate: 20,
      discount_percent: 0,
      category: "",
    });
  };

  const save = async () => {
    try {
      if (editing === "new") {
        await api.post("/products/", form);
      } else {
        await api.put(`/products/${editing}/`, form);
      }
      setEditing(null);
      load();
    } catch (e) {
      alert("Greška: " + JSON.stringify(e.response?.data));
    }
  };

  const remove = async (id) => {
    if (!confirm("Obrisati proizvod?")) return;
    await api.delete(`/products/${id}/`);
    load();
  };

  return (
    <div className="admin-wrap">
      <div className="admin-head">
        <h2>Upravljanje proizvodima</h2>
        <button onClick={startCreate}>+ Novi proizvod</button>
      </div>

      {editing && (
        <div className="edit-form">
          <h3>{editing === "new" ? "Novi" : "Uredi"} proizvod</h3>
          <div className="form-grid">
            <label>
              Naziv
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label>
              Barkod
              <input
                value={form.barcode}
                onChange={(e) => setForm({ ...form, barcode: e.target.value })}
              />
            </label>
            <label>
              Cijena
              <input
                type="number"
                step="0.01"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
              />
            </label>
            <label>
              Stanje
              <input
                type="number"
                value={form.stock}
                onChange={(e) => setForm({ ...form, stock: e.target.value })}
              />
            </label>
            <label>
              PDV %
              <input
                type="number"
                step="0.01"
                value={form.tax_rate}
                onChange={(e) => setForm({ ...form, tax_rate: e.target.value })}
              />
            </label>
            <label>
              Popust %
              <input
                type="number"
                step="0.01"
                value={form.discount_percent}
                onChange={(e) =>
                  setForm({ ...form, discount_percent: e.target.value })
                }
              />
            </label>
            <label>
              Kategorija
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                <option value="">Bez kategorije</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-actions">
            <button onClick={save}>Sačuvaj</button>
            <button onClick={() => setEditing(null)} className="secondary">
              Otkaži
            </button>
          </div>
        </div>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Naziv</th>
            <th>Barkod</th>
            <th>Cijena</th>
            <th>Stanje</th>
            <th>PDV %</th>
            <th>Popust %</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td>{p.id}</td>
              <td>{p.name}</td>
              <td>{p.barcode}</td>
              <td>{p.price} KM</td>
              <td className={p.stock < 5 ? "low-stock" : ""}>{p.stock}</td>
              <td>{p.tax_rate}</td>
              <td>{p.discount_percent}</td>
              <td>
                <button onClick={() => startEdit(p)}>Uredi</button>
                <button onClick={() => remove(p.id)} className="danger">
                  Obriši
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
