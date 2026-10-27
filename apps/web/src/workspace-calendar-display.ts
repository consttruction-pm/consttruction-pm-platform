import type { WorkspaceCalendarMode } from "./workspace-model.js";

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

const JALALI_DATE_FORMAT = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
  timeZone: "UTC",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/**
 * Format a canonical ISO schedule date for display without changing it.
 *
 * Storage and calculation always use the ISO Gregorian date from the shared
 * core. Only this presentation step converts it to the Jalali display
 * calendar. The conversion parses the date as a UTC calendar date, so no
 * local timezone offset can shift the displayed day. Invalid or non-date
 * values are returned unchanged instead of being guessed.
 */
export function formatWorkspaceCalendarDate(
  value: string,
  mode: WorkspaceCalendarMode,
): string {
  if (mode !== "jalali") return value;
  const match = ISO_DATE.exec(value);
  if (!match) return value;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const utcDate = new Date(Date.UTC(year, month - 1, day));
  if (
    Number.isNaN(utcDate.getTime()) ||
    utcDate.getUTCFullYear() !== year ||
    utcDate.getUTCMonth() !== month - 1 ||
    utcDate.getUTCDate() !== day
  ) {
    return value;
  }
  return JALALI_DATE_FORMAT.format(utcDate);
}
