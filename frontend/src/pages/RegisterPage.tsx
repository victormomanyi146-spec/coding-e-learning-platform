import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
    const { isAuthenticated, register } = useAuth();
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    if (isAuthenticated) return <Navigate to="/dashboard" replace />;

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        if (password !== passwordConfirm) {
            setError("The passwords do not match.");
            return;
        }
        setLoading(true);
        try {
            await register(username.trim(), email.trim(), password, passwordConfirm);
            navigate("/dashboard", { replace: true });
        } catch (registrationError) {
            setError(
                registrationError instanceof Error
                    ? registrationError.message
                    : "Unable to create your account.",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-page">
            <section className="auth-card">
                <div className="auth-brand">
                    <div className="brand-mark">TH</div>
                    <div><strong>Tech Haven</strong><span>Learn. Build. Prove.</span></div>
                </div>
                <div className="auth-heading">
                    <span className="eyebrow">CREATE A STUDENT ACCOUNT</span>
                    <h1>Start building<br />your skills.</h1>
                    <p>Create your account to enrol in courses, submit projects and track your progress.</p>
                </div>
                {error && <div className="auth-error" role="alert">{error}</div>}
                <form className="auth-form" onSubmit={handleSubmit}>
                    <label>Username
                        <input value={username} onChange={event => setUsername(event.target.value)} autoComplete="username" required minLength={3} />
                    </label>
                    <label>Email address
                        <input type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" required />
                    </label>
                    <label>Password
                        <input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" required minLength={8} />
                    </label>
                    <label>Confirm password
                        <input type="password" value={passwordConfirm} onChange={event => setPasswordConfirm(event.target.value)} autoComplete="new-password" required minLength={8} />
                    </label>
                    <button type="submit" className="primary-button auth-submit" disabled={loading}>
                        {loading ? "Creating account..." : "Create account"}
                    </button>
                </form>
                <div className="auth-footer">
                    <p>Already registered? <Link to="/login">Sign in</Link></p>
                    <Link to="/">← Back to Tech Haven</Link>
                </div>
            </section>
        </div>
    );
}
