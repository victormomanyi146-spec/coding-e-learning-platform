import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import {
    QueryClient,
    QueryClientProvider,
} from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import "./styles.css";

const queryClient =
    new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 60_000,
                retry: 1,
            },
        },
    });

const rootElement =
    document.getElementById("root");

if (!rootElement) {
    throw new Error(
        "React root element was not found.",
    );
}

createRoot(rootElement).render(
    <StrictMode>
        <QueryClientProvider
            client={queryClient}
        >
            <AuthProvider>
                <BrowserRouter>
                    <App />
                </BrowserRouter>
            </AuthProvider>
        </QueryClientProvider>
    </StrictMode>,
);
