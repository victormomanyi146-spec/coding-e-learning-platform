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