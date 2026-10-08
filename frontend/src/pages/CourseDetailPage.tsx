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
    enrollInCourse,
    getCourseDetail,
    getCourseProgress,
} from "../api/client";

import { useAuth } from "../context/AuthContext";

import type {
    Lesson,
    ProgressModule,
} from "../types/api";

function formatActivityType(activityType: string) {
    return activityType
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) =>
            letter.toUpperCase(),
        );
}

function LessonStatus({
    lesson,
    progressModule,
    unlocked,
}: {
    lesson: Lesson;
    progressModule: ProgressModule | undefined;
    unlocked: boolean;
}) {
    const progressLesson =
        progressModule?.lessons.find(
            (item) => item.id === lesson.id,
        );

    const completed =
        Boolean(progressLesson?.is_completed);

    return (
        <span
            className={
                completed
                    ? "th-lesson-status is-complete"
                    : unlocked
                      ? "th-lesson-status"
                      : "th-lesson-status is-locked"
            }
            aria-hidden="true"
        >
            {completed
                ? "✓"
                : unlocked
                  ? lesson.order
                  : "🔒"}
        </span>
    );
}

export default function CourseDetailPage() {
    const { slug } = useParams<{ slug: string }>();

    const { auth } = useAuth();
    const user = auth?.user;
    const token = auth?.token;

    const queryClient = useQueryClient();

    const [
        selectedLessonId,
        setSelectedLessonId,
    ] = useState<number | null>(null);

    const courseQuery = useQuery({
        queryKey: ["course", slug],
        queryFn: () =>
            getCourseDetail(slug as string),
        enabled: Boolean(slug),
    });

    const progressQuery = useQuery({
        queryKey: ["course-progress", slug],
        queryFn: () =>
            getCourseProgress(
                slug as string,
                token as string,
            ),
        enabled: Boolean(slug && token),
        retry: false,
    });

    const enrollmentMutation = useMutation({
        mutationFn: () =>
            enrollInCourse(
                slug as string,
                token as string,
            ),
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: [
                    "course-progress",
                    slug,
                ],
            });
        },
    });

    const lessons = useMemo(
        () =>
            courseQuery.data?.modules.flatMap(
                (module) => module.lessons,
            ) ?? [],
        [courseQuery.data],
    );

    const progressByModule = useMemo(() => {
        const map =
            new Map<number, ProgressModule>();

        for (
            const module of
                progressQuery.data?.modules ?? []
        ) {
            map.set(
                module.id,
                module,
            );
        }

        return map;
    }, [progressQuery.data]);

    const isEnrolled =
        Boolean(
            progressQuery.data
                ?.is_enrolled,
        );

    const lessonStates = useMemo(() => {
        const states = new Map<
            number,
            {
                completed: boolean;
                unlocked: boolean;
                lockReason: string;
            }
        >();

        if (!courseQuery.data) {
            return states;
        }

        courseQuery.data.modules.forEach(
            (module, moduleIndex) => {
                const moduleProgress =
                    progressByModule.get(
                        module.id,
                    );

                module.lessons.forEach(
                    (lesson, lessonIndex) => {
                        const progressLesson =
                            moduleProgress?.lessons.find(
                                (item) =>
                                    item.id ===
                                    lesson.id,
                            );

                        const completed =
                            Boolean(
                                progressLesson?.is_completed,
                            );

                        let unlocked = true;
                        let lockReason = "";

                        if (isEnrolled) {
                            if (
                                lessonIndex > 0
                            ) {
                                const previousLesson =
                                    module.lessons[
                                        lessonIndex - 1
                                    ];

                                const previousState =
                                    states.get(
                                        previousLesson.id,
                                    );

                                unlocked =
                                    Boolean(
                                        previousState?.completed,
                                    );

                                if (!unlocked) {
                                    lockReason =
                                        "Complete the previous lesson first.";
                                }
                            } else if (
                                moduleIndex > 0
                            ) {
                                const previousModule =
                                    courseQuery
                                        .data
                                        .modules[
                                        moduleIndex - 1
                                    ];

                                const previousProgress =
                                    progressByModule.get(
                                        previousModule.id,
                                    );

                                unlocked =
                                    Boolean(
                                        previousProgress &&
                                            previousProgress.lessons_total >
                                                0 &&
                                            previousProgress.lessons_completed ===
                                                previousProgress.lessons_total,
                                    );

                                if (!unlocked) {
                                    lockReason =
                                        "Complete the previous module first.";
                                }
                            }
                        }

                        states.set(
                            lesson.id,
                            {
                                completed,
                                unlocked,
                                lockReason,
                            },
                        );
                    },
                );
            },
        );

        return states;
    }, [
        courseQuery.data,
        progressByModule,
        isEnrolled,
    ]);

    const recommendedLesson =
        useMemo(() => {
            if (lessons.length === 0) {
                return undefined;
            }

            if (!isEnrolled) {
                return lessons[0];
            }

            return (
                lessons.find(
                    (lesson) => {
                        const state =
                            lessonStates.get(
                                lesson.id,
                            );

                        return (
                            state?.unlocked &&
                            !state.completed
                        );
                    },
                ) ??
                lessons[lessons.length - 1]
            );
        }, [
            lessons,
            isEnrolled,
            lessonStates,
        ]);

    const selectedLesson =
        lessons.find(
            (lesson) =>
                lesson.id === selectedLessonId,
        ) ??
        recommendedLesson ??
        lessons[0];

    const selectedLessonState =
        selectedLesson
            ? lessonStates.get(
                  selectedLesson.id,
              )
            : undefined;

    const recommendedRequiredActivities =
        recommendedLesson
            ? recommendedLesson.activities.filter(
                  (activity) =>
                      activity.is_required,
              ).length
            : 0;

    const selectedLessonIndex =
        selectedLesson
            ? lessons.findIndex(
                  (lesson) =>
                      lesson.id ===
                      selectedLesson.id,
              )
            : -1;

    const previousLesson =
        selectedLessonIndex > 0
            ? lessons[
                  selectedLessonIndex - 1
              ]
            : undefined;

    const nextLesson =
        selectedLessonIndex >= 0 &&
        selectedLessonIndex <
            lessons.length - 1
            ? lessons[
                  selectedLessonIndex + 1
              ]
            : undefined;

    if (courseQuery.isPending) {
        return (
            <main className="th-course-page">
                <div className="th-course-loading">
                    Loading your learning path...
                </div>
            </main>
        );
    }

    if (
        courseQuery.isError ||
        !courseQuery.data
    ) {
        return (
            <main className="th-course-page">
                <section className="th-course-error">
                    <span className="th-eyebrow">
                        COURSE ERROR
                    </span>

                    <h1>
                        Course unavailable.
                    </h1>

                    <p>
                        {courseQuery.error instanceof Error
                            ? courseQuery.error.message
                            : "We could not load this course."}
                    </p>

                    <Link
                        className="th-primary-button"
                        to="/courses"
                    >
                        Back to courses
                    </Link>
                </section>
            </main>
        );
    }

    const course =
        courseQuery.data;

    const progress =
        progressQuery.data?.progress;


    return (
        <main className="th-course-page">
            <section className="th-detail-hero">
                <div className="th-detail-hero-copy">
                    <Link
                        className="th-back-link"
                        to="/courses"
                    >
                        ← Course catalog
                    </Link>

                    <div className="th-detail-badges">
                        <span className="th-course-badge">
                            {course.level}
                        </span>

                        <span className="th-course-duration">
                            {course.duration}
                        </span>
                    </div>

                    <span className="th-eyebrow">
                        TECH HAVEN /{" "}
                        {course.title}
                    </span>

                    <h1>
                        {course.title}
                    </h1>

                    <p>
                        {course.description}
                    </p>

                    <div className="th-detail-meta">
                        <span>
                            Instructor
                            <strong>
                                {course.instructor}
                            </strong>
                        </span>

                        <span>
                            Modules
                            <strong>
                                {
                                    course
                                        .modules
                                        .length
                                }
                            </strong>
                        </span>

                        <span>
                            Lessons
                            <strong>
                                {
                                    lessons.length
                                }
                            </strong>
                        </span>
                    </div>
                </div>

                <div className="th-progress-panel">
                    <div className="th-progress-panel-heading">
                        <div>
                            <span className="th-eyebrow">
                                YOUR PROGRESS
                            </span>

                            <strong>
                                {isEnrolled
                                    ? `${
                                          progress
                                              ?.overall_percentage ??
                                          0
                                      }%`
                                    : "Not started"}
                            </strong>
                        </div>

                        {isEnrolled &&
                            progress && (
                                <span>
                                    {
                                        progress.lessons_completed
                                    }
                                    /
                                    {
                                        progress.lessons_total
                                    }{" "}
                                    lessons
                                </span>
                            )}
                    </div>

                    <div
                        className="th-progress-track"
                        role="progressbar"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={
                            progress
                                ?.overall_percentage ??
                            0
                        }
                    >
                        <span
                            style={{
                                width: `${
                                    progress
                                        ?.overall_percentage ??
                                    0
                                }%`,
                            }}
                        />
                    </div>

                    {isEnrolled ? (
                        <p>
                            Continue through the
                            course outline to
                            increase your
                            measurable progress.
                        </p>
                    ) : user ? (
                        <button
                            className="th-primary-button th-full-button"
                            type="button"
                            disabled={
                                enrollmentMutation.isPending
                            }
                            onClick={() =>
                                enrollmentMutation.mutate()
                            }
                        >
                            {enrollmentMutation.isPending
                                ? "Enrolling..."
                                : "Enroll and start learning"}
                        </button>
                    ) : (
                        <Link
                            className="th-primary-button th-full-button"
                            to="/login"
                            state={{
                                from: `/courses/${slug}`,
                            }}
                        >
                            Sign in to start learning
                        </Link>
                    )}

                    {enrollmentMutation.isError && (
                        <p className="th-inline-error">
                            {enrollmentMutation.error instanceof Error
                                ? enrollmentMutation.error.message
                                : "Enrollment failed. Please try again."}
                        </p>
                    )}
                </div>
            </section>

            {isEnrolled &&
                progress &&
                !progressQuery.isPending && (
                    <section
                        className={
                            progressQuery.data
                                ?.course_completed
                                ? "th-next-action is-complete"
                                : "th-next-action"
                        }
                    >
                        <div>
                            <span className="th-eyebrow">
                                {progressQuery.data
                                    ?.course_completed
                                    ? "COURSE COMPLETE"
                                    : "NEXT RECOMMENDED ACTION"}
                            </span>

                            <h2>
                                {progressQuery.data
                                    ?.course_completed
                                    ? "You have completed this learning path."
                                    : recommendedLesson
                                      ? `Continue with ${recommendedLesson.title}`
                                      : "Continue learning"}
                            </h2>

                            <p>
                                {progressQuery.data
                                    ?.course_completed
                                    ? "Your course progress is complete. Your certificate is ready to review."
                                    : recommendedLesson
                                      ? recommendedRequiredActivities > 0
                                          ? `Complete the ${recommendedRequiredActivities} required ${recommendedRequiredActivities === 1 ? "activity" : "activities"} in this lesson to keep progressing.`
                                          : "Continue this lesson to keep your learning path moving."
                                      : "Continue through the course outline to complete your learning path."}
                            </p>
                        </div>

                        {progressQuery.data
                            ?.course_completed ? (
                            <Link
                                className="th-primary-button"
                                to="/certificates"
                            >
                                View certificates
                            </Link>
                        ) : recommendedLesson ? (
                            <button
                                className="th-primary-button"
                                type="button"
                                onClick={() =>
                                    setSelectedLessonId(
                                        recommendedLesson.id,
                                    )
                                }
                            >
                                Continue learning →
                            </button>
                        ) : null}
                    </section>
                )}

            <section className="th-learning-layout">
                <aside className="th-learning-sidebar">
                    <div className="th-sidebar-heading">
                        <span className="th-eyebrow">
                            COURSE OUTLINE
                        </span>

                        <strong>
                            {
                                course.modules
                                    .length
                            }{" "}
                            modules
                        </strong>
                    </div>

                    {course.modules.map(
                        (module) => {
                            const moduleProgress =
                                progressByModule.get(
                                    module.id,
                                );

                            return (
                                <div
                                    className="th-module"
                                    key={module.id}
                                >
                                    <div className="th-module-heading">
                                        <div>
                                            <span>
                                                Module{" "}
                                                {
                                                    module.order
                                                }
                                            </span>

                                            <strong>
                                                {
                                                    module.title
                                                }
                                            </strong>
                                        </div>

                                        {isEnrolled && (
                                            <small>
                                                {
                                                    moduleProgress
                                                        ?.progress_percentage ??
                                                    0
                                                }
                                                %
                                            </small>
                                        )}
                                    </div>

                                    {module.lessons.map(
                                        (
                                            lesson,
                                        ) => {
                                            const lessonState =
                                                lessonStates.get(
                                                    lesson.id,
                                                );

                                            const isLocked =
                                                isEnrolled &&
                                                !lessonState
                                                    ?.unlocked;

                                            return (
                                                <button
                                                    className={
                                                        selectedLesson?.id ===
                                                        lesson.id
                                                            ? "th-lesson-link is-active"
                                                            : isLocked
                                                              ? "th-lesson-link is-locked"
                                                              : "th-lesson-link"
                                                    }
                                                    key={
                                                        lesson.id
                                                    }
                                                    type="button"
                                                    disabled={
                                                        isLocked
                                                    }
                                                    title={
                                                        isLocked
                                                            ? lessonState
                                                                  ?.lockReason
                                                            : undefined
                                                    }
                                                    aria-label={
                                                        isLocked
                                                            ? `${lesson.title}. ${lessonState?.lockReason}`
                                                            : lesson.title
                                                    }
                                                    onClick={() =>
                                                        setSelectedLessonId(
                                                            lesson.id,
                                                        )
                                                    }
                                                >
                                                    <LessonStatus
                                                        lesson={
                                                            lesson
                                                        }
                                                        progressModule={
                                                            moduleProgress
                                                        }
                                                        unlocked={
                                                            lessonState
                                                                ?.unlocked ??
                                                            true
                                                        }
                                                    />

                                                    <span>
                                                        {
                                                            lesson.title
                                                        }

                                                        {lessonState
                                                            ?.completed && (
                                                            <small className="th-lesson-state-label">
                                                                Complete
                                                            </small>
                                                        )}

                                                        {isLocked && (
                                                            <small className="th-lesson-state-label">
                                                                Locked
                                                            </small>
                                                        )}
                                                    </span>
                                                </button>
                                            );
                                        },
                                    )}
                                </div>
                            );
                        },
                    )}
                </aside>

                <section className="th-lesson-workspace">
                    {progressQuery.isFetching &&
                        user && (
                            <div className="th-sync-note">
                                Syncing your
                                progress...
                            </div>
                        )}

                    {selectedLesson ? (
                        <>
                            <div className="th-lesson-heading">
                                <span className="th-eyebrow">
                                    LESSON{" "}
                                    {
                                        selectedLesson.order
                                    }
                                </span>

                                <h2>
                                    {
                                        selectedLesson.title
                                    }
                                </h2>
                            </div>

                            <article
                                className="th-lesson-content"
                                dangerouslySetInnerHTML={{
                                    __html:
                                        selectedLesson.content,
                                }}
                            />

                            <section className="th-activities-section">
                                <div className="th-section-heading">
                                    <div>
                                        <span className="th-eyebrow">
                                            PRACTICE
                                        </span>

                                        <h3>
                                            Activities
                                        </h3>
                                    </div>

                                    <span>
                                        {selectedLessonState?.completed
                                            ? "Lesson complete"
                                            : `${selectedLesson.activities.length} total`}
                                    </span>
                                </div>

                                {selectedLesson.activities.length ===
                                0 ? (
                                    <div className="th-empty-state">
                                        No activities
                                        have been
                                        added to
                                        this lesson
                                        yet.
                                    </div>
                                ) : (
                                    <div className="th-activity-list">
                                        {selectedLesson.activities.map(
                                            (
                                                activity,
                                            ) => (
                                                <Link
                                                    className="th-activity-card"
                                                    key={
                                                        activity.id
                                                    }
                                                    to={
                                                        activity.activity_type === "quiz"
                                                            ? `/courses/${slug}/quiz/${activity.id}`
                                                            : `/courses/${slug}/lessons/${selectedLesson.id}/activities/${activity.id}`
                                                    }
                                                >
                                                    <div className="th-activity-card-top">
                                                        <span className="th-activity-type">
                                                            {formatActivityType(
                                                                activity.activity_type,
                                                            )}
                                                        </span>

                                                        {activity.is_required && (
                                                            <span className="th-required-badge">
                                                                Required
                                                            </span>
                                                        )}
                                                    </div>

                                                    <h4>
                                                        {
                                                            activity.title
                                                        }
                                                    </h4>

                                                    <p>
                                                        {activity.instructions ||
                                                            "Complete this activity to reinforce the lesson."}
                                                    </p>

                                                    <div className="th-activity-meta">
                                                        <span>
                                                            Max
                                                            score:{" "}
                                                            {
                                                                activity.max_score
                                                            }
                                                        </span>

                                                        <span>
                                                            Activity{" "}
                                                            {
                                                                activity.order
                                                            }
                                                        </span>
                                                    </div>
                                                </Link>
                                            ),
                                        )}
                                    </div>
                                )}
                            </section>

                            <div className="th-lesson-navigation">
                                {previousLesson ? (
                                    <button
                                        className="th-secondary-button"
                                        type="button"
                                        onClick={() =>
                                            setSelectedLessonId(
                                                previousLesson.id,
                                            )
                                        }
                                    >
                                        ← Previous
                                    </button>
                                ) : (
                                    <span />
                                )}

                                {nextLesson &&
                                (
                                    lessonStates.get(
                                        nextLesson.id,
                                    )?.unlocked ??
                                    true
                                ) ? (
                                    <button
                                        className="th-primary-button"
                                        type="button"
                                        onClick={() =>
                                            setSelectedLessonId(
                                                nextLesson.id,
                                            )
                                        }
                                    >
                                        Next lesson →
                                    </button>
                                ) : nextLesson ? (
                                    <span className="th-completion-hint">
                                        Complete this lesson to
                                        unlock the next one.
                                    </span>
                                ) : (
                                    <span className="th-completion-hint">
                                        End of available
                                        lessons
                                    </span>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="th-empty-state">
                            This course does not
                            contain any lessons yet.
                        </div>
                    )}
                </section>
            </section>
        </main>
    );
}





