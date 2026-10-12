
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

const loginModes: LoginMode[] = ["student", "instructor", "admin"];

export default function LoginPage() {
    const { auth, isAuthenticated, login, register } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const [view, setView] = useState<AuthView>("signin");
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    if (isAuthenticated) {
        const home =
            auth?.user.role === "ADMIN"
                ? "/admin/overview"
                : auth?.user.role === "INSTRUCTOR"
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
                await register(
                    username.trim(),
                    email.trim(),
                    password,
                    passwordConfirm,
                );

                navigate("/dashboard", { replace: true });
                return;
            }

            // Use one sign-in form for every account type.
            // Each existing backend endpoint still verifies the account role.
            let authenticatedMode: LoginMode | null = null;
            let lastAuthError: unknown;

            for (const candidateMode of loginModes) {
                try {
                    await login(
                        username.trim(),
                        password,
                        candidateMode,
                    );

                    authenticatedMode = candidateMode;
                    break;
                } catch (authError) {
                    lastAuthError = authError;
                }
            }

            if (!authenticatedMode) {
                throw lastAuthError instanceof Error
                    ? lastAuthError
                    : new Error(
                        "Unable to sign in. Check your username and password.",
                    );
            }

            const from = (
                location.state as
                    | { from?: string }
                    | null
                    | undefined
            )?.from;

            const destination =
                authenticatedMode === "instructor"
                    ? (
                        from?.startsWith("/instructor")
                            ? from
                            : "/instructor/assessments"
                    )
                    : authenticatedMode === "admin"
                        ? "/admin/overview"
                        : (
                            from && !from.startsWith("/instructor")
                                ? from
                                : "/dashboard"
                        );

            navigate(destination, { replace: true });
        } catch (authError) {
            setError(
                authError instanceof Error
                    ? authError.message
                    : view === "signup"
                        ? "We could not create your account. Please check your details and try again."
                        : "Unable to sign in. Check your username and password or contact an administrator.",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-page">
            <section
                className="auth-card"
                aria-labelledby="auth-title"
            >
                <Link
                    to="/"
                    className="auth-brand"
                    aria-label="Tech Haven home"
                >
                    <span className="brand-mark">TH</span>

                    <span className="auth-brand-copy">
                        <strong>Tech Haven</strong>
                        <span>Learn. Build. Prove.</span>
                    </span>
                </Link>

                <div className="auth-heading">
                    <span className="eyebrow">
                        A PREMIUM LEARNING EXPERIENCE
                    </span>

                    <h1 id="auth-title">
                        {view === "signin"
                            ? "Welcome back."
                            : "Build your future."}
                    </h1>

                    <p>
                        {view === "signin"
                            ? "Sign in to continue learning, building projects and proving your skills."
                            : "Create your student account and start learning with a clear path to progress."}
                    </p>
                </div>

                <div
                    className="auth-tabs"
                    role="tablist"
                    aria-label="Account access"
                >
                    <button
                        id="signin-tab"
                        type="button"
                        role="tab"
                        aria-selected={view === "signin"}
                        aria-controls="auth-panel"
                        className={
                            view === "signin"
                                ? "auth-tab active"
                                : "auth-tab"
                        }
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
                        className={
                            view === "signup"
                                ? "auth-tab active"
                                : "auth-tab"
                        }
                        onClick={() => switchView("signup")}
                    >
                        Sign up
                    </button>
                </div>

                {error && (
                    <div className="auth-error" role="alert">
                        {error}
                    </div>
                )}

                <form
                    id="auth-panel"
                    className="auth-form"
                    onSubmit={handleSubmit}
                >
                    {view === "signin" ? (
                        <>
                            <label>
                                Username
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(event) =>
                                        setUsername(event.target.value)
                                    }
                                    autoComplete="username"
                                    required
                                />
                            </label>

                            <label>
                                Password
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(event) =>
                                        setPassword(event.target.value)
                                    }
                                    autoComplete="current-password"
                                    required
                                />
                            </label>

                            <button
                                type="submit"
                                className="primary-button auth-submit"
                                disabled={loading}
                            >
                                {loading ? "Signing in…" : "Sign in"}
                            </button>
                        </>
                    ) : (
                        <>
                            <p className="signup-role-note">
                                New public accounts are created as{" "}
                                <strong>Students</strong>. Instructor and
                                Administrator access is assigned separately
                                by an authorized administrator.
                            </p>

                            <label>
                                Username
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(event) =>
                                        setUsername(event.target.value)
                                    }
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
                                    onChange={(event) =>
                                        setEmail(event.target.value)
                                    }
                                    autoComplete="email"
                                    required
                                />
                            </label>

                            <label>
                                Password
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(event) =>
                                        setPassword(event.target.value)
                                    }
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
                                    onChange={(event) =>
                                        setPasswordConfirm(event.target.value)
                                    }
                                    autoComplete="new-password"
                                    minLength={8}
                                    required
                                />
                            </label>

                            <button
                                type="submit"
                                className="primary-button auth-submit"
                                disabled={loading}
                            >
                                {loading
                                    ? "Creating account…"
                                    : "Create student account"}
                            </button>
                        </>
                    )}
                </form>

                {view === "signup" && (
                    <p className="instructor-apply-prompt">Want to teach at Tech Haven? <Link to="/instructor/apply">Apply as an instructor</Link>.</p>
                )}

                <div className="auth-footer">
                    <span>
                        {view === "signin"
                            ? "New to Tech Haven?"
                            : "Already have an account?"}
                    </span>{" "}

                    <button
                        type="button"
                        className="auth-inline-action"
                        onClick={() =>
                            switchView(
                                view === "signin" ? "signup" : "signin",
                            )
                        }
                    >
                        {view === "signin"
                            ? "Create an account"
                            : "Sign in instead"}
                    </button>

                    <Link to="/" className="auth-home-link">
                        ← Back to Tech Haven
                    </Link>
                </div>
            </section>
        </div>
    );
}
