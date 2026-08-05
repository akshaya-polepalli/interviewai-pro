import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown } from "lucide-react";

export type SelectOption = { value: string; label: string };

type SelectFieldProps = {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  label?: string;
  id?: string;
  className?: string;
};

type MenuRect = { top: number; left: number; width: number; maxHeight: number };

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
  const [rect, setRect] = useState<MenuRect | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const selected = options.find((o) => o.value === value) ?? options[0];

  const measure = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const gap = 6;
    const spaceBelow = window.innerHeight - r.bottom - gap - 8;
    const spaceAbove = r.top - gap - 8;
    const openUp = spaceBelow < 200 && spaceAbove > spaceBelow;
    const maxHeight = Math.max(160, Math.min(288, openUp ? spaceAbove : spaceBelow));
    setRect({
      top: openUp ? r.top - gap - maxHeight : r.bottom + gap,
      left: r.left,
      width: r.width,
      maxHeight,
    });
  }, []);

  useLayoutEffect(() => {
    if (open) measure();
  }, [open, measure]);

  useEffect(() => {
    if (!open) return;
    function onDown(event: MouseEvent) {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [open, measure]);

  return (
    <div className={className}>
      {label ? (
        <label htmlFor={fieldId} className="mb-2 block text-sm text-ink-muted">
          {label}
        </label>
      ) : null}
      <button
        id={fieldId}
        ref={triggerRef}
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

      {open && rect
        ? createPortal(
            <ul
              ref={menuRef}
              role="listbox"
              aria-labelledby={fieldId}
              className="select-dropdown fixed z-[1000] overflow-y-auto rounded-xl border border-white/25 py-1 shadow-[0_20px_60px_rgba(0,0,0,0.75)]"
              style={{
                top: rect.top,
                left: rect.left,
                width: rect.width,
                maxHeight: rect.maxHeight,
                backgroundColor: "#1A2438",
              }}
            >
              {options.map((opt) => {
                const active = opt.value === value;
                return (
                  <li key={opt.value} role="option" aria-selected={active}>
                    <button
                      type="button"
                      className={[
                        "flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm transition",
                        active
                          ? "bg-accent/25 font-medium text-ink"
                          : "text-ink hover:bg-white/15",
                      ].join(" ")}
                      onClick={() => {
                        onChange(opt.value);
                        setOpen(false);
                      }}
                    >
                      <span className="truncate">{opt.label}</span>
                      {active ? <Check className="h-4 w-4 shrink-0 text-accent" /> : null}
                    </button>
                  </li>
                );
              })}
            </ul>,
            document.body,
          )
        : null}
    </div>
  );
}
