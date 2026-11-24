import { redirect } from "next/navigation";

/** "/" itself has no screen: middleware sends people to /home or /welcome. This is the fallback. */
export default function Root() {
  redirect("/welcome");
}
