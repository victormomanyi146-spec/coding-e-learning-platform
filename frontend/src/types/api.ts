export interface Course {
    id: number;
    title: string;
    slug: string;
    description: string;
    instructor: string;
    duration: string;
    level: string;
    created_at: string;
}

export interface AuthUser {
    id: number;
    username: string;
    email: string;
    role: string;
    is_staff?: boolean;
}

export interface LoginResponse {
    token: string;
    user: AuthUser;
}

export interface Notification {
    id: number;
    notification_type: string;
    title: string;
    message: string;
    link_url: string;
    is_read: boolean;
    created_at: string;
}

export interface NotificationResponse {
    count: number;
    unread_count: number;
    results: Notification[];
}

export interface Activity {
    id: number;
    title: string;
    activity_type: string;
    instructions: string;
    order: number;
    max_score: number;
    is_required: boolean;
}

export interface Lesson {
    id: number;
    title: string;
    content: string;
    order: number;
    activities: Activity[];
}

export interface CourseModule {
    id: number;
    title: string;
    order: number;
    lessons: Lesson[];
}

export interface CourseDetail extends Course {
    modules: CourseModule[];
}

export interface EnrollmentResponse {
    detail: string;
    created: boolean;
    enrollment: {
        id: number;
        student: string;
        course: {
            id: number;
            title: string;
            slug: string;
        };
        enrolled_at: string;
    };
}

export interface ProgressLesson {
    id: number;
    title: string;
    order: number;
    is_completed: boolean;
}

export interface ProgressModule {
    id: number;
    title: string;
    order: number;
    progress_percentage: number;
    lessons_completed: number;
    lessons_total: number;
    activities_completed: number;
    activities_total: number;
    lessons: ProgressLesson[];
}

export interface CourseProgressResponse {
    course: {
        id: number;
        title: string;
        slug: string;
    };
    is_enrolled: boolean;
    course_completed: boolean;
    progress: {
        overall_percentage: number;
        lesson_percentage: number;
        activity_percentage: number;
        lessons_completed: number;
        lessons_total: number;
        activities_completed: number;
        activities_total: number;
        average_score: number;
    };
    modules: ProgressModule[];
    recent_assessments: Array<Record<string, unknown>>;
}

export interface Submission {
    id: number;
    student: {
        id: number;
        username: string;
    };
    activity: {
        id: number;
        title: string;
        activity_type: string;
        max_score: number;
    };
    course: {
        id: number;
        title: string;
        slug: string;
    };
    code: string;
    response_text: string;
    github_url: string;
    attachment_url: string | null;
    submitted_at: string;
    status: string;
    score: number | null;
    feedback: string;
}

export interface SubmissionResponse {
    detail: string;
    submission: Submission;
}

export interface SubmissionListResponse {
    count: number;
    results: Submission[];
}

export interface QuizChoice {
    id: number;
    choice_text: string;
    order: number;
}

export interface QuizQuestion {
    id: number;
    question_text: string;
    order: number;
    points: number;
    choices: QuizChoice[];
}

export interface QuizDetail {
    id: number;
    activity: {
        id: number;
        title: string;
        activity_type: string;
        instructions: string;
        max_score: number;
        lesson: {
            id: number;
            title: string;
        };
        course: {
            id: number;
            title: string;
            slug: string;
        };
    };
    passing_score: number;
    total_points: number;
    questions: QuizQuestion[];
    created_at: string;
}

export interface QuizAttempt {
    id: number;
    quiz: {
        id: number;
        activity_id: number;
        title: string;
        passing_score: number;
        lesson: {
            id: number;
            title: string;
        };
        course: {
            id: number;
            title: string;
            slug: string;
        };
    };
    score: number;
    total_points: number;
    percentage: number;
    passed: boolean;
    completed_at: string | null;
    created_at: string;
    answers: Array<{
        id: number;
        question: {
            id: number;
            question_text: string;
            points: number;
        };
        selected_choice: {
            id: number;
            choice_text: string;
        } | null;
        is_correct: boolean;
        points_awarded: number;
    }>;
}

export interface QuizAttemptResponse {
    detail: string;
    result: {
        earned_points: number;
        total_points: number;
        percentage: number;
        passed: boolean;
        passing_score: number;
    };
    attempt: QuizAttempt;
}

export interface SubmissionReviewResponse {
    detail: string;
    submission: Submission;
}

export interface Certificate {
    id: number;
    verification_code: string;
    learner_name: string;
    course: {
        id: number;
        title: string;
        slug: string;
    };
    course_title: string;
    average_score: number | null;
    issued_at: string;
    is_valid: boolean;
    verification_url: string;
}

export interface CertificateListResponse {
    count: number;
    results: Certificate[];
}