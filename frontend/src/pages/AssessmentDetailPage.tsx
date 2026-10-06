import { useQuery } from "@tanstack/react-query";
import {
    Link,
    useParams,
} from "react-router";
import {
    getQuizAttemptDetail,
    getSubmissionDetail,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import type {
    QuizAttempt,
    Submission,
} from "../types/api";

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function SubmissionDetail({
    submission,
}: {
    submission: Submission;
}) {
    const percentage =
        submission.score === null ||
        submission.activity.max_score <= 0
            ? null
            : (submission.score /
                  submission.activity.max_score) *
              100;

    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        PRACTICAL ASSESSMENT
                    </span>

                    <h1>
                        {submission.activity.title}
                    </h1>

                    <p>
                        {submission.course.title}
                    </p>
                </div>

                <Link
                    to="/assessments"
                    className="text-link"
                >
                    Back to assessments
                </Link>
            </section>

            <section className="dashboard-stats">
                <article>
                    <span>Status</span>
                    <strong>
                        {submission.score === null
                            ? "Pending"
                            : "Graded"}
                    </strong>
                    <small>
                        {submission.status}
                    </small>
                </article>

                <article>
                    <span>Score</span>
                    <strong>
                        {submission.score === null
                            ? "-"
                            : `${submission.score}/${submission.activity.max_score}`}
                    </strong>
                    <small>
                        {percentage === null
                            ? "Awaiting assessment"
                            : `${percentage.toFixed(1)}%`}
                    </small>
                </article>

                <article>
                    <span>Submitted</span>
                    <strong>
                        {formatDate(
                            submission.submitted_at,
                        )}
                    </strong>
                </article>
            </section>

            <section className="dashboard-grid">
                <div className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                INSTRUCTOR FEEDBACK
                            </span>

                            <h2>
                                Assessment review
                            </h2>
                        </div>
                    </div>

                    <div className="status-card">
                        {submission.feedback ? (
                            <p>
                                {submission.feedback}
                            </p>
                        ) : (
                            <p>
                                No instructor feedback has
                                been added yet.
                            </p>
                        )}
                    </div>
                </div>

                <aside className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                ACTIVITY
                            </span>

                            <h2>
                                Assessment details
                            </h2>
                        </div>
                    </div>

                    <div className="assessment-options">
                        <article>
                            <span className="feature-number">
                                TYPE
                            </span>

                            <h3>
                                {
                                    submission.activity
                                        .activity_type
                                }
                            </h3>

                            <p>
                                Maximum score:{" "}
                                {submission.activity.max_score}
                            </p>
                        </article>

                        <article>
                            <span className="feature-number">
                                DATE
                            </span>

                            <h3>
                                {formatDate(
                                    submission.submitted_at,
                                )}
                            </h3>

                            <p>
                                Submission timestamp
                            </p>
                        </article>
                    </div>
                </aside>
            </section>

            {submission.response_text && (
                <section className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                RESPONSE
                            </span>

                            <h2>
                                Submitted response
                            </h2>
                        </div>
                    </div>

                    <div className="status-card">
                        <p>
                            {submission.response_text}
                        </p>
                    </div>
                </section>
            )}

            {submission.code && (
                <section className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                CODE
                            </span>

                            <h2>
                                Submitted code
                            </h2>
                        </div>
                    </div>

                    <pre className="assessment-code">
                        {submission.code}
                    </pre>
                </section>
            )}

            {(submission.github_url ||
                submission.attachment_url) && (
                <section className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                EVIDENCE
                            </span>

                            <h2>
                                Submission evidence
                            </h2>
                        </div>
                    </div>

                    <div className="assessment-options">
                        {submission.github_url && (
                            <article>
                                <span className="feature-number">
                                    01
                                </span>

                                <h3>
                                    GitHub repository
                                </h3>

                                <a
                                    href={
                                        submission.github_url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-link"
                                >
                                    Open repository
                                </a>
                            </article>
                        )}

                        {submission.attachment_url && (
                            <article>
                                <span className="feature-number">
                                    02
                                </span>

                                <h3>
                                    Attachment
                                </h3>

                                <a
                                    href={
                                        submission.attachment_url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-link"
                                >
                                    Open attachment
                                </a>
                            </article>
                        )}
                    </div>
                </section>
            )}
        </div>
    );
}

function QuizAttemptDetail({
    attempt,
}: {
    attempt: QuizAttempt;
}) {
    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        QUIZ ATTEMPT
                    </span>

                    <h1>
                        {attempt.quiz.title}
                    </h1>

                    <p>
                        {attempt.quiz.course.title}
                        {" · "}
                        {attempt.quiz.lesson.title}
                    </p>
                </div>

                <Link
                    to="/assessments"
                    className="text-link"
                >
                    Back to assessments
                </Link>
            </section>

            <section className="dashboard-stats">
                <article>
                    <span>Result</span>
                    <strong>
                        {attempt.passed
                            ? "Passed"
                            : "Not passed"}
                    </strong>
                    <small>
                        Passing score:{" "}
                        {attempt.quiz.passing_score}%
                    </small>
                </article>

                <article>
                    <span>Score</span>
                    <strong>
                        {attempt.score}/
                        {attempt.total_points}
                    </strong>
                    <small>
                        {attempt.percentage.toFixed(1)}%
                    </small>
                </article>

                <article>
                    <span>Completed</span>
                    <strong>
                        {attempt.completed_at
                            ? formatDate(
                                  attempt.completed_at,
                              )
                            : "In progress"}
                    </strong>
                </article>
            </section>

            <section className="dashboard-panel">
                <div className="panel-heading">
                    <div>
                        <span className="eyebrow">
                            QUESTION REVIEW
                        </span>

                        <h2>
                            Your answers
                        </h2>
                    </div>

                    <Link
                        to={`/courses/${attempt.quiz.course.slug}/quiz/${attempt.quiz.activity_id}`}
                        className="text-link"
                    >
                        Retake quiz
                    </Link>
                </div>

                <div className="assessment-list">
                    {attempt.answers.map(
                        (answer, index) => (
                            <article
                                key={answer.id}
                                className="assessment-card"
                            >
                                <div>
                                    <span className="course-level">
                                        Question {index + 1}
                                        {" · "}
                                        {answer.is_correct
                                            ? "Correct"
                                            : "Needs review"}
                                    </span>

                                    <h3>
                                        {
                                            answer.question
                                                .question_text
                                        }
                                    </h3>

                                    <p>
                                        Your answer:{" "}
                                        {answer
                                            .selected_choice
                                            ?.choice_text ??
                                            "No answer selected"}
                                    </p>
                                </div>

                                <div className="assessment-card-meta">
                                    <strong>
                                        {answer.points_awarded}/
                                        {
                                            answer.question
                                                .points
                                        }
                                    </strong>

                                    <small>
                                        {answer.is_correct
                                            ? "Correct answer"
                                            : "Review this question"}
                                    </small>
                                </div>
                            </article>
                        ),
                    )}
                </div>
            </section>
        </div>
    );
}

export default function AssessmentDetailPage() {
    const {
        submissionId,
        attemptId,
    } = useParams<{
        submissionId?: string;
        attemptId?: string;
    }>();

    const { auth } = useAuth();
    const token = auth?.token ?? "";

    const submissionQuery = useQuery({
        queryKey: [
            "assessment-submission-detail",
            submissionId,
            token,
        ],
        queryFn: () =>
            getSubmissionDetail(
                Number(submissionId),
                token,
            ),
        enabled:
            Boolean(token) &&
            Boolean(submissionId),
    });

    const attemptQuery = useQuery({
        queryKey: [
            "assessment-quiz-attempt-detail",
            attemptId,
            token,
        ],
        queryFn: () =>
            getQuizAttemptDetail(
                Number(attemptId),
                token,
            ),
        enabled:
            Boolean(token) &&
            Boolean(attemptId),
    });

    if (
        submissionId &&
        submissionQuery.isPending
    ) {
        return (
            <div className="page">
                <div className="status-card">
                    Loading assessment details...
                </div>
            </div>
        );
    }

    if (
        attemptId &&
        attemptQuery.isPending
    ) {
        return (
            <div className="page">
                <div className="status-card">
                    Loading quiz attempt...
                </div>
            </div>
        );
    }

    if (
        submissionId &&
        submissionQuery.isError
    ) {
        return (
            <div className="page">
                <div className="status-card error">
                    Unable to load this submission.
                    <br />
                    <Link
                        to="/assessments"
                        className="text-link"
                    >
                        Back to assessments
                    </Link>
                </div>
            </div>
        );
    }

    if (
        attemptId &&
        attemptQuery.isError
    ) {
        return (
            <div className="page">
                <div className="status-card error">
                    Unable to load this quiz attempt.
                    <br />
                    <Link
                        to="/assessments"
                        className="text-link"
                    >
                        Back to assessments
                    </Link>
                </div>
            </div>
        );
    }

    if (
        submissionId &&
        submissionQuery.data
    ) {
        return (
            <SubmissionDetail
                submission={
                    submissionQuery.data
                }
            />
        );
    }

    if (
        attemptId &&
        attemptQuery.data
    ) {
        return (
            <QuizAttemptDetail
                attempt={attemptQuery.data}
            />
        );
    }

    return (
        <div className="page">
            <div className="status-card error">
                Assessment was not specified.
                <br />
                <Link
                    to="/assessments"
                    className="text-link"
                >
                    Back to assessments
                </Link>
            </div>
        </div>
    );
}