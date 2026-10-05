export type DesktopV1TrialState = "active" | "expired";
export type DesktopV1InstallationCheck = "allowed" | "expired";

export const DEFAULT_DESKTOP_V1_TRIAL_DAYS = 60;

export type DesktopV1TrialConfig = Readonly<{
  release_date: string;
  installation_cutoff_date: string;
  trial_days?: number;
}>;

export type DesktopV1TrialRecord = Readonly<{
  first_installation_at: string;
}>;

export interface DesktopV1TrialStore {
  read(): DesktopV1TrialRecord | null;
  write(record: DesktopV1TrialRecord): void;
}

export interface DesktopV1TrialClock {
  now(): Date;
}

function parseDate(value: string): Date {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("INVALID_TRIAL_DATE");
  }
  return parsed;
}

function addCalendarDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result;
}

export function installationStatus(
  config: DesktopV1TrialConfig,
  now: Date,
): DesktopV1InstallationCheck {
  const releaseDate = parseDate(config.release_date);
  const cutoff = parseDate(config.installation_cutoff_date);
  if (cutoff.getTime() < releaseDate.getTime()) {
    throw new Error("INVALID_INSTALLATION_WINDOW");
  }
  return now.getTime() <= cutoff.getTime() ? "allowed" : "expired";
}

export class InMemoryDesktopV1TrialStore implements DesktopV1TrialStore {
  private record: DesktopV1TrialRecord | null = null;

  read(): DesktopV1TrialRecord | null {
    return this.record;
  }

  write(record: DesktopV1TrialRecord): void {
    this.record = Object.freeze({ ...record });
  }
}

export class DesktopV1LocalTrial {
  private readonly trialDays: number;

  constructor(
    private readonly config: DesktopV1TrialConfig,
    private readonly store: DesktopV1TrialStore,
    private readonly clock: DesktopV1TrialClock,
  ) {
    this.trialDays = config.trial_days ?? DEFAULT_DESKTOP_V1_TRIAL_DAYS;
    if (!Number.isInteger(this.trialDays) || this.trialDays <= 0) {
      throw new Error("INVALID_TRIAL_DAYS");
    }
    parseDate(config.release_date);
    parseDate(config.installation_cutoff_date);
  }

  ensureInstallationAllowed(): void {
    if (installationStatus(this.config, this.clock.now()) === "expired") {
      throw new Error("DESKTOP_V1_INSTALLATION_EXPIRED");
    }
  }

  ensureInitialized(): DesktopV1TrialRecord {
    this.ensureInstallationAllowed();
    const existing = this.store.read();
    if (existing) {
      parseDate(existing.first_installation_at);
      return existing;
    }

    const firstInstallation = this.clock.now().toISOString();
    const record = Object.freeze({ first_installation_at: firstInstallation });
    this.store.write(record);
    return record;
  }

  state(): DesktopV1TrialState {
    const record = this.ensureInitialized();
    const firstInstallation = parseDate(record.first_installation_at);
    const expiresAt = addCalendarDays(firstInstallation, this.trialDays);
    return this.clock.now().getTime() <= expiresAt.getTime() ? "active" : "expired";
  }

  isOnlineActivationEnabled(): false {
    return false;
  }

  expiresAt(): Date {
    const record = this.ensureInitialized();
    return addCalendarDays(parseDate(record.first_installation_at), this.trialDays);
  }
}
