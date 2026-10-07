import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";

import {
    getCourseDetail,
    getCourses,
    getCourseProgress,
    getSubmissions,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import type {
    Course,
    CourseDetail,
    Submission,
} from "../types/api";

type ProjectStatus =
    | "not_started"
    | "awaiting_review"
    | "needs_correction"
    | "graded";

type Project = {
    activityId: number;
    activityTitle: string;
    activityType: string;
    instructions: string;
    maxScore: number;
    required: boolean;
    courseTitle: string;
    courseSlug: string;
    lessonId: number;
    lessonTitle: string;
    moduleTitle: string;
    status: ProjectStatus;
    latestSubmission: Submission | null;
};

function normalizeList<T>(value: unknown): T[] {
    if (Array.isArray(value)) {
        return value as T[];
    }

    if (
        value &&
        typeof value === "object" &&
        "results" in value
    ) {
        const results = (
            value as { results?: unknown }
        ).results;

        return Array.isArray(results)
            ? (results as T[])
            : [];
    }

    return [];
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function activityTypeLabel(value: string) {
    if (value === "coding") {
        return "Coding Project";
    }

    if (value === "assignment") {
        return "Assignment";
    }

    if (value === "lab") {
        return "Practical Lab";
    }

    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) =>
            letter.toUpperCase(),
        );
}

function getProjectStatus(
    submission: Submission | null,
): ProjectStatus {
    if (!submission) {
        return "not_started";
    }

    if (
        submission.status
            .toLowerCase()
            .includes("correction")
    ) {
        return "needs_correction";
    }

    if (submission.score !== null) {
        return "graded";
    }

    return "awaiting_review";
}

function statusLabel(status: ProjectStatus) {
    return {
        not_started: "Not started",
        awaiting_review: "Awaiting review",
        needs_correction: "Needs correction",
        graded: "Graded",
    }[status];
}

function latestSubmission(
    submissions: Submission[],
    activityId: number,
) {
    return (
        submissions
            .filter(
                (submission) =>
                    submission.activity.id ===
                    activityId,
            )
            .sort(
                (first, second) =>
                    new Date(
                        second.submitted_at,
                    ).getTime() -
                    new Date(
                        first.submitted_at,
                    ).getTime(),
            )[0] ?? null
    );
}

async function loadProjects(
    token: string,
): Promise<Project[]> {
    const [
        coursesResponse,
        submissionsResponse,
    ] = await Promise.all([
        getCourses(),
        getSubmissions(token),
    ]);

    const courses = normalizeList<Course>(
        coursesResponse,
    );

    const submissions =
        submissionsResponse.results ?? [];

    const courseDetails =
        await Promise.all(
            courses.map(async (course) => {
                try {
                    return await getCourseDetail(
                        course.slug,
                    );
                } catch {
                    return null;
                }
            }),
        );

    return courseDetails
        .filter(
            (
                course,
            ): course is CourseDetail =>
                course !== null,
        )
        .flatMap((course) =>
            course.modules.flatMap((module) =>
                module.lessons.flatMap((lesson) =>
                    lesson.activities
                        .filter((activity) =>
                            [
                                "coding",
                                "assignment",
                                "lab",
                            ].includes(
                                activity.activity_type,
                            ),
                        )
                        .map((activity) => {
                            const submission =
                                latestSubmission(
                                    submissions,
                                    activity.id,
                                );

                            return {
                                activityId:
                                    activity.id,
                                activityTitle:
                                    activity.title,
                                activityType:
                                    activity.activity_type,
                                instructions:
                                    activity.instructions,
                                maxScore:
                                    activity.max_score,
                                required:
                                    activity.is_required,
                                courseTitle:
                                    course.title,
                                courseSlug:
                                    course.slug,
                                lessonId:
                                    lesson.id,
                                lessonTitle:
                                    lesson.title,
                                moduleTitle:
                                    module.title,
                                status:
                                    getProjectStatus(
                                        submission,
                                    ),
                                latestSubmission:
                                    submission,
                            };
                        }),
                ),
            ),
        );
}

export default function ProjectsPage() {
    const {
        courseSlug,
        activityId,
    } = useParams<{
        courseSlug?: string;
        activityId?: string;
    }>();

    const { auth } = useAuth();
    const token = auth?.token ?? "";

    const projectsQuery = useQuery({
        queryKey: ["projects", token],
        queryFn: () => loadProjects(token),
        enabled: Boolean(token),
    });

    if (courseSlug && activityId) {
        return (
            <ProjectDetail
                project={projectsQuery.data?.find(
                    (item) =>
                        item.courseSlug ===
                            courseSlug &&
                        String(
                            item.activityId,
                        ) === activityId,
                )}
                token={token}
            />
        );
    }

    return (
        <ProjectCatalog
            projects={
                projectsQuery.data ?? []
            }
            pending={projectsQuery.isPending}
            error={projectsQuery.isError}
        />
    );
}

function ProjectCatalog({
    projects,
    pending,
    error,
}: {
    projects: Project[];
    pending: boolean;
    error: boolean;
}) {
    const [filter, setFilter] =
        useState<"all" | "in_progress" | "graded">(
            "all",
        );

    const [search, setSearch] =
        useState("");

    const filteredProjects = useMemo(() => {
        const query = search
            .trim()
            .toLowerCase();

        return projects.filter((project) => {
            const matchesFilter =
                filter === "all" ||
                (filter === "in_progress" &&
                    [
                        "awaiting_review",
                        "needs_correction",
                    ].includes(
                        project.status,
                    )) ||
                (filter === "graded" &&
                    project.status === "graded");

            if (!matchesFilter) {
                return false;
            }

            if (!query) {
                return true;
            }

            return [
                project.activityTitle,
                project.courseTitle,
                project.lessonTitle,
                project.moduleTitle,
            ].some((value) =>
                value
                    .toLowerCase()
                    .includes(query),
            );
        });
    }, [filter, projects, search]);

    const notStarted =
        projects.filter(
            (project) =>
                project.status ===
                "not_started",
        ).length;

    const inProgress =
        projects.filter((project) =>
            [
                "awaiting_review",
                "needs_correction",
            ].includes(project.status),
        ).length;

    const graded =
        projects.filter(
            (project) =>
                project.status === "graded",
        ).length;

    const scoredProjects =
        projects.filter(
            (project) =>
                project.latestSubmission
                    ?.score !== null &&
                project.latestSubmission
                    ?.score !== undefined,
        );

    const averageScore =
        scoredProjects.length > 0
            ? scoredProjects.reduce(
                  (total, project) =>
                      total +
                      ((project.latestSubmission
                          ?.score ?? 0) /
                          Math.max(
                              project.maxScore,
                              1,
                          )) *
                          100,
                  0,
              ) / scoredProjects.length
            : null;

    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        BUILD PORTFOLIO
                    </span>

                    <h1>
                        Build real projects.
                    </h1>

                    <p>
                        Discover practical work,
                        submit your solution, and
                        track review, feedback,
                        scores, and course progress.
                    </p>
                </div>
            </section>

            <section className="project-stats">
                <div className="project-stat">
                    <span>Total</span>
                    <strong>{projects.length}</strong>
                </div>

                <div className="project-stat">
                    <span>Not started</span>
                    <strong>{notStarted}</strong>
                </div>

                <div className="project-stat">
                    <span>In progress</span>
                    <strong>{inProgress}</strong>
                </div>

                <div className="project-stat">
                    <span>Graded</span>
                    <strong>{graded}</strong>
                </div>

                <div className="project-stat">
                    <span>Average</span>
                    <strong>
                        {averageScore === null
                            ? "—"
                            : `${averageScore.toFixed(1)}%`}
                    </strong>
                </div>
            </section>

            <section className="project-center-panel">
                <div className="project-toolbar">
                    <div>
                        <span className="eyebrow">
                            PROJECT WORKSPACE
                        </span>

                        <h2>
                            Your build queue
                        </h2>
                    </div>

                    <input
                        className="project-search"
                        type="search"
                        value={search}
                        onChange={(event) =>
                            setSearch(
                                event.target.value,
                            )
                        }
                        placeholder="Search projects..."
                    />
                </div>

                <div className="project-filters">
                    {[
                        ["all", "All"],
                        [
                            "in_progress",
                            "In progress",
                        ],
                        ["graded", "Graded"],
                    ].map(
                        ([value, label]) => (
                            <button
                                key={value}
                                type="button"
                                className={
                                    filter ===
                                    value
                                        ? "project-filter active"
                                        : "project-filter"
                                }
                                onClick={() =>
                                    setFilter(
                                        value as
                                            | "all"
                                            | "in_progress"
                                            | "graded",
                                    )
                                }
                            >
                                {label}
                            </button>
                        ),
                    )}
                </div>
            </section>

            {pending && (
                <div className="status-card">
                    Loading project catalog...
                </div>
            )}

            {error && (
                <div className="status-card error">
                    Unable to load projects.
                </div>
            )}

            {!pending &&
                !error &&
                filteredProjects.length ===
                    0 && (
                    <div className="status-card">
                        No projects match your
                        current filter.
                    </div>
                )}

            <div className="project-grid">
                {filteredProjects.map(
                    (project) => (
                        <article
                            className="project-card"
                            key={`${project.courseSlug}-${project.activityId}`}
                        >
                            <div className="project-card-top">
                                <span className="project-type">
                                    {activityTypeLabel(
                                        project.activityType,
                                    )}
                                </span>

                                <span
                                    className={`project-status project-status-${project.status}`}
                                >
                                    {statusLabel(
                                        project.status,
                                    )}
                                </span>
                            </div>

                            <span className="project-course">
                                {project.courseTitle}
                            </span>

                            <h2>
                                {project.activityTitle}
                            </h2>

                            <p>
                                {project.instructions}
                            </p>

                            <div className="project-meta">
                                <span>
                                    {
                                        project.moduleTitle
                                    }
                                </span>

                                <span>
                                    {
                                        project.lessonTitle
                                    }
                                </span>

                                <span>
                                    Max{" "}
                                    {project.maxScore}
                                </span>
                            </div>

                            {project.latestSubmission && (
                                <div className="project-submission-mini">
                                    <span>
                                        Latest submission
                                    </span>

                                    <strong>
                                        {project
                                            .latestSubmission
                                            .score ===
                                        null
                                            ? "Awaiting review"
                                            : `${
                                                  project
                                                      .latestSubmission
                                                      .score
                                              } / ${
                                                  project.maxScore
                                              }`}
                                    </strong>

                                    <small>
                                        {formatDate(
                                            project
                                                .latestSubmission
                                                .submitted_at,
                                        )}
                                    </small>
                                </div>
                            )}

                            <Link
                                className="primary-button project-open-button"
                                to={`/projects/${project.courseSlug}/${project.activityId}`}
                            >
                                View project
                            </Link>
                        </article>
                    ),
                )}
            </div>
        </div>
    );
}

function ProjectDetail({
    project,
    token,
}: {
    project: Project | undefined;
    token: string;
}) {
    const progressQuery =
        useQuery({
            queryKey: [
                "project-course-progress",
                token,
                project?.courseSlug,
            ],
            queryFn: () =>
                getCourseProgress(
                    project!.courseSlug,
                    token,
                ),
            enabled: Boolean(
                token &&
                    project?.courseSlug,
            ),
        });

    if (!project) {
        return (
            <div className="page centered-page">
                <div className="empty-panel">
                    <span className="eyebrow">
                        PROJECT NOT FOUND
                    </span>

                    <h1>
                        Project unavailable.
                    </h1>

                    <p>
                        This project is not
                        available to your account.
                    </p>

                    <Link
                        className="primary-button"
                        to="/projects"
                    >
                        Back to projects
                    </Link>
                </div>
            </div>
        );
    }

    const submission =
        project.latestSubmission;

    const scorePercentage =
        submission?.score !== null &&
        submission?.score !== undefined
            ? (submission.score /
                  Math.max(
                      project.maxScore,
                      1,
                  )) *
              100
            : null;

    const courseProgress =
        progressQuery.data?.progress
            .overall_percentage ?? 0;

    return (
        <div className="page">
            <Link
                className="th-back-link"
                to="/projects"
            >
                ← Back to projects
            </Link>

            <section className="project-detail-hero">
                <div>
                    <div className="project-detail-badges">
                        <span className="project-type">
                            {activityTypeLabel(
                                project.activityType,
                            )}
                        </span>

                        <span
                            className={`project-status project-status-${project.status}`}
                        >
                            {statusLabel(
                                project.status,
                            )}
                        </span>

                        {project.required && (
                            <span className="th-required-badge">
                                Required
                            </span>
                        )}
                    </div>

                    <span className="eyebrow">
                        {project.courseTitle}
                    </span>

                    <h1>
                        {project.activityTitle}
                    </h1>

                    <p>
                        {project.instructions}
                    </p>
                </div>

                <div className="project-score-card">
                    <span>Maximum score</span>

                    <strong>
                        {project.maxScore}
                    </strong>

                    <small>
                        {project.lessonTitle}
                    </small>
                </div>
            </section>

            <section className="project-detail-grid">
                <div className="project-detail-main">
                    <div className="project-detail-panel">
                        <span className="eyebrow">
                            PROJECT STATUS
                        </span>

                        <h2>
                            {submission
                                ? "Your latest work"
                                : "Ready to build"}
                        </h2>

                        {!submission && (
                            <p>
                                You have not submitted
                                this project yet.
                            </p>
                        )}

                        {submission && (
                            <>
                                <div className="project-result-row">
                                    <div>
                                        <span>
                                            Status
                                        </span>

                                        <strong>
                                            {statusLabel(
                                                project.status,
                                            )}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>
                                            Score
                                        </span>

                                        <strong>
                                            {submission.score ===
                                            null
                                                ? "Pending"
                                                : `${submission.score} / ${project.maxScore}`}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>
                                            Submitted
                                        </span>

                                        <strong>
                                            {formatDate(
                                                submission.submitted_at,
                                            )}
                                        </strong>
                                    </div>
                                </div>

                                {scorePercentage !==
                                    null && (
                                    <div className="project-progress-block">
                                        <div>
                                            <span>
                                                Project score
                                            </span>

                                            <strong>
                                                {scorePercentage.toFixed(
                                                    0,
                                                )}
                                                %
                                            </strong>
                                        </div>

                                        <div className="project-progress-track">
                                            <span
                                                style={{
                                                    width: `${Math.min(
                                                        scorePercentage,
                                                        100,
                                                    )}%`,
                                                }}
                                            />
                                        </div>
                                    </div>
                                )}

                                {submission.feedback && (
                                    <div className="project-feedback">
                                        <span className="eyebrow">
                                            INSTRUCTOR FEEDBACK
                                        </span>

                                        <p>
                                            {
                                                submission.feedback
                                            }
                                        </p>
                                    </div>
                                )}
                            </>
                        )}

                        <Link
                            className="primary-button project-submit-button"
                            to={`/courses/${project.courseSlug}/lessons/${project.lessonId}/activities/${project.activityId}`}
                        >
                            {submission
                                ? "Open project workspace"
                                : "Start project"}
                        </Link>
                    </div>

                    {submission && (
                        <div className="project-detail-panel">
                            <span className="eyebrow">
                                SUBMISSION
                            </span>

                            <h2>
                                Latest submission
                            </h2>

                            {submission.github_url && (
                                <a
                                    href={
                                        submission.github_url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    Open GitHub submission
                                </a>
                            )}

                            {submission.response_text && (
                                <div className="project-submission-details">
                                    <span>
                                        Written response
                                    </span>

                                    <p>
                                        {
                                            submission.response_text
                                        }
                                    </p>
                                </div>
                            )}

                            {!submission.github_url &&
                                !submission.response_text &&
                                submission.code && (
                                    <div className="project-submission-details">
                                        <span>
                                            Code submitted
                                        </span>

                                        <p>
                                            Code has been
                                            submitted for
                                            instructor review.
                                        </p>
                                    </div>
                                )}
                        </div>
                    )}
                </div>

                <aside className="project-detail-sidebar">
                    <div className="project-detail-panel">
                        <span className="eyebrow">
                            COURSE PROGRESS
                        </span>

                        <strong className="project-course-progress-value">
                            {courseProgress.toFixed(
                                0,
                            )}
                            %
                        </strong>

                        <div className="project-progress-track">
                            <span
                                style={{
                                    width: `${Math.min(
                                        courseProgress,
                                        100,
                                    )}%`,
                                }}
                            />
                        </div>

                        <p>
                            Overall progress in{" "}
                            <strong>
                                {project.courseTitle}
                            </strong>
                            .
                        </p>

                        <Link
                            className="secondary-button"
                            to={`/courses/${project.courseSlug}`}
                        >
                            Open course
                        </Link>
                    </div>

                    <div className="project-detail-panel">
                        <span className="eyebrow">
                            PROJECT CONTEXT
                        </span>

                        <dl className="project-context">
                            <div>
                                <dt>Module</dt>
                                <dd>
                                    {
                                        project.moduleTitle
                                    }
                                </dd>
                            </div>

                            <div>
                                <dt>Lesson</dt>
                                <dd>
                                    {
                                        project.lessonTitle
                                    }
                                </dd>
                            </div>

                            <div>
                                <dt>Maximum score</dt>
                                <dd>
                                    {
                                        project.maxScore
                                    }
                                </dd>
                            </div>
                        </dl>
                    </div>
                </aside>
            </section>
        </div>
    );
}