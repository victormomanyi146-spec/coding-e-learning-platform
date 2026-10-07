import { useState } from "react";
import {
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";
import { Link } from "react-router";
import {
    getNotifications,
    markNotificationRead,
} from "../api/client";
import { useAuth } from "../context/AuthContext";

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function typeLabel(value: string) {
    return value
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (letter) =>
            letter.toUpperCase(),
        );
}

export default function NotificationsPage() {
    const { auth } = useAuth();
    const token = auth?.token ?? "";
    const queryClient = useQueryClient();

    const [filter, setFilter] = useState<
        "all" | "unread"
    >("all");

    const notificationsQuery = useQuery({
        queryKey: ["notifications", token],
        queryFn: () => getNotifications(token),
        enabled: Boolean(token),
    });

    const markReadMutation = useMutation({
        mutationFn: (notificationId: number) =>
            markNotificationRead(
                notificationId,
                token,
            ),
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({
                    queryKey: [
                        "notifications",
                        token,
                    ],
                }),
                queryClient.invalidateQueries({
                    queryKey: [
                        "shell-notifications",
                        token,
                    ],
                }),
            ]);
        },
    });

    const notifications =
        notificationsQuery.data?.results ?? [];

    const unreadCount =
        notificationsQuery.data?.unread_count ?? 0;

    const visibleNotifications =
        filter === "unread"
            ? notifications.filter(
                  (notification) =>
                      !notification.is_read,
              )
            : notifications;

    return (
        <div className="page">
            <section className="page-heading">
                <div>
                    <span className="eyebrow">
                        NOTIFICATION CENTER
                    </span>

                    <h1>
                        Stay in the loop.
                    </h1>

                    <p>
                        Review learning updates,
                        assessment feedback, and
                        important Tech Haven
                        activity from one place.
                    </p>
                </div>
            </section>

            <section className="dashboard-stats notification-stats">
                <article>
                    <span>Total</span>
                    <strong>
                        {notificationsQuery.isPending
                            ? "â€”"
                            : notifications.length}
                    </strong>
                    <small>
                        notifications received
                    </small>
                </article>

                <article>
                    <span>Unread</span>
                    <strong>
                        {notificationsQuery.isPending
                            ? "â€”"
                            : unreadCount}
                    </strong>
                    <small>
                        need your attention
                    </small>
                </article>

                <article>
                    <span>Read</span>
                    <strong>
                        {notificationsQuery.isPending
                            ? "â€”"
                            : notifications.filter(
                                  (notification) =>
                                      notification.is_read,
                              ).length}
                    </strong>
                    <small>
                        already reviewed
                    </small>
                </article>
            </section>

            <section className="dashboard-panel notification-center-panel">
                <div className="panel-heading notification-toolbar">
                    <div>
                        <span className="eyebrow">
                            ACTIVITY FEED
                        </span>
                        <h2>
                            Your notifications
                        </h2>
                    </div>

                    <div
                        className="notification-filters"
                        role="group"
                        aria-label="Notification filter"
                    >
                        <button
                            type="button"
                            className={
                                filter === "all"
                                    ? "notification-filter active"
                                    : "notification-filter"
                            }
                            onClick={() =>
                                setFilter("all")
                            }
                        >
                            All
                        </button>

                        <button
                            type="button"
                            className={
                                filter === "unread"
                                    ? "notification-filter active"
                                    : "notification-filter"
                            }
                            onClick={() =>
                                setFilter("unread")
                            }
                        >
                            Unread
                            {unreadCount > 0
                                ? ` (${unreadCount})`
                                : ""}
                        </button>
                    </div>
                </div>

                {notificationsQuery.isPending && (
                    <div className="status-card">
                        Loading your notifications...
                    </div>
                )}

                {notificationsQuery.isError && (
                    <div className="status-card error">
                        Unable to load your
                        notifications right now.
                    </div>
                )}

                {notificationsQuery.isSuccess &&
                    visibleNotifications.length === 0 && (
                        <div className="status-card">
                            <strong>
                                {filter === "unread"
                                    ? "You are all caught up."
                                    : "No notifications yet."}
                            </strong>

                            <p>
                                {filter === "unread"
                                    ? "There are no unread updates waiting for you."
                                    : "New learning and assessment updates will appear here."}
                            </p>
                        </div>
                    )}

                {visibleNotifications.length > 0 && (
                    <div className="notification-list">
                        {visibleNotifications.map(
                            (notification) => (
                                <article
                                    key={notification.id}
                                    className={
                                        notification.is_read
                                            ? "notification-card"
                                            : "notification-card unread"
                                    }
                                >
                                    <div>
                                        <div className="notification-card-top">
                                            <span className="course-level">
                                                {typeLabel(
                                                    notification.notification_type,
                                                )}
                                            </span>

                                            <time
                                                dateTime={
                                                    notification.created_at
                                                }
                                            >
                                                {formatDate(
                                                    notification.created_at,
                                                )}
                                            </time>
                                        </div>

                                        <h3>
                                            {notification.title}
                                        </h3>

                                        <p>
                                            {notification.message}
                                        </p>

                                        <div className="notification-card-actions">
                                            {notification.link_url && (
                                                <Link
                                                    to={
                                                        notification.link_url
                                                    }
                                                    className="text-link"
                                                >
                                                    Open notification â†’
                                                </Link>
                                            )}

                                            {!notification.is_read && (
                                                <button
                                                    type="button"
                                                    className="secondary-button notification-read-button"
                                                    disabled={
                                                        markReadMutation.isPending
                                                    }
                                                    onClick={() =>
                                                        markReadMutation.mutate(
                                                            notification.id,
                                                        )
                                                    }
                                                >
                                                    {markReadMutation.isPending
                                                        ? "Marking read..."
                                                        : "Mark as read"}
                                                </button>
                                            )}

                                            {notification.is_read && (
                                                <span className="notification-read-label">
                                                    Read
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <span
                                        className={
                                            notification.is_read
                                                ? "notification-status-dot read"
                                                : "notification-status-dot"
                                        }
                                        aria-hidden="true"
                                    />
                                </article>
                            ),
                        )}
                    </div>
                )}
            </section>

            <section className="dashboard-cta">
                <div>
                    <span className="eyebrow">
                        NEXT STEP
                    </span>

                    <h2>
                        Turn every update into
                        progress.
                    </h2>

                    <p>
                        Continue learning or review
                        your latest assessment work.
                    </p>
                </div>

                <Link
                    to="/assessments"
                    className="primary-button"
                >
                    Open assessments
                </Link>
            </section>
        </div>
    );
}