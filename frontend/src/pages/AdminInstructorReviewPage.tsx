import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import {
    downloadInstructorApplicationDocument,
    getInstructorApplications,
    reviewInstructorApplication,
    type InstructorApplicationSummary,
} from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function AdminInstructorReviewPage() {
    const { auth } = useAuth();
    const [applications, setApplications] = useState<InstructorApplicationSummary[]>([]);
    const [notes, setNotes] = useState<Record<number, string>>({});
    const [loading, setLoading] = useState(true);
    const [busyId, setBusyId] = useState<number | null>(null);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    const refresh = useCallback(async () => {
        if (!auth?.token || auth.user.role !== "ADMIN") return;
        setLoading(true);
        setError("");
        try {
            const response = await getInstructorApplications(auth.token);
            setApplications(response.results);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load instructor applications.");
        } finally {
            setLoading(false);
        }
    }, [auth]);

    const applicationToken = auth?.token;
    const applicationRole = auth?.user.role;
    useEffect(() => {
        if (!applicationToken || applicationRole !== "ADMIN") return;

        let cancelled = false;
        getInstructorApplications(applicationToken)
            .then(response => {
                if (!cancelled) setApplications(response.results);
            })
            .catch(loadError => {
                if (!cancelled) {
                    setError(loadError instanceof Error ? loadError.message : "Unable to load instructor applications.");
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [applicationToken, applicationRole]);

    async function download(applicationId: number, documentType: "cv" | "qualification", fallbackName: string) {
        if (!auth?.token) return;
        setError("");
        try {
            const blob = await downloadInstructorApplicationDocument(applicationId, documentType, auth.token);
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = fallbackName || `${documentType}-${applicationId}`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        } catch (downloadError) {
            setError(downloadError instanceof Error ? downloadError.message : "Unable to download document.");
        }
    }

    async function decide(application: InstructorApplicationSummary, decision: "approve" | "reject") {
        if (!auth?.token) return;
        if (decision === "reject" && !notes[application.id]?.trim() && !window.confirm("Reject this application without adding a note for the applicant?")) return;
        if (decision === "approve" && !window.confirm(`Approve ${application.username} as a Tech Haven instructor?`)) return;
        setBusyId(application.id);
        setError("");
        setMessage("");
        try {
            const response = await reviewInstructorApplication(application.id, decision, notes[application.id] ?? "", auth.token);
            setApplications(current => current.filter(item => item.id !== application.id));
            setMessage(`${application.username}: ${response.detail}`);
        } catch (reviewError) {
            setError(reviewError instanceof Error ? reviewError.message : "Unable to review this application.");
        } finally {
            setBusyId(null);
        }
    }

    return (
        <div className="page">
            <header className="page-heading">
                <div>
                    <span className="eyebrow">PHASE 2 · ADMINISTRATOR REVIEW</span>
                    <h1>Instructor applications</h1>
                    <p>Review verified email applicants and their supporting documents. Approval is the only step that assigns the INSTRUCTOR role and staff permissions.</p>
                </div>
                <button type="button" className="secondary-button" onClick={() => void refresh()} disabled={loading}>Refresh</button>
            </header>
            {error && <div className="auth-error" role="alert">{error}</div>}
            {message && <div className="application-status" role="status">{message}</div>}
            {loading && <div className="status-card">Loading applications…</div>}
            {!loading && !error && applications.length === 0 && (
                <div className="status-card">There are no email-verified instructor applications waiting for review.</div>
            )}
            <div className="application-review-list">
                {applications.map(application => (
                    <article className="application-review-card" key={application.id}>
                        <span className="eyebrow">APPLICATION #{application.id} · {new Date(application.created_at).toLocaleString()}</span>
                        <h2>{application.username}</h2>
                        <p><strong>Email:</strong> {application.email}</p>
                        <p><strong>Qualification:</strong> {application.qualification}</p>
                        <p><strong>Awarding institution:</strong> {application.awarding_institution}</p>
                        <p><strong>Experience:</strong><br />{application.experience_summary}</p>
                        <p><strong>Email verified:</strong> {application.email_verified_at ? new Date(application.email_verified_at).toLocaleString() : "Not verified"}</p>
                        <div className="application-review-actions">
                            <button type="button" onClick={() => void download(application.id, "cv", application.cv_filename)}>Download CV ({application.cv_filename})</button>
                            {application.has_qualification_document && <button type="button" className="secondary" onClick={() => void download(application.id, "qualification", application.qualification_filename)}>Download supporting credential</button>}
                        </div>
                        <label style={{ display: "grid", gap: 8, marginTop: 18, color: "#4B1222", fontWeight: 700 }}>
                            Review notes (optional; included in rejection email)
                            <textarea value={notes[application.id] ?? ""} onChange={event => setNotes(current => ({ ...current, [application.id]: event.target.value }))} maxLength={3000} rows={3} />
                        </label>
                        <div className="application-review-actions">
                            <button type="button" onClick={() => void decide(application, "approve")} disabled={busyId === application.id}>{busyId === application.id ? "Saving…" : "Approve instructor"}</button>
                            <button type="button" className="secondary" onClick={() => void decide(application, "reject")} disabled={busyId === application.id}>{busyId === application.id ? "Saving…" : "Reject application"}</button>
                        </div>
                    </article>
                ))}
            </div>
            <p className="instructor-apply-prompt"><Link to="/instructor">Back to instructor workspace</Link></p>
        </div>
    );
}
