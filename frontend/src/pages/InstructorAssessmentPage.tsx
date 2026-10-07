import { useState } from "react";
import { Link, Navigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { getSubmissions } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Submission } from "../types/api";

type Filter =
    | "all"
    | "pending"
    | "graded"
    | "correction"
    | "error";

const filters: Array<{ value: Filter; label: string }> = [
    { value: "all", label: "All" },
    { value: "pending", label: "Pending" },
    { value: "graded", label: "Graded" },
    { value: "correction", label: "Needs correction" },
    { value: "error", label: "Execution errors" },
];

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

function getStatus(submission: Submission) {
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

function matchesFilter(
    submission: Submission,
    filter: Filter,
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

    return submission.status === filter;
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

export default function InstructorAssessmentPage() {
    const { auth } = useAuth();
    const token = auth?.token ?? "";

    const [filter, setFilter] =
        useState<Filter>("pending");

    const instructor =
        isInstructor(
            auth?.user.role,
            auth?.user.is_staff,
        );

    const submissionsQuery = useQuery({
        queryKey: [
            "instructor-assessment-submissions",
            token,
        ],
        queryFn: () => getSubmissions(token),
        enabled: Boolean(token) && instructor,
    });

    const submissions =
        submissionsQuery.data?.results ?? [];

    const stats = {
        all: submissions.length,
        pending: submissions.filter(
            (submission) =>
                submission.status === "submitted" &&
                submission.score === null,
        ).length,
        graded: submissions.filter(
            (submission) =>
                submission.status !== "correction" &&
                submission.score !== null,
        ).length,
        correction: submissions.filter(
            (submission) =>
                submission.status === "correction",
        ).length,
        error: submissions.filter(
            (submission) =>
                submission.status === "error",
        ).length,
    };
    const visibleSubmissions =
        submissions.filter((submission) =>
            matchesFilter(
                submission,
                filter,
            ),
        );

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
                        INSTRUCTOR WORKSPACE
                    </span>

                    <h1>
                        Review student
                        <br />
                        assessments.
                    </h1>

                    <p>
                        Review submitted work, assign
                        grades, provide feedback, and
                        return practical assessment
                        results to learners.
                    </p>
                </div>

                <Link
                    to="/assessments"
                    className="text-link"
                >
                    Student assessment center ?
                </Link>
            </section>

            <section className="dashboard-stats">
                <article>
                    <span>All submissions</span>
                    <strong>
                        {submissionsQuery.isPending
                            ? "�"
                            : stats.all}
                    </strong>
                    <small>
                        student assessment records
                    </small>
                </article>

                <article>
                    <span>Pending review</span>
                    <strong>
                        {submissionsQuery.isPending
                            ? "�"
                            : stats.pending}
                    </strong>
                    <small>
                        submissions requiring action
                    </small>
                </article>

                <article>
                    <span>Graded</span>
                    <strong>
                        {submissionsQuery.isPending
                            ? "�"
                            : stats.graded}
                    </strong>
                    <small>
                        completed assessments
                    </small>
                </article>

                <article>
                    <span>Needs correction</span>
                    <strong>
                        {submissionsQuery.isPending
                            ? "�"
                            : stats.correction}
                    </strong>
                    <small>
                        learners requiring another pass
                    </small>
                </article>
            </section>

            <section className="dashboard-panel">
                <div className="panel-heading">
                    <div>
                        <span className="eyebrow">
                            REVIEW QUEUE
                        </span>

                        <h2>
                            Student submissions
                        </h2>
                    </div>
                </div>

                <div className="assessment-options">
                    {filters.map((item) => (
                        <button
                            key={item.value}
                            type="button"
                            className={
                                filter === item.value
                                    ? "primary-button"
                                    : "secondary-button"
                            }
                            onClick={() =>
                                setFilter(item.value)
                            }
                        >
                            {item.label}
                            {" � "}
                            {stats[item.value]}
                        </button>
                    ))}
                </div>

                {submissionsQuery.isPending && (
                    <div className="status-card">
                        Loading the review queue...
                    </div>
                )}

                {submissionsQuery.isError && (
                    <div className="status-card error">
                        Unable to load student submissions.
                        <br />
                        {submissionsQuery.error instanceof Error
                            ? submissionsQuery.error.message
                            : "Please try again."}
                    </div>
                )}

                {submissionsQuery.isSuccess &&
                    visibleSubmissions.length === 0 && (
                        <div className="status-card">
                            <strong>
                                No submissions in this view.
                            </strong>

                            <p>
                                There are no student
                                submissions matching the
                                selected filter.
                            </p>
                        </div>
                    )}

                {submissionsQuery.isSuccess &&
                    visibleSubmissions.length > 0 && (
                        <div className="assessment-list">
                            {visibleSubmissions.map(
                                (submission) => (
                                    <article
                                        key={submission.id}
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
                                                <br />
                                                Course:{" "}
                                                {
                                                    submission
                                                        .course
                                                        .title
                                                }
                                                <br />
                                                Submitted:{" "}
                                                {formatDate(
                                                    submission.submitted_at,
                                                )}
                                            </p>
                                        </div>

                                        <div className="assessment-card-meta">
                                            <span>
                                                {getStatus(
                                                    submission,
                                                )}
                                            </span>

                                            <strong>
                                                {submission.score === null
                                                    ? "Not graded"
                                                    : `${submission.score}/${submission.activity.max_score}`}
                                            </strong>

                                            <small>
                                                {
                                                    submission
                                                        .activity
                                                        .max_score
                                                }{" "}
                                                max points
                                            </small>

                                            <Link
                                                to={`/instructor/assessments/submissions/${submission.id}`}
                                                className="text-link"
                                            >
                                                Review submission ?
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
