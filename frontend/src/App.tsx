import AssessmentCenterPage from "./pages/AssessmentCenterPage";
import AssessmentDetailPage from "./pages/AssessmentDetailPage";
import {
    Link,
    NavLink,
    Route,
    Routes,
} from "react-router";
import { useAuth } from "./context/AuthContext";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import { useQuery } from "@tanstack/react-query";
import {
    getCourses,
    getNotifications,
} from "./api/client";
import type { Course } from "./types/api";
import ProtectedRoute from "./components/ProtectedRoute";
import CourseDetailPage from "./pages/CourseDetailPage";
import ActivityPage from "./pages/ActivityPage";
import QuizPage from "./pages/QuizPage";
import InstructorAssessmentPage from "./pages/InstructorAssessmentPage";
import InstructorDashboardPage from "./pages/InstructorDashboardPage";

const navigation = [
    { label: "Home", path: "/" },
    { label: "Dashboard", path: "/dashboard" },
    { label: "Courses", path: "/courses" },
    { label: "Assessments", path: "/assessments" },
    { label: "Projects", path: "/projects" },
    { label: "Certificates", path: "/certificates" },
    { label: "Notifications", path: "/notifications" },
];

function AppShell() {
    const {
        auth,
        logout,
    } = useAuth();

    const token =
        auth?.token ?? "";



    const isInstructor =
        Boolean(auth?.user.is_staff) ||
        auth?.user.role === "INSTRUCTOR" ||
        auth?.user.role === "ADMIN";

    const notificationsQuery =
        useQuery({
            queryKey: [
                "shell-notifications",
                token,
            ],
            queryFn: () =>
                getNotifications(token),
            enabled: Boolean(token),
        });

    return (
        <div className="app-shell">
            <aside className="sidebar">
                <Link
                    to="/"
                    className="brand"
                >
                    <div className="brand-mark">
                        TH
                    </div>

                    <div>
                        <strong>
                            Tech Haven
                        </strong>

                        <span>
                            Learn. Build. Prove.
                        </span>
                    </div>
                </Link>

                <nav
                    className="sidebar-nav"
                    aria-label="Primary"
                >
                    {[
                        ...navigation,
                        ...(isInstructor
                            ? [
                                  {
                                      label: "Instructor",
                                      path: "/instructor",
                                  },
                              ]
                            : []),
                    ].map(
                        (item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                end={
                                    item.path ===
                                    "/"
                                }
                                className={({
                                    isActive,
                                }) =>
                                    isActive
                                        ? "nav-link active"
                                        : "nav-link"
                                }
                            >
                                <span>
                                    {item.label}
                                </span>
                            </NavLink>
                        ),
                    )}
                </nav>

                <div className="sidebar-footer">
                    <div className="upgrade-card">
                        <span className="eyebrow">
                            TECH HAVEN PRO
                        </span>

                        <strong>
                            Build skills that
                            compound.
                        </strong>

                        <p>
                            Advanced projects,
                            assessments and
                            career-ready learning
                            are coming.
                        </p>
                    </div>
                </div>
            </aside>

            <section className="app-content">
                <header className="topbar">
                    <div>
                        <span className="topbar-label">
                            TECH HAVEN
                        </span>

                        <span className="topbar-title">
                            Technology Skills Hub
                        </span>
                    </div>

                    <div className="topbar-actions">
                        {auth && (
                            <>
                                <Link
                                    to="/notifications"
                                    className="icon-button"
                                >
                                    Notifications
                                    {notificationsQuery
                                        .data
                                        ?.unread_count
                                        ? ` (${notificationsQuery.data.unread_count})`
                                        : ""}
                                </Link>

                                <div className="profile-chip">
                                    <span className="avatar">
                                        {auth.user.username
                                            .slice(0, 2)
                                            .toUpperCase()}
                                    </span>

                                    <span>
                                        {
                                            auth.user.username
                                        }
                                    </span>
                                </div>

                                <button
                                    type="button"
                                    className="icon-button"
                                    onClick={logout}
                                >
                                    Sign out
                                </button>
                            </>
                        )}

                        {!auth && (
                            <Link
                                to="/login"
                                className="icon-button"
                            >
                                Sign in
                            </Link>
                        )}
                    </div>
                </header>

                <main>
                    <Routes>
                        <Route
                            path="/"
                            element={
                                <LandingPage />
                            }
                        />

                        <Route
                            path="/login"
                            element={
                                <LoginPage />
                            }
                        />

                        <Route element={<ProtectedRoute />}>
                            <Route
                                path="/dashboard"
                                element={
                                    <DashboardPage />
                                }
                            />
                        </Route>

                        <Route
                            path="/courses"
                            element={
                                <CoursesPage />
                            }
                        />

                        <Route
                            path="/courses/:slug"
                            element={
                                <CourseDetailPage />
                            }
                        />

                        <Route
                            path="/courses/:slug/lessons/:lessonId/activities/:activityId"
                            element={
                                <ActivityPage />
                            }
                        />

                        <Route
                            path="/courses/:slug/quiz/:activityId"
                            element={
                                <QuizPage />
                            }
                        />

                        <Route element={<ProtectedRoute />}>
    <Route
        path="/assessments"
        element={
            <AssessmentCenterPage />
        }
    />    <Route
        path="/assessments/submissions/:submissionId"
        element={
            <AssessmentDetailPage />
        }
    />

    <Route
        path="/assessments/quiz-attempts/:attemptId"
        element={
            <AssessmentDetailPage />
        }
    />

</Route>                          <Route
                              path="/instructor"
                              element={
                                  <InstructorDashboardPage />
                              }
                          />


                        <Route
                            path="/instructor/assessments"
                            element={
                                <InstructorAssessmentPage />
                            }
                        />

                        <Route
                            path="/instructor/assessments/submissions/:submissionId"
                            element={
                                <AssessmentDetailPage />
                            }
                        />

                        <Route
                            path="/projects"element={
                                <ComingSoonPage
                                    title="Projects"
                                    description="Practical projects and portfolio evidence are the next commercial layer of Tech Haven."
                                />
                            }
                        />

                        <Route
                            path="/certificates"
                            element={
                                <ComingSoonPage
                                    title="Certificates"
                                    description="Verified learner achievements will appear here."
                                />
                            }
                        />

                        <Route
                            path="/notifications"
                            element={
                                <ComingSoonPage
                                    title="Notifications"
                                    description="The existing Django notification system is ready and will be connected to this React view next."
                                />
                            }
                        />

                        <Route
                            path="*"
                            element={
                                <NotFoundPage />
                            }
                        />
                    </Routes>
                </main>
            </section>
        </div>
    );
}

function LandingPage() {
    return (
        <div className="page">
            <section className="hero-card">
                <div className="hero-copy">
                    <span className="eyebrow">
                        TECH HAVEN
                    </span>

                    <h1>
                        Technology skills,
                        <br />
                        built for the real world.
                    </h1>

                    <p>
                        Learn practical skills,
                        build meaningful projects,
                        prove what you know, and
                        prepare for the opportunities
                        ahead.
                    </p>

                    <div className="hero-actions">
                        <Link
                            className="primary-button"
                            to="/courses"
                        >
                            Explore courses
                        </Link>

                        <Link
                            className="secondary-button"
                            to="/login"
                        >
                            Student sign in
                        </Link>
                    </div>
                </div>

                <div className="hero-panel">
                    <span className="hero-panel-label">
                        LEARNING LOOP
                    </span>

                    <div className="learning-loop">
                        <div>Learn</div>
                        <div>Practice</div>
                        <div>Submit</div>
                        <div>Get Assessed</div>
                        <div>Improve</div>
                        <div>Progress</div>
                    </div>
                </div>
            </section>

            <section className="feature-grid">
                <FeatureCard
                    metric="01"
                    title="Learn"
                    text="Structured technology courses and guided lessons."
                />

                <FeatureCard
                    metric="02"
                    title="Build"
                    text="Practical coding, assignments, labs and future projects."
                />

                <FeatureCard
                    metric="03"
                    title="Prove"
                    text="Assessments, grades, certificates and verified skills."
                />

                <FeatureCard
                    metric="04"
                    title="Launch"
                    text="A future talent layer connecting skills with opportunities."
                />
            </section>
        </div>
    );
}

function CoursesPage() {
    const coursesQuery =
        useQuery({
            queryKey: ["courses"],
            queryFn: getCourses,
        });

    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        LEARNING CATALOG
                    </span>

                    <h1>
                        Explore Tech Haven
                        courses.
                    </h1>

                    <p>
                        Live course data is
                        delivered by your existing
                        Django REST API.
                    </p>
                </div>
            </section>

            {coursesQuery.isPending && (
                <div className="status-card">
                    Loading courses...
                </div>
            )}

            {coursesQuery.isError && (
                <div className="status-card error">
                    Unable to reach the Django API.
                </div>
            )}

            {coursesQuery.isSuccess && (
                <div className="course-grid">
                    {coursesQuery.data.results.map(
                        (course) => (
                            <CourseCard
                                key={course.id}
                                course={course}
                            />
                        ),
                    )}
                </div>
            )}
        </div>
    );
}

function CourseCard({
    course,
}: {
    course: Course;
}) {
    return (
        <article className="course-card">
            <div className="course-card-top">
                <span className="course-level">
                    {course.level}
                </span>

                <span className="course-duration">
                    {course.duration}
                </span>
            </div>

            <h3>{course.title}</h3>

            <p>
                {course.description}
            </p>

            <Link
                className="course-card-footer"
                to={`/courses/${course.slug}`}
            >
                <span>
                    Instructor:{" "}
                    {course.instructor}
                </span>

                <span className="course-arrow">
                    ?
                </span>
            </Link>
        </article>
    );
}

function FeatureCard({
    metric,
    title,
    text,
}: {
    metric: string;
    title: string;
    text: string;
}) {
    return (
        <article className="feature-card">
            <span className="feature-number">
                {metric}
            </span>

            <h3>{title}</h3>

            <p>{text}</p>
        </article>
    );
}

function ComingSoonPage({
    title,
    description,
}: {
    title: string;
    description: string;
}) {
    return (
        <div className="page centered-page">
            <div className="empty-panel">
                <span className="eyebrow">
                    NEXT LAYER
                </span>

                <h1>{title}</h1>

                <p>
                    {description}
                </p>

                <Link
                    className="primary-button"
                    to="/"
                >
                    Back to Tech Haven
                </Link>
            </div>
        </div>
    );
}

function NotFoundPage() {
    return (
        <div className="page centered-page">
            <div className="empty-panel">
                <span className="eyebrow">
                    404
                </span>

                <h1>
                    Page not found.
                </h1>

                <p>
                    The Tech Haven route you
                    requested does not exist.
                </p>

                <Link
                    className="primary-button"
                    to="/"
                >
                    Return home
                </Link>
            </div>
        </div>
    );
}

export default AppShell;
