import {
    createContext,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import {
    loginRequest,
    registerRequest,
    type LoginMode,
} from "../api/auth";
import type { AuthUser } from "../types/api";

interface AuthState {
    token: string;
    user: AuthUser;
}

interface AuthContextValue {
    auth: AuthState | null;
    isAuthenticated: boolean;
    login: (
        username: string,
        password: string,
        mode?: LoginMode,
    ) => Promise<void>;
    register: (
        username: string,
        email: string,
        password: string,
        passwordConfirm: string,
    ) => Promise<void>;    logout: () => void;
}

const STORAGE_KEY = "tech_haven_auth";

const AuthContext =
    createContext<AuthContextValue | undefined>(
        undefined,
    );

function readStoredAuth(): AuthState | null {
    const stored = sessionStorage.getItem(
        STORAGE_KEY,
    );

    if (!stored) {
        return null;
    }

    try {
        return JSON.parse(stored) as AuthState;
    } catch {
        sessionStorage.removeItem(STORAGE_KEY);
        return null;
    }
}

export function AuthProvider({
    children,
}: {
    children: ReactNode;
}) {
    const [auth, setAuth] =
        useState<AuthState | null>(
            readStoredAuth,
        );

    async function login(
        username: string,
        password: string,
        mode: LoginMode = "student",
    ) {
        const response =
            await loginRequest(
                username,
                password,
                mode,
            );

        const nextAuth: AuthState = {
            token: response.token,
            user: response.user,
        };

        sessionStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(nextAuth),
        );

        setAuth(nextAuth);
    }

    async function register(
        username: string,
        email: string,
        password: string,
        passwordConfirm: string,
    ) {
        const response = await registerRequest(
            username,
            email,
            password,
            passwordConfirm,
        );

        const nextAuth: AuthState = {
            token: response.token,
            user: response.user,
        };

        sessionStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(nextAuth),
        );

        setAuth(nextAuth);
    }
    function logout() {
        sessionStorage.removeItem(
            STORAGE_KEY,
        );

        setAuth(null);
    }

    const value = useMemo(
        () => ({
            auth,
            isAuthenticated: Boolean(auth),
            login,
            register,
            logout,
        }),
        [auth],
    );

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// oxlint-disable-next-line react/only-export-components
export function useAuth() {
    const context =
        useContext(AuthContext);

    if (!context) {
        throw new Error(
            "useAuth must be used inside AuthProvider.",
        );
    }

    return context;
}