# ACT-005 — Table font, colour and row height (2026-11-12)

- Contract: `cubi-activity-table-font-v26.v1`
- Suite: `apps/web/e2e/activity-table-font-v26.mjs`
- Tested code: `dbe361aeed4e4e5feb2b48bcd44b8d7db6579db8` (`dbe361ae`)
- Fixture: local-full-stack preview, `preview-rps-01`, 14 activity rows
- Help source: [Change Activity Table font, color, and row height](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_table_font_color_and_row_height.htm)

| # | Scenario | Cell | Result |
|---|---|---|---|
| 01 | The dialog writes Cairo 14 px, `#102030` text, `#fdf6e3` background, fixed 26 px rows and hides type icons; the grid and cells reflect every value and the layout publishes the table presentation | 1366×768 en LTR | PASS |
| 02 | The saved presentation survives a full reload (font, colours, 26 px rows) | 1366×768 en LTR | PASS |
| 03 | `Reset to defaults` restores 11 px Tahoma, `#000000`/`#ffffff`, fixed 18 px rows and icons, publishes the reset and survives a reload | 1366×768 en LTR | PASS |
| 04 | The Persian dialog (`قلم و ردیف جدول`) shows the Persian reset label and both the dialog and the table render RTL at 1280×720 with no overflow | 1280×720 fa RTL | PASS |
| 05 | The reset table presentation fits 1920×1080 with no horizontal overflow | 1920×1080 en LTR | PASS |

Machine-readable report: `activity-table-font-v26.json` — 5/5 scenarios pass, `testedCodeSha` = `gitHead` = `dbe361aeed4e4e5feb2b48bcd44b8d7db6579db8`, zero exceptions, zero console errors, zero API failures. Screenshots: `01`–`05`.

The suite's first run exposed a real defect: an unchecked `Show activity type icons` was absent from `FormData`, so the saved `true` survived and icons could never be turned off. The table fieldset now carries a marker input and both table flags are read as booleans; a regression test covers the reset and the cleared checkbox.
