import { startSession } from "@/lib/server/session";

export async function POST(request: Request) {
  return startSession(request, "/auth/register");
}
