import {
    useState,
    type FormEvent,
} from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";

import {
    getCertificates,
    getCourseProgress,
    getCourses,
} from "../api/client";

import { useAuth } from "../context/AuthContext";

import type {
    Certificate,
    Course,
} from "../types/api";

function normalizeList<T>(
    value: unknown,
): T[] {
    if (Array.isArray(value)) {
        return value as T[];
    }

    if (
        value &&
        typeof value === "object" &&
        "results" in value
    ) {
        const results = (
            value as {
                results?: unknown;
            }
        ).results;

        return Array.isArray(results)
            ? (results as T[])
            : [];
    }

    return [];
}

function formatDate(
    value: string,
) {
    return new Intl.DateTimeFormat(
        undefined,
        {
            dateStyle: "medium",
            timeStyle: "short",
        },
    ).format(new Date(value));
}

function backendBaseUrl() {
    const configured =
        import.meta.env.VITE_BACKEND_BASE_URL;

    if (configured) {
        return configured.replace(
            /\/$/,
            "",
        );
    }

    if (import.meta.env.DEV) {
        return "http://127.0.0.1:8000";
    }

    return "https://coding-e-learning-platform.onrender.com";
}

type CertificateCenterData = {
    courses: Course[];
    certificates: Certificate[];
    inProgressCourses: Course[];
};

async function loadCertificateCenter(
    token: string,
): Promise<CertificateCenterData> {
    const [
        coursesResponse,
        certificatesResponse,
    ] = await Promise.all([
        getCourses(),
        getCertificates(token),
    ]);

    const courses = normalizeList<Course>(
        coursesResponse,
    );

    const progressResults =
        await Promise.all(
            courses.map(
                async (course) => {
                    try {
                        const progress =
                            await getCourseProgress(
                                course.slug,
                                token,
                            );

                        return {
                            course,
                            progress,
                        };
                    } catch {
                        return null;
                    }
                },
            ),
        );

    const inProgressCourses =
        progressResults.flatMap(
            (item) => {
                if (
                    item === null ||
                    !item.progress.is_enrolled ||
                    item.progress.course_completed
                ) {
                    return [];
                }

                return [item.course];
            },
        );

    return {
        courses,
        certificates:
            certificatesResponse.results ?? [],
        inProgressCourses,
    };
}

export default function CertificatesPage() {
    const { auth } = useAuth();

    const token =
        auth?.token ?? "";

    const [verificationCode, setVerificationCode] =
        useState("");

    const certificateQuery =
        useQuery({
            queryKey: [
                "certificate-center",
                token,
            ],
            queryFn: () =>
                loadCertificateCenter(
                    token,
                ),
            enabled: Boolean(token),
        });

    const data =
        certificateQuery.data;

    const certificates =
        data?.certificates ?? [];

    const certifiedScores =
        certificates
            .map(
                (certificate) =>
                    certificate.average_score,
            )
            .filter(
                (
                    score,
                ): score is number =>
                    score !== null,
            );

    const averageCertifiedScore =
        certifiedScores.length === 0
            ? null
            : certifiedScores.reduce(
                  (
                      total,
                      score,
                  ) => total + score,
                  0,
              ) /
              certifiedScores.length;

    function verifyCertificate(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        const code =
            verificationCode.trim();

        if (!code) {
            return;
        }

        window.location.assign(
            `${backendBaseUrl()}/courses/certificates/verify/${encodeURIComponent(
                code,
            )}/`,
        );
    }

    if (
        certificateQuery.isPending
    ) {
        return (
            <div className="page">
                <section className="certificate-hero">
                    <div>
                        <span className="eyebrow">
                            ACHIEVEMENT CENTER
                        </span>

                        <h1>
                            Your certificates
                        </h1>

                        <p>
                            Loading your learning
                            achievements...
                        </p>
                    </div>
                </section>

                <div className="status-card">
                    Loading certificate
                    center...
                </div>
            </div>
        );
    }

    if (
        certificateQuery.isError
    ) {
        return (
            <div className="page">
                <section className="certificate-hero">
                    <div>
                        <span className="eyebrow">
                            ACHIEVEMENT CENTER
                        </span>

                        <h1>
                            Your certificates
                        </h1>

                        <p>
                            We could not load your
                            certificate records.
                        </p>
                    </div>
                </section>

                <div className="status-card error">
                    Unable to load certificates.
                    Please sign in again and retry.
                </div>
            </div>
        );
    }

    return (
        <div className="page certificate-center">
            <section className="certificate-hero">
                <div>
                    <span className="eyebrow">
                        ACHIEVEMENT CENTER
                    </span>

                    <h1>
                        Earn it. Prove it.
                    </h1>

                    <p>
                        Track completed courses,
                        access verified certificate
                        records, and share proof of
                        your progress.
                    </p>
                </div>

                <div className="certificate-hero-award">
                    <span>
                        Certificates earned
                    </span>

                    <strong>
                        {certificates.length}
                    </strong>

                    <small>
                        Keep completing required
                        lessons to unlock more.
                    </small>
                </div>
            </section>

            <section className="certificate-stats">
                <div className="certificate-stat">
                    <span>
                        Courses
                    </span>

                    <strong>
                        {data?.courses.length ?? 0}
                    </strong>
                </div>

                <div className="certificate-stat">
                    <span>
                        Certificates earned
                    </span>

                    <strong>
                        {certificates.length}
                    </strong>
                </div>

                <div className="certificate-stat">
                    <span>
                        In progress
                    </span>

                    <strong>
                        {data?.inProgressCourses
                            .length ?? 0}
                    </strong>
                </div>

                <div className="certificate-stat">
                    <span>
                        Average certified score
                    </span>

                    <strong>
                        {averageCertifiedScore ===
                        null
                            ? "?"
                            : `${averageCertifiedScore.toFixed(
                                  1,
                              )}%`}
                    </strong>
                </div>
            </section>

            <div className="certificate-content-grid">
                <section className="certificate-panel">
                    <div className="certificate-panel-heading">
                        <div>
                            <span className="eyebrow">
                                EARNED
                            </span>

                            <h2>
                                Your certificate
                                records
                            </h2>
                        </div>
                    </div>

                    {certificates.length ===
                        0 && (
                        <div className="certificate-empty">
                            <span className="certificate-empty-icon">
                                ?
                            </span>

                            <h3>
                                No certificates yet
                            </h3>

                            <p>
                                Complete all required
                                lessons in an enrolled
                                course to unlock its
                                certificate.
                            </p>

                            <Link
                                className="primary-button"
                                to="/courses"
                            >
                                Explore courses
                            </Link>
                        </div>
                    )}

                    <div className="certificate-grid">
                        {certificates.map(
                            (
                                certificate,
                            ) => (
                                <article
                                    className="certificate-card"
                                    key={
                                        certificate.id
                                    }
                                >
                                    <div className="certificate-card-top">
                                        <span className="certificate-award-badge">
                                            ?
                                        </span>

                                        <span
                                            className={
                                                certificate.is_valid
                                                    ? "certificate-valid"
                                                    : "certificate-invalid"
                                            }
                                        >
                                            {certificate.is_valid
                                                ? "Valid"
                                                : "Invalid"}
                                        </span>
                                    </div>

                                    <span className="certificate-course">
                                        {
                                            certificate.course_title
                                        }
                                    </span>

                                    <h3>
                                        Certificate of
                                        Completion
                                    </h3>

                                    <p>
                                        Awarded to{" "}
                                        <strong>
                                            {
                                                certificate.learner_name
                                            }
                                        </strong>
                                    </p>

                                    <div className="certificate-metrics">
                                        <div>
                                            <span>
                                                Score
                                            </span>

                                            <strong>
                                                {certificate.average_score ===
                                                null
                                                    ? "?"
                                                    : `${certificate.average_score}%`}
                                            </strong>
                                        </div>

                                        <div>
                                            <span>
                                                Issued
                                            </span>

                                            <strong>
                                                {formatDate(
                                                    certificate.issued_at,
                                                )}
                                            </strong>
                                        </div>
                                    </div>

                                    <div className="certificate-card-actions">
                                        <a
                                            className="primary-button"
                                            href={
                                                certificate.verification_url
                                            }
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            Verify certificate
                                        </a>

                                        <span className="certificate-code">
                                            Code:{" "}
                                            {
                                                certificate.verification_code
                                            }
                                        </span>
                                    </div>
                                </article>
                            ),
                        )}
                    </div>
                </section>

                <aside className="certificate-sidebar">
                    <section className="certificate-panel certificate-progress-panel">
                        <span className="eyebrow">
                            IN PROGRESS
                        </span>

                        <h2>
                            Courses you're working
                            toward
                        </h2>

                        {data?.inProgressCourses
                            .length ? (
                            <div className="certificate-course-list">
                                {data.inProgressCourses.map(
                                    (
                                        course,
                                    ) => (
                                        <div
                                            className="certificate-course-item"
                                            key={
                                                course.id
                                            }
                                        >
                                            <div>
                                                <span>
                                                    {
                                                        course.level
                                                    }
                                                </span>

                                                <strong>
                                                    {
                                                        course.title
                                                    }
                                                </strong>
                                            </div>

                                            <Link
                                                to={`/courses/${course.slug}`}
                                            >
                                                Continue
                                            </Link>
                                        </div>
                                    ),
                                )}
                            </div>
                        ) : (
                            <p className="certificate-muted">
                                No enrolled courses are
                                currently in progress.
                            </p>
                        )}
                    </section>

                    <section className="certificate-panel certificate-verification-panel">
                        <span className="eyebrow">
                            PUBLIC VERIFICATION
                        </span>

                        <h2>
                            Verify a certificate
                        </h2>

                        <p>
                            Enter a certificate
                            verification code to open
                            its public verification
                            record.
                        </p>

                        <form
                            onSubmit={
                                verifyCertificate
                            }
                        >
                            <label
                                htmlFor="certificate-verification-code"
                            >
                                Verification code
                            </label>

                            <input
                                id="certificate-verification-code"
                                type="text"
                                value={
                                    verificationCode
                                }
                                onChange={(
                                    event,
                                ) =>
                                    setVerificationCode(
                                        event.target
                                            .value,
                                    )
                                }
                                placeholder="Enter UUID"
                                autoComplete="off"
                            />

                            <button
                                className="primary-button"
                                type="submit"
                                disabled={
                                    !verificationCode.trim()
                                }
                            >
                                Verify certificate
                            </button>
                        </form>
                    </section>
                </aside>
            </div>
        </div>
    );
}
