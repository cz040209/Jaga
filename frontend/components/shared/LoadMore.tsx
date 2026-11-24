"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";

/**
 * Infinite scroll: an invisible marker at the end of a list. When it scrolls
 * into view (or nearly), the next page loads. Also a button, for keyboards.
 */
export function LoadMore({
  hasMore,
  loading,
  onLoadMore,
  endText = "That's everything",
}: {
  hasMore: boolean;
  loading: boolean;
  onLoadMore: () => void;
  endText?: string;
}) {
  const marker = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = marker.current;
    if (!element || !hasMore) return;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && !loading && onLoadMore(),
      { rootMargin: "300px" }, // start loading a little before the end
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasMore, loading, onLoadMore]);

  return (
    <div ref={marker} className="flex justify-center py-5 text-[13px] text-muted-foreground">
      {loading ? (
        <Loader2 className="size-5 animate-spin text-teal-500" aria-label="Loading more" />
      ) : hasMore ? (
        <button onClick={onLoadMore} className="font-semibold text-teal-600 dark:text-teal-400">
          Load more
        </button>
      ) : (
        <span>{endText}</span>
      )}
    </div>
  );
}
