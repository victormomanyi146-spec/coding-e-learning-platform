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
}: {
    lesson: Lesson;
    progressModule: ProgressModule | undefined;
}) {
    const progressLesson =
        progressModule?.lessons.find(
            (item) => item.id === lesson.id,
        );

    return (
        <span
            className={
                progressLesson?.is_completed
                    ? "th-lesson-status is-complete"
                    : "th-lesson-status"
            }
        >
            {progressLesson?.is_completed
                ? "✓"
                : lesson.order}
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

    const selectedLesson =
        lessons.find(
            (lesson) =>
                lesson.id === selectedLessonId,
        ) ?? lessons[0];

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

    const isEnrolled =
        Boolean(
            progressQuery.data
                ?.is_enrolled,
        );

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
                                        ) => (
                                            <button
                                                className={
                                                    selectedLesson?.id ===
                                                    lesson.id
                                                        ? "th-lesson-link is-active"
                                                        : "th-lesson-link"
                                                }
                                                key={
                                                    lesson.id
                                                }
                                                type="button"
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
                                                />

                                                <span>
                                                    {
                                                        lesson.title
                                                    }
                                                </span>
                                            </button>
                                        ),
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
                                        {
                                            selectedLesson
                                                .activities
                                                .length
                                        }{" "}
                                        total
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

                                {nextLesson ? (
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





