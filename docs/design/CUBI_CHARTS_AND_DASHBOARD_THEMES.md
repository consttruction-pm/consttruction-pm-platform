# Cubi Chart Catalog & Dashboard Theme Reference

**Status:** Design reference / inspiration baseline  
**Version:** 1.0  
**Date:** 2026-11-19  
**Companion visual document:** `Cubi_Chart_and_Dashboard_Design_Reference_FA.docx` (illustrative chart thumbnails and dashboard-theme mockups)

## Purpose

Provide a shared visual and product-design reference for Cubi dashboards, chart selection, and user-selectable dashboard/chart themes. This document records design intent; it does **not** claim that the listed UI features have already been implemented.

## Chart catalog

| Chart | Primary use in Cubi | Common tools / reference products |
|---|---|---|
| Line / Area | Time-series progress, cost, productivity, variance | Power BI, Tableau, Excel, Plotly, Apache ECharts |
| Bar / Lollipop | Compare WBS packages, contractors, activities, KPIs | Power BI, Tableau, Excel, ECharts |
| Waterfall | Explain movement from baseline budget to forecast | Power BI, Excel, Tableau, Plotly, Highcharts |
| S-Curve | Planned vs actual cumulative progress; forecast when available | Primavera P6 reporting/exports, Power BI, Excel, Plotly |
| Gantt | Activities, durations, relationships, milestones, baselines | Primavera P6, Microsoft Project, Asta Powerproject, Highcharts |
| Resource Histogram | Resource demand and over-allocation by period | Primavera P6, Microsoft Project, Excel, Power BI |
| Heatmap | Risk, variance, status intensity across two dimensions | Power BI, Tableau, Plotly, ECharts |
| Radar / Spider | Compare a small set of performance dimensions | Excel, Power BI, Tableau, ECharts |
| Treemap | Hierarchical cost/resource/WBS composition | Power BI, Tableau, Plotly, ECharts |
| Sankey | Flow of budget, labor, materials, or work volume | Tableau, Plotly, ECharts, Flourish |
| Gauge / KPI | One metric against a target or threshold; not a trend substitute | Power BI, Tableau, ECharts, Highcharts |
| Milestone Trend Analysis | Forecast-date movement across schedule updates | Primavera reports/exports, Excel, Power BI, custom UI |

## Selectable dashboard themes

1. **Executive Dark** — navy/charcoal canvas, layered dark cards, restrained cyan/blue accent; suitable for control-room and executive displays.
2. **Clean Light** — bright neutral canvas, white cards, readable typography and subtle grid; suitable for daily work and formal reporting.
3. **Glass / Gradient** — restrained translucent surfaces and gradients; decorative treatment must never reduce data legibility.
4. **Industrial Neutral** — light gray/white surfaces with amber/orange accents; suitable for engineering and site operations.

The theme system should support custom user themes and light/dark variants.

## User customization requirements

- Select the overall dashboard theme independently from each chart's visual theme.
- Configure chart palette, line width, markers, transparency, typography, grid, legend, and labels.
- Add, remove, resize, and rearrange dashboard widgets; save personal layouts and share templates.
- Provide role-oriented starter layouts for Project Manager, Project Controls Manager, Site Manager, Executive, and Analyst.
- Support desktop, tablet, and mobile responsive layouts.
- Display units, reporting period, data source, last refresh time, and KPI definition/context.
- Support drill-down, filtering, and cross-filtering where meaningful.
- Never rely on color alone to communicate status; include text, icons, or patterns and preserve accessible contrast.

## Technical direction (proposal, subject to repository architecture review)

- Evaluate **Apache ECharts** as the primary web charting engine because of its broad chart catalog, customization, and theme support.
- Evaluate **Plotly** as a complementary option for specialist analytical/statistical visualizations.
- Use a purpose-built or specialist Gantt/scheduling component for schedule views.
- Confirm compatibility with the current Cubi stack, bundle/performance constraints, licensing, accessibility, and test strategy before selecting dependencies.

## Data correctness and project-controls safeguards

- Presentation components must not own or redefine schedule or cost calculations.
- Chart series must be sourced from validated domain outputs and carry explicit units, dates, baseline/version context, and missing-data semantics.
- Planned, actual, forecast, and baseline series must remain distinguishable.
- CPM, float, critical path, earned value, resource, and cost calculations must be validated independently against their authoritative business rules and relevant Primavera documentation.
- Never fabricate missing observations or imply that illustrative sample values are measured project data.

## Initial acceptance criteria

- [ ] The user can choose a dashboard theme from the theme catalog.
- [ ] The user can choose a chart style independently of the dashboard theme.
- [ ] At least the 12 chart families listed above are represented in the product roadmap; availability must be verified chart by chart.
- [ ] Users can save and restore dashboard layouts.
- [ ] Theme changes preserve chart semantics, units, thresholds, and accessibility.
- [ ] Responsive behavior is verified at desktop, tablet, and mobile breakpoints.
- [ ] Chart data provenance, reporting period, and refresh timestamp are visible.
- [ ] Schedule and cost calculations are tested separately from visual rendering.

## Reference galleries

- Apache ECharts examples: https://echarts.apache.org/examples/en/index.html
- Apache ECharts features: https://echarts.apache.org/en/feature.html
- Plotly chart gallery: https://plotly.com/graphs/
- Plotly chart-type guide: https://plotly.com/blog/types-of-charts/
- Highcharts demos: https://www.highcharts.com/demo
- Microsoft Office chart types: https://support.microsoft.com/en-us/excel/available-chart-types-in-office
- Dribbble project-management dashboard inspiration: https://dribbble.com/search/project-management-dashboard
- Dribbble dashboard-theme inspiration: https://dribbble.com/search/dashboard-theme

## Design note

The companion DOCX contains illustrative images for each chart family and four dashboard-theme mockups. Those images are original explanatory mockups, not screenshots copied from the named products. External galleries above are the places to inspect real product examples and compare interaction patterns.
