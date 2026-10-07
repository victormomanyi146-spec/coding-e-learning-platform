import {
    useState,
} from "react";
import type { FormEvent } from "react";
import {
    Link,
    Navigate,
    useLocation,
    useNavigate,
} from "react-router";
import { useAuth } from "../context/AuthContext";
import type { LoginMode } from "../api/auth";

export default function LoginPage() {
    const {
        isAuthenticated,
        login,
    } = useAuth();

    const navigate =
        useNavigate();

    const location =
        useLocation();

    const [mode, setMode] =
        useState<LoginMode>("student");

    const [username, setUsername] =
        useState("");

    const [password, setPassword] =
        useState("");

    const [error, setError] =
        useState("");

    const [loading, setLoading] =
        useState(false);

    if (isAuthenticated) {
        return (
            <Navigate
                to="/dashboard"
                replace
            />
        );
    }

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();
        setError("");
        setLoading(true);

        try {
            await login(
                username.trim(),
                password,
                mode,
            );

            const destination =
                (
                    location.state as
                    | { from?: string }
                    | null
                    | undefined
                )?.from ??
                (
                    mode === "instructor"
                        ? "/instructor/assessments"
                        : "/dashboard"
                );

            navigate(
                destination,
                { replace: true },
            );
        } catch (loginError) {
            setError(
                loginError instanceof Error
                    ? loginError.message
                    : "Unable to sign in.",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-page">
            <section className="auth-card">
                <div className="auth-brand">
                    <div className="brand-mark">
                        TH
                    </div>

                    <div>
                        <strong>
                            Tech Haven
                        </strong>

                        <span>
                            Learn. Build. Prove.
                        </span>
                    </div>
                </div>

                <div className="auth-heading">
                    <span className="eyebrow">
                        {mode === "instructor"
                            ? "INSTRUCTOR ACCESS"
                            : "WELCOME BACK"}
                    </span>

                    <h1>
                        Sign in to
                        <br />
                        your learning hub.
                    </h1>

                    <p>
                        Continue your learning,
                        assessment and career
                        journey.
                    </p>
                </div>

                <div
                    className="auth-mode-switch"
                    role="tablist"
                    aria-label="Account type"
                >
                    <button
                        type="button"
                        className={
                            mode === "student"
                                ? "primary-button"
                                : "secondary-button"
                        }
                        onClick={() => {
                            setMode("student");
                            setError("");
                        }}
                    >
                        Student
                    </button>

                    <button
                        type="button"
                        className={
                            mode === "instructor"
                                ? "primary-button"
                                : "secondary-button"
                        }
                        onClick={() => {
                            setMode("instructor");
                            setError("");
                        }}
                    >
                        Instructor
                    </button>
                </div>

                {error && (
                    <div
                        className="auth-error"
                        role="alert"
                    >
                        {error}
                    </div>
                )}

                <form
                    className="auth-form"
                    onSubmit={handleSubmit}
                >
                    <label>
                        Username

                        <input
                            value={username}
                            onChange={(event) =>
                                setUsername(
                                    event.target.value,
                                )
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
                                setPassword(
                                    event.target.value,
                                )
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
                        {loading
                            ? "Signing in..."
                            : mode === "instructor"
                                ? "Sign in as instructor"
                                : "Sign in"}
                    </button>
                </form>

                <div className="auth-footer">
                    <Link to="/">
                        ← Back to Tech Haven
                    </Link>
                </div>
            </section>
        </div>
    );
}