import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
    getCourses,
    getNotifications,
} from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
    const {
        auth,
        logout,
    } = useAuth();

    const token =
        auth?.token ?? "";

    const coursesQuery =
        useQuery({
            queryKey: [
                "dashboard-courses",
            ],
            queryFn: getCourses,
        });

    const notificationsQuery =
        useQuery({
            queryKey: [
                "dashboard-notifications",
                token,
            ],
            queryFn: () =>
                getNotifications(token),
            enabled: Boolean(token),
        });

    const username =
        auth?.user.username ??
        "Learner";

    return (
        <div className="page dashboard-page">
            <section className="dashboard-welcome">
                <div>
                    <span className="eyebrow">
                        STUDENT DASHBOARD
                    </span>

                    <h1>
                        Welcome back,
                        <br />
                        {username}.
                    </h1>

                    <p>
                        Your Tech Haven workspace
                        is connected to the Django
                        learning engine.
                    </p>
                </div>

                <button
                    type="button"
                    className="secondary-button"
                    onClick={logout}
                >
                    Sign out
                </button>
            </section>

            <section className="dashboard-stats">
                <article>
                    <span>Courses</span>
                    <strong>
                        {coursesQuery.data?.count ??
                            "—"}
                    </strong>
                    <small>
                        available in the catalog
                    </small>
                </article>

                <article>
                    <span>Unread</span>
                    <strong>
                        {notificationsQuery.data
                            ?.unread_count ??
                            "—"}
                    </strong>
                    <small>
                        learning notifications
                    </small>
                </article>

                <article>
                    <span>Account</span>
                    <strong>
                        {auth?.user.role ??
                            "STUDENT"}
                    </strong>
                    <small>
                        authenticated profile
                    </small>
                </article>
            </section>

            <section className="dashboard-grid">
                <div className="dashboard-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                EXPLORE
                            </span>

                            <h2>
                                Continue building
                                your skills.
                            </h2>
                        </div>

                        <Link
                            to="/courses"
                            className="text-link"
                        >
                            View catalog →
                        </Link>
                    </div>

                    {coursesQuery.isPending && (
                        <div className="status-card">
                            Loading the course
                            catalog...
                        </div>
                    )}

                    {coursesQuery.isError && (
                        <div className="status-card error">
                            Unable to load the course
                            catalog.
                        </div>
                    )}

                    {coursesQuery.isSuccess && (
                        <div className="mini-course-grid">
                            {coursesQuery.data.results
                                .slice(0, 3)
                                .map((course) => (
                                    <article
                                        key={course.id}
                                        className="mini-course-card"
                                    >
                                        <span>
                                            {
                                                course.level
                                            }
                                        </span>

                                        <h3>
                                            {
                                                course.title
                                            }
                                        </h3>

                                        <p>
                                            {
                                                course.description
                                            }
                                        </p>
                                    </article>
                                ))}
                        </div>
                    )}
                </div>

                <aside className="dashboard-panel notification-panel">
                    <div className="panel-heading">
                        <div>
                            <span className="eyebrow">
                                ACTIVITY
                            </span>

                            <h2>
                                Notifications
                            </h2>
                        </div>

                        <Link
                            to="/notifications"
                            className="text-link"
                        >
                            View all →
                        </Link>
                    </div>

                    {notificationsQuery.isPending && (
                        <p className="muted-text">
                            Loading notifications...
                        </p>
                    )}

                    {notificationsQuery.isError && (
                        <p className="muted-text">
                            Notifications could not
                            be loaded.
                        </p>
                    )}

                    {notificationsQuery.isSuccess &&
                        notificationsQuery.data.results.length ===
                            0 && (
                            <p className="muted-text">
                                No notifications yet.
                            </p>
                        )}

                    {notificationsQuery.isSuccess &&
                        notificationsQuery.data.results
                            .slice(0, 4)
                            .map((notification) => (
                                <div
                                    key={
                                        notification.id
                                    }
                                    className={
                                        notification.is_read
                                            ? "mini-notification"
                                            : "mini-notification unread"
                                    }
                                >
                                    <strong>
                                        {
                                            notification.title
                                        }
                                    </strong>

                                    <p>
                                        {
                                            notification.message
                                        }
                                    </p>
                                </div>
                            ))}
                </aside>
            </section>

            <section className="dashboard-cta">
                <div>
                    <span className="eyebrow">
                        THE TECH HAVEN MODEL
                    </span>

                    <h2>
                        Learn. Build. Prove. Launch.
                    </h2>

                    <p>
                        Every future feature will
                        connect back to practical
                        skills and measurable
                        outcomes.
                    </p>
                </div>

                <Link
                    to="/courses"
                    className="primary-button"
                >
                    Explore learning
                </Link>
            </section>
        </div>
    );
}
