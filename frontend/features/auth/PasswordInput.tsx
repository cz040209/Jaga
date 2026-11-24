"use client";

import { Eye, EyeOff, LockKeyhole } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";

type Props = React.ComponentProps<"input"> & { invalid?: boolean };

/** Password field with a show/hide toggle. (React 19: `ref` is a normal prop, passed through.) */
export function PasswordInput({ invalid, ...props }: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <Input
      type={visible ? "text" : "password"}
      leading={<LockKeyhole />}
      invalid={invalid}
      trailing={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="rounded-full p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
        </button>
      }
      {...props}
    />
  );
}
