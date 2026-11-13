import assert from "node:assert/strict";
import test from "node:test";

import {
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
  readCookieValue,
  withCsrfHeader,
} from "./csrf.js";

test("reads a single cookie value and decodes it", () => {
  assert.equal(
    readCookieValue(CSRF_COOKIE_NAME, "other=1; cubi_csrf=a%2Bb%2Fc%3D; tail=2"),
    "a+b/c=",
  );
  assert.equal(readCookieValue(CSRF_COOKIE_NAME, "cubi_csrf="), "");
  assert.equal(readCookieValue(CSRF_COOKIE_NAME, "cp_session=abc"), null);
  assert.equal(readCookieValue(CSRF_COOKIE_NAME, ""), null);
});

test("adds the CSRF header to mutating requests", () => {
  const cookie = "cp_session=secret; cubi_csrf=signed-value";
  for (const method of ["POST", "PUT", "PATCH", "DELETE", "post"]) {
    const headers = withCsrfHeader(method, {}, cookie);
    assert.equal(headers[CSRF_HEADER_NAME], "signed-value", method);
  }
});

test("leaves safe and unauthenticated requests untouched", () => {
  assert.deepEqual(withCsrfHeader("GET", {}, "cubi_csrf=signed-value"), {});
  assert.deepEqual(withCsrfHeader("HEAD", { Accept: "text/html" }, "cubi_csrf=x"), {
    Accept: "text/html",
  });
  assert.deepEqual(withCsrfHeader("POST", {}, "cp_session=secret"), {});
});

test("does not overwrite an explicitly supplied CSRF header", () => {
  assert.deepEqual(
    withCsrfHeader("POST", { "x-csrf-token": "explicit" }, "cubi_csrf=cookie-value"),
    { "x-csrf-token": "explicit" },
  );
});

test("preserves existing headers when adding the token", () => {
  const headers = withCsrfHeader(
    "PATCH",
    { "Content-Type": "application/json" },
    "cubi_csrf=token-value",
  );
  assert.deepEqual(headers, {
    "Content-Type": "application/json",
    [CSRF_HEADER_NAME]: "token-value",
  });
});
