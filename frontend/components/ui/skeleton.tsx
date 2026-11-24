import { cn } from "@/lib/utils";

/** Loading placeholder with a soft light sweeping across it. */
export function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "animate-shimmer rounded-xl bg-[linear-gradient(90deg,#eef2f5_25%,#f8fafb_50%,#eef2f5_75%)] bg-[length:200%_100%] dark:bg-[linear-gradient(90deg,#1a2438_25%,#25324a_50%,#1a2438_75%)]",
        className,
      )}
      {...props}
    />
  );
}
