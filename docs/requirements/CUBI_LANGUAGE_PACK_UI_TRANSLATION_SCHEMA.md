# CUBI UI Language-Pack Translation Resource v1

A language pack that declares `capabilities.ui: true` must provide the manifest-declared `resources.translation` resource as UTF-8 JSON with this shape:

```json
{
  "schema_version": "cubi-ui-translations.v1",
  "display_name": "Deutsch",
  "direction": "ltr",
  "translations": {
    "workspace.project": "Projekt",
    "navigation.schedule": "Zeitplan",
    "navigation.schedule.submenu.0": "Aktivitätenraster",
    "column.activity_name": "Aktivitätsname",
    "landing.title": "..."
  }
}
```

## Contract

- `schema_version` must equal `cubi-ui-translations.v1`.
- `display_name` is the language name shown in the language switcher.
- `direction` must be `ltr` or `rtl`; it controls document and workspace direction independently of the project calendar.
- The language-pack manifest `language_tag` is the registered locale identifier (for example `de-DE` or `ar`).
- `translations` maps stable, language-neutral IDs to non-empty strings. Do not use translated text as the key.
- Unknown IDs use the declared English fallback until translated; missing/invalid required resource data rejects the UI language-pack update before activation.
- UI resource parsing is performed before activation; registration occurs only after the language-pack runtime successfully verifies and activates the pack.
- UI strings and translation resources must not contain hidden product behavior, executable code or HTML. Values are rendered as text and escaped by the view layer.
- Translation coverage must be measured separately; a structurally valid pack is not proof that every UI surface is translated.

## Initial resource namespaces

- `workspace.<label-id>`: workspace panels, controls, field chooser and status text.
- `navigation.<menu-key>`, `navigation.<menu-key>.status`, `navigation.<menu-key>.submenu.<index>`: menu labels and submenus.
- `column.<field-id>`: default activity grid columns.
- `shell.<label-id>`: authenticated web shell.
- `bootstrap.<label-id>`: project bootstrap and initialization flow.
- `landing.<label-id>`: public landing page copy, including indexed feature and footer fields.

The registry and schema are extensible; adding a language must not require adding a language-specific conditional to UI source code.
