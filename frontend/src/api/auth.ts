import { apiRequest } from "./client";
import type { LoginResponse } from "../types/api";

export type LoginMode = "student" | "instructor" | "admin";

const LOGIN_ENDPOINTS: Record<LoginMode, string> = {
    student: "/api/accounts/login/",
    instructor: "/api/accounts/instructor-login/",
    admin: "/api/accounts/admin-login/",
};

export function loginRequest(
    username: string,
    password: string,
    mode: LoginMode = "student",
) {
    return apiRequest<LoginResponse>(LOGIN_ENDPOINTS[mode], {
        method: "POST",
        body: JSON.stringify({ username, password }),
    });
}

export function registerRequest(
    username: string,
    email: string,
    password: string,
    passwordConfirm: string,
) {
    return apiRequest<LoginResponse>("/api/accounts/register/", {
        method: "POST",
        body: JSON.stringify({
            username,
            email,
            password,
            password_confirm: passwordConfirm,
        }),
    });
}
