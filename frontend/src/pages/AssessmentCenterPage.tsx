import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
    getCourseDetail,
    getCourses,
    getQuiz,
    getQuizAttempts,
    getSubmissions,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import type {
    Course,
    CourseDetail,
    QuizAttempt,
    QuizDetail,
} from "../types/api";
const EMPTY_SUBMISSIONS: import("../types/api").Submission[] = [];

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function statusLabel(status: string) {
    const normalized = status.toLowerCase();

    if (normalized.includes("correction")) {
        return "Needs correction";
    }

    if (
        normalized.includes("graded") ||
        normalized.includes("approved") ||
        normalized.includes("complete")
    ) {
        return "Graded";
    }

    if (
        normalized.includes("pending") ||
        normalized.includes("review")
    ) {
        return "Awaiting review";
    }

    if (
        normalized.includes("reject") ||
        normalized.includes("fail")
    ) {
        return "Needs improvement";
    }

    return status;
}

function normalizeList<T>(value: unknown): T[] {
    if (Array.isArray(value)) {
        return value as T[];
    }

    if (
        value &&
        typeof value === "object" &&
        "results" in value
    ) {
        const results = (value as { results?: unknown }).results;

        if (Array.isArray(results)) {
            return results as T[];
        }
    }

    return [];
}

type QuizActivity = {
    activityId: number;
    activityTitle: string;
    courseTitle: string;
    courseSlug: string;
    lessonTitle: string;
};

type QuizAvailability =
    | "available"
    | "locked"
    | "enrollment"
    | "unavailable";

type QuizAssessment = QuizActivity & {
    quiz: QuizDetail | null;
    attempts: QuizAttempt[];
    availability: QuizAvailability;
    errorMessage: string | null;
};

function getAvailability(
    message: string,
): QuizAvailability {
    const normalized = message.toLowerCase();

    if (normalized.includes("enrollment")) {
        return "enrollment";
    }

    if (normalized.includes("locked")) {
        return "locked";
    }

    return "unavailable";
}

export default function AssessmentCenterPage() {
    const { auth } = useAuth();
    const token = auth?.token ?? "";

    const submissionsQuery = useQuery({
        queryKey: ["assessment-submissions", token],
        queryFn: () => getSubmissions(token),
        enabled: Boolean(token),
    });

    const quizzesQuery = useQuery({
        queryKey: ["assessment-quizzes", token],
        enabled: Boolean(token),
        queryFn: async (): Promise<QuizAssessment[]> => {
            const coursesResponse = await getCourses();

            const courses = normalizeList<Course>(
                coursesResponse,
            );

            const courseDetails = await Promise.all(
                courses.map(async (course) => {
                    try {
                        return await getCourseDetail(course.slug);
                    } catch {
                        return null;
                    }
                }),
            );

            const quizActivities =
                courseDetails
                    .filter(
                        (
                            course,
                        ): course is CourseDetail =>
                            course !== null,
                    )
                    .flatMap((course) =>
                        (course.modules ?? []).flatMap(
                            (module) =>
                                (module.lessons ?? []).flatMap(
                                    (lesson) =>
                                        (lesson.activities ?? [])
                                            .filter(
                                                (activity) =>
                                                    activity.activity_type ===
                                                    "quiz",
                                            )
                                            .map(
                                                (
                                                    activity,
                                                ): QuizActivity => ({
                                                    activityId:
                                                        activity.id,
                                                    activityTitle:
                                                        activity.title,
                                                    courseTitle:
                                                        course.title,
                                                    courseSlug:
                                                        course.slug,
                                                    lessonTitle:
                                                        lesson.title,
                                                }),
                                            ),
                                ),
                        ),
                    );

            return Promise.all(
                quizActivities.map(
                    async (
                        activity,
                    ): Promise<QuizAssessment> => {
                        let quiz: QuizDetail | null = null;
                        let attempts: QuizAttempt[] = [];
                        let availability:
                            QuizAvailability =
                            "unavailable";
                        let errorMessage: string | null =
                            null;

                        try {
                            quiz = await getQuiz(
                                activity.activityId,
                                token,
                            );

                            availability = "available";
                        } catch (error) {
                            errorMessage =
                                error instanceof Error
                                    ? error.message
                                    : null;

                            availability =
                                getAvailability(
                                    errorMessage ?? "",
                                );
                        }

                        if (
                            availability === "available" &&
                            quiz
                        ) {
                            try {
                                const attemptsResponse =
                                    await getQuizAttempts(
                                        activity.activityId,
                                        token,
                                    );

                                attempts =
                                    normalizeList<QuizAttempt>(
                                        attemptsResponse,
                                    ).sort(
                                        (
                                            first,
                                            second,
                                        ) =>
                                            new Date(
                                                second.created_at,
                                            ).getTime() -
                                            new Date(
                                                first.created_at,
                                            ).getTime(),
                                    );
                            } catch {
                                attempts = [];
                            }
                        }

                        return {
                            ...activity,
                            quiz,
                            attempts,
                            availability,
                            errorMessage,
                        };
                    },
                ),
            );
        },
    });

    const submissions =
        submissionsQuery.data?.results ??
        EMPTY_SUBMISSIONS;

    const gradedSubmissions =
        submissions.filter(
            (submission) =>
                submission.status !== "correction" &&
                submission.score !== null,
        );

    const pendingSubmissions =
        submissions.filter(
            (submission) =>
                submission.score === null,
        );

    const averageScore =
        gradedSubmissions.length > 0
            ? gradedSubmissions.reduce(
                  (total, submission) =>
                      total +
                      ((submission.score ?? 0) /
                          Math.max(
                              submission.activity
                                  .max_score,
                              1,
                          )) *
                          100,
                  0,
              ) / gradedSubmissions.length
            : null;

    const quizAssessments =
        quizzesQuery.data ?? [];

    const quizAttemptCount =
        quizAssessments.reduce(
            (total, assessment) =>
                total + assessment.attempts.length,
            0,
        );

    const availableQuizCount =
        quizAssessments.filter(
            (assessment) =>
                assessment.availability === "available",
        ).length;

    const lockedQuizCount =
        quizAssessments.filter(
            (assessment) =>
                assessment.availability === "locked",
        ).length;

    const enrollmentRequiredCount =
        quizAssessments.filter(
            (assessment) =>
                assessment.availability === "enrollment",
        ).length;
    const quizAttempts = quizAssessments.flatMap(
        (assessment) => assessment.attempts,
    );

    const passedQuizAttempts = quizAttempts.filter(
        (attempt) => attempt.passed,
    ).length;

    const quizAverage =
        quizAttempts.length > 0
            ? quizAttempts.reduce(
                  (total, attempt) =>
                      total + attempt.percentage,
                  0,
              ) / quizAttempts.length
            : null;

    const quizPassRate =
        quizAttempts.length > 0
            ? (passedQuizAttempts / quizAttempts.length) * 100
            : null;

    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        ASSESSMENT CENTER
                    </span>

                    <h1>
                        Prove what
                        <br />
                        you can build.
                    </h1>

                    <p>
                        Submit your work, complete
                        assessments, review feedback,
                        and track your progress from
                        one workspace.
                    </p>
                </div>
            </section>

            <section className="dashboard-stats">
                <article>
                    <span>Submitted</span>
                    <strong>
                        {submissionsQuery.isPending
                            ? "—"
                            : submissions.length}
                    </strong>
                    <small>
                        assessment submissions
                    </small>
                </article>

                <article>
                    <span>Awaiting review</span>
                    <strong>
                        {submissionsQuery.isPending
                            ? "—"
                            : pendingSubmissions.length}
                    </strong>
                    <small>
                        submissions needing assessment
                    </small>
                </article>

                <article>
                    <span>Average score</span>
                    <strong>
                        {averageScore === null
                            ? "—"
                            : `${averageScore.toFixed(1)}%`}
                    </strong>
                    <small>
                        across graded submissions
                    </small>
                </article>

                <article>
                    <span>Quiz attempts</span>
                    <strong>
                        {quizzesQuery.isPending
                            ? "—"
                            : quizAttemptCount}
                    </strong>
                    <small>
                        recorded quiz attempts
                    </small>
                </article>
            </section>

            <section className="dashboard-grid">
                <div className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                YOUR WORK
                            </span>
                            <h2>
                                Recent submissions
                            </h2>
                        </div>

                        <Link
                            to="/courses"
                            className="text-link"
                        >
                            Browse courses →
                        </Link>
                    </div>

                    {submissionsQuery.isPending && (
                        <div className="status-card">
                            Loading your assessments...
                        </div>
                    )}

                    {submissionsQuery.isError && (
                        <div className="status-card error">
                            Unable to load your
                            assessment submissions.
                        </div>
                    )}

                    {submissionsQuery.isSuccess &&
                        submissions.length === 0 && (
                            <div className="status-card">
                                <strong>
                                    No submissions yet.
                                </strong>
                                <p>
                                    Complete an activity
                                    inside one of your
                                    courses to start
                                    building your
                                    assessment record.
                                </p>
                                <Link
                                    to="/courses"
                                    className="primary-button"
                                >
                                    Explore courses
                                </Link>
                            </div>
                        )}

                    {submissionsQuery.isSuccess &&
                        submissions.length > 0 && (
                            <div className="assessment-list">
                                {submissions
                                    .slice(0, 8)
                                    .map(
                                        (submission) => (
                                            <article
                                                key={
                                                    submission.id
                                                }
                                                className="assessment-card"
                                            >
                                                <div>
                                                    <span className="course-level">
                                                        {
                                                            submission
                                                                .activity
                                                                .activity_type
                                                        }
                                                    </span>
                                                    <h3>
                                                        {
                                                            submission
                                                                .activity
                                                                .title
                                                        }
                                                    </h3>
                                                    <p>
                                                        {
                                                            submission
                                                                .course
                                                                .title
                                                        }
                                                    </p>
                                                </div>

                                                <div className="assessment-card-meta">
                                                    <span>
                                                        {statusLabel(
                                                            submission.status,
                                                        )}
                                                    </span>
                                                    <strong>
                                                        {submission.score ===
                                                        null
                                                            ? "Pending"
                                                            : `${submission.score}/${submission.activity.max_score}`}
                                                    </strong>
                                                    <small>
                                                        {formatDate(
                                                            submission.submitted_at,
                                                        )}
                                                    </small>

   <Link
       to={`/assessments/submissions/${submission.id}`}
       className="text-link"
   >
       View assessment
   </Link>
                                                </div>
                                            </article>
                                        ),
                                    )}
                            </div>
                        )}
                </div>

                <aside className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                ASSESSMENT TYPES
                            </span>
                            <h2>
                                Choose your next
                                challenge.
                            </h2>
                        </div>
                    </div>

                    <div className="assessment-options">
                        <article>
                            <span className="feature-number">
                                01
                            </span>
                            <h3>
                                Coding activities
                            </h3>
                            <p>
                                Write and submit code
                                against practical
                                learning activities.
                            </p>
                        </article>

                        <article>
                            <span className="feature-number">
                                02
                            </span>
                            <h3>
                                Quizzes
                            </h3>
                            <p>
                                Test your understanding
                                and receive an immediate
                                score.
                            </p>
                        </article>

                        <article>
                            <span className="feature-number">
                                03
                            </span>
                            <h3>
                                Instructor review
                            </h3>
                            <p>
                                Receive scores and
                                feedback on submitted
                                practical work.
                            </p>
                        </article>
                    </div>
                </aside>
            </section>

                        <section className="dashboard-panel">
                <div className="panel-heading">
                    <div>
                        <span className="eyebrow">
                            ASSESSMENT SCORECARD
                        </span>
                        <h2>
                            Your assessment performance
                        </h2>
                    </div>

                    <span className="text-link">
                        Practical + quiz results
                    </span>
                </div>

                <div className="dashboard-stats">
                    <article>
                        <span>Practical average</span>
                        <strong>
                            {averageScore === null
                                ? "-"
                                : `${averageScore.toFixed(1)}%`}
                        </strong>
                        <small>
                            across graded submissions
                        </small>
                    </article>

                    <article>
                        <span>Quiz average</span>
                        <strong>
                            {quizAverage === null
                                ? "-"
                                : `${quizAverage.toFixed(1)}%`}
                        </strong>
                        <small>
                            across recorded quiz attempts
                        </small>
                    </article>

                    <article>
                        <span>Quiz pass rate</span>
                        <strong>
                            {quizPassRate === null
                                ? "-"
                                : `${quizPassRate.toFixed(1)}%`}
                        </strong>
                        <small>
                            passed attempts vs total attempts
                        </small>
                    </article>

                    <article>
                        <span>Passed quizzes</span>
                        <strong>
                            {quizzesQuery.isPending
                                ? "-"
                                : `${passedQuizAttempts}/${quizAttemptCount}`}
                        </strong>
                        <small>
                            successful quiz attempts
                        </small>
                    </article>
                </div>
            </section>
<section className="dashboard-panel">
                <div className="panel-heading">
                    <div>
                        <span className="eyebrow">
                            QUIZ ASSESSMENTS
                        </span>
                        <h2>
                            Available quizzes
                        </h2>
                    </div>

                    <span className="text-link">
                        {quizzesQuery.isPending
                            ? "Loading..."
                            : `${availableQuizCount} available · ${lockedQuizCount} locked · ${enrollmentRequiredCount} enrollment required`}
                    </span>
                </div>

                {quizzesQuery.isPending && (
                    <div className="status-card">
                        Loading quiz assessments...
                    </div>
                )}

                {quizzesQuery.isError && (
                    <div className="status-card error">
                        Unable to load quiz assessments.
                    </div>
                )}

                {quizzesQuery.isSuccess &&
                    quizAssessments.length === 0 && (
                        <div className="status-card">
                            <strong>
                                No quiz activities found.
                            </strong>
                            <p>
                                Quiz assessments will appear
                                here as they are added to
                                your courses.
                            </p>
                        </div>
                    )}

                {quizzesQuery.isSuccess &&
                    quizAssessments.length > 0 && (
                        <div className="assessment-list">
                            {quizAssessments.map(
                                (assessment) => {
                                    const latestAttempt =
                                        assessment
                                            .attempts[0];

                                    const isAvailable =
                                        assessment.availability ===
                                        "available";

                                    let statusText =
                                        "Unavailable";

                                    if (isAvailable) {
                                        statusText =
                                            "Available";
                                    } else if (
                                        assessment.availability ===
                                        "locked"
                                    ) {
                                        statusText =
                                            "Locked";
                                    } else if (
                                        assessment.availability ===
                                        "enrollment"
                                    ) {
                                        statusText =
                                            "Enrollment required";
                                    }

                                    return (
                                        <article
                                            key={
                                                assessment.activityId
                                            }
                                            className="assessment-card"
                                        >
                                            <div>
                                                <span className="course-level">
                                                    {statusText}
                                                </span>

                                                <h3>
                                                    {
                                                        assessment.activityTitle
                                                    }
                                                </h3>

                                                <p>
                                                    {
                                                        assessment.courseTitle
                                                    }
                                                    {" · "}
                                                    {
                                                        assessment.lessonTitle
                                                    }
                                                </p>

                                                {assessment.quiz ? (
                                                    <small>
                                                        {
                                                            assessment
                                                                .quiz
                                                                .questions
                                                                .length
                                                        }{" "}
                                                        questions
                                                        {" · "}
                                                        {
                                                            assessment
                                                                .quiz
                                                                .total_points
                                                        }{" "}
                                                        points
                                                        {" · "}
                                                        Passing score{" "}
                                                        {
                                                            assessment
                                                                .quiz
                                                                .passing_score
                                                        }
                                                        %
                                                    </small>
                                                ) : (
                                                    <small>
                                                        {assessment
                                                            .availability ===
                                                        "locked"
                                                            ? "Complete the required activities to unlock this quiz."
                                                            : assessment
                                                                  .availability ===
                                                              "enrollment"
                                                              ? "Enroll in this course to access its assessments."
                                                              : assessment
                                                                    .errorMessage ??
                                                                "This quiz is not currently available."}
                                                    </small>
                                                )}
                                            </div>

                                            <div className="assessment-card-meta">
                                                {latestAttempt ? (
                                                    <>
                                                        <span>
                                                            {latestAttempt
                                                                .passed
                                                                ? "Passed"
                                                                : "Needs improvement"}
                                                        </span>

                                                        <strong>
                                                            {latestAttempt.percentage.toFixed(
                                                                1,
                                                            )}
                                                            %
                                                        </strong>

                                                        <small>
                                                            Latest attempt{" "}
                                                            {formatDate(
                                                                latestAttempt.created_at,
                                                            )}
                                                        </small>
                                                    </>
                                                ) : (
                                                    <>
                                                        <span>
                                                            {isAvailable
                                                                ? "Not attempted"
                                                                : "Not available yet"}
                                                        </span>

                                                        <strong>
                                                            —
                                                        </strong>

                                                        <small>
                                                            {isAvailable
                                                                ? "Ready when you are"
                                                                : "Complete the required course conditions"}
                                                        </small>
                                                    </>
                                                )}

                                                {isAvailable && (
                                                    <Link
                                                        to={`/courses/${assessment.courseSlug}/quiz/${assessment.activityId}`}
                                                        className="primary-button"
                                                    >
                                                        Take quiz →
                                                    </Link>
                                                )}

                                                {!isAvailable && (
                                                    <Link
                                                        to={`/courses/${assessment.courseSlug}`}
                                                        className="text-link"
                                                    >
                                                        {assessment.availability ===
                                                        "locked"
                                                            ? "Continue course →"
                                                            : "View course →"}
                                                    </Link>
                                                )}
                                            </div>
                                        </article>
                                    );
                                },
                            )}
                        </div>
                    )}
            </section>

            <section className="dashboard-panel">
                <div className="panel-heading">
                    <div>
                        <span className="eyebrow">
                            QUIZ HISTORY
                        </span>
                        <h2>
                            Recent attempts
                        </h2>
                    </div>

                    <span className="text-link">
                        {quizzesQuery.isPending
                            ? "Loading..."
                            : `${quizAttemptCount} total`}
                    </span>
                </div>

                {quizzesQuery.isPending && (
                    <div className="status-card">
                        Loading quiz history...
                    </div>
                )}

                {quizzesQuery.isSuccess &&
                    quizAttemptCount === 0 && (
                        <div className="status-card">
                            <strong>
                                No quiz attempts yet.
                            </strong>
                            <p>
                                Complete an available quiz
                                and your attempt history will
                                be recorded here.
                            </p>
                        </div>
                    )}

                {quizzesQuery.isSuccess &&
                    quizAttemptCount > 0 && (
                        <div className="assessment-list">
                            {quizAssessments
                                .flatMap(
                                    (assessment) =>
                                        assessment.attempts
                                            .slice(0, 3)
                                            .map(
                                                (
                                                    attempt,
                                                ) => ({
                                                    assessment,
                                                    attempt,
                                                }),
                                            ),
                                )
                                .sort(
                                    (
                                        first,
                                        second,
                                    ) =>
                                        new Date(
                                            second.attempt.created_at,
                                        ).getTime() -
                                        new Date(
                                            first.attempt.created_at,
                                        ).getTime(),
                                )
                                .slice(0, 10)
                                .map(
                                    ({
                                        assessment,
                                        attempt,
                                    }) => (
                                        <article
                                            key={`${assessment.activityId}-${attempt.id}`}
                                            className="assessment-card"
                                        >
                                            <div>
                                                <span className="course-level">
                                                    {attempt.passed
                                                        ? "Passed"
                                                        : "Not passed"}
                                                </span>

                                                <h3>
                                                    {
                                                        assessment.activityTitle
                                                    }
                                                </h3>

                                                <p>
                                                    {
                                                        assessment.courseTitle
                                                    }
                                                </p>
                                            </div>

                                            <div className="assessment-card-meta">
                                                <strong>
                                                    {attempt.percentage.toFixed(
                                                        1,
                                                    )}
                                                    %
                                                </strong>

                                                <span>
                                                    {
                                                        attempt.score
                                                    }{" "}
                                                    /{" "}
                                                    {
                                                        attempt.total_points
                                                    }
                                                </span>

                                                <small>
                                                    {formatDate(
                                                        attempt.created_at,
                                                    )}
                                                </small>

                                                <Link
       to={`/assessments/quiz-attempts/${attempt.id}`}
       className="text-link"
   >
       View attempt
   </Link>

   <Link
       to={`/courses/${assessment.courseSlug}/quiz/${assessment.activityId}`}
       className="text-link"
   >
       Retake quiz
   </Link>
                                            </div>
                                        </article>
                                    ),
                                )}
                        </div>
                    )}
            </section>
        </div>
    );
}