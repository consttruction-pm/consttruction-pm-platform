const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const JALALI_INPUT = /^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$/;
const MS_PER_DAY = 86_400_000;

/**
 * Gregorian day bounds accepted for typed Jalali entry. The surface is a
 * workspace date control, not a historical calendar; keeping a bounded range
 * makes the inverse conversion deterministic and fail-closed.
 */
const MIN_GREGORIAN_DAY = Math.floor(Date.UTC(1800, 0, 1) / MS_PER_DAY);
const MAX_GREGORIAN_DAY = Math.floor(Date.UTC(2400, 0, 1) / MS_PER_DAY);

const PERSIAN_PARTS = new Intl.DateTimeFormat("en-u-ca-persian-nu-latn", {
  timeZone: "UTC",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

function normalizeDigits(value: string): string {
  let result = "";
  for (const character of value) {
    const persian = PERSIAN_DIGITS.indexOf(character);
    const arabic = ARABIC_DIGITS.indexOf(character);
    if (persian >= 0) result += String(persian);
    else if (arabic >= 0) result += String(arabic);
    else result += character;
  }
  return result;
}

type JalaliParts = { year: number; month: number; day: number };

function jalaliParts(dayOrdinal: number): JalaliParts | null {
  const date = new Date(dayOrdinal * MS_PER_DAY);
  if (Number.isNaN(date.getTime())) return null;
  const parts = PERSIAN_PARTS.formatToParts(date);
  const value = (type: string): number => {
    const part = parts.find((item) => item.type === type);
    return part ? Number(part.value) : Number.NaN;
  };
  const result = { year: value("year"), month: value("month"), day: value("day") };
  if (!Object.values(result).every((item) => Number.isInteger(item) && item > 0)) {
    return null;
  }
  return result;
}

function compareJalali(dayOrdinal: number, target: JalaliParts): number {
  const actual = jalaliParts(dayOrdinal);
  if (!actual) return 1;
  if (actual.year !== target.year) return actual.year - target.year;
  if (actual.month !== target.month) return actual.month - target.month;
  return actual.day - target.day;
}

function isValidIsoDate(value: string): boolean {
  const match = ISO_DATE.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    !Number.isNaN(date.getTime()) &&
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

/**
 * Convert a typed Jalali calendar date to its canonical ISO Gregorian date.
 *
 * The function accepts Persian, Arabic-Indic or Latin digits and `/`, `-` or
 * `.` separators. It resolves the date through the runtime's Persian calendar
 * data and then verifies the round-trip, so an impossible date (for example
 * 1404/12/30 in a non-leap year) returns null instead of being normalized to a
 * neighbouring day. Storage and calculation continue to use ISO Gregorian
 * dates only.
 */
export function parseJalaliDateInput(raw: string): string | null {
  const match = JALALI_INPUT.exec(normalizeDigits(raw).trim());
  if (!match) return null;
  const target = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
  if (target.month < 1 || target.month > 12 || target.day < 1 || target.day > 31) {
    return null;
  }

  let low = MIN_GREGORIAN_DAY;
  let high = MAX_GREGORIAN_DAY;
  while (low < high) {
    const middle = low + Math.floor((high - low) / 2);
    if (compareJalali(middle, target) >= 0) high = middle;
    else low = middle + 1;
  }
  if (compareJalali(low, target) !== 0) return null;
  const iso = new Date(low * MS_PER_DAY).toISOString().slice(0, 10);
  return isValidIsoDate(iso) ? iso : null;
}

/**
 * Render a canonical ISO date as a typed Jalali value without changing it.
 * Invalid input is returned unchanged so a caller never invents a date.
 */
export function formatJalaliDateInput(value: string): string {
  const match = ISO_DATE.exec(value);
  if (!match || !isValidIsoDate(value)) return value;
  const dayOrdinal = Math.floor(
    Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) / MS_PER_DAY,
  );
  const parts = jalaliParts(dayOrdinal);
  if (!parts) return value;
  const pad = (item: number): string => String(item).padStart(2, "0");
  return `${parts.year}/${pad(parts.month)}/${pad(parts.day)}`;
}

export function isValidCanonicalIsoDate(value: string): boolean {
  return isValidIsoDate(value);
}
