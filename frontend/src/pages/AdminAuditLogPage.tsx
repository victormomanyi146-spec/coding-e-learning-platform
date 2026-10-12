import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { getAdminAuditLogs, type AuditActionFilter } from "../api/admin";
import { useAuth } from "../context/AuthContext";

function showDate(value: string | null) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

export default function AdminAuditLogPage() {
    const { auth } = useAuth();
    const token = auth?.token ?? "";
    const isAdmin = auth?.user.role === "ADMIN";
    const [searchInput, setSearchInput] = useState("");
    const [search, setSearch] = useState("");
    const [action, setAction] = useState<AuditActionFilter>("ALL");
    const [page, setPage] = useState(1);
    const logs = useQuery({
        queryKey: ["admin-audit-log", token, search, action, page],
        queryFn: () => getAdminAuditLogs(token, { q: search, action, page, page_size: 25 }),
        enabled: Boolean(token && isAdmin),
    });

    function submitSearch(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setPage(1);
        setSearch(searchInput.trim());
    }

    return (
        <div className="page admin-audit-page">
            <header className="page-heading">
                <div><span className="eyebrow">PLATFORM CONTROL · ACCOUNTABILITY</span><h1>Account access audit log</h1><p>Review who activated or deactivated an account, when the change happened, and the reason recorded by the administrator.</p></div>
                <button type="button" className="secondary-button" onClick={() => void logs.refetch()} disabled={logs.isFetching}>Refresh log</button>
            </header>
            <nav className="admin-dashboard-links" aria-label="Administrator tools">
                <Link to="/admin/overview">Admin overview →</Link>
                <Link to="/admin/accounts">Manage accounts →</Link>
            </nav>
            {logs.data && <section className="admin-audit-summary"><article><span>All access changes</span><strong>{logs.data.summary.all}</strong></article><article><span>Activations</span><strong>{logs.data.summary.activations}</strong></article><article><span>Deactivations</span><strong>{logs.data.summary.deactivations}</strong></article></section>}
            <form className="admin-account-filters admin-audit-filters" onSubmit={submitSearch}>
                <label>Search administrator, account or reason<input value={searchInput} onChange={event => setSearchInput(event.target.value)} placeholder="Search audit events" maxLength={120} /></label>
                <label>Action<select value={action} onChange={event => { setAction(event.target.value as AuditActionFilter); setPage(1); }}><option value="ALL">All access changes</option><option value="ACTIVATED">Activated</option><option value="DEACTIVATED">Deactivated</option></select></label>
                <button type="submit">Search</button>
            </form>
            {logs.isPending && <div className="status-card">Loading audit log…</div>}
            {logs.isError && <div className="auth-error" role="alert">{logs.error instanceof Error ? logs.error.message : "Unable to load audit history."}</div>}
            {logs.data && <>
                <div className="admin-account-table-wrap"><table className="admin-audit-table"><thead><tr><th>Date & time</th><th>Action</th><th>Administrator</th><th>Account</th><th>Reason</th></tr></thead><tbody>
                    {logs.data.results.map(event => <tr key={event.id}><td>{showDate(event.created_at)}</td><td><span className={`admin-audit-action ${event.action === "ACTIVATED" ? "is-activation" : "is-deactivation"}`}>{event.action === "ACTIVATED" ? "Activated" : "Deactivated"}</span></td><td>{event.actor_username}</td><td>{event.target_username}</td><td className="admin-audit-reason">{event.reason}</td></tr>)}
                    {logs.data.results.length === 0 && <tr><td colSpan={5} className="admin-account-empty">No audit events match these filters.</td></tr>}
                </tbody></table></div>
                <footer className="admin-account-pagination"><span>{logs.data.count === 0 ? "0 events" : `${(logs.data.page - 1) * logs.data.page_size + 1}–${Math.min(logs.data.page * logs.data.page_size, logs.data.count)} of ${logs.data.count} events`}</span><div><button type="button" className="secondary-button" onClick={() => setPage(current => Math.max(1, current - 1))} disabled={logs.data.page <= 1 || logs.isFetching}>Previous</button><span>Page {logs.data.page} of {logs.data.pages}</span><button type="button" className="secondary-button" onClick={() => setPage(current => Math.min(logs.data.pages, current + 1))} disabled={logs.data.page >= logs.data.pages || logs.isFetching}>Next</button></div></footer>
            </>}
            <p className="admin-account-safety-note">Audit records are generated on the server only when an account’s active status actually changes. A reason is required for each change.</p>
        </div>
    );
}
