const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type ApiErrorResponse = {
    detail?: string;
    non_field_errors?: string[];
    [key: string]: unknown;
};

export async function apiRequest<T>(
    path: string,
    options: RequestInit = {},
    token?: string,
): Promise<T> {
    const headers = new Headers(options.headers);

    headers.set("Accept", "application/json");

    if (
        options.body &&
        !headers.has("Content-Type")
    ) {
        headers.set(
            "Content-Type",
            "application/json",
        );
    }

    if (token) {
        headers.set(
            "Authorization",
            `Token ${token}`,
        );
    }

    const response = await fetch(
        `${API_BASE_URL}${path}`,
        {
            ...options,
            headers,
        },
    );

    if (!response.ok) {
        let detail =
            `Request failed with status ${response.status}.`;

        try {
            const errorData =
                (await response.json()) as ApiErrorResponse;

            if (typeof errorData.detail === "string") {
                detail = errorData.detail;
            } else if (
                Array.isArray(errorData.non_field_errors) &&
                errorData.non_field_errors.length > 0
            ) {
                detail = errorData.non_field_errors[0];
            } else {
                for (const value of Object.values(errorData)) {
                    if (
                        Array.isArray(value) &&
                        value.length > 0
                    ) {
                        detail = String(value[0]);
                        break;
                    }
                }
            }
        } catch {
            // Keep the default error message.
        }

        throw new Error(detail);
    }

    return response.json() as Promise<T>;
}

export function getCourses() {
    return apiRequest<{
        count: number;
        results: import("../types/api").Course[];
    }>("/api/courses/");
}

export function getNotifications(token: string) {
    return apiRequest<import("../types/api").NotificationResponse>(
        "/api/notifications/",
        {},
        token,
    );
}

export function getCourseDetail(slug: string) {
    return apiRequest<import("../types/api").CourseDetail>(
        `/api/courses/${encodeURIComponent(slug)}/`,
    );
}

export function enrollInCourse(
    slug: string,
    token: string,
) {
    return apiRequest<import("../types/api").EnrollmentResponse>(
        `/api/courses/${encodeURIComponent(slug)}/enroll/`,
        {
            method: "POST",
        },
        token,
    );
}

export function getCourseProgress(
    slug: string,
    token: string,
) {
    return apiRequest<import("../types/api").CourseProgressResponse>(
        `/api/courses/${encodeURIComponent(slug)}/progress/`,
        {},
        token,
    );
}

export function getSubmissions(token: string) {
    return apiRequest<
        import("../types/api").SubmissionListResponse
    >(
        "/api/submissions/",
        {},
        token,
    );
}

export function getSubmissionDetail(
    submissionId: number,
    token: string,
) {
    return apiRequest<
        import("../types/api").Submission
    >(
        `/api/submissions/${submissionId}/`,
        {},
        token,
    );
}
export function createSubmission(
    data: {
        activity: number;
        code?: string;
        response_text?: string;
        github_url?: string;
    },
    token: string,
) {
    return apiRequest<
        import("../types/api").SubmissionResponse
    >(
        "/api/submissions/",
        {
            method: "POST",
            body: JSON.stringify(data),
        },
        token,
    );
}

export function getQuiz(
    activityId: number,
    token: string,
) {
    return apiRequest<
        import("../types/api").QuizDetail
    >(
        `/api/quizzes/${activityId}/`,
        {},
        token,
    );
}

export function submitQuizAttempt(
    activityId: number,
    answers: Record<string, number>,
    token: string,
) {
    return apiRequest<
        import("../types/api").QuizAttemptResponse
    >(
        `/api/quizzes/${activityId}/attempts/`,
        {
            method: "POST",
            body: JSON.stringify({
                answers,
            }),
        },
        token,
    );
}

export function getQuizAttempts(
    activityId: number,
    token: string,
) {
    return apiRequest<{
        count: number;
        results: import("../types/api").QuizAttempt[];
    }>(
        `/api/quizzes/${activityId}/attempts/`,
        {},
        token,
    );
}

export function getQuizAttemptDetail(
    attemptId: number,
    token: string,
) {
    return apiRequest<
        import("../types/api").QuizAttempt
    >(
        `/api/quizzes/attempts/${attemptId}/`,
        {},
        token,
    );
}
export function completeReadingActivity(
    activityId: number,
    token: string,
) {
    return apiRequest<{
        detail: string;
        created: boolean;
        activity: {
            id: number;
            title: string;
            is_completed: boolean;
        };
        course: {
            id: number;
            title: string;
            slug: string;
        };
        progress: {
            overall_percentage: number;
            lesson_percentage: number;
            activity_percentage: number;
            lessons_completed: number;
            lessons_total: number;
            activities_completed: number;
            activities_total: number;
        };
    }>(
        `/api/activities/${activityId}/complete/`,
        {
            method: "POST",
            body: JSON.stringify({}),
        },
        token,
    );
}
