import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";

import { getCourses } from "../api/client";
import type { Course } from "../types/api";

function CourseCard({ course }: { course: Course }) {
    return (
        <article className="th-course-card">
            <div className="th-course-card-top">
                <span className="th-course-badge">
                    {course.level}
                </span>

                <span className="th-course-duration">
                    {course.duration}
                </span>
            </div>

            <h2>{course.title}</h2>

            <p className="th-course-description">
                {course.description}
            </p>

            <div className="th-course-meta">
                <span>Instructor</span>
                <strong>{course.instructor}</strong>
            </div>

            <Link
                className="th-course-card-link"
                to={`/courses/${course.slug}`}
            >
                Open course
                <span aria-hidden="true">→</span>
            </Link>
        </article>
    );
}

export default function CourseCatalogPage() {
    const coursesQuery = useQuery({
        queryKey: ["courses"],
        queryFn: getCourses,
    });

    if (coursesQuery.isPending) {
        return (
            <main className="th-course-page">
                <div className="th-course-loading">
                    Loading the Tech Haven course catalog...
                </div>
            </main>
        );
    }

    if (coursesQuery.isError) {
        return (
            <main className="th-course-page">
                <section className="th-course-error">
                    <span className="th-eyebrow">
                        CATALOG ERROR
                    </span>

                    <h1>We couldn't load the courses.</h1>

                    <p>
                        {coursesQuery.error instanceof Error
                            ? coursesQuery.error.message
                            : "Please try again."}
                    </p>

                    <button
                        className="th-primary-button"
                        type="button"
                        onClick={() => coursesQuery.refetch()}
                    >
                        Retry catalog
                    </button>
                </section>
            </main>
        );
    }

    return (
        <main className="th-course-page">
            <section className="th-course-hero">
                <div>
                    <span className="th-eyebrow">
                        TECH HAVEN / LEARNING
                    </span>

                    <h1>Build skills that become proof.</h1>

                    <p>
                        Follow structured courses from your first
                        lesson through practical activities and
                        measurable progress.
                    </p>
                </div>

                <div className="th-course-hero-stat">
                    <strong>{coursesQuery.data.count}</strong>
                    <span>courses live</span>
                </div>
            </section>

            <section className="th-course-outline-intro">
                <div>
                    <span className="th-eyebrow">LEARN</span>
                    <h2>Choose your next skill path.</h2>
                </div>

                <p>
                    Open a course to explore its modules, lessons,
                    activities, and learner progress.
                </p>
            </section>

            <section
                className="th-course-grid"
                aria-label="Course catalog"
            >
                {coursesQuery.data.results.map((course) => (
                    <CourseCard
                        key={course.id}
                        course={course}
                    />
                ))}
            </section>
        </main>
    );
}

