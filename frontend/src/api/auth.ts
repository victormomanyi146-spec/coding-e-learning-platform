import { apiBlobRequest, apiRequest } from "./client";
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


export interface InstructorApplicationStartResponse {
    detail: string;
    application_id: number;
    email: string;
    status: string;
    otp_expires_in_seconds: number;
}

export interface InstructorApplicationStatusResponse {
    detail: string;
    application_id: number;
    status: string;
}

export interface InstructorApplicationSummary {
    id: number;
    username: string;
    email: string;
    qualification: string;
    awarding_institution: string;
    experience_summary: string;
    cv_filename: string;
    has_qualification_document: boolean;
    qualification_filename: string;
    status: string;
    created_at: string;
    email_verified_at: string | null;
}

export function createInstructorApplication(formData: FormData) {
    return apiRequest<InstructorApplicationStartResponse>("/api/accounts/instructor-applications/", {
        method: "POST",
        body: formData,
    });
}

export function verifyInstructorApplicationOtp(applicationId: number, otp: string) {
    return apiRequest<InstructorApplicationStatusResponse>("/api/accounts/instructor-applications/verify-otp/", {
        method: "POST",
        body: JSON.stringify({ application_id: applicationId, otp }),
    });
}

export function resendInstructorApplicationOtp(applicationId: number) {
    return apiRequest<{ detail: string }>("/api/accounts/instructor-applications/resend-otp/", {
        method: "POST",
        body: JSON.stringify({ application_id: applicationId }),
    });
}

export function getInstructorApplications(token: string) {
    return apiRequest<{ count: number; results: InstructorApplicationSummary[] }>(
        "/api/accounts/admin/instructor-applications/",
        {},
        token,
    );
}

export function reviewInstructorApplication(
    applicationId: number,
    decision: "approve" | "reject",
    adminNotes: string,
    token: string,
) {
    return apiRequest<{ detail: string; application: InstructorApplicationSummary }>(
        `/api/accounts/admin/instructor-applications/${applicationId}/review/`,
        { method: "POST", body: JSON.stringify({ decision, admin_notes: adminNotes }) },
        token,
    );
}

export function downloadInstructorApplicationDocument(
    applicationId: number,
    documentType: "cv" | "qualification",
    token: string,
) {
    return apiBlobRequest(
        `/api/accounts/admin/instructor-applications/${applicationId}/documents/${documentType}/`,
        token,
    );
}
