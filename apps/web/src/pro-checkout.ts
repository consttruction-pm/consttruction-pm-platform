/**
 * CUBI Pro monthly checkout interaction.
 *
 * This module calculates a transparent estimate for the UI and requests a
 * server-authoritative checkout session. It never claims payment succeeded
 * locally and never grants/extends an entitlement in the browser.
 */
export const PRO_MONTHLY_UNIT_PRICE_MINOR = 999;
export const PRO_MONTHLY_CURRENCY = "USD";
export const PRO_MONTHLY_PLAN = "pro_monthly" as const;

export function calculateProMonthlyTotal(monthQuantity: number): number {
  if (!Number.isSafeInteger(monthQuantity) || monthQuantity < 1) {
    throw new RangeError("INVALID_MONTH_QUANTITY");
  }
  const total = PRO_MONTHLY_UNIT_PRICE_MINOR * monthQuantity;
  if (!Number.isSafeInteger(total)) throw new RangeError("MONTH_QUANTITY_TOTAL_OUT_OF_RANGE");
  return total;
}

export function isValidProMonthQuantity(value: number): boolean {
  try {
    calculateProMonthlyTotal(value);
    return true;
  } catch {
    return false;
  }
}

export function formatProAmount(amountMinor: number, locale = "en"): string {
  return new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US", {
    style: "currency",
    currency: PRO_MONTHLY_CURRENCY,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amountMinor / 100);
}

function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  }
  // This fallback is for local previews only; the server must still enforce
  // idempotency with a payment-provider event/transaction identity.
  return `cubi-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function siteBasePath(): string {
  const configured = document.querySelector<HTMLMetaElement>('meta[name="cubi-base-url"]')?.content.trim();
  if (!configured || configured.includes("__CUBI_BASE_URL__")) return "";
  try {
    return new URL(configured).pathname.replace(/\/+$/, "");
  } catch {
    return "";
  }
}

function copyFor(locale: string) {
  return locale === "fa"
    ? {
        invalid: "تعداد ماه باید یک عدد صحیح مثبت باشد.",
        starting: "در حال اتصال به درگاه پرداخت…",
        notConfigured: "درگاه پرداخت آنلاین هنوز به این سایت متصل نشده است؛ هیچ مبلغی دریافت نشده است.",
        failed: "شروع پرداخت موفق نبود. لطفاً دوباره تلاش کنید.",
        network: "ارتباط با سرویس پرداخت برقرار نشد؛ هیچ پرداختی انجام نشده است.",
        checkout: "ادامه پرداخت",
      }
    : {
        invalid: "Enter a positive whole number of months.",
        starting: "Connecting to checkout…",
        notConfigured: "Online payment is not connected to this site yet. No charge has been made.",
        failed: "Checkout could not be started. Please try again.",
        network: "The payment service could not be reached. No payment was made.",
        checkout: "Continue to checkout",
      };
}

export function mountProCheckout(): void {
  if (typeof document === "undefined" || typeof window === "undefined") return;
  const form = document.querySelector<HTMLFormElement>("#pro-checkout-form");
  const quantityInput = document.querySelector<HTMLInputElement>("#month-quantity");
  const totalOutput = document.querySelector<HTMLElement>("#checkout-total");
  const notice = document.querySelector<HTMLElement>("#checkout-notice");
  const submit = document.querySelector<HTMLButtonElement>("#checkout-submit");
  const unitPrice = document.querySelector<HTMLElement>("#checkout-unit-price");
  const decrease = document.querySelector<HTMLButtonElement>("#month-decrease");
  const increase = document.querySelector<HTMLButtonElement>("#month-increase");
  const quickQuantities = [...document.querySelectorAll<HTMLButtonElement>("[data-month-quantity]")];
  if (!form || !quantityInput || !totalOutput || !notice || !submit || !unitPrice) return;

  const locale = document.documentElement.lang.toLowerCase().startsWith("fa") ? "fa" : "en";
  const copy = copyFor(locale);
  const updateSummary = (): boolean => {
    const quantity = quantityInput.valueAsNumber;
    const valid = isValidProMonthQuantity(quantity);
    quantityInput.setAttribute("aria-invalid", valid ? "false" : "true");
    submit.disabled = !valid;
    if (valid) {
      totalOutput.textContent = formatProAmount(calculateProMonthlyTotal(quantity), locale);
      notice.textContent = "";
      notice.dataset.state = "idle";
      return true;
    }
    totalOutput.textContent = "—";
    notice.textContent = copy.invalid;
    notice.dataset.state = "error";
    return false;
  };

  unitPrice.textContent = formatProAmount(PRO_MONTHLY_UNIT_PRICE_MINOR, locale);
  quantityInput.addEventListener("input", updateSummary);
  decrease?.addEventListener("click", () => {
    const current = isValidProMonthQuantity(quantityInput.valueAsNumber) ? quantityInput.valueAsNumber : 1;
    quantityInput.value = String(Math.max(1, current - 1));
    updateSummary();
  });
  increase?.addEventListener("click", () => {
    const current = isValidProMonthQuantity(quantityInput.valueAsNumber) ? quantityInput.valueAsNumber : 0;
    quantityInput.value = String(current + 1);
    updateSummary();
  });
  for (const button of quickQuantities) {
    button.addEventListener("click", () => {
      const quantity = Number(button.dataset.monthQuantity);
      quantityInput.value = String(quantity);
      updateSummary();
      quantityInput.focus();
    });
  }
  updateSummary();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!updateSummary()) return;

    const monthQuantity = quantityInput.valueAsNumber;
    const originalLabel = submit.textContent || copy.checkout;
    submit.disabled = true;
    submit.textContent = copy.checkout;
    notice.textContent = copy.starting;
    notice.dataset.state = "pending";

    try {
      const response = await fetch(new URL(`${siteBasePath()}/api/billing/checkout`, window.location.origin), {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": createIdempotencyKey(),
        },
        body: JSON.stringify({
          plan: PRO_MONTHLY_PLAN,
          month_quantity: monthQuantity,
          return_url: window.location.href,
        }),
      });
      const payload: unknown = await response.json().catch(() => null);
      const record = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
      const checkoutUrl = typeof record.checkout_url === "string" ? record.checkout_url : "";
      if (response.ok && checkoutUrl) {
        const target = new URL(checkoutUrl, window.location.origin);
        const localPreview = target.hostname === "localhost" || target.hostname === "127.0.0.1";
        if (target.protocol !== "https:" && !(localPreview && target.protocol === "http:")) {
          throw new Error("UNSAFE_CHECKOUT_URL");
        }
        window.location.assign(target.href);
        return;
      }

      const notConfigured = response.status === 404 || response.status === 501 ||
        response.status === 503 || record.code === "PAYMENT_PROVIDER_NOT_CONFIGURED";
      notice.textContent = notConfigured ? copy.notConfigured : copy.failed;
      notice.dataset.state = "error";
    } catch (error) {
      notice.textContent = error instanceof Error && error.message === "UNSAFE_CHECKOUT_URL"
        ? copy.failed : copy.network;
      notice.dataset.state = "error";
    } finally {
      if (document.contains(form)) {
        submit.disabled = !isValidProMonthQuantity(quantityInput.valueAsNumber);
        submit.textContent = originalLabel;
      }
    }
  });
}

if (typeof document !== "undefined") mountProCheckout();
