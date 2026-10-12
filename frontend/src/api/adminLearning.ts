import { apiRequest } from "./client";
export type AdminLearningKey = "courses" | "modules" | "lessons" | "activities" | "quizzes" | "questions" | "choices" | "enrollments" | "submissions" | "certificates";
export interface AdminLearningRecord { id: number; [key: string]: unknown; }
export interface AdminLearningPage { count: number; page: number; page_size: number; pages: number; results: AdminLearningRecord[]; }
export function getAdminLearningResource(resource: AdminLearningKey, token: string, query = "") {
 const params = new URLSearchParams(); if (query.trim()) params.set("q", query.trim()); params.set("page_size", "100");
 return apiRequest<AdminLearningPage>(`/api/accounts/admin/learning/${resource}/?${params.toString()}`, {}, token);
}
export function createAdminLearningRecord(resource: AdminLearningKey, payload: Record<string, unknown>, token: string) {
 return apiRequest<AdminLearningRecord>(`/api/accounts/admin/learning/${resource}/`, {method:"POST", body:JSON.stringify(payload)}, token);
}
export function updateAdminLearningRecord(resource: AdminLearningKey, id: number, payload: Record<string, unknown>, token: string) {
 return apiRequest<AdminLearningRecord>(`/api/accounts/admin/learning/${resource}/${id}/`, {method:"PATCH", body:JSON.stringify(payload)}, token);
}
