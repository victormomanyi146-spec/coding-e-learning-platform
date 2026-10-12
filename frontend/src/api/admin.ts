import { apiRequest } from "./client";

export type ManagedAccountRole = "STUDENT" | "INSTRUCTOR" | "ADMIN";
export type AccountStatusFilter = "ALL" | "ACTIVE" | "INACTIVE";
export type AccountRoleFilter = "ALL" | ManagedAccountRole;

export interface AdminAccount {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    role: ManagedAccountRole;
    is_active: boolean;
    is_staff: boolean;
    is_superuser: boolean;
    date_joined: string | null;
    last_login: string | null;
}

export interface AdminAccountPage {
    count: number;
    page: number;
    page_size: number;
    pages: number;
    summary: {
        total: number;
        students: number;
        instructors: number;
        admins: number;
        inactive: number;
    };
    results: AdminAccount[];
}

export function getAdminAccounts(
    token: string,
    filters: {
        q: string;
        role: AccountRoleFilter;
        status: AccountStatusFilter;
        page: number;
        page_size?: number;
    },
) {
    const params = new URLSearchParams();
    if (filters.q.trim()) params.set("q", filters.q.trim());
    params.set("role", filters.role);
    params.set("status", filters.status);
    params.set("page", String(filters.page));
    params.set("page_size", String(filters.page_size ?? 25));
    return apiRequest<AdminAccountPage>(`/api/accounts/admin/users/?${params.toString()}`, {}, token);
}

export function setAdminAccountActive(userId: number, isActive: boolean, reason: string, token: string) {
    return apiRequest<{ detail: string; account: AdminAccount }>(
        `/api/accounts/admin/users/${userId}/`,
        { method: "PATCH", body: JSON.stringify({ is_active: isActive, reason }) },
        token,
    );
}

export interface AdminAuditEvent {
    id: number;
    actor_username: string;
    target_username: string;
    action: "ACTIVATED" | "DEACTIVATED";
    reason: string;
    created_at: string | null;
}

export interface AdminOverviewData {
    summary: {
        total_accounts: number;
        active_accounts: number;
        inactive_accounts: number;
        students: number;
        instructors: number;
        administrators: number;
        courses: number;
        enrollments: number;
        submissions: number;
        pending_submissions: number;
        graded_submissions: number;
        certificates_issued: number;
        instructor_applications_pending_review: number;
        instructor_applications_pending_email: number;
        instructor_applications_approved: number;
        instructor_applications_rejected: number;
    };
    recent_accounts: Array<Pick<AdminAccount, "id" | "username" | "email" | "role" | "is_active" | "date_joined">>;
    recent_audit_events: AdminAuditEvent[];
}

export interface AdminAuditLogPage {
    count: number;
    page: number;
    page_size: number;
    pages: number;
    summary: { all: number; activations: number; deactivations: number };
    results: AdminAuditEvent[];
}

export type AuditActionFilter = "ALL" | "ACTIVATED" | "DEACTIVATED";

export function getAdminOverview(token: string) {
    return apiRequest<AdminOverviewData>("/api/accounts/admin/overview/", {}, token);
}

export function getAdminAuditLogs(token: string, filters: { q: string; action: AuditActionFilter; page: number; page_size?: number }) {
    const params = new URLSearchParams();
    if (filters.q.trim()) params.set("q", filters.q.trim());
    params.set("action", filters.action);
    params.set("page", String(filters.page));
    params.set("page_size", String(filters.page_size ?? 25));
    return apiRequest<AdminAuditLogPage>(`/api/accounts/admin/audit-log/?${params.toString()}`, {}, token);
}
