import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    Link,
    Navigate,
} from "react-router";
import { getSubmissions } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Submission } from "../types/api";
const EMPTY_SUBMISSIONS: Submission[] = [];

type StatusFilter =
    | "all"
    | "pending"
    | "graded"
    | "correction"
    | "error";

function isInstructor(
    role: string | undefined,
    isStaff: boolean | undefined,
) {
    return (
        Boolean(isStaff) ||
        role === "INSTRUCTOR" ||
        role === "ADMIN"
    );
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function statusLabel(submission: Submission) {
    if (submission.status === "correction") {
        return "Needs correction";
    }

    if (submission.status === "error") {
        return "Execution error";
    }

    if (submission.score !== null) {
        return "Graded";
    }

    return "Pending review";
}

function matchesStatus(
    submission: Submission,
    filter: StatusFilter,
) {
    if (filter === "all") {
        return true;
    }

    if (filter === "pending") {
        return (
            submission.status === "submitted" &&
            submission.score === null
        );
    }

    if (filter === "graded") {
        return (
            submission.status !== "correction" &&
            submission.status !== "error" &&
            submission.score !== null
        );
    }

    return submission.status === filter;
}

export default function InstructorDashboardPage() {
    const { auth } = useAuth();
    const token = auth?.token ?? "";

    const instructor = isInstructor(
        auth?.user.role,
        auth?.user.is_staff,
    );

    const submissionsQuery = useQuery({
        queryKey: [
            "instructor-dashboard-submissions",
            token,
        ],
        queryFn: () => getSubmissions(token),
        enabled: Boolean(token) && instructor,
    });

    const [search, setSearch] = useState("");
    const [courseFilter, setCourseFilter] =
        useState("all");
    const [studentFilter, setStudentFilter] =
        useState("all");
    const [statusFilter, setStatusFilter] =
        useState<StatusFilter>("all");

    const submissions =
        submissionsQuery.data?.results ??
        EMPTY_SUBMISSIONS;

    const courseOptions = useMemo(
        () =>
            Array.from(
                new Set(
                    submissions.map(
                        (submission) =>
                            submission.course.title,
                    ),
                ),
            ).sort(),
        [submissions],
    );

    const studentOptions = useMemo(
        () =>
            Array.from(
                new Set(
                    submissions.map(
                        (submission) =>
                            submission.student.username,
                    ),
                ),
            ).sort(),
        [submissions],
    );

    const stats = useMemo(() => {
        const pending = submissions.filter(
            (submission) =>
                submission.status === "submitted" &&
                submission.score === null,
        );

        const correction = submissions.filter(
            (submission) =>
                submission.status === "correction",
        );

        const errors = submissions.filter(
            (submission) =>
                submission.status === "error",
        );

        const graded = submissions.filter(
            (submission) =>
                submission.status !== "correction" &&
                submission.status !== "error" &&
                submission.score !== null,
        );

        const average =
            graded.length > 0
                ? graded.reduce(
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
                  ) / graded.length
                : null;

        return {
            total: submissions.length,
            pending: pending.length,
            correction: correction.length,
            errors: errors.length,
            graded: graded.length,
            average,
            reviewRate:
                submissions.length > 0
                    ? ((submissions.length -
                          pending.length) /
                          submissions.length) *
                      100
                    : 0,
        };
    }, [submissions]);

    const visibleSubmissions = useMemo(() => {
        const normalizedSearch =
            search.trim().toLowerCase();

        return submissions
            .filter((submission) =>
                matchesStatus(
                    submission,
                    statusFilter,
                ),
            )
            .filter(
                (submission) =>
                    courseFilter === "all" ||
                    submission.course.title ===
                        courseFilter,
            )
            .filter(
                (submission) =>
                    studentFilter === "all" ||
                    submission.student.username ===
                        studentFilter,
            )
            .filter((submission) => {
                if (!normalizedSearch) {
                    return true;
                }

                return [
                    submission.activity.title,
                    submission.course.title,
                    submission.student.username,
                    submission.activity.activity_type,
                ].some((value) =>
                    value
                        .toLowerCase()
                        .includes(normalizedSearch),
                );
            })
            .sort(
                (first, second) =>
                    new Date(
                        second.submitted_at,
                    ).getTime() -
                    new Date(
                        first.submitted_at,
                    ).getTime(),
            );
    }, [
        submissions,
        search,
        courseFilter,
        studentFilter,
        statusFilter,
    ]);

    const courseAnalytics = useMemo(() => {
        const grouped = new Map<
            string,
            {
                title: string;
                total: number;
                pending: number;
                correction: number;
                graded: number;
                average: number | null;
                students: Set<string>;
                scores: number[];
            }
        >();

        for (const submission of submissions) {
            const title =
                submission.course.title;

            const existing =
                grouped.get(title) ?? {
                    title,
                    total: 0,
                    pending: 0,
                    correction: 0,
                    graded: 0,
                    average: null,
                    students: new Set<string>(),
                    scores: [],
                };

            existing.total += 1;
            existing.students.add(
                submission.student.username,
            );

            if (
                submission.status === "submitted" &&
                submission.score === null
            ) {
                existing.pending += 1;
            }

            if (
                submission.status ===
                "correction"
            ) {
                existing.correction += 1;
            }

            if (
                submission.status !==
                    "correction" &&
                submission.status !== "error" &&
                submission.score !== null
            ) {
                existing.graded += 1;
                existing.scores.push(
                    (submission.score /
                        Math.max(
                            submission.activity
                                .max_score,
                            1,
                        )) *
                        100,
                );
            }

            grouped.set(title, existing);
        }

        return Array.from(
            grouped.values(),
        )
            .map((course) => ({
                ...course,
                average:
                    course.scores.length > 0
                        ? course.scores.reduce(
                              (total, score) =>
                                  total + score,
                              0,
                          ) /
                          course.scores.length
                        : null,
            }))
            .sort(
                (first, second) =>
                    second.total - first.total,
            );
    }, [submissions]);

    const activityTypeAnalytics = useMemo(() => {
        const grouped = new Map<
            string,
            {
                type: string;
                total: number;
                pending: number;
                graded: number;
                correction: number;
            }
        >();

        for (const submission of submissions) {
            const type =
                submission.activity.activity_type;

            const existing =
                grouped.get(type) ?? {
                    type,
                    total: 0,
                    pending: 0,
                    graded: 0,
                    correction: 0,
                };

            existing.total += 1;

            if (
                submission.status === "submitted" &&
                submission.score === null
            ) {
                existing.pending += 1;
            }

            if (
                submission.status === "correction"
            ) {
                existing.correction += 1;
            }

            if (
                submission.status !==
                    "correction" &&
                submission.status !== "error" &&
                submission.score !== null
            ) {
                existing.graded += 1;
            }

            grouped.set(type, existing);
        }

        return Array.from(
            grouped.values(),
        ).sort(
            (first, second) =>
                second.total - first.total,
        );
    }, [submissions]);

    const pendingSubmissions = useMemo(
        () =>
            submissions
                .filter(
                    (submission) =>
                        submission.status ===
                            "submitted" &&
                        submission.score === null,
                )
                .sort(
                    (first, second) =>
                        new Date(
                            first.submitted_at,
                        ).getTime() -
                        new Date(
                            second.submitted_at,
                        ).getTime(),
                )
                .slice(0, 8),
        [submissions],
    );

    const oldestPending =
        pendingSubmissions[0] ?? null;

    if (!instructor) {
        return (
            <Navigate
                to="/dashboard"
                replace
            />
        );
    }

    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        INSTRUCTOR DASHBOARD
                    </span>

                    <h1>
                        See the learning workload.
                    </h1>

                    <p>
                        Monitor review demand, student
                        activity, course performance, and
                        practical assessment quality from
                        one workspace.
                    </p>
                </div>

                <Link
                    to="/instructor/assessments"
                    className="text-link"
                >
                    Open review queue
                </Link>
            </section>

            {submissionsQuery.isPending && (
                <div className="status-card">
                    Loading instructor analytics...
                </div>
            )}

            {submissionsQuery.isError && (
                <div className="status-card error">
                    Unable to load instructor analytics.
                    <br />
                    {submissionsQuery.error instanceof
                    Error
                        ? submissionsQuery.error.message
                        : "Please try again."}
                </div>
            )}

            {submissionsQuery.isSuccess && (
                <>
                    <section className="dashboard-stats">
                        <article>
                            <span>
                                Total submissions
                            </span>
                            <strong>
                                {stats.total}
                            </strong>
                            <small>
                                all student assessment
                                records
                            </small>
                        </article>

                        <article>
                            <span>
                                Awaiting review
                            </span>
                            <strong>
                                {stats.pending}
                            </strong>
                            <small>
                                action required
                            </small>
                        </article>

                        <article>
                            <span>
                                Needs correction
                            </span>
                            <strong>
                                {stats.correction}
                            </strong>
                            <small>
                                returned to learners
                            </small>
                        </article>

                        <article>
                            <span>
                                Graded
                            </span>
                            <strong>
                                {stats.graded}
                            </strong>
                            <small>
                                completed reviews
                            </small>
                        </article>

                        <article>
                            <span>
                                Practical average
                            </span>
                            <strong>
                                {stats.average ===
                                null
                                    ? "—"
                                    : `${stats.average.toFixed(1)}%`}
                            </strong>
                            <small>
                                correction attempts
                                excluded
                            </small>
                        </article>

                        <article>
                            <span>
                                Review coverage
                            </span>
                            <strong>
                                {stats.reviewRate.toFixed(
                                    1,
                                )}
                                %
                            </strong>
                            <small>
                                records already reviewed
                            </small>
                        </article>
                    </section>

                    <section className="dashboard-panel">
                        <div className="panel-heading">
                            <div>
                                <span className="eyebrow">
                                    REVIEW WORKLOAD
                                </span>

                                <h2>
                                    Current queue
                                </h2>
                            </div>

                            <Link
                                to="/instructor/assessments"
                                className="text-link"
                            >
                                Review submissions →
                            </Link>
                        </div>

                        {oldestPending && (
                            <div className="status-card">
                                <strong>
                                    Oldest pending:{" "}
                                    {
                                        oldestPending
                                            .activity
                                            .title
                                    }
                                </strong>

                                <p>
                                    {
                                        oldestPending
                                            .student
                                            .username
                                    }
                                    {" · "}
                                    {
                                        oldestPending
                                            .course
                                            .title
                                    }
                                    {" · "}
                                    {formatDate(
                                        oldestPending.submitted_at,
                                    )}
                                </p>

                                <Link
                                    to={`/instructor/assessments/submissions/${oldestPending.id}`}
                                    className="text-link"
                                >
                                    Review oldest submission →
                                </Link>
                            </div>
                        )}

                        <div className="assessment-list">
                            {pendingSubmissions.length ===
                            0 ? (
                                <div className="status-card">
                                    No submissions are
                                    currently awaiting
                                    review.
                                </div>
                            ) : (
                                pendingSubmissions.map(
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
                                                    Student:{" "}
                                                    {
                                                        submission
                                                            .student
                                                            .username
                                                    }
                                                    {" · "}
                                                    {
                                                        submission
                                                            .course
                                                            .title
                                                    }
                                                </p>
                                            </div>

                                            <div className="assessment-card-meta">
                                                <span>
                                                    Pending
                                                </span>

                                                <small>
                                                    {formatDate(
                                                        submission.submitted_at,
                                                    )}
                                                </small>

                                                <Link
                                                    to={`/instructor/assessments/submissions/${submission.id}`}
                                                    className="text-link"
                                                >
                                                    Review →
                                                </Link>
                                            </div>
                                        </article>
                                    ),
                                )
                            )}
                        </div>
                    </section>

                    <section className="dashboard-grid">
                        <div className="dashboard-panel">
                            <div className="panel-heading">
                                <div>
                                    <span className="eyebrow">
                                        PERFORMANCE
                                    </span>

                                    <h2>
                                        Course analytics
                                    </h2>
                                </div>
                            </div>

                            <div className="assessment-list">
                                {courseAnalytics.map(
                                    (course) => (
                                        <article
                                            key={
                                                course.title
                                            }
                                            className="assessment-card"
                                        >
                                            <div>
                                                <span className="course-level">
                                                    {
                                                        course.students
                                                            .size
                                                    }{" "}
                                                    students
                                                </span>

                                                <h3>
                                                    {
                                                        course.title
                                                    }
                                                </h3>

                                                <p>
                                                    {
                                                        course.total
                                                    }{" "}
                                                    submissions ·{" "}
                                                    {
                                                        course.graded
                                                    }{" "}
                                                    graded ·{" "}
                                                    {
                                                        course.pending
                                                    }{" "}
                                                    pending
                                                </p>
                                            </div>

                                            <div className="assessment-card-meta">
                                                <strong>
                                                    {course.average ===
                                                    null
                                                        ? "—"
                                                        : `${course.average.toFixed(1)}%`}
                                                </strong>

                                                <small>
                                                    practical average
                                                </small>

                                                {course.correction >
                                                    0 && (
                                                    <span>
                                                        {
                                                            course.correction
                                                        }{" "}
                                                        correction
                                                        {
                                                            course.correction ===
                                                            1
                                                                ? ""
                                                                : "s"}
                                                    </span>
                                                )}
                                            </div>
                                        </article>
                                    ),
                                )}
                            </div>
                        </div>

                        <aside className="dashboard-panel">
                            <div className="panel-heading">
                                <div>
                                    <span className="eyebrow">
                                        ACTIVITY MIX
                                    </span>

                                    <h2>
                                        Assessment types
                                    </h2>
                                </div>
                            </div>

                            <div className="assessment-options">
                                {activityTypeAnalytics.map(
                                    (item) => (
                                        <article
                                            key={item.type}
                                        >
                                            <span className="feature-number">
                                                {item.type
                                                    .replaceAll(
                                                        "_",
                                                        " ",
                                                    )
                                                    .toUpperCase()}
                                            </span>

                                            <h3>
                                                {
                                                    item.total
                                                }
                                            </h3>

                                            <p>
                                                {
                                                    item.graded
                                                }{" "}
                                                graded ·{" "}
                                                {
                                                    item.pending
                                                }{" "}
                                                pending ·{" "}
                                                {
                                                    item.correction
                                                }{" "}
                                                correction
                                            </p>
                                        </article>
                                    ),
                                )}
                            </div>
                        </aside>
                    </section>

                    <section className="dashboard-panel">
                        <div className="panel-heading">
                            <div>
                                <span className="eyebrow">
                                    SUBMISSION EXPLORER
                                </span>

                                <h2>
                                    Search and filter
                                </h2>
                            </div>

                            <span className="text-link">
                                {visibleSubmissions.length}{" "}
                                matching
                            </span>
                        </div>

                        <div className="assessment-options">
                            <article>
                                <label htmlFor="submission-search">
                                    Search
                                </label>

                                <input
                                    id="submission-search"
                                    type="search"
                                    value={search}
                                    onChange={(event) =>
                                        setSearch(
                                            event.target
                                                .value,
                                        )
                                    }
                                    placeholder="Student, course, activity..."
                                />
                            </article>

                            <article>
                                <label htmlFor="course-filter">
                                    Course
                                </label>

                                <select
                                    id="course-filter"
                                    value={courseFilter}
                                    onChange={(event) =>
                                        setCourseFilter(
                                            event.target
                                                .value,
                                        )
                                    }
                                >
                                    <option value="all">
                                        All courses
                                    </option>

                                    {courseOptions.map(
                                        (course) => (
                                            <option
                                                key={course}
                                                value={course}
                                            >
                                                {course}
                                            </option>
                                        ),
                                    )}
                                </select>
                            </article>

                            <article>
                                <label htmlFor="student-filter">
                                    Student
                                </label>

                                <select
                                    id="student-filter"
                                    value={studentFilter}
                                    onChange={(event) =>
                                        setStudentFilter(
                                            event.target
                                                .value,
                                        )
                                    }
                                >
                                    <option value="all">
                                        All students
                                    </option>

                                    {studentOptions.map(
                                        (student) => (
                                            <option
                                                key={student}
                                                value={student}
                                            >
                                                {student}
                                            </option>
                                        ),
                                    )}
                                </select>
                            </article>

                            <article>
                                <label htmlFor="status-filter">
                                    Status
                                </label>

                                <select
                                    id="status-filter"
                                    value={statusFilter}
                                    onChange={(event) =>
                                        setStatusFilter(
                                            event.target
                                                .value as StatusFilter,
                                        )
                                    }
                                >
                                    <option value="all">
                                        All statuses
                                    </option>
                                    <option value="pending">
                                        Pending review
                                    </option>
                                    <option value="graded">
                                        Graded
                                    </option>
                                    <option value="correction">
                                        Needs correction
                                    </option>
                                    <option value="error">
                                        Execution errors
                                    </option>
                                </select>
                            </article>
                        </div>

                        <div className="assessment-list">
                            {visibleSubmissions.length ===
                            0 ? (
                                <div className="status-card">
                                    No submissions match
                                    the selected filters.
                                </div>
                            ) : (
                                visibleSubmissions.map(
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
                                                            .student
                                                            .username
                                                    }
                                                    {" · "}
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
                                                        submission,
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
                                                    to={`/instructor/assessments/submissions/${submission.id}`}
                                                    className="text-link"
                                                >
                                                    Review →
                                                </Link>
                                            </div>
                                        </article>
                                    ),
                                )
                            )}
                        </div>
                    </section>
                </>
            )}
        </div>
    );
}