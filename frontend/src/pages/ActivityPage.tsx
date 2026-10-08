import {
    useMemo,
    useState,
} from "react";

import type { FormEvent } from "react";

import {
    Link,
    useParams,
} from "react-router";

import {
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";

import {
    completeReadingActivity,
    createSubmission,
    getCourseDetail,
    getSubmissions,
} from "../api/client";

import { useAuth } from "../context/AuthContext";

function activityTypeLabel(value: string) {
    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) =>
            letter.toUpperCase(),
        );
}

export default function ActivityPage() {
    const {
        slug,
        lessonId,
        activityId,
    } = useParams<{
        slug: string;
        lessonId: string;
        activityId: string;
    }>();

    const { auth } = useAuth();

    const token = auth?.token ?? "";

    const queryClient =
        useQueryClient();

    const [code, setCode] =
        useState("");

    const [responseText, setResponseText] =
        useState("");

    const [githubUrl, setGithubUrl] =
        useState("");

    const courseQuery = useQuery({
        queryKey: [
            "course",
            slug,
        ],
        queryFn: () =>
            getCourseDetail(
                slug as string,
            ),
        enabled: Boolean(slug),
    });

    const submissionsQuery = useQuery({
        queryKey: [
            "submissions",
            token,
        ],
        queryFn: () =>
            getSubmissions(token),
        enabled: Boolean(token),
    });

    const submitMutation =
        useMutation({
            mutationFn: () =>
                createSubmission(
                    {
                        activity:
                            Number(
                                activityId,
                            ),
                        ...(code
                            ? {
                                  code,
                              }
                            : {}),
                        ...(responseText
                            ? {
                                  response_text:
                                      responseText,
                              }
                            : {}),
                        ...(githubUrl
                            ? {
                                  github_url:
                                      githubUrl,
                              }
                            : {}),
                    },
                    token,
                ),
            onSuccess:
                async () => {
                    await queryClient.invalidateQueries(
                        {
                            queryKey: [
                                "submissions",
                                token,
                            ],
                        },
                    );

                    await queryClient.invalidateQueries(
                        {
                            queryKey: [
                                "course-progress",
                                slug,
                            ],
                        },
                    );

                    setCode("");
                    setResponseText("");
                    setGithubUrl("");
                },
        });

    const readingCompletionMutation =
        useMutation({
            mutationFn: () =>
                completeReadingActivity(
                    Number(activityId),
                    token,
                ),
            onSuccess:
                async () => {
                    await queryClient.invalidateQueries(
                        {
                            queryKey: [
                                "course-progress",
                                slug,
                            ],
                        },
                    );
                },
        });

    const activity =
        (() => {
            const course =
                courseQuery.data;

            if (!course) {
                return undefined;
            }

            for (
                const module of
                    course.modules
            ) {
                for (
                    const lesson of
                        module.lessons
                ) {
                    if (
                        String(
                            lesson.id,
                        ) !==
                        String(
                            lessonId,
                        )
                    ) {
                        continue;
                    }

                    const foundActivity =
                        lesson.activities.find(
                            (item) =>
                                String(
                                    item.id,
                                ) ===
                                String(
                                    activityId,
                                ),
                        );

                    if (
                        foundActivity
                    ) {
                        return {
                            module,
                            lesson,
                            activity:
                                foundActivity,
                        };
                    }
                }
            }

            return undefined;
        })();

    const latestSubmission =
        useMemo(() => {
            return (
                submissionsQuery.data?.results
                    .filter(
                        (submission) =>
                            submission.activity.id ===
                            Number(
                                activityId,
                            ),
                    )[0]
            );
        }, [
            submissionsQuery.data,
            activityId,
        ]);

    if (courseQuery.isPending) {
        return (
            <main className="th-course-page">
                <div className="th-course-loading">
                    Loading activity...
                </div>
            </main>
        );
    }

    if (
        courseQuery.isError ||
        !courseQuery.data ||
        !activity ||
        !activity.activity
    ) {
        return (
            <main className="th-course-page">
                <section className="th-course-error">
                    <span className="th-eyebrow">
                        ACTIVITY ERROR
                    </span>

                    <h1>
                        Activity unavailable.
                    </h1>

                    <p>
                        We could not find this
                        learning activity.
                    </p>

                    <Link
                        className="th-primary-button"
                        to={`/courses/${slug}`}
                    >
                        Back to course
                    </Link>
                </section>
            </main>
        );
    }

    const currentActivity =
        activity.activity;

    const isReading =
        currentActivity.activity_type ===
        "reading";

    const isCoding =
        currentActivity.activity_type ===
        "coding";

    const isSubmissionActivity =
        [
            "coding",
            "assignment",
            "lab",
        ].includes(
            currentActivity.activity_type,
        );

    function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        submitMutation.mutate();
    }

    if (isReading) {
        return (
            <main className="th-course-page">
                <div className="th-activity-page">
                    <Link
                        className="th-back-link"
                        to={`/courses/${slug}`}
                    >
                        ← Back to course
                    </Link>

                    <section className="th-activity-hero">
                        <div>
                            <div className="th-detail-badges">
                                <span className="th-activity-type">
                                    Reading
                                </span>

                                {currentActivity.is_required && (
                                    <span className="th-required-badge">
                                        Required
                                    </span>
                                )}
                            </div>

                            <span className="th-eyebrow">
                                LEARN /{" "}
                                {activity.module.title}
                            </span>

                            <h1>
                                {
                                    currentActivity.title
                                }
                            </h1>

                            <p>
                                {
                                    currentActivity.instructions ||
                                    "Read the material carefully, then mark this activity complete."
                                }
                            </p>
                        </div>

                        <div className="th-activity-score-card">
                            <span>
                                Activity
                            </span>

                            <strong>
                                {currentActivity.order}
                            </strong>

                            <small>
                                Reading checkpoint
                            </small>
                        </div>
                    </section>

                    <section className="th-reading-complete-panel">
                        <div>
                            <span className="th-eyebrow">
                                READING CHECKPOINT
                            </span>

                            <h2>
                                Finished this reading?
                            </h2>

                            <p>
                                Mark it complete to update
                                your Tech Haven learning
                                progress.
                            </p>
                        </div>

                        {readingCompletionMutation.isSuccess ? (
                            <div className="th-reading-complete-success">
                                <strong>
                                    ✓ Completed
                                </strong>

                                <span>
                                    Progress updated
                                    successfully.
                                </span>
                            </div>
                        ) : (
                            <button
                                className="th-primary-button"
                                type="button"
                                disabled={
                                    readingCompletionMutation.isPending
                                }
                                onClick={() =>
                                    readingCompletionMutation.mutate()
                                }
                            >
                                {readingCompletionMutation.isPending
                                    ? "Saving..."
                                    : "Mark as complete"}
                            </button>
                        )}

                        {readingCompletionMutation.isError && (
                            <div className="th-form-error">
                                {readingCompletionMutation.error instanceof Error
                                    ? readingCompletionMutation.error.message
                                    : "Unable to complete this reading activity."}
                            </div>
                        )}
                    </section>
                </div>
            </main>
        );
    }

    if (!isSubmissionActivity) {
        return (
            <main className="th-course-page">
                <section className="th-course-error">
                    <span className="th-eyebrow">
                        ACTIVITY TYPE
                    </span>

                    <h1>
                        {
                            currentActivity.title
                        }
                    </h1>

                    <p>
                        This activity type
                        uses a dedicated
                        experience.
                    </p>

                    <Link
                        className="th-primary-button"
                        to={`/courses/${slug}`}
                    >
                        Back to course
                    </Link>
                </section>
            </main>
        );
    }

    return (
        <main className="th-course-page">
            <div className="th-activity-page">
                <Link
                    className="th-back-link"
                    to={`/courses/${slug}`}
                >
                    ← Back to course
                </Link>

                <section className="th-activity-hero">
                    <div>
                        <div className="th-detail-badges">
                            <span className="th-activity-type">
                                {activityTypeLabel(
                                    currentActivity.activity_type,
                                )}
                            </span>

                            {currentActivity.is_required && (
                                <span className="th-required-badge">
                                    Required
                                </span>
                            )}
                        </div>

                        <span className="th-eyebrow">
                            PRACTICE /{" "}
                            {activity.module.title}
                        </span>

                        <h1>
                            {
                                currentActivity.title
                            }
                        </h1>

                        <p>
                            {
                                currentActivity.instructions
                            }
                        </p>
                    </div>

                    <div className="th-activity-score-card">
                        <span>
                            Maximum score
                        </span>

                        <strong>
                            {
                                currentActivity.max_score
                            }
                        </strong>

                        <small>
                            Activity{" "}
                            {currentActivity.order}
                        </small>
                    </div>
                </section>

                {latestSubmission && (
                    <section className="th-submission-status">
                        <div>
                            <span className="th-eyebrow">
                                LATEST SUBMISSION
                            </span>

                            <strong>
                                {
                                    latestSubmission.status
                                }
                            </strong>
                        </div>

                        <div>
                            <span>
                                Score
                            </span>

                            <strong>
                                {latestSubmission.score ??
                                    "Pending"}
                            </strong>
                        </div>

                        {latestSubmission.feedback && (
                            <p>
                                {
                                    latestSubmission.feedback
                                }
                            </p>
                        )}
                    </section>
                )}

                <form
                    className="th-activity-form"
                    onSubmit={
                        handleSubmit
                    }
                >
                    {isCoding && (
                        <label>
                            <span>
                                Python code
                            </span>

                            <textarea
                                className="th-code-editor"
                                value={code}
                                onChange={(
                                    event,
                                ) =>
                                    setCode(
                                        event
                                            .target
                                            .value,
                                    )
                                }
                                placeholder="Write your Python solution here..."
                                rows={16}
                            />
                        </label>
                    )}

                    {!isCoding && (
                        <label>
                            <span>
                                Your response
                            </span>

                            <textarea
                                value={
                                    responseText
                                }
                                onChange={(
                                    event,
                                ) =>
                                    setResponseText(
                                        event
                                            .target
                                            .value,
                                    )
                                }
                                placeholder="Write your response here..."
                                rows={12}
                            />
                        </label>
                    )}

                    <label>
                        <span>
                            GitHub URL{" "}
                            <small>
                                optional
                            </small>
                        </span>

                        <input
                            type="url"
                            value={
                                githubUrl
                            }
                            onChange={(
                                event,
                            ) =>
                                setGithubUrl(
                                    event
                                        .target
                                        .value,
                                )
                            }
                            placeholder="https://github.com/username/project"
                        />
                    </label>

                    <div className="th-form-actions">
                        <Link
                            className="th-secondary-button"
                            to={`/courses/${slug}`}
                        >
                            Save and return
                        </Link>

                        <button
                            className="th-primary-button"
                            type="submit"
                            disabled={
                                submitMutation.isPending
                            }
                        >
                            {submitMutation.isPending
                                ? "Submitting..."
                                : "Submit for assessment"}
                        </button>
                    </div>

                    {submitMutation.isError && (
                        <div className="th-form-error">
                            {submitMutation.error instanceof Error
                                ? submitMutation.error.message
                                : "Submission failed. Please try again."}
                        </div>
                    )}

                    {submitMutation.isSuccess && (
                        <div className="th-form-success">
                            Submission sent successfully.
                            Your instructor can now review
                            your work.
                        </div>
                    )}
                </form>
            </div>
        </main>
    );
}
