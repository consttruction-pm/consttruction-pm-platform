import { describe, expect, it } from "node:test";
import {
  DesktopV1LocalTrial,
  InMemoryDesktopV1TrialStore,
  installationStatus,
  type DesktopV1TrialClock,
} from "./trial-policy.js";

class FixedClock implements DesktopV1TrialClock {
  constructor(private current: Date) {}

  now(): Date {
    return new Date(this.current);
  }

  set(value: string): void {
    this.current = new Date(value);
  }
}

const config = {
  release_date: "2026-10-05T00:00:00.000Z",
  installation_cutoff_date: "2027-10-05T00:00:00.000Z",
};

describe("Desktop V1 local trial", () => {
  it("allows installation through the one-year cutoff", () => {
    expect(
      installationStatus(config, new Date("2027-10-05T00:00:00.000Z")),
    ).toBe("allowed");
    expect(
      installationStatus(config, new Date("2027-10-05T00:00:01.000Z")),
    ).toBe("expired");
  });

  it("initializes once and keeps the original first-install date", () => {
    const clock = new FixedClock(new Date("2026-10-05T10:00:00.000Z"));
    const store = new InMemoryDesktopV1TrialStore();
    const trial = new DesktopV1LocalTrial(config, store, clock);

    expect(trial.ensureInitialized().first_installation_at).toBe(
      "2026-10-05T10:00:00.000Z",
    );

    clock.set("2026-10-20T10:00:00.000Z");
    expect(trial.ensureInitialized().first_installation_at).toBe(
      "2026-10-05T10:00:00.000Z",
    );
  });

  it("keeps all V1 features active for 60 calendar days", () => {
    const clock = new FixedClock(new Date("2026-10-05T10:00:00.000Z"));
    const trial = new DesktopV1LocalTrial(
      config,
      new InMemoryDesktopV1TrialStore(),
      clock,
    );

    trial.ensureInitialized();
    clock.set("2026-12-04T10:00:00.000Z");
    expect(trial.state()).toBe("active");

    clock.set("2026-12-05T10:00:00.000Z");
    expect(trial.state()).toBe("active");

    clock.set("2026-12-06T10:00:00.000Z");
    expect(trial.state()).toBe("expired");
  });

  it("does not enable online activation", () => {
    const clock = new FixedClock(new Date("2026-10-05T10:00:00.000Z"));
    const trial = new DesktopV1LocalTrial(
      config,
      new InMemoryDesktopV1TrialStore(),
      clock,
    );
    expect(trial.isOnlineActivationEnabled()).toBe(false);
  });

  it("rejects normal installation after the one-year cutoff", () => {
    const clock = new FixedClock(new Date("2027-10-06T00:00:00.000Z"));
    const trial = new DesktopV1LocalTrial(
      config,
      new InMemoryDesktopV1TrialStore(),
      clock,
    );
    expect(() => trial.ensureInitialized()).toThrow(
      "DESKTOP_V1_INSTALLATION_EXPIRED",
    );
  });
});
