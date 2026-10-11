import {
    Navigate,
    Outlet,
    useLocation,
} from "react-router";
import { useAuth } from "../context/AuthContext";
import type { AuthUser } from "../types/api";

type AppRole = AuthUser["role"];

export default function ProtectedRoute({
    requiredRoles,
}: {
    requiredRoles?: AppRole[];
}) {
    const { auth, isAuthenticated } = useAuth();
    const location = useLocation();

    if (!isAuthenticated || !auth) {
        return (
            <Navigate
                to="/login"
                replace
                state={{ from: location.pathname }}
            />
        );
    }

    if (requiredRoles && !requiredRoles.includes(auth.user.role)) {
        return <Navigate to="/dashboard" replace />;
    }

    return <Outlet />;
}
