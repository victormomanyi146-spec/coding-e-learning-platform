import {
    useMemo,
    useState,
} from "react";

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
    getQuiz,
    submitQuizAttempt,
} from "../api/client";

import { useAuth } from "../context/AuthContext";

export default function QuizPage() {
    const {
        slug,
        activityId,
    } = useParams<{
        slug: string;
        activityId: string;
    }>();

    const { auth } = useAuth();

    const token = auth?.token ?? "";

    const queryClient =
        useQueryClient();

    const [answers, setAnswers] =
        useState<
            Record<string, number>
        >({});

    const quizQuery = useQuery({
        queryKey: [
            "quiz",
            activityId,
            token,
        ],
        queryFn: () =>
            getQuiz(
                Number(activityId),
                token,
            ),
        enabled: Boolean(
            activityId &&
            token,
        ),
    });

    const submitMutation =
        useMutation({
            mutationFn: () =>
                submitQuizAttempt(
                    Number(activityId),
                    answers,
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

    const answeredCount =
        useMemo(
            () =>
                Object.keys(
                    answers,
                ).length,
            [answers],
        );

    if (quizQuery.isPending) {
        return (
            <main className="th-course-page">
                <div className="th-course-loading">
                    Loading quiz...
                </div>
            </main>
        );
    }

    if (
        quizQuery.isError ||
        !quizQuery.data
    ) {
        return (
            <main className="th-course-page">
                <section className="th-course-error">
                    <span className="th-eyebrow">
                        QUIZ ERROR
                    </span>

                    <h1>
                        Quiz unavailable.
                    </h1>

                    <p>
                        {quizQuery.error instanceof Error
                            ? quizQuery.error.message
                            : "We could not load this quiz."}
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

    const quiz =
        quizQuery.data;

    if (
        submitMutation.isSuccess
    ) {
        const result =
            submitMutation.data.result;

        return (
            <main className="th-course-page">
                <section className="th-quiz-result">
                    <span className="th-eyebrow">
                        QUIZ COMPLETE
                    </span>

                    <h1>
                        {
                            quiz.activity
                                .title
                        }
                    </h1>

                    <div className="th-quiz-result-score">
                        <strong>
                            {
                                result.percentage
                            }%
                        </strong>

                        <span>
                            {
                                result.passed
                                    ? "Passed"
                                    : "Not passed"
                            }
                        </span>
                    </div>

                    <p>
                        You earned{" "}
                        {
                            result.earned_points
                        }{" "}
                        of{" "}
                        {
                            result.total_points
                        }{" "}
                        points. Passing score:{" "}
                        {
                            result.passing_score
                        }%.
                    </p>

                    <div className="th-form-actions">
                        <button
                            className="th-secondary-button"
                            type="button"
                            onClick={() =>
                                submitMutation.reset()
                            }
                        >
                            Review answers
                        </button>

                        <Link
                            className="th-primary-button"
                            to={`/courses/${slug}`}
                        >
                            Return to course
                        </Link>
                    </div>
                </section>
            </main>
        );
    }

    return (
        <main className="th-course-page">
            <div className="th-quiz-page">
                <Link
                    className="th-back-link"
                    to={`/courses/${slug}`}
                >
                    ← Back to course
                </Link>

                <section className="th-quiz-header">
                    <span className="th-eyebrow">
                        ASSESS / QUIZ
                    </span>

                    <h1>
                        {
                            quiz.activity
                                .title
                        }
                    </h1>

                    <p>
                        {
                            quiz.activity
                                .instructions
                        }
                    </p>

                    <div className="th-quiz-progress">
                        {answeredCount}/
                        {
                            quiz.questions
                                .length
                        }{" "}
                        questions answered
                    </div>
                </section>

                <form
                    className="th-quiz-form"
                    onSubmit={(
                        event,
                    ) => {
                        event.preventDefault();

                        submitMutation.mutate();
                    }}
                >
                    {quiz.questions.map(
                        (
                            question,
                            index,
                        ) => (
                            <fieldset
                                className="th-question-card"
                                key={
                                    question.id
                                }
                            >
                                <legend>
                                    <span>
                                        Question{" "}
                                        {
                                            index +
                                            1
                                        }
                                    </span>

                                    {
                                        question.points
                                    }{" "}
                                    point
                                    {question.points ===
                                    1
                                        ? ""
                                        : "s"}
                                </legend>

                                <h2>
                                    {
                                        question.question_text
                                    }
                                </h2>

                                <div className="th-choice-list">
                                    {question.choices.map(
                                        (
                                            choice,
                                        ) => (
                                            <label
                                                className="th-choice"
                                                key={
                                                    choice.id
                                                }
                                            >
                                                <input
                                                    type="radio"
                                                    name={`question-${question.id}`}
                                                    checked={
                                                        answers[
                                                            String(
                                                                question.id,
                                                            )
                                                        ] ===
                                                        choice.id
                                                    }
                                                    onChange={() =>
                                                        setAnswers(
                                                            (
                                                                current,
                                                            ) => ({
                                                                ...current,
                                                                [String(
                                                                    question.id,
                                                                )]:
                                                                    choice.id,
                                                            }),
                                                        )
                                                    }
                                                />

                                                <span>
                                                    {
                                                        choice.choice_text
                                                    }
                                                </span>
                                            </label>
                                        ),
                                    )}
                                </div>
                            </fieldset>
                        ),
                    )}

                    {submitMutation.isError && (
                        <div className="th-form-error">
                            {submitMutation.error instanceof Error
                                ? submitMutation.error.message
                                : "Quiz submission failed."}
                        </div>
                    )}

                    <div className="th-form-actions">
                        <Link
                            className="th-secondary-button"
                            to={`/courses/${slug}`}
                        >
                            Exit quiz
                        </Link>

                        <button
                            className="th-primary-button"
                            type="submit"
                            disabled={
                                submitMutation.isPending ||
                                answeredCount === 0
                            }
                        >
                            {submitMutation.isPending
                                ? "Submitting..."
                                : "Submit quiz"}
                        </button>
                    </div>
                </form>
            </div>
        </main>
    );
}
