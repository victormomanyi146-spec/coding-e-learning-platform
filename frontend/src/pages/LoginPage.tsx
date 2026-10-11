import { useState } from "react";
import type { FormEvent } from "react";
import {
    Link,
    Navigate,
    useLocation,
    useNavigate,
} from "react-router";
import type { LoginMode } from "../api/auth";
import { useAuth } from "../context/AuthContext";

type AuthView = "signin" | "signup";

const roleOptions: Array<{ value: LoginMode; label: string; hint: string }> = [
    { value: "student", label: "Student", hint: "Learn and track your progress" },
    { value: "instructor", label: "Instructor", hint: "Review assessments and learners" },
    { value: "admin", label: "Administrator", hint: "Manage platform access" },
];

export default function LoginPage() {
    const { auth, isAuthenticated, login, register } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [view, setView] = useState<AuthView>("signin");
    const [mode, setMode] = useState<LoginMode>("student");
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    if (isAuthenticated) {
        const home = auth?.user.role === "INSTRUCTOR"
            ? "/instructor/assessments"
            : "/dashboard";
        return <Navigate to={home} replace />;
    }

    function switchView(next: AuthView) {
        setView(next);
        setError("");
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");

        if (view === "signup" && password !== passwordConfirm) {
            setError("Your passwords do not match. Please try again.");
            return;
        }

        setLoading(true);
        try {
            if (view === "signup") {
                await register(username.trim(), email.trim(), password, passwordConfirm);
                navigate("/dashboard", { replace: true });
                return;
            }

            await login(username.trim(), password, mode);
            const from = (location.state as { from?: string } | null | undefined)?.from;
            const destination = mode === "instructor"
                ? (from?.startsWith("/instructor") ? from : "/instructor/assessments")
                : mode === "admin"
                    ? "/dashboard"
                    : (from && !from.startsWith("/instructor") ? from : "/dashboard");
            navigate(destination, { replace: true });
        } catch (authError) {
            setError(
                authError instanceof Error
                    ? authError.message
                    : view === "signup"
                        ? "We could not create your account. Please check the details and try again."
                        : "Unable to sign in. Check your details and selected account type.",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-page">
            <section className="auth-card" aria-labelledby="auth-title">
                <Link to="/" className="auth-brand" aria-label="Tech Haven home">
                    <span className="brand-mark">TH</span>
                    <span className="auth-brand-copy">
                        <strong>Tech Haven</strong>
                        <span>Learn. Build. Prove.</span>
                    </span>
                </Link>

                <div className="auth-heading">
                    <span className="eyebrow">A PREMIUM LEARNING EXPERIENCE</span>
                    <h1 id="auth-title">
                        {view === "signin" ? "Welcome back." : "Build your future."}
                    </h1>
                    <p>
                        {view === "signin"
                            ? "Sign in to continue learning, building projects and proving your skills."
                            : "Create your student account and start learning with a clear path to progress."}
                    </p>
                </div>

                <div className="auth-tabs" role="tablist" aria-label="Account access">
                    <button
                        id="signin-tab"
                        type="button"
                        role="tab"
                        aria-selected={view === "signin"}
                        aria-controls="auth-panel"
                        className={view === "signin" ? "auth-tab active" : "auth-tab"}
                        onClick={() => switchView("signin")}
                    >
                        Sign in
                    </button>
                    <button
                        id="signup-tab"
                        type="button"
                        role="tab"
                        aria-selected={view === "signup"}
                        aria-controls="auth-panel"
                        className={view === "signup" ? "auth-tab active" : "auth-tab"}
                        onClick={() => switchView("signup")}
                    >
                        Sign up
                    </button>
                </div>

                {error && <div className="auth-error" role="alert">{error}</div>}

                <form id="auth-panel" className="auth-form" onSubmit={handleSubmit}>
                    {view === "signin" ? (
                        <>
                            <fieldset className="role-picker">
                                <legend>Sign in as</legend>
                                <div className="role-options">
                                    {roleOptions.map((role) => (
                                        <button
                                            key={role.value}
                                            type="button"
                                            className={mode === role.value ? "role-option active" : "role-option"}
                                            aria-pressed={mode === role.value}
                                            onClick={() => {
                                                setMode(role.value);
                                                setError("");
                                            }}
                                        >
                                            <span>{role.label}</span>
                                            <small>{role.hint}</small>
                                        </button>
                                    ))}
                                </div>
                                <p className="role-note">
                                    Your account type is verified by the server. Selecting a role here does not grant privileges.
                                </p>
                            </fieldset>
                            <label>
                                Username
                                <input
                                    value={username}
                                    onChange={(event) => setUsername(event.target.value)}
                                    autoComplete="username"
                                    required
                                />
                            </label>
                            <label>
                                Password
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                    autoComplete="current-password"
                                    required
                                />
                            </label>
                            <button type="submit" className="primary-button auth-submit" disabled={loading}>
                                {loading ? "Signing in…" : `Sign in as ${roleOptions.find((item) => item.value === mode)?.label}`}
                            </button>
                        </>
                    ) : (
                        <>
                            <p className="signup-role-note">
                                New public accounts are created as <strong>Students</strong>. Instructor and Administrator access is assigned separately by an authorized administrator.
                            </p>
                            <label>
                                Username
                                <input
                                    value={username}
                                    onChange={(event) => setUsername(event.target.value)}
                                    autoComplete="username"
                                    minLength={3}
                                    maxLength={150}
                                    required
                                />
                            </label>
                            <label>
                                Email address
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(event) => setEmail(event.target.value)}
                                    autoComplete="email"
                                    required
                                />
                            </label>
                            <label>
                                Password
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                    autoComplete="new-password"
                                    minLength={8}
                                    required
                                />
                            </label>
                            <label>
                                Confirm password
                                <input
                                    type="password"
                                    value={passwordConfirm}
                                    onChange={(event) => setPasswordConfirm(event.target.value)}
                                    autoComplete="new-password"
                                    minLength={8}
                                    required
                                />
                            </label>
                            <button type="submit" className="primary-button auth-submit" disabled={loading}>
                                {loading ? "Creating account…" : "Create student account"}
                            </button>
                        </>
                    )}
                </form>

                <div className="auth-footer">
                    <span>{view === "signin" ? "New to Tech Haven?" : "Already have an account?"}</span>{" "}
                    <button type="button" className="auth-inline-action" onClick={() => switchView(view === "signin" ? "signup" : "signin")}>
                        {view === "signin" ? "Create an account" : "Sign in instead"}
                    </button>
                    <Link to="/" className="auth-home-link">← Back to Tech Haven</Link>
                </div>
            </section>
        </div>
    );
}
