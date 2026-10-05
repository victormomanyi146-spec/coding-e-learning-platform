import { apiRequest } from "./client";
import type { LoginResponse } from "../types/api";

export function loginRequest(
    username: string,
    password: string,
) {
    return apiRequest<LoginResponse>(
        "/api/accounts/login/",
        {
            method: "POST",
            body: JSON.stringify({
                username,
                password,
            }),
        },
    );
}
