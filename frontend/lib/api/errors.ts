/**
 * One error type for every failed API call.
 *
 * The backend answers errors in two shapes:
 *   - business errors:   { "detail": "Not enough money", "code": "insufficient_funds" }
 *   - validation (422):  { "detail": [{ "loc": ["body", "email"], "msg": "..." }] }
 * Screens react to `code` (stable), never to the wording of `message`.
 */

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    /** For 422s: field name -> first message, e.g. { email: "value is not a valid email" } */
    public readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ValidationItem = { loc?: (string | number)[]; msg?: string };

function cleanMessage(msg: string): string {
  // Pydantic prefixes custom messages with "Value error, ".
  return msg.replace(/^Value error, /, "");
}

export async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Not JSON (e.g. a proxy error page).
  }

  const data = (body ?? {}) as { detail?: unknown; code?: unknown };

  if (Array.isArray(data.detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const item of data.detail as ValidationItem[]) {
      const field = item.loc?.[item.loc.length - 1];
      if (typeof field === "string" && item.msg && !(field in fieldErrors)) {
        fieldErrors[field] = cleanMessage(item.msg);
      }
    }
    const first = Object.values(fieldErrors)[0] ?? "Please check the form and try again.";
    return new ApiError(response.status, "validation_error", first, fieldErrors);
  }

  const message =
    typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.";
  const code = typeof data.code === "string" ? data.code : `http_${response.status}`;
  return new ApiError(response.status, code, message);
}

export function networkError(): ApiError {
  return new ApiError(0, "network_error", "Can't reach Jaga right now. Check your connection.");
}
