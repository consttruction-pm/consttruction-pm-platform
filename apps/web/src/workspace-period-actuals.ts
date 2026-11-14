import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Stored period performance client.
 *
 * Period actuals are immutable, period-addressed facts owned by the shared
 * activity-period actual service. This module validates the wire contract and
 * builds an exact payload; it never derives units, cost or dates.
 */

export const PERIOD_ACTUAL_API_VERSION = "p6-activity-period-actual-api.v1";

export type StoredPeriodActual = {
  actualId: string;
  activityId: string;
  periodId: string;
  actualUnits: string | null;
  actualCost: string | null;
  unit: string | null;
  currency: string | null;
  note: string | null;
};

export type PeriodActualInput = {
  activityId: string;
  periodId: string;
  actualUnits: string;
  actualCost: string;
  unit: string;
  currency: string;
  note: string;
};

export type PeriodActualFilters = {
  activityId?: string | null;
  periodId?: string | null;
};

const DECIMAL = /^-?\d+(\.\d+)?$/;

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function decimalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" || !value.trim() || !DECIMAL.test(value.trim())) {
    throw new Error(code);
  }
  return value.trim();
}

export function parsePeriodActual(value: unknown): StoredPeriodActual {
  if (
    !isRecord(value) ||
    value.contract_version !== PERIOD_ACTUAL_API_VERSION ||
    value.kind !== "p6_activity_period_actual"
  ) {
    throw new Error("INVALID_PERIOD_ACTUAL");
  }
  const payload = value.activity_period_actual;
  if (!isRecord(payload)) throw new Error("INVALID_PERIOD_ACTUAL");
  return {
    actualId: requiredText(payload.actual_id, "INVALID_PERIOD_ACTUAL"),
    activityId: requiredText(payload.activity_id, "INVALID_PERIOD_ACTUAL"),
    periodId: requiredText(payload.period_id, "INVALID_PERIOD_ACTUAL"),
    actualUnits: decimalText(payload.actual_units, "INVALID_PERIOD_ACTUAL"),
    actualCost: decimalText(payload.actual_cost, "INVALID_PERIOD_ACTUAL"),
    unit: optionalText(payload.unit, "INVALID_PERIOD_ACTUAL"),
    currency: optionalText(payload.currency, "INVALID_PERIOD_ACTUAL"),
    note: optionalText(payload.note, "INVALID_PERIOD_ACTUAL"),
  };
}

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function parsePeriodActualList(value: unknown): StoredPeriodActual[] {
  if (
    !isRecord(value) ||
    value.contract_version !== PERIOD_ACTUAL_API_VERSION ||
    !Array.isArray(value.activity_period_actuals)
  ) {
    throw new Error("INVALID_PERIOD_ACTUAL_LIST");
  }
  return value.activity_period_actuals.map((item) => parsePeriodActual(item));
}

export function periodActualsPath(context: ProjectContext, filters: PeriodActualFilters = {}): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/activity-period-actuals`;
  const params = new URLSearchParams();
  if (filters.activityId) params.set("activity_id", filters.activityId);
  if (filters.periodId) params.set("period_id", filters.periodId);
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}

export async function loadPeriodActuals(
  transport: ApiTransport,
  context: ProjectContext,
  filters: PeriodActualFilters = {},
): Promise<ApiResult<StoredPeriodActual[]>> {
  const result = await transport.get<unknown>(periodActualsPath(context, filters), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parsePeriodActualList(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_PERIOD_ACTUAL_LIST");
  }
}

/** Deterministic identity: one stored actual per activity and financial period. */
export function periodActualId(activityId: string, periodId: string): string {
  const activity = activityId.trim();
  const period = periodId.trim();
  if (!activity || !period) throw new Error("PERIOD_ACTUAL_SCOPE_REQUIRED");
  return `SPP-${activity}-${period}`;
}

function decimalInput(value: string, code: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!DECIMAL.test(trimmed)) throw new Error(code);
  return trimmed;
}

function optionalInput(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function buildPeriodActualPayload(input: PeriodActualInput): Record<string, unknown> {
  const activity = input.activityId.trim();
  const period = input.periodId.trim();
  if (!activity || !period) throw new Error("PERIOD_ACTUAL_SCOPE_REQUIRED");
  const units = decimalInput(input.actualUnits, "INVALID_ACTUAL_UNITS");
  const cost = decimalInput(input.actualCost, "INVALID_ACTUAL_COST");
  if (units === null && cost === null) throw new Error("PERIOD_ACTUAL_VALUE_REQUIRED");
  return {
    contract_version: PERIOD_ACTUAL_API_VERSION,
    actual_id: periodActualId(activity, period),
    activity_id: activity,
    period_id: period,
    actual_units: units,
    actual_cost: cost,
    unit: optionalInput(input.unit),
    currency: optionalInput(input.currency),
    note: optionalInput(input.note),
  };
}

export async function savePeriodActual(
  transport: ApiTransport,
  context: ProjectContext,
  input: PeriodActualInput,
): Promise<ApiResult<StoredPeriodActual>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildPeriodActualPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_PERIOD_ACTUAL_INPUT");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    periodActualsPath(context),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parsePeriodActual(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_PERIOD_ACTUAL");
  }
}

export function periodActualErrorNotice(code: string, locale: string): string {
  const prefix = text(locale, "Period actual was not stored", "واقعی دوره ذخیره نشد");
  switch (code) {
    case "PERIOD_ACTUAL_SCOPE_REQUIRED":
      return text(
        locale,
        "Select an activity and a financial period before storing a period actual.",
        "پیش از ذخیرهٔ واقعی دوره، یک فعالیت و دورهٔ مالی انتخاب کنید.",
      );
    case "PERIOD_ACTUAL_VALUE_REQUIRED":
      return text(
        locale,
        "Enter actual units or actual cost.",
        "واحد واقعی یا هزینهٔ واقعی را وارد کنید.",
      );
    case "INVALID_ACTUAL_UNITS":
      return text(locale, "Actual units must be a decimal number.", "واحد واقعی باید عدد اعشاری باشد.");
    case "INVALID_ACTUAL_COST":
      return text(locale, "Actual cost must be a decimal number.", "هزینهٔ واقعی باید عدد اعشاری باشد.");
    case "IMMUTABLE_ACTIVITY_PERIOD_ACTUAL":
      return text(
        locale,
        "A stored actual already exists for this activity and period and cannot be overwritten. Stored period actuals are immutable and no correction route exists.",
        "برای این فعالیت و دوره یک واقعی ذخیره‌شده وجود دارد و قابل بازنویسی نیست. واقعی‌های دوره تغییرناپذیرند و مسیر اصلاحی وجود ندارد.",
      );
    case "P6_ACTIVITY_PERIOD_ACTUAL_ACTIVITY_NOT_FOUND":
      return text(
        locale,
        "The selected activity no longer exists in this project.",
        "فعالیت انتخاب‌شده دیگر در این پروژه وجود ندارد.",
      );
    case "P6_ACTIVITY_PERIOD_ACTUAL_PERIOD_NOT_FOUND":
      return text(
        locale,
        "The selected financial period no longer exists in this project.",
        "دورهٔ مالی انتخاب‌شده دیگر در این پروژه وجود ندارد.",
      );
    case "P6_ACTIVITY_PERIOD_ACTUAL_INSERT_FAILED":
      return text(
        locale,
        "The stored actual could not be read back after the write.",
        "خواندن واقعی ذخیره‌شده پس از نوشتن ممکن نشد.",
      );
    case "REVISION_CONFLICT":
      return text(
        locale,
        "The project revision changed. Reload the page and try again.",
        "ویرایش پروژه تغییر کرده است. صفحه را دوباره بارگذاری کنید.",
      );
    case "AUTHORIZATION_DENIED":
    case "AUTHORIZATION_PERMISSION_DENIED":
    case "P6_ACTIVITY_PERIOD_ACTUAL_WRITE_NOT_AUTHORIZED":
      return text(
        locale,
        "You do not have permission to store period actuals.",
        "شما اجازهٔ ذخیرهٔ واقعی‌های دوره را ندارید.",
      );
    case "P6_ACTIVITY_PERIOD_ACTUAL_REQUEST_INVALID":
      return text(
        locale,
        "The service rejected the period actual values.",
        "سرویس مقادیر واقعی دوره را نپذیرفت.",
      );
    default:
      return `${prefix} (${code})`;
  }
}
