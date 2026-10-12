import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAdminAccounts, setAdminAccountActive, type AdminAccount, type AccountRoleFilter, type AccountStatusFilter } from "../api/admin";
import { useAuth } from "../context/AuthContext";

function formatDate(value: string | null) {
    if (!value) return "Never";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

export default function AdminAccountsPage() {
    const { auth } = useAuth();
    const queryClient = useQueryClient();
    const token = auth?.token ?? "";
    const isAdmin = auth?.user.role === "ADMIN";
    const [searchInput, setSearchInput] = useState("");
    const [search, setSearch] = useState("");
    const [role, setRole] = useState<AccountRoleFilter>("ALL");
    const [accountStatus, setAccountStatus] = useState<AccountStatusFilter>("ALL");
    const [page, setPage] = useState(1);
    const [notice, setNotice] = useState("");

    const accountsQuery = useQuery({
        queryKey: ["admin-accounts", token, search, role, accountStatus, page],
        queryFn: () => getAdminAccounts(token, { q: search, role, status: accountStatus, page, page_size: 25 }),
        enabled: Boolean(token && isAdmin),
    });

    const statusMutation = useMutation({
        mutationFn: ({ account, active, reason }: { account: AdminAccount; active: boolean; reason: string }) =>
            setAdminAccountActive(account.id, active, reason, token),
        onSuccess: async (response) => {
            setNotice(response.detail);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["admin-accounts"] }),
                queryClient.invalidateQueries({ queryKey: ["admin-overview"] }),
                queryClient.invalidateQueries({ queryKey: ["admin-audit-log"] }),
            ]);
        },
        onError: (error: Error) => setNotice(error.message || "The account could not be updated."),
    });

    const data = accountsQuery.data;

    function submitSearch(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setPage(1);
        setSearch(searchInput.trim());
    }

    function changeRoleFilter(value: AccountRoleFilter) {
        setRole(value);
        setPage(1);
    }

    function changeStatusFilter(value: AccountStatusFilter) {
        setAccountStatus(value);
        setPage(1);
    }

    function toggleAccount(account: AdminAccount) {
        const active = !account.is_active;
        const action = active ? "reactivate" : "deactivate";
        const warning = active
            ? `Reactivate ${account.username}? They will be able to sign in again.`
            : `Deactivate ${account.username}? Their current API token will be revoked and they will no longer be able to sign in.`;
        if (!window.confirm(`${action === "reactivate" ? "Reactivate" : "Deactivate"} this account?\n\n${warning}`)) return;
        const reason = window.prompt(`Enter the reason to ${action} ${account.username}. This reason will be recorded in the audit log.`, "");
        if (reason === null) return;
        if (!reason.trim()) {
            window.alert("A reason is required before changing account access.");
            return;
        }
        setNotice("");
        statusMutation.mutate({ account, active, reason: reason.trim() });
    }

    return (
        <div className="page admin-accounts-page">
            <header className="page-heading">
                <div>
                    <span className="eyebrow">PLATFORM CONTROL · ADMINISTRATOR</span>
                    <h1>Account management</h1>
                    <p>Search learner and instructor accounts, review access status, and safely activate or suspend accounts.</p>
                </div>
                <button type="button" className="secondary-button" onClick={() => void accountsQuery.refetch()} disabled={accountsQuery.isFetching}>Refresh accounts</button>
            </header>

            <div className="admin-account-links">
                <Link to="/admin/instructor-applications">Review instructor applications →</Link>
            </div>

            {data && (
                <section className="admin-account-metrics" aria-label="Account totals">
                    <article><span>Total accounts</span><strong>{data.summary.total}</strong></article>
                    <article><span>Students</span><strong>{data.summary.students}</strong></article>
                    <article><span>Instructors</span><strong>{data.summary.instructors}</strong></article>
                    <article><span>Administrators</span><strong>{data.summary.admins}</strong></article>
                    <article><span>Inactive accounts</span><strong>{data.summary.inactive}</strong></article>
                </section>
            )}

            <form className="admin-account-filters" onSubmit={submitSearch}>
                <label>
                    Search accounts
                    <input value={searchInput} onChange={event => setSearchInput(event.target.value)} placeholder="Username, email, first or last name" maxLength={120} />
                </label>
                <label>
                    Role
                    <select value={role} onChange={event => changeRoleFilter(event.target.value as AccountRoleFilter)}>
                        <option value="ALL">All roles</option>
                        <option value="STUDENT">Students</option>
                        <option value="INSTRUCTOR">Instructors</option>
                        <option value="ADMIN">Administrators</option>
                    </select>
                </label>
                <label>
                    Account status
                    <select value={accountStatus} onChange={event => changeStatusFilter(event.target.value as AccountStatusFilter)}>
                        <option value="ALL">All statuses</option>
                        <option value="ACTIVE">Active</option>
                        <option value="INACTIVE">Inactive</option>
                    </select>
                </label>
                <button type="submit">Search</button>
            </form>

            {notice && <div className="application-status" role="status">{notice}</div>}
            {accountsQuery.isError && <div className="auth-error" role="alert">{accountsQuery.error instanceof Error ? accountsQuery.error.message : "Unable to load accounts."}</div>}
            {accountsQuery.isPending && <div className="status-card">Loading account directory…</div>}

            {data && (
                <>
                    <div className="admin-account-table-wrap">
                        <table className="admin-account-table">
                            <thead>
                                <tr><th>Account</th><th>Role</th><th>Status</th><th>Joined</th><th>Last sign-in</th><th>Access</th></tr>
                            </thead>
                            <tbody>
                                {data.results.map(account => (
                                    <tr key={account.id}>
                                        <td>
                                            <strong>{account.username}</strong>
                                            <span>{account.email || "No email recorded"}</span>
                                            {(account.first_name || account.last_name) && <small>{[account.first_name, account.last_name].filter(Boolean).join(" ")}</small>}
                                        </td>
                                        <td><span className={`admin-role-pill role-${account.role.toLowerCase()}`}>{account.role === "ADMIN" ? "Administrator" : account.role === "INSTRUCTOR" ? "Instructor" : "Student"}</span></td>
                                        <td><span className={`admin-status-pill ${account.is_active ? "is-active" : "is-inactive"}`}>{account.is_active ? "Active" : "Inactive"}</span></td>
                                        <td>{formatDate(account.date_joined)}</td>
                                        <td>{formatDate(account.last_login)}</td>
                                        <td>
                                            {account.is_superuser ? (
                                                <span className="admin-protected-account">Protected admin</span>
                                            ) : (
                                                <button
                                                    type="button"
                                                    className={account.is_active ? "admin-account-action danger" : "admin-account-action"}
                                                    onClick={() => toggleAccount(account)}
                                                    disabled={statusMutation.isPending}
                                                >
                                                    {statusMutation.isPending ? "Saving…" : account.is_active ? "Deactivate" : "Reactivate"}
                                                </button>
                                            )}
                                            {account.is_staff && !account.is_superuser && <small className="admin-access-note">Staff-enabled</small>}
                                        </td>
                                    </tr>
                                ))}
                                {data.results.length === 0 && <tr><td colSpan={6} className="admin-account-empty">No accounts match these filters.</td></tr>}
                            </tbody>
                        </table>
                    </div>
                    <footer className="admin-account-pagination">
                        <span>{data.count === 0 ? "0 accounts" : `${(data.page - 1) * data.page_size + 1}–${Math.min(data.page * data.page_size, data.count)} of ${data.count} accounts`}</span>
                        <div>
                            <button type="button" className="secondary-button" onClick={() => setPage(current => Math.max(1, current - 1))} disabled={data.page <= 1 || accountsQuery.isFetching}>Previous</button>
                            <span>Page {data.page} of {data.pages}</span>
                            <button type="button" className="secondary-button" onClick={() => setPage(current => Math.min(data.pages, current + 1))} disabled={data.page >= data.pages || accountsQuery.isFetching}>Next</button>
                        </div>
                    </footer>
                </>
            )}

            <p className="admin-account-safety-note">Administrator accounts are protected on this screen. Instructor privileges are granted through the verified instructor-application approval workflow, not by changing a role in the account directory.</p>
        </div>
    );
}
