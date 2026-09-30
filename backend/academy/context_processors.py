from .models import Notification


def notifications(request):
    unread_notification_count = 0
    recent_notifications = Notification.objects.none()

    if request.user.is_authenticated:
        unread_notification_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        recent_notifications = (
            Notification.objects
            .filter(recipient=request.user)
            .order_by("-created_at")[:5]
        )

    return {
        "unread_notification_count": unread_notification_count,
        "recent_notifications": recent_notifications,
    }
