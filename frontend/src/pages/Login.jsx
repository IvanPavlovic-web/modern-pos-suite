import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("cashier1");
  const [password, setPassword] = useState("cashier123");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/pos");
    } catch (err) {
      setError("Pogrešno korisničko ime ili lozinka.");
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-box" onSubmit={submit}>
        <h2>Prijava</h2>
        {error && <div className="error">{error}</div>}
        <label>Korisničko ime</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} />
        <label>Lozinka</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Prijavi se</button>
        <div className="hint">
          Demo: <b>admin/admin123</b>, <b>manager/manager123</b>,{" "}
          <b>cashier1/cashier123</b>
        </div>
      </form>
    </div>
  );
}
