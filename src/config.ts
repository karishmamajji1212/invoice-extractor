import { BASE_URL } from "@/context/ApiContext";

export { BASE_URL };

export function getApiEndpoint(path: string): string {
  return `${BASE_URL}${path}`;
}
