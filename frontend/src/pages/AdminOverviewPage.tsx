import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { getAdminOverview } from "../api/admin";
import { useAuth } from "../context/AuthContext";

function showDate(value: string | null) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

export default function AdminOverviewPage() {
    const { auth } = useAuth();
    const token = auth?.token ?? "";
    const isAdmin = auth?.user.role === "ADMIN";
    const overview = useQuery({
        queryKey: ["admin-overview", token],
        queryFn: () => getAdminOverview(token),
        enabled: Boolean(token && isAdmin),
    });
    const data = overview.data;
    const summary = data?.summary;

    return (
        <div className="page admin-overview-page">
            <header className="page-heading">
                <div>
                    <span className="eyebrow">PLATFORM CONTROL · ADMINISTRATOR</span>
                    <h1>Admin overview</h1>
                    <p>Monitor learner access, course activity, assessment volume, certificates, and instructor onboarding.</p>
                </div>
                <button type="button" className="secondary-button" onClick={() => void overview.refetch()} disabled={overview.isFetching}>Refresh overview</button>
            </header>
            <nav className="admin-dashboard-links" aria-label="Administrator tools">
                <Link to="/admin/accounts">Manage accounts →</Link>
                <Link to="/admin/instructor-applications">Review instructor applications →</Link>
                <Link to="/admin/audit-log">View audit log →</Link>
            </nav>
            {overview.isPending && <div className="status-card">Loading platform statistics…</div>}
            {overview.isError && <div className="auth-error" role="alert">{overview.error instanceof Error ? overview.error.message : "Unable to load platform statistics."}</div>}
            {summary && (
                <>
                    <section className="admin-overview-section">
                        <div className="admin-section-heading"><span className="eyebrow">IDENTITIES & ACCESS</span><h2>Accounts</h2></div>
                        <div className="admin-overview-metrics">
                            <article><span>Total accounts</span><strong>{summary.total_accounts}</strong></article>
                            <article><span>Active</span><strong>{summary.active_accounts}</strong></article>
                            <article><span>Inactive</span><strong>{summary.inactive_accounts}</strong></article>
                            <article><span>Students</span><strong>{summary.students}</strong></article>
                            <article><span>Instructors</span><strong>{summary.instructors}</strong></article>
                            <article><span>Administrators</span><strong>{summary.administrators}</strong></article>
                        </div>
                    </section>
                    <section className="admin-overview-section">
                        <div className="admin-section-heading"><span className="eyebrow">LEARNING ACTIVITY</span><h2>Platform usage</h2></div>
                        <div className="admin-overview-metrics">
                            <article><span>Courses</span><strong>{summary.courses}</strong></article>
                            <article><span>Enrollments</span><strong>{summary.enrollments}</strong></article>
                            <article><span>Submissions</span><strong>{summary.submissions}</strong></article>
                            <article><span>Pending reviews</span><strong>{summary.pending_submissions}</strong></article>
                            <article><span>Graded submissions</span><strong>{summary.graded_submissions}</strong></article>
                            <article><span>Certificates issued</span><strong>{summary.certificates_issued}</strong></article>
                        </div>
                    </section>
                    <section className="admin-overview-section">
                        <div className="admin-section-heading"><span className="eyebrow">INSTRUCTOR ONBOARDING</span><h2>Application pipeline</h2></div>
                        <div className="admin-overview-metrics admin-overview-metrics-compact">
                            <article><span>Awaiting email verification</span><strong>{summary.instructor_applications_pending_email}</strong></article>
                            <article><span>Awaiting review</span><strong>{summary.instructor_applications_pending_review}</strong></article>
                            <article><span>Approved</span><strong>{summary.instructor_applications_approved}</strong></article>
                            <article><span>Rejected</span><strong>{summary.instructor_applications_rejected}</strong></article>
                        </div>
                    </section>
                    <section className="admin-overview-lower-grid">
                        <article className="admin-overview-panel">
                            <header><div><span className="eyebrow">LATEST REGISTRATIONS</span><h2>Recent accounts</h2></div><Link to="/admin/accounts">View all</Link></header>
                            <div className="admin-overview-list">
                                {data.recent_accounts.map(account => (
                                    <div className="admin-overview-list-row" key={account.id}>
                                        <div><strong>{account.username}</strong><span>{account.email || "No email recorded"}</span></div>
                                        <div className="admin-overview-list-meta"><span className={`admin-status-pill ${account.is_active ? "is-active" : "is-inactive"}`}>{account.is_active ? "Active" : "Inactive"}</span><small>{showDate(account.date_joined)}</small></div>
                                    </div>
                                ))}
                                {data.recent_accounts.length === 0 && <p className="admin-overview-empty">No accounts found.</p>}
                            </div>
                        </article>
                        <article className="admin-overview-panel">
                            <header><div><span className="eyebrow">ACCESS CHANGES</span><h2>Recent audit events</h2></div><Link to="/admin/audit-log">View log</Link></header>
                            <div className="admin-overview-list">
                                {data.recent_audit_events.map(event => (
                                    <div className="admin-overview-list-row" key={event.id}>
                                        <div><strong>{event.action === "ACTIVATED" ? "Account activated" : "Account deactivated"}: {event.target_username}</strong><span>By {event.actor_username}</span><small>{event.reason}</small></div>
                                        <div className="admin-overview-list-meta"><small>{showDate(event.created_at)}</small></div>
                                    </div>
                                ))}
                                {data.recent_audit_events.length === 0 && <p className="admin-overview-empty">No account access changes have been recorded yet.</p>}
                            </div>
                        </article>
                    </section>
                </>
            )}
        </div>
    );
}
