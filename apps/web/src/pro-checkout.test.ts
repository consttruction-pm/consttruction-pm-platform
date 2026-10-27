import assert from "node:assert/strict";
import test from "node:test";
import {
  PRO_MONTHLY_CURRENCY,
  PRO_MONTHLY_PLAN,
  PRO_MONTHLY_UNIT_PRICE_MINOR,
  calculateProMonthlyTotal,
  formatProAmount,
  isValidProMonthQuantity,
} from "./pro-checkout.js";

test("Pro checkout price is one monthly unit and the only paid plan", () => {
  assert.equal(PRO_MONTHLY_UNIT_PRICE_MINOR, 999);
  assert.equal(PRO_MONTHLY_CURRENCY, "USD");
  assert.equal(PRO_MONTHLY_PLAN, "pro_monthly");
});

test("monthly quantity totals are exact for one, five and twelve units", () => {
  assert.equal(calculateProMonthlyTotal(1), 999);
  assert.equal(calculateProMonthlyTotal(5), 4995);
  assert.equal(calculateProMonthlyTotal(12), 11988);
});

test("checkout quantity accepts only safe positive whole numbers", () => {
  for (const value of [1, 5, 12, 120]) assert.equal(isValidProMonthQuantity(value), true);
  for (const value of [0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, Number.MAX_SAFE_INTEGER]) {
    assert.equal(isValidProMonthQuantity(value), false, String(value));
  }
  assert.throws(() => calculateProMonthlyTotal(0), /INVALID_MONTH_QUANTITY/);
  assert.throws(() => calculateProMonthlyTotal(1.2), /INVALID_MONTH_QUANTITY/);
});

test("checkout amount formatting is locale-aware", () => {
  assert.equal(formatProAmount(999, "en"), "$9.99");
  assert.match(formatProAmount(4995, "en"), /49\.95/);
  assert.ok(formatProAmount(11988, "fa").length > 0);
});
