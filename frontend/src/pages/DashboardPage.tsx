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

    const username =
        auth?.user.username ??
        "Learner";

    return (
        <div className="page dashboard-page">
            <section className="dashboard-welcome">
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
                        Your Tech Haven workspace
                        is connected to the Django
                        learning engine.
                    </p>
                </div>

                <button
                    type="button"
                    className="secondary-button"
                    onClick={logout}
                >
                    Sign out
                </button>
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
            </section>

            <section className="dashboard-grid">
                <div className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                MY LEARNING
                            </span>

                            <h2>
                                Keep building momentum.
                            </h2>
                        </div>

                        <Link
                            to="/courses"
                            className="text-link"
                        >
                            View catalog →
                        </Link>
                    </div>

                    {coursesQuery.isPending && (
                        <div className="status-card">
                            Loading your learning
                            workspace...
                        </div>
                    )}

                    {coursesQuery.isError && (
                        <div className="status-card error">
                            Unable to load your
                            learning workspace.
                        </div>
                    )}

                    {coursesQuery.isSuccess &&
                        progressLoading && (
                            <div className="status-card">
                                Checking your course
                                progress...
                            </div>
                        )}

                    {coursesQuery.isSuccess &&
                        progressError && (
                            <div className="status-card error">
                                Some course progress
                                data could not be
                                loaded. You can
                                continue from the
                                Courses page.
                            </div>
                        )}

                    {coursesQuery.isSuccess &&
                        !progressLoading &&
                        enrolledSnapshots.length ===
                            0 && (
                            <div className="status-card">
                                <strong>
                                    Start your first
                                    learning path.
                                </strong>

                                <p>
                                    Choose a course from
                                    the Tech Haven
                                    catalog and begin
                                    building practical
                                    skills.
                                </p>

                                <Link
                                    to="/courses"
                                    className="primary-button"
                                >
                                    Explore courses
                                </Link>
                            </div>
                        )}

                    {enrolledSnapshots.length >
                        0 && (
                        <div className="mini-course-grid">
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

                                    return (
                                        <article
                                            key={
                                                course.id
                                            }
                                            className="mini-course-card"
                                        >
                                            <span>
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

                                            <div
                                                style={{
                                                    marginTop:
                                                        "16px",
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        display:
                                                            "flex",
                                                        justifyContent:
                                                            "space-between",
                                                        gap:
                                                            "12px",
                                                        marginBottom:
                                                            "7px",
                                                    }}
                                                >
                                                    <small>
                                                        Progress
                                                    </small>

                                                    <strong>
                                                        {
                                                            percentage
                                                        }
                                                        %
                                                    </strong>
                                                </div>

                                                <div
                                                    className="th-progress-track"
                                                    role="progressbar"
                                                    aria-valuemin={
                                                        0
                                                    }
                                                    aria-valuemax={
                                                        100
                                                    }
                                                    aria-valuenow={
                                                        percentage
                                                    }
                                                    aria-label={`${course.title} progress`}
                                                >
                                                    <span
                                                        style={{
                                                            width: `${percentage}%`,
                                                        }}
                                                    />
                                                </div>
                                            </div>

                                            <div
                                                style={{
                                                    display:
                                                        "flex",
                                                    justifyContent:
                                                        "space-between",
                                                    gap:
                                                        "12px",
                                                    alignItems:
                                                        "center",
                                                    marginTop:
                                                        "16px",
                                                }}
                                            >
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

                                                <Link
                                                    to={`/courses/${course.slug}`}
                                                    className="text-link"
                                                >
                                                    {progress
                                                        ?.course_completed
                                                        ? "Review course →"
                                                        : "Continue →"}
                                                </Link>
                                            </div>
                                        </article>
                                    );
                                },
                            )}
                        </div>
                    )}

                    {enrolledSnapshots.length >
                        0 && (
                        <div
                            style={{
                                marginTop:
                                    "20px",
                            }}
                        >
                            <span className="eyebrow">
                                OVERALL PROGRESS
                            </span>

                            <p
                                className="muted-text"
                                style={{
                                    marginTop:
                                        "8px",
                                }}
                            >
                                Your average completion
                                across enrolled courses
                                is{" "}
                                <strong>
                                    {
                                        averageCompletion
                                    }
                                    %
                                </strong>
                                .
                            </p>
                        </div>
                    )}
                </div>

                <aside className="dashboard-panel notification-panel">
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

                    {notificationsQuery.isPending && (
                        <p className="muted-text">
                            Loading notifications...
                        </p>
                    )}

                    {notificationsQuery.isError && (
                        <p className="muted-text">
                            Notifications could not
                            be loaded.
                        </p>
                    )}

                    {notificationsQuery.isSuccess &&
                        notificationsQuery.data.results.length ===
                            0 && (
                            <p className="muted-text">
                                No notifications yet.
                            </p>
                        )}

                    {notificationsQuery.isSuccess &&
                        notificationsQuery.data.results
                            .slice(0, 4)
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
                </aside>
            </section>

            <section className="dashboard-cta">
                <div>
                    <span className="eyebrow">
                        THE TECH HAVEN MODEL
                    </span>

                    <h2>
                        Learn. Build. Prove. Launch.
                    </h2>

                    <p>
                        Every learning activity now
                        contributes to measurable
                        progress, assessments, and
                        credentials.
                    </p>
                </div>

                <Link
                    to="/courses"
                    className="primary-button"
                >
                    Explore learning
                </Link>
            </section>
        </div>
    );
}