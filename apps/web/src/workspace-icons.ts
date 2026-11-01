/**
 * One small icon family for the desktop chrome. Icons are stroked geometry on a
 * 16×16 grid so they inherit text colour, stay crisp at 100–125 % zoom and do
 * not require an external icon font or copyrighted artwork.
 */
const PATHS: Record<string, string> = {
  file: "M4 2h5l3 3v9H4z M9 2v3h3",
  settings:
    "M8 6.2a1.8 1.8 0 1 0 0 3.6 1.8 1.8 0 0 0 0-3.6z M8 2v1.4 M8 12.6V14 M2 8h1.4 M12.6 8H14 M3.8 3.8l1 1 M11.2 11.2l1 1 M12.2 3.8l-1 1 M4.8 11.2l-1 1",
  tree: "M3 3h4v3H3z M9 8h4v3H9z M9 12h4v3H9z M5 6v8h2 M7 9.5h2 M7 13.5h2",
  activity: "M2 9h3V6h4v5h5",
  edit: "M3 13l1-3 7-7 2 2-7 7z M10 4l2 2",
  find: "M7 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M10 10l3 3",
  group: "M2 4h12 M4 8h8 M6 12h4",
  undo: "M5 5H2V2 M2 5a6 6 0 1 1 1.5 6",
  redo: "M11 5h3V2 M14 5a6 6 0 1 0-1.5 6",
  columns: "M2 3h12v10H2z M6 3v10 M10 3v10",
  calendar: "M2 4h12v10H2z M2 7h12 M5 2v3 M11 2v3",
  clock: "M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2z M8 4.5V8l2.5 1.5",
  filter: "M2 3h12l-4.5 5v5l-3 1V8z",
  sort: "M4 3v10 M2 11l2 2 2-2 M9 4h5 M9 8h4 M9 12h3",
  bars: "M2 12h3V7h3v5h3V4h3",
  table: "M2 3h12v10H2z M2 6h12 M2 9h12 M6 3v10",
  print: "M4 7V2h8v5 M2 7h12v6h-2v-3H4v3H2z",
  help: "M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2z M6.3 6a1.8 1.8 0 1 1 2.2 2.4c-.4.2-.5.6-.5 1.1 M8 11.6v.2",
  close: "M4 4l8 8 M12 4l-8 8",
  plus: "M8 3v10 M3 8h10",
  check: "M3 8.5l3 3 7-7",
  left: "M10 3L5 8l5 5",
  right: "M6 3l5 5-5 5",
  link: "M6 10l4-4 M5 7l-2 2a2.1 2.1 0 0 0 3 3l2-2 M11 9l2-2a2.1 2.1 0 0 0-3-3L8 6",
  network: "M2 2h4v3H2z M10 2h4v3h-4z M6 11h4v3H6z M4 5v3h8V5 M8 8v3",
  resource: "M6 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M2 14c0-2.2 1.8-4 4-4s4 1.8 4 4 M11 5.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M11 8c1.7 0 3 1.3 3 3",
  book: "M3 3h4a2 2 0 0 1 2 2v8a2 2 0 0 0-2-2H3z M13 3H9a2 2 0 0 0-2 2v8a2 2 0 0 1 2-2h4z",
  warning: "M8 2l6 11H2z M8 6v4 M8 11.5v.2",
  folder: "M2 4h5l1.5 2H14v7H2z",
  portfolio: "M2 3h5v4H2z M2 9h5v4H2z M9 3h5v4H9z M9 9h5v4H9z",
  wbs: "M2 3h5v3H2z M9 3h5v3H9z M6 9h4v3H6z M5 6v5h3 M9 6v5H8",
  money: "M8 3a5 5 0 1 0 0 10A5 5 0 0 0 8 3z M6 6h3a1.5 1.5 0 0 1 0 3H7 M6 9h4 M8 5v6",
  forms: "M3 2h10v12H3z M5 5h6 M5 8h6 M5 11h4",
  progress: "M2 13h12 M4 11l3-3 2 2 4-5",
  comment: "M3 3h10v7H8l-3 3v-3H3z",
  tools: "M3 13l5-5 M9 3l4 4-2 2-4-4z M10 9l3 3-1 1z",
  assignment: "M2 6h7 M6 3l3 3-3 3 M11 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M8 14c0-1.7 1.3-3 3-3s3 1.3 3 3",
  save: "M3 2h8l2 2v10H3z M5 2v5h6V2 M5 14v-4h6v4",
  open: "M2 4h5l1.5 2H14l-2 7H3z",
  compare: "M4 2v12 M12 2v12 M7 5h4 M7 8h4 M7 11h4",
  baseline: "M2 8h12 M4 4v8 M8 5.5v5 M12 6.5v3",
  fullscreen: "M2 6V2h4 M10 2h4v4 M14 10v4h-4 M6 14H2v-4",
  exitfullscreen: "M6 2v4H2 M14 6h-4V2 M10 14v-4h4 M2 10h4v4",
  refresh: "M13 8a5 5 0 1 1-1.5-3.5 M13 2v3h-3",
  home: "M2 7l6-5 6 5 M4 6v7h8V6 M6.5 13V9h3v4",
  language:
    "M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2z M2 8h12 M8 2c1.8 1.7 2.7 3.7 2.7 6S9.8 12.3 8 14C6.2 12.3 5.3 10.3 5.3 8S6.2 3.7 8 2z",
};

export function workspaceIcon(name: string): string {
  const path = PATHS[name] ?? PATHS.activity;
  return `<svg class="cp-icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"><path d="${path}"></path></svg>`;
}
