import {
    useQueries,
    useQuery,
} from "@tanstack/react-query";
import { Link } from "react-router";
import {
    getCourses,
    getCourseProgress,
    getNotifications,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import type {
    CourseProgressResponse,
} from "../types/api";

type DashboardAssessment = {
    kind?: string;
    title: string;
    lesson_title?: string;
    submitted_at: string;
    score?: number | null;
    max_score?: number | null;
    percentage?: number | null;
    status: string;
    feedback?: string | null;
};

function assessmentTone(status: string) {
    switch (status) {
        case "Needs correction":
            return "correction";

        case "Pending":
            return "pending";

        case "Error":
            return "error";

        case "Not passed":
            return "attention";

        case "Quiz Passed":
        case "Graded":
            return "success";

        default:
            return "neutral";
    }
}

function assessmentLabel(status: string) {
    switch (status) {
        case "Pending":
            return "Awaiting review";

        case "Error":
            return "Execution error";

        case "Not passed":
            return "Retake recommended";

        default:
            return status;
    }
}

function formatScore(
    item: DashboardAssessment,
) {
    if (
        typeof item.percentage === "number"
    ) {
        return `${Math.round(item.percentage)}%`;
    }

    return "—";
}

function formatDate(value: string) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return new Intl.DateTimeFormat(
        undefined,
        {
            month: "short",
            day: "numeric",
            year: "numeric",
        },
    ).format(date);
}

export default function DashboardPage() {
    const {
        auth,
        logout,
    } = useAuth();

    const token =
        auth?.token ?? "";

    const coursesQuery =
        useQuery({
            queryKey: [
                "dashboard-courses",
            ],
            queryFn: getCourses,
        });

    const notificationsQuery =
        useQuery({
            queryKey: [
                "dashboard-notifications",
                token,
            ],
            queryFn: () =>
                getNotifications(token),
            enabled: Boolean(token),
        });

    const courses =
        coursesQuery.data?.results ?? [];

    const progressQueries =
        useQueries({
            queries: courses.map(
                (course) => ({
                    queryKey: [
                        "dashboard-progress",
                        token,
                        course.slug,
                    ],
                    queryFn:
                        async (): Promise<
                            CourseProgressResponse | null
                        > => {
                            try {
                                return await getCourseProgress(
                                    course.slug,
                                    token,
                                );
                            } catch (error) {
                                if (
                                    error instanceof
                                        Error &&
                                    error.message
                                        .toLowerCase()
                                        .includes(
                                            "enrollment required",
                                        )
                                ) {
                                    return null;
                                }

                                throw error;
                            }
                        },
                    enabled:
                        Boolean(token) &&
                        coursesQuery.isSuccess,
                    retry: false,
                }),
            ),
        });

    const courseSnapshots =
        courses.map(
            (
                course,
                index,
            ) => ({
                course,
                progress:
                    progressQueries[index]
                        ?.data ?? null,
                isPending:
                    progressQueries[index]
                        ?.isPending ?? false,
                isError:
                    progressQueries[index]
                        ?.isError ?? false,
            }),
        );

    const enrolledSnapshots =
        courseSnapshots.filter(
            (snapshot) =>
                snapshot.progress
                    ?.is_enrolled === true,
        );

    const completedCount =
        enrolledSnapshots.filter(
            (snapshot) =>
                snapshot.progress
                    ?.course_completed === true,
        ).length;

    const averageCompletion =
        enrolledSnapshots.length > 0
            ? Math.round(
                  enrolledSnapshots.reduce(
                      (
                          total,
                          snapshot,
                      ) =>
                          total +
                          (
                              snapshot.progress
                                  ?.progress
                                  .overall_percentage ??
                              0
                          ),
                      0,
                  ) /
                      enrolledSnapshots.length,
              )
            : 0;

    const averageAssessmentScoreValues =
        enrolledSnapshots
            .map(
                (snapshot) =>
                    snapshot.progress
                        ?.progress
                        .average_score,
            )
            .filter(
                (
                    score,
                ): score is number =>
                    typeof score === "number",
            );

    const averageAssessmentScore =
        averageAssessmentScoreValues.length > 0
            ? Math.round(
                  (
                      averageAssessmentScoreValues.reduce(
                          (total, score) =>
                              total + score,
                          0,
                      ) /
                      averageAssessmentScoreValues.length
                  ) *
                      10,
              ) / 10
            : null;

    const progressLoading =
        coursesQuery.isSuccess &&
        progressQueries.some(
            (query) =>
                query.isPending,
        );

    const progressError =
        coursesQuery.isSuccess &&
        progressQueries.some(
            (query) =>
                query.isError,
        );

    const assessmentItems =
        enrolledSnapshots
            .flatMap(
                (snapshot) =>
                    (
                        snapshot.progress
                            ?.recent_assessments ?? []
                    ).map(
                        (item) =>
                            item as DashboardAssessment,
                    ),
            )
            .filter(
                (item) =>
                    typeof item.title === "string" &&
                    typeof item.status === "string",
            )
            .sort(
                (a, b) =>
                    new Date(
                        b.submitted_at,
                    ).getTime() -
                    new Date(
                        a.submitted_at,
                    ).getTime(),
            );

    const attentionItems =
        assessmentItems
            .filter(
                (item) =>
                    [
                        "Needs correction",
                        "Pending",
                        "Error",
                        "Not passed",
                    ].includes(
                        item.status,
                    ),
            )
            .slice(0, 3);

    const latestAchievement =
        assessmentItems.find(
            (item) =>
                (
                    item.status ===
                        "Graded" ||
                    item.status ===
                        "Quiz Passed"
                ) &&
                typeof item.percentage ===
                    "number",
        );

    const activeSnapshot =
        [
            ...enrolledSnapshots
                .filter(
                    (snapshot) =>
                        !snapshot.progress
                            ?.course_completed,
                ),
        ].sort(
            (a, b) =>
                (
                    b.progress
                        ?.progress
                        .overall_percentage ??
                    0
                ) -
                (
                    a.progress
                        ?.progress
                        .overall_percentage ??
                    0
                ),
        )[0] ??
        enrolledSnapshots[0];

    const activePercentage =
        Math.round(
            activeSnapshot?.progress
                ?.progress
                .overall_percentage ?? 0,
        );

    const activeNextLesson =
        activeSnapshot
            ? activeSnapshot.progress?.modules
                  .flatMap(
                      (module) =>
                          module.lessons,
                  )
                  .find(
                      (lesson) =>
                          !lesson.is_completed,
                  )
            : undefined;

    const unreadCount =
        notificationsQuery.data
            ?.unread_count ?? 0;

    const username =
        auth?.user.username ??
        "Learner";

    const hasActiveCourse =
        Boolean(activeSnapshot);

    const activeCourseComplete =
        activeSnapshot?.progress
            ?.course_completed === true;

    return (
        <div className="page dashboard-page">
            <section className="dashboard-welcome dashboard-hero">
                <div>
                    <span className="eyebrow">
                        STUDENT DASHBOARD
                    </span>

                    <h1>
                        Welcome back,
                        <br />
                        {username}.
                    </h1>

                    <p>
                        Pick up where you left off,
                        track your progress, and keep
                        turning practice into proof.
                    </p>
                </div>

                <div className="dashboard-hero-actions">
                    {hasActiveCourse && (
                        <Link
                            to={`/courses/${activeSnapshot.course.slug}`}
                            className="primary-button"
                        >
                            {activeCourseComplete
                                ? "Review your course →"
                                : "Continue learning →"}
                        </Link>
                    )}

                    <button
                        type="button"
                        className="secondary-button"
                        onClick={logout}
                    >
                        Sign out
                    </button>
                </div>
            </section>

            <section className="dashboard-stats">
                <article>
                    <span>Catalog</span>

                    <strong>
                        {coursesQuery.isPending
                            ? "—"
                            : coursesQuery.data?.count ??
                              "—"}
                    </strong>

                    <small>
                        courses available
                    </small>
                </article>

                <article>
                    <span>Enrolled</span>

                    <strong>
                        {coursesQuery.isPending ||
                        progressLoading
                            ? "—"
                            : enrolledSnapshots.length}
                    </strong>

                    <small>
                        learning paths started
                    </small>
                </article>

                <article>
                    <span>Completed</span>

                    <strong>
                        {coursesQuery.isPending ||
                        progressLoading
                            ? "—"
                            : completedCount}
                    </strong>

                    <small>
                        courses completed
                    </small>
                </article>

                <article>
                    <span>Assessment average</span>

                    <strong>
                        {coursesQuery.isPending ||
                        progressLoading
                            ? "—"
                            : averageAssessmentScore !== null
                              ? `${averageAssessmentScore}%`
                              : "—"}
                    </strong>

                    <small>
                        best scored attempts
                    </small>
                </article>
            </section>

            {coursesQuery.isPending && (
                <div className="status-card">
                    Loading your learning workspace...
                </div>
            )}

            {coursesQuery.isError && (
                <div className="status-card error">
                    Unable to load your learning workspace.
                </div>
            )}

            {coursesQuery.isSuccess &&
                progressLoading && (
                    <div className="status-card">
                        Checking your course progress...
                    </div>
                )}

            {coursesQuery.isSuccess &&
                progressError && (
                    <div className="status-card error">
                        Some course progress data could not
                        be loaded. You can continue from the
                        Courses page.
                    </div>
                )}

            {coursesQuery.isSuccess &&
                !progressLoading &&
                enrolledSnapshots.length === 0 && (
                    <section className="dashboard-empty">
                        <span className="eyebrow">
                            START HERE
                        </span>

                        <h2>
                            Your next step is waiting.
                        </h2>

                        <p>
                            Choose a course from the Tech Haven
                            catalog and start building practical
                            skills through lessons, activities,
                            and assessments.
                        </p>

                        <Link
                            to="/courses"
                            className="primary-button"
                        >
                            Explore courses →
                        </Link>
                    </section>
                )}

            {enrolledSnapshots.length > 0 && (
                <>
                    <section className="dashboard-command-grid">
                        <article className="dashboard-focus-card">
                            <div className="dashboard-focus-main">
                                <span className="eyebrow">
                                    {activeCourseComplete
                                        ? "COURSE COMPLETE"
                                        : "CONTINUE LEARNING"}
                                </span>

                                <h2>
                                    {activeSnapshot?.course.title}
                                </h2>

                                <p>
                                    {activeCourseComplete
                                        ? "You have completed this learning path. Review your work or open your credential."
                                        : activeNextLesson
                                          ? `Next lesson: ${activeNextLesson.title}.`
                                          : "Your next accessible lesson is ready."}
                                </p>

                                <div className="dashboard-action-row">
                                    <Link
                                        to={
                                            activeSnapshot
                                                ? `/courses/${activeSnapshot.course.slug}`
                                                : "/courses"
                                        }
                                        className="primary-button"
                                    >
                                        {activeCourseComplete
                                            ? "Review course"
                                            : "Continue learning"}
                                    </Link>

                                    {activeCourseComplete && (
                                        <Link
                                            to="/certificates"
                                            className="secondary-button"
                                        >
                                            View certificates
                                        </Link>
                                    )}
                                </div>
                            </div>

                            <div className="dashboard-focus-progress">
                                <span>Course progress</span>

                                <strong>
                                    {activePercentage}%
                                </strong>

                                <div
                                    className="th-progress-track"
                                    role="progressbar"
                                    aria-valuemin={0}
                                    aria-valuemax={100}
                                    aria-valuenow={
                                        activePercentage
                                    }
                                    aria-label={`${activeSnapshot?.course.title} progress`}
                                >
                                    <span
                                        style={{
                                            width: `${activePercentage}%`,
                                        }}
                                    />
                                </div>

                                <small>
                                    {
                                        activeSnapshot?.progress
                                            ?.progress
                                            .lessons_completed
                                    }
                                    /
                                    {
                                        activeSnapshot?.progress
                                            ?.progress
                                            .lessons_total
                                    }{" "}
                                    lessons complete
                                </small>
                            </div>
                        </article>

                        <aside className="dashboard-attention-card">
                            <div className="panel-heading">
                                <div>
                                    <span className="eyebrow">
                                        ASSESSMENT ATTENTION
                                    </span>

                                    <h2>
                                        {attentionItems.length > 0
                                            ? "Action needed"
                                            : "You are clear"}
                                    </h2>
                                </div>

                                <Link
                                    to="/assessments"
                                    className="text-link"
                                >
                                    Open center →
                                </Link>
                            </div>

                            {attentionItems.length === 0 ? (
                                <div className="dashboard-attention-empty">
                                    <strong>
                                        No assessments need your
                                        attention.
                                    </strong>

                                    <p>
                                        Recent practical work and
                                        quizzes are not waiting for a
                                        correction, review, or retry.
                                    </p>
                                </div>
                            ) : (
                                <div className="dashboard-attention-list">
                                    {attentionItems.map(
                                        (
                                            item,
                                            index,
                                        ) => (
                                            <Link
                                                key={`${item.kind ?? "assessment"}-${item.title}-${item.submitted_at}-${index}`}
                                                to="/assessments"
                                                className="dashboard-attention-item"
                                            >
                                                <div>
                                                    <strong>
                                                        {item.title}
                                                    </strong>

                                                    <small>
                                                        {
                                                            item.lesson_title
                                                        }
                                                    </small>
                                                </div>

                                                <span
                                                    className={`dashboard-status-badge ${assessmentTone(item.status)}`}
                                                >
                                                    {assessmentLabel(
                                                        item.status,
                                                    )}
                                                </span>
                                            </Link>
                                        ),
                                    )}
                                </div>
                            )}
                        </aside>
                    </section>

                    <section className="dashboard-content-grid">
                        <div className="dashboard-panel">
                            <div className="panel-heading">
                                <div>
                                    <span className="eyebrow">
                                        MY LEARNING
                                    </span>

                                    <h2>
                                        Course progress
                                    </h2>
                                </div>

                                <Link
                                    to="/courses"
                                    className="text-link"
                                >
                                    View catalog →
                                </Link>
                            </div>

                            <div className="dashboard-course-list">
                                {enrolledSnapshots.map(
                                    ({
                                        course,
                                        progress,
                                    }) => {
                                        const percentage =
                                            Math.round(
                                                progress
                                                    ?.progress
                                                    .overall_percentage ??
                                                0,
                                            );

                                        const isComplete =
                                            progress
                                                ?.course_completed ===
                                            true;

                                        return (
                                            <article
                                                key={
                                                    course.id
                                                }
                                                className="dashboard-course-row"
                                            >
                                                <div className="dashboard-course-row-main">
                                                    <div>
                                                        <span className="dashboard-course-level">
                                                            {
                                                                course.level
                                                            }
                                                        </span>

                                                        <h3>
                                                            {
                                                                course.title
                                                            }
                                                        </h3>

                                                        <p>
                                                            {
                                                                course.description
                                                            }
                                                        </p>
                                                    </div>

                                                    <div className="dashboard-course-result">
                                                        <strong>
                                                            {
                                                                percentage
                                                            }
                                                            %
                                                        </strong>

                                                        <small>
                                                            {
                                                                progress
                                                                    ?.progress
                                                                    .lessons_completed
                                                            }
                                                            /
                                                            {
                                                                progress
                                                                    ?.progress
                                                                    .lessons_total
                                                            }{" "}
                                                            lessons
                                                        </small>
                                                    </div>
                                                </div>

                                                <div className="dashboard-course-progress">
                                                    <div className="dashboard-inline-progress">
                                                        <span
                                                            style={{
                                                                width: `${percentage}%`,
                                                            }}
                                                        />
                                                    </div>

                                                    <Link
                                                        to={`/courses/${course.slug}`}
                                                        className="text-link"
                                                    >
                                                        {isComplete
                                                            ? "Review course →"
                                                            : "Continue →"}
                                                    </Link>
                                                </div>
                                            </article>
                                        );
                                    },
                                )}
                            </div>

                            <div className="dashboard-overall-progress">
                                <div>
                                    <span>
                                        Average completion
                                    </span>

                                    <strong>
                                        {averageCompletion}%
                                    </strong>
                                </div>

                                <p>
                                    Your average learning progress
                                    across all enrolled courses.
                                </p>
                            </div>
                        </div>

                        <div className="dashboard-side-stack">
                            <article className="dashboard-panel dashboard-achievement">
                                <div className="panel-heading">
                                    <div>
                                        <span className="eyebrow">
                                            RECENT ACHIEVEMENT
                                        </span>

                                        <h2>
                                            {latestAchievement
                                                ? "Latest result"
                                                : "Your next result"}
                                        </h2>
                                    </div>
                                </div>

                                {latestAchievement ? (
                                    <div className="dashboard-achievement-result">
                                        <div>
                                            <span>
                                                {
                                                    latestAchievement.kind ===
                                                    "quiz"
                                                        ? "QUIZ"
                                                        : "PRACTICAL ASSESSMENT"
                                                }
                                            </span>

                                            <h3>
                                                {
                                                    latestAchievement.title
                                                }
                                            </h3>

                                            <p>
                                                {
                                                    latestAchievement.lesson_title
                                                }
                                            </p>
                                        </div>

                                        <strong>
                                            {formatScore(
                                                latestAchievement,
                                            )}
                                        </strong>

                                        <small>
                                            {
                                                latestAchievement.status
                                            }
                                            {" · "}
                                            {formatDate(
                                                latestAchievement.submitted_at,
                                            )}
                                        </small>
                                    </div>
                                ) : (
                                    <div className="dashboard-achievement-empty">
                                        <strong>
                                            Submit your first
                                            assessment.
                                        </strong>

                                        <p>
                                            Scores and quiz results
                                            will appear here as you
                                            build your portfolio of
                                            proof.
                                        </p>

                                        <Link
                                            to="/assessments"
                                            className="text-link"
                                        >
                                            View assessments →
                                        </Link>
                                    </div>
                                )}
                            </article>

                            <article className="dashboard-panel dashboard-notifications">
                                <div className="panel-heading">
                                    <div>
                                        <span className="eyebrow">
                                            ACTIVITY
                                        </span>

                                        <h2>
                                            Notifications
                                        </h2>
                                    </div>

                                    <Link
                                        to="/notifications"
                                        className="text-link"
                                    >
                                        View all →
                                    </Link>
                                </div>

                                <div className="dashboard-notification-summary">
                                    <strong>
                                        {unreadCount}
                                    </strong>

                                    <span>
                                        unread
                                    </span>
                                </div>

                                {notificationsQuery.isPending && (
                                    <p className="muted-text">
                                        Loading notifications...
                                    </p>
                                )}

                                {notificationsQuery.isError && (
                                    <p className="muted-text">
                                        Notifications could not be
                                        loaded.
                                    </p>
                                )}

                                {notificationsQuery.isSuccess &&
                                    notificationsQuery.data.results
                                        .length === 0 && (
                                        <p className="muted-text">
                                            No notifications yet.
                                        </p>
                                    )}

                                {notificationsQuery.isSuccess &&
                                    notificationsQuery.data.results
                                        .slice(0, 3)
                                        .map(
                                            (
                                                notification,
                                            ) => (
                                                <div
                                                    key={
                                                        notification.id
                                                    }
                                                    className={
                                                        notification.is_read
                                                            ? "mini-notification"
                                                            : "mini-notification unread"
                                                    }
                                                >
                                                    <strong>
                                                        {
                                                            notification.title
                                                        }
                                                    </strong>

                                                    <p>
                                                        {
                                                            notification.message
                                                        }
                                                    </p>
                                                </div>
                                            ),
                                        )}
                            </article>
                        </div>
                    </section>
                </>
            )}

            <section className="dashboard-cta">
                <div>
                    <span className="eyebrow">
                        THE TECH HAVEN MODEL
                    </span>

                    <h2>
                        Learn. Build. Prove. Launch.
                    </h2>

                    <p>
                        Your dashboard turns course progress,
                        assessments, corrections, and results
                        into one practical next-step loop.
                    </p>
                </div>

                <Link
                    to={
                        hasActiveCourse
                            ? `/courses/${activeSnapshot?.course.slug}`
                            : "/courses"
                    }
                    className="primary-button"
                >
                    {hasActiveCourse
                        ? "Continue learning"
                        : "Explore learning"}
                </Link>
            </section>
        </div>
    );
}
