import { BASE_URL } from "@/context/ApiContext";

export { BASE_URL };

export function getApiEndpoint(path: string): string {
  // If BASE_URL is an absolute HTTP/HTTPS URL
  if (BASE_URL.startsWith("http://") || BASE_URL.startsWith("https://")) {
    return `${BASE_URL}${path}`;
  }

  // If BASE_URL is a relative path (e.g. /api for dev proxy)
  return `${BASE_URL}${path}`;
}
