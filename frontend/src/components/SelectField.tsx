import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export type SelectOption = { value: string; label: string };

type SelectFieldProps = {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  label?: string;
  id?: string;
  className?: string;
};

/** Custom select — avoids unreadable native <option> popups on Windows dark UIs. */
export function SelectField({
  value,
  onChange,
  options,
  label,
  id,
  className = "",
}: SelectFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    function onDoc(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      {label ? (
        <label htmlFor={fieldId} className="mb-2 block text-sm text-ink-muted">
          {label}
        </label>
      ) : null}
      <button
        id={fieldId}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        className="field flex w-full items-center justify-between gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="truncate text-ink">{selected?.label ?? "Select…"}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-ink-muted transition ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <ul
          role="listbox"
          aria-labelledby={fieldId}
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-white/15 bg-canvas-elevated py-1 shadow-glass"
        >
          {options.map((opt) => {
            const active = opt.value === value;
            return (
              <li key={opt.value} role="option" aria-selected={active}>
                <button
                  type="button"
                  className={[
                    "w-full px-3 py-2.5 text-left text-sm transition",
                    active
                      ? "bg-accent/20 font-medium text-ink"
                      : "text-ink hover:bg-white/10",
                  ].join(" ")}
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                >
                  {opt.label}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
