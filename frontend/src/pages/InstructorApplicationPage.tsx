import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import {
    createInstructorApplication,
    resendInstructorApplicationOtp,
    verifyInstructorApplicationOtp,
} from "../api/auth";

export default function InstructorApplicationPage() {
    const [phase, setPhase] = useState<"application" | "otp" | "review">("application");
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [qualification, setQualification] = useState("");
    const [institution, setInstitution] = useState("");
    const [experience, setExperience] = useState("");
    const [cv, setCv] = useState<File | null>(null);
    const [qualificationDocument, setQualificationDocument] = useState<File | null>(null);
    const [applicationId, setApplicationId] = useState<number | null>(null);
    const [otp, setOtp] = useState("");
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    async function submitApplication(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        setMessage("");
        if (password !== passwordConfirm) {
            setError("Your passwords do not match.");
            return;
        }
        if (!cv) {
            setError("Upload your CV to submit an instructor application.");
            return;
        }
        const cvExt = cv.name.split(".").pop()?.toLowerCase();
        if (!cvExt || !["pdf", "doc", "docx"].includes(cvExt)) {
            setError("Your CV must be a PDF, DOC, or DOCX file.");
            return;
        }
        if (cv.size > 10 * 1024 * 1024 || (qualificationDocument && qualificationDocument.size > 10 * 1024 * 1024)) {
            setError("Each file must be 10 MB or smaller.");
            return;
        }
        setLoading(true);
        try {
            const data = new FormData();
            data.append("username", username.trim());
            data.append("email", email.trim());
            data.append("password", password);
            data.append("password_confirm", passwordConfirm);
            data.append("qualification", qualification.trim());
            data.append("awarding_institution", institution.trim());
            data.append("experience_summary", experience.trim());
            data.append("cv", cv);
            if (qualificationDocument) data.append("qualification_document", qualificationDocument);
            const response = await createInstructorApplication(data);
            setApplicationId(response.application_id);
            setPhase("otp");
            setMessage(`We sent a verification code to ${response.email}. Enter it below to complete Phase 1.`);
        } catch (submissionError) {
            setError(submissionError instanceof Error ? submissionError.message : "Unable to submit your application.");
        } finally {
            setLoading(false);
        }
    }

    async function verifyOtp(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!applicationId) return;
        setError("");
        setMessage("");
        setLoading(true);
        try {
            const response = await verifyInstructorApplicationOtp(applicationId, otp.trim());
            setPhase("review");
            setMessage(response.detail);
        } catch (verificationError) {
            setError(verificationError instanceof Error ? verificationError.message : "Unable to verify the code.");
        } finally {
            setLoading(false);
        }
    }

    async function resendOtp() {
        if (!applicationId) return;
        setError("");
        setMessage("");
        setLoading(true);
        try {
            const response = await resendInstructorApplicationOtp(applicationId);
            setMessage(response.detail);
        } catch (resendError) {
            setError(resendError instanceof Error ? resendError.message : "Unable to resend the code.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-page">
            <section className="auth-card instructor-application-card" aria-labelledby="instructor-apply-title">
                <Link to="/" className="auth-brand" aria-label="Tech Haven home">
                    <span className="brand-mark">TH</span>
                    <span className="auth-brand-copy"><strong>Tech Haven</strong><span>Learn. Build. Prove.</span></span>
                </Link>
                <div className="auth-heading">
                    <span className="eyebrow">INSTRUCTOR ONBOARDING · TWO PHASES</span>
                    <h1 id="instructor-apply-title">Apply to teach.</h1>
                    <p>Submit your qualifications and CV. Verify your email, then wait for an administrator to review your credentials before instructor access is granted.</p>
                </div>
                <div className="application-status">
                    <strong>Phase 1:</strong> submit credentials and verify your email by OTP.<br />
                    <strong>Phase 2:</strong> an administrator reviews your application and decides whether to approve instructor access.
                </div>
                {error && <div className="auth-error" role="alert">{error}</div>}
                {message && <div className="application-status" role="status">{message}</div>}
                {phase === "application" && (
                    <form className="auth-form" onSubmit={submitApplication} encType="multipart/form-data">
                        <label>Username<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" minLength={3} maxLength={150} required /></label>
                        <label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" required /></label>
                        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" minLength={8} required /></label>
                        <label>Confirm password<input type="password" value={passwordConfirm} onChange={e => setPasswordConfirm(e.target.value)} autoComplete="new-password" minLength={8} required /></label>
                        <label>Highest relevant qualification<input value={qualification} onChange={e => setQualification(e.target.value)} placeholder="e.g. BSc Computer Science" maxLength={200} required /></label>
                        <label>Awarding institution<input value={institution} onChange={e => setInstitution(e.target.value)} placeholder="University or certification body" maxLength={200} required /></label>
                        <label>Teaching and professional experience<textarea value={experience} onChange={e => setExperience(e.target.value)} minLength={20} maxLength={3000} rows={5} placeholder="Describe relevant subjects, teaching experience, certifications and professional work." required /></label>
                        <label>Curriculum vitae (CV) · PDF, DOC or DOCX · up to 10 MB<input type="file" accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={e => setCv(e.target.files?.[0] ?? null)} required /></label>
                        <label>Qualification certificate / supporting credential · optional · up to 10 MB<input type="file" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={e => setQualificationDocument(e.target.files?.[0] ?? null)} /></label>
                        <button type="submit" className="primary-button auth-submit" disabled={loading}>{loading ? "Submitting application…" : "Submit application & send OTP"}</button>
                    </form>
                )}
                {phase === "otp" && (
                    <form className="auth-form" onSubmit={verifyOtp}>
                        <label>Six-digit email verification code<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))} required /></label>
                        <button type="submit" className="primary-button auth-submit" disabled={loading}>{loading ? "Verifying…" : "Verify email (Phase 1)"}</button>
                        <button type="button" className="secondary-button" onClick={resendOtp} disabled={loading}>Resend verification code</button>
                        <p className="instructor-apply-prompt">Your application reference is <strong>{applicationId}</strong>. Keep it for support requests.</p>
                    </form>
                )}
                {phase === "review" && (
                    <div className="auth-form">
                        <div className="application-status"><strong>Phase 1 complete — email verified.</strong><br />Your application is awaiting Phase 2 administrator review. Your account remains inactive: you cannot sign in until a superuser approves your application.</div>
                        <Link className="primary-button auth-submit" to="/">Back to Tech Haven</Link>
                    </div>
                )}
                <div className="auth-footer">
                    <p>Already have an account? <Link to="/login">Sign in</Link></p>
                    <Link to="/register">Register as a student</Link>
                    <br /><Link to="/">← Back to Tech Haven</Link>
                </div>
            </section>
        </div>
    );
}
