import { BASE_URL } from "@/context/ApiContext";

export { BASE_URL };

export function getApiEndpoint(path: string): string {
  // If BASE_URL is a relative path (e.g. /api for dev proxy)
  if (import.meta.env.MODE === "development") {
    return `${BASE_URL}/${path}`;
  }
  return `${BASE_URL}${path}`;
}
