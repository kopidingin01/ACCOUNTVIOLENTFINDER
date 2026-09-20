import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import Layout from "../components/Layout";
import { useAuth } from "../hooks/useAuth";
import type { Role, User } from "../types";

const ROLES: Role[] = ["ADMIN", "ANALYST", "REVIEWER", "AUDITOR", "VIEWER"];

const ROLE_BLURB: Record<Role, string> = {
  ADMIN: "Akses penuh, termasuk kelola platform, kebijakan, dan pengguna lain.",
  ANALYST: "Buat case, kelola evidence, jalankan assessment, buat report, pakai Account Finder.",
  REVIEWER: "Approve/reject/minta bukti tambahan di Review Queue.",
  AUDITOR: "Lihat Audit Logs saja.",
  VIEWER: "Lihat semua data, tidak bisa mengubah apapun.",
};

export default function Users() {
  const { hasRole } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({ username: "", email: "", full_name: "", password: "", role: "ANALYST" as Role });

  function refresh() {
    api.get<User[]>("/users").then(setUsers).catch(() => {});
  }
  useEffect(refresh, []);

  async function createUser() {
    setError(null);
    setMessage(null);
    try {
      const created = await api.post<User>("/users", form);
      setMessage(`Akun "${created.username}" berhasil dibuat dengan role ${created.role}.`);
      setForm({ username: "", email: "", full_name: "", password: "", role: "ANALYST" });
      setShowForm(false);
      refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError("Username atau email sudah dipakai.");
      } else {
        setError(e instanceof ApiError ? String(e.detail) : "Gagal membuat akun.");
      }
    }
  }

  async function toggleActive(user: User) {
    await api.patch(`/users/${user.id}`, { is_active: !user.is_active });
    refresh();
  }

  if (!hasRole("ADMIN")) {
    return (
      <Layout title="Users">
        <div className="text-rose-400 text-sm">Hanya ADMIN yang bisa mengelola pengguna.</div>
      </Layout>
    );
  }

  return (
    <Layout title="Users">
      <p className="text-sm text-slate-400 mb-4">
        Tambahkan anggota tim supaya bisa ikut mengumpulkan evidence, menjalankan assessment, atau meninjau laporan —
        masing-masing dibatasi sesuai role yang Anda pilih untuknya.
      </p>

      <div className="mb-4">
        <button onClick={() => setShowForm((s) => !s)} className="text-sm px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white">
          {showForm ? "Batal" : "+ Tambah Anggota Tim"}
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-surface-border bg-surface-panel p-4 space-y-3 max-w-md">
          <input
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
          <input
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            placeholder="Nama lengkap"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
          <input
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <input
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            placeholder="Password sementara (min. 8 karakter)"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <select
            className="w-full rounded-md bg-surface border border-surface-border px-3 py-2 text-sm"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <p className="text-[11px] text-slate-500">{ROLE_BLURB[form.role]}</p>
          {error && <div className="text-sm text-rose-400">{error}</div>}
          <button onClick={createUser} className="px-3 py-1.5 rounded-md bg-accent-DEFAULT text-white text-sm">
            Buat Akun
          </button>
        </div>
      )}

      {message && <div className="mb-4 text-sm text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 rounded-md px-3 py-2">{message}</div>}

      <div className="rounded-lg border border-surface-border bg-surface-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Username</th>
              <th className="text-left px-4 py-2">Nama</th>
              <th className="text-left px-4 py-2">Email</th>
              <th className="text-left px-4 py-2">Role</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-surface-border">
                <td className="px-4 py-2">{u.username}</td>
                <td className="px-4 py-2 text-slate-400">{u.full_name}</td>
                <td className="px-4 py-2 text-slate-400">{u.email}</td>
                <td className="px-4 py-2">
                  <span className="px-2 py-0.5 rounded bg-white/5 text-[11px] text-slate-300 uppercase tracking-wide">{u.role}</span>
                </td>
                <td className="px-4 py-2">
                  {u.is_active ? (
                    <span className="text-emerald-400 text-xs">Aktif</span>
                  ) : (
                    <span className="text-rose-400 text-xs">Nonaktif</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <button onClick={() => toggleActive(u)} className="text-xs text-blue-400 hover:underline">
                    {u.is_active ? "Nonaktifkan" : "Aktifkan"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
