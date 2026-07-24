import React, { createContext, useContext } from "react";

// Determine BASE_URL dynamically: use VITE_API_BASE_URL if set, else dev proxy / local / render fallback
export const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.MODE === "development"
    ? "http://localhost:8000"
    : "https://invoice-extractor-g0g6.onrender.com");

// Create React Context for BASE_URL
const BaseUrlContext = createContext<string>(BASE_URL);

/**
 * Provider component that wraps the app and makes BASE_URL available to all child components.
 */
export const BaseUrlProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  return (
    <BaseUrlContext.Provider value={BASE_URL}>
      {children}
    </BaseUrlContext.Provider>
  );
};

/**
 * Custom hook to access BASE_URL from any component in the UI.
 * Usage: const baseUrl = useBaseUrl();
 */
export const useBaseUrl = () => {
  return useContext(BaseUrlContext);
};
