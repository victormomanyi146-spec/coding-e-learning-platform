import { apiRequest } from "./client";
import type { LoginResponse } from "../types/api";

export type LoginMode =
    | "student"
    | "instructor";

export function loginRequest(
    username: string,
    password: string,
    mode: LoginMode = "student",
) {
    const endpoint =
        mode === "instructor"
            ? "/api/accounts/instructor-login/"
            : "/api/accounts/login/";

    return apiRequest<LoginResponse>(
        endpoint,
        {
            method: "POST",
            body: JSON.stringify({
                username,
                password,
            }),
        },
    );
}


export function registerRequest(
    username: string,
    email: string,
    password: string,
    passwordConfirm: string,
) {
    return apiRequest<LoginResponse>(
        "/api/accounts/register/",
        {
            method: "POST",
            body: JSON.stringify({
                username,
                email,
                password,
                password_confirm: passwordConfirm,
            }),
        },
    );
}
