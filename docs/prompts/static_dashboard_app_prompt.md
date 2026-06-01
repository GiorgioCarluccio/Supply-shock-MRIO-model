# Codex / Claude Code Prompt — Build Static MVP Dashboard App

You are working on the GitHub repository:

```text
Supply-shock-MRIO-model
```

The project has already implemented the analytical pipeline. The current objective is to build a **static demonstrative dashboard application**.

This is not a live impact calculator. The app must read precomputed outputs and present them in a clean, informative, branded dashboard.

Do **not** build a user-triggered live simulation engine in the frontend.

Do **not** run the IO propagation model from the browser.

The frontend should be a polished static dashboard over generated files.

---

## 1. Project context

The project estimates climate-related physical risk impacts on Italian provincial economic sectors.

The model estimates:

```text
business interruption impacts
```

not physical asset damage.

The analytical engine uses:

- provincial Italian SAM / IO economic network;
- hazard exposure data;
- calibrated supply and demand shocks;
- IO propagation model;
- precomputed scenario results.

The dashboard must let users explore:

1. direct hazard exposure;
2. calibrated shocks;
3. direct and indirect economic impact;
4. sectoral impacts;
5. interprovincial and intersectoral flow changes;
6. methodology.

The app is for **demonstration and communication**. It should be visually strong, explanatory, and easy to interrogate.

---

## 2. Static dashboard only

The app must use precomputed files.

Expected existing data folders include:

```text
data/processed/climate/
data/processed/shocks/
data/processed/model_inputs/
data/processed/simulations/
data/processed/dashboard/
```

The app should consume dashboard-ready files from:

```text
data/processed/dashboard/
```

Expected files may include:

```text
scenario_index.json
kpi_summary.csv
province_losses.csv
sector_losses.csv
province_sector_losses.csv
top_penalized_flows.csv
top_favored_flows.csv
province_flow_heatmap.csv
sector_flow_heatmap.csv
```

If some files are missing or columns differ, inspect the repository and adapt with minimal changes. Do not redesign the analytical pipeline unless necessary.

The app should include a small data-preparation/export script that copies or converts dashboard files into frontend-readable static assets, for example:

```text
frontend/public/data/
```

Do not require Databricks, Python model execution, or backend runtime for the dashboard.

---

## 3. Scenario execution assumptions

For the dashboard outputs, scenarios must be generated with:

```text
max_iter = 1
gamma = 0.5
```

If a scenario metadata file or build report exists, validate that the stored outputs were generated with:

```text
iterations = 1
gamma = 0.5
```

If this metadata is not available, add a visible caveat in the dashboard methodology section:

```text
Scenario outputs are static demonstrative results. Runtime parameters should be verified in the scenario build report.
```

Do not silently imply that the dashboard is a live calculator.

---

## 4. Frontend technology

Build the frontend with:

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Apache ECharts
MapLibre GL or Leaflet
```

Preferred:

```text
Next.js + TypeScript + Tailwind + shadcn/ui + ECharts + MapLibre
```

Use MapLibre if the Italian province GeoJSON can be loaded cleanly. Use Leaflet if faster to implement.

Do not introduce unnecessary state-management libraries unless clearly needed.

Do not introduce a backend unless strictly necessary. For this static MVP, prefer static JSON/CSV assets loaded client-side.

---

## 5. Brand identity

A brand-assets folder will be available in the repository root, for example:

```text
brand/
```

or:

```text
assets/brand/
```

It may contain:

```text
OpenEconomics-LOGO BLACK.png
OpenEconomics-LOGO WHITE.png
OE_Brand Manual_pag17-20.pdf
openeconomics-brand-dataviz.skill
```

Inspect this folder before implementing UI styling.

Use OpenEconomics visual identity.

Known brand palette:

```text
White    #FFFFFF
Black    #000000
Bluette  #4400B3
Lime     #B9FF69
```

Use black and white as the core visual foundation.

Use Bluette as the main accent colour.

Use Lime as the secondary accent colour, mostly for highlights, positive emphasis, active state, or selected elements.

Do not overuse Lime.

The style should be:

```text
clean
analytical
corporate
modern
data-centric
high-contrast
methodological
```

Avoid generic SaaS-dashboard aesthetics.

Avoid gradients, decorative backgrounds, heavy shadows, 3D effects, and visual noise.

---

## 6. Data-visualisation style

Use the uploaded OpenEconomics data-visualisation rules where possible.

General chart rules:

- white chart canvas;
- no chart borders;
- no decorative backgrounds;
- no 3D charts;
- no gradient fills;
- clear chart titles;
- short explanatory subtitles;
- source/note line when useful;
- horizontal gridlines only for value axes;
- use Bluette first;
- use Lime second only where it improves interpretation;
- avoid more than 5 colours in one chart;
- use grey only for baselines/reference elements;
- prefer bar charts, maps, line/area where necessary, and Sankey for flows.

Recommended chart colour order:

```text
1. Bluette  #4400B3
2. Lime     #B9FF69
3. Violet   #6E1AFF
4. Magenta  #C300C3
5. Cyan     #00FFFF
```

For negative/penalised changes, use Bluette/dark tones or a clear loss palette.

For favoured/reallocated flows, use Lime or a positive accent.

Maintain accessibility and legibility.

---

## 7. Typography

Use a clean, legible font stack.

If Atkinson Hyperlegible is available in the project, use it for dashboard text and chart text.

Otherwise use a system fallback:

```css
font-family: Inter, Atkinson Hyperlegible, system-ui, sans-serif;
```

Chart numeric labels can use a monospaced fallback:

```css
font-family: "Atkinson Hyperlegible Mono", "Roboto Mono", ui-monospace, monospace;
```

Use large, clear section titles. The dashboard should contain explanatory text, not only charts.

---

## 8. Geographic data

The project already contains ISTAT shapefiles for Italian provinces.

Likely locations include:

```text
data/raw/istat/ProvCM01012024_g/
data/processed/climate/istat_provinces_2024.gpkg
```

Create a script to export the province geometry to frontend-ready GeoJSON:

```text
scripts/export_province_geojson_for_frontend.py
```

Output:

```text
frontend/public/data/geographies/italy_provinces.geojson
```

The GeoJSON properties must include, where available:

```text
province_code
province_name
province_abbr
region_code
```

If a province-code crosswalk exists, use it to align GeoJSON properties with model/dashboard data.

If the mapping is incomplete, fail clearly.

---

## 9. Required UX concept

The dashboard must allow users to interrogate the system by selecting:

```text
hazard
scenario / severity
region / province
sector
```

Core hazards:

```text
heatwave
flood
landslide
```

Flood and landslide have severity distinctions.

Heatwave may have a central/static scenario.

The interface must answer these questions:

1. How exposed is this province to the selected hazard?
2. What calibrated supply and demand shocks are applied?
3. Which sectors are most affected in this province?
4. How much of the impact is direct vs indirect?
5. Which other provinces/sectors transmit or absorb the shock?
6. Which economic flows are most penalised or favoured?
7. How was the result calculated?

---

## 10. Main information architecture

Create the following main sections/pages.

### 10.1 Executive Overview

Purpose: give an immediate reading of the selected hazard/scenario.

Content:

- scenario selector;
- hazard selector;
- headline KPI cards;
- Italy province map;
- top exposed provinces;
- top impacted provinces;
- top impacted sectors;
- direct vs indirect loss split;
- short explanatory paragraph.

KPI cards should include:

```text
Total production loss
Loss rate
Direct loss
Indirect loss
Most exposed province
Most impacted sector
```

Use concise explanatory text below the KPI row.

### 10.2 Regional Exposure & Impact

Purpose: let users select a province and understand direct and indirect exposure.

Controls:

```text
hazard
scenario/severity
province
```

For selected province show:

- direct hazard exposure;
- calibrated supply shock;
- calibrated demand shock;
- total production loss;
- direct loss;
- indirect loss;
- indirect exposure ratio;
- top affected sectors in province;
- top incoming/outgoing impacted flows involving that province.

Direct exposure should come from:

```text
province_hazard_exposure.csv
```

Calibrated shock should come from:

```text
shock_matrix.csv
```

Impact should come from:

```text
province_results.csv
province_sector_losses.csv
```

Define:

```text
indirect_loss = total_loss - direct_loss
indirect_exposure_ratio = indirect_loss / total_loss
```

Protect against division by zero.

### 10.3 Sectoral Impact

Purpose: show how impacts vary by sector.

Content:

- bar chart of sector losses;
- bar chart of sector loss rates;
- sector-by-province table;
- sector selector;
- map of selected sector loss by province;
- short explanation of sector vulnerability assumptions.

### 10.4 Network Flows

Purpose: communicate economic propagation and flow reconfiguration.

Content:

- top penalised flows table;
- top favoured/reallocated flows table;
- Sankey diagram for the most relevant flows;
- province-to-province heatmap;
- sector-to-sector heatmap.

Sankey should show either:

```text
origin province/sector -> destination province/sector
```

or a simplified structure:

```text
Province -> Sector -> Province
```

Keep Sankey readable. Limit to top 15–25 flows.

Use separate visual treatment for:

```text
penalised flows
favoured flows
```

### 10.5 Methodology

Purpose: explain the pipeline clearly.

This section must not be only text. It should include:

- flow diagram of the modelling pipeline;
- small chart showing exposure-to-shock transformation;
- schematic of SAM / IO propagation;
- explanation cards for direct vs indirect impact;
- chart or mini-diagram showing how gamma and iterations are used.

Methodology should explain:

```text
Hazard exposure
→ equivalent stop days
→ supply shock / demand shock
→ IO propagation
→ direct and indirect losses
→ flow reconfiguration
```

Mention:

```text
Dashboard uses precomputed static scenarios.
Scenarios shown here use max_iter = 1 and gamma = 0.5.
Results are demonstrative and should not be interpreted as asset-damage estimates.
```

### 10.6 Data & Assumptions

Purpose: improve credibility and transparency.

Content:

- data source cards;
- scenario assumptions;
- sector vulnerability assumptions;
- shock caps;
- date/status of generated outputs;
- caveats.

Include these caveats:

```text
Physical hazard exposure is transformed into business-interruption shock through assumptions on interruption days and sector vulnerability.
Flood and landslide exposure reflect shares of local business units exposed/risk-classified.
Heatwave exposure is derived from E-OBS maximum-temperature hot-day indicators.
The model estimates short-term production interruption and network propagation, not physical asset loss.
```

---

## 11. Layout

Use a professional dashboard layout:

```text
Top bar:
  OpenEconomics logo
  project title
  scenario controls

Left sidebar or tab navigation:
  Overview
  Regional
  Sectors
  Network
  Methodology
  Data & assumptions

Main area:
  cards, maps, charts, explanatory panels
```

Use sticky top controls if useful.

The dashboard should be readable on a laptop screen.

Do not optimise heavily for mobile, but avoid breaking completely on smaller screens.

---

## 12. Static data adapter

Create a frontend data adapter layer.

Suggested folder:

```text
frontend/src/lib/data/
```

Implement functions such as:

```typescript
loadScenarioIndex()
loadKpiSummary()
loadProvinceLosses()
loadSectorLosses()
loadProvinceSectorLosses()
loadTopFlows()
loadProvinceFlowHeatmap()
loadSectorFlowHeatmap()
loadHazardExposure()
loadShockMatrix()
loadProvinceGeoJson()
```

These functions should read from:

```text
/public/data/
```

or imported static assets.

Create TypeScript types:

```text
Scenario
Hazard
ProvinceExposure
ShockRecord
KpiSummary
ProvinceLoss
SectorLoss
ProvinceSectorLoss
FlowRecord
HeatmapCell
```

Avoid hardcoding column names in many components. Centralise mappings in one place.

---

## 13. Data export script

Create:

```text
scripts/export_dashboard_data_for_frontend.py
```

This script should copy or convert required files from:

```text
data/processed/dashboard/
data/processed/climate/
data/processed/shocks/
```

to:

```text
frontend/public/data/
```

Expected frontend data assets:

```text
frontend/public/data/scenario_index.json
frontend/public/data/kpi_summary.json
frontend/public/data/province_losses.json
frontend/public/data/sector_losses.json
frontend/public/data/province_sector_losses.json
frontend/public/data/top_penalized_flows.json
frontend/public/data/top_favored_flows.json
frontend/public/data/province_flow_heatmap.json
frontend/public/data/sector_flow_heatmap.json
frontend/public/data/province_hazard_exposure.json
frontend/public/data/shock_matrix.json
frontend/public/data/geographies/italy_provinces.geojson
```

Prefer JSON for frontend consumption.

CSV can remain in `data/processed/`, but the frontend should consume JSON unless there is a strong reason not to.

---

## 14. Component structure

Suggested frontend structure:

```text
frontend/
  app/
    page.tsx
    methodology/page.tsx
    data-assumptions/page.tsx
  components/
    layout/
      AppShell.tsx
      TopBar.tsx
      Sidebar.tsx
      ControlPanel.tsx
    cards/
      KpiCard.tsx
      ExplanationCard.tsx
    charts/
      BarChart.tsx
      ProvinceMap.tsx
      SectorBarChart.tsx
      DirectIndirectChart.tsx
      FlowSankey.tsx
      HeatmapChart.tsx
      MethodologyFlow.tsx
    tables/
      FlowTable.tsx
      ProvinceSectorTable.tsx
    sections/
      ExecutiveOverview.tsx
      RegionalExposurePanel.tsx
      SectorImpactPanel.tsx
      NetworkFlowPanel.tsx
      MethodologyPanel.tsx
      DataAssumptionsPanel.tsx
  lib/
    data/
    formatters.ts
    constants.ts
    brand.ts
  public/
    data/
    logos/
```

This is a suggested structure. Keep it simple and adapt if needed.

---

## 15. Map requirements

Province map must support:

- colour by exposure;
- colour by calibrated supply shock;
- colour by total loss;
- colour by loss rate;
- hover tooltip;
- selected province highlight;
- click to select province.

Tooltip should show:

```text
province name
hazard exposure
supply shock
demand shock
total loss
loss rate
direct loss
indirect loss
```

Use Italian province boundaries.

Do not use a generic map without province boundaries.

---

## 16. Chart requirements

### Bar charts

Use horizontal bar charts for rankings.

Examples:

```text
Top exposed provinces
Top impacted provinces
Top impacted sectors
Province-sector losses
```

### Direct vs indirect chart

Use stacked bar or paired bars.

Show:

```text
direct loss
indirect loss
```

### Sankey

Use Sankey only for top flows.

Limit complexity.

If Sankey becomes unreadable, provide a table fallback and a simplified Sankey.

### Heatmaps

Use heatmaps for:

```text
province-to-province flow changes
sector-to-sector flow changes
```

Include filters.

---

## 17. Methodological diagrams

Implement at least one visual flow diagram in the methodology section.

It can be:

- custom React cards connected with arrows;
- Mermaid rendered if already available;
- ECharts graph;
- simple CSS layout.

Required pipeline diagram:

```text
Climate hazard data
→ Provincial exposure indicators
→ Shock calibration
→ SAM/IO propagation model
→ Direct and indirect losses
→ Flow reconfiguration
→ Dashboard outputs
```

Also include a mini diagram:

```text
Exposure × interruption days × sector vulnerability
= equivalent stop days
→ supply shock
→ demand shock
```

---

## 18. Dashboard narrative

Text matters.

Each page/section should include 2–4 concise explanatory sentences.

Avoid walls of text.

Every chart should have a title and, where useful, a note.

Examples:

```text
“Direct exposure reflects the province’s physical hazard exposure before economic propagation.”
“Indirect impact captures losses transmitted through input-output dependencies with other provinces and sectors.”
“The dashboard uses static precomputed scenarios; changing the selector does not run a new model.”
```

---

## 19. Data governance and caveats

Add a visible methodology note:

```text
This dashboard presents scenario-based estimates. Results are not forecasts and are not observed losses.
```

Add another note:

```text
The model estimates business-interruption impacts on production flows. It does not estimate physical damage to assets.
```

If possible, add a small “Data status” card:

```text
Climate exposure: processed
Shock calibration: processed
SAM model inputs: processed
Simulation outputs: static
Frontend mode: static demo
```

---

## 20. Implementation constraints

Do not:

- change heatwave methodology;
- change shock calibration formulas unless needed to read data;
- change model logic;
- require Databricks at frontend runtime;
- run model from frontend;
- create a live calculator;
- introduce a backend unless absolutely necessary;
- hardcode absolute Windows paths;
- commit large data files;
- delete existing outputs.

Do:

- inspect repository before coding;
- use existing dashboard/static outputs;
- create frontend export script if needed;
- use TypeScript types;
- centralise constants and formatting;
- keep UI polished but simple;
- make the demo credible and explanatory.

---

## 21. Tests and validation

Add lightweight tests or validation scripts.

Create:

```text
scripts/test_frontend_data_export.py
```

It should validate:

- required processed files exist;
- exported frontend JSON files exist;
- province GeoJSON exists;
- scenario index exists;
- at least one scenario is available;
- province loss records can join with GeoJSON province codes;
- shock records can join with province and sector records;
- no critical numeric fields are entirely null.

Add a simple frontend smoke test if the project has a test framework. If not, do not introduce a heavy testing framework.

---

## 22. README update

Update README with a new section:

```text
Static dashboard app
```

Include:

- dashboard purpose;
- frontend stack;
- data export command;
- frontend install command;
- frontend run command;
- note that dashboard is static/demo;
- note that scenarios use `max_iter = 1` and `gamma = 0.5`.

Commands to document:

```powershell
.\.venv\Scripts\python.exe scripts\export_dashboard_data_for_frontend.py

cd frontend
npm install
npm run dev
```

If the frontend already exists, adapt commands accordingly.

---

## 23. Brand asset handling

Copy logos to:

```text
frontend/public/logos/
```

Use:

```text
OpenEconomics-LOGO BLACK.png
```

on light backgrounds.

Use:

```text
OpenEconomics-LOGO WHITE.png
```

on dark/Bluette backgrounds.

Do not distort logos.

Keep appropriate padding and clear space.

---

## 24. Final response required

After implementation, summarize:

- files created;
- files modified;
- frontend stack used;
- data export script created;
- pages/sections implemented;
- maps implemented;
- charts implemented;
- methodology section implemented;
- brand assets integrated;
- how to export data;
- how to run the app;
- known limitations.

Explicitly report:

1. The app is static and demonstrative.
2. It reads precomputed files only.
3. It does not run simulations live.
4. Scenario outputs are expected to use `max_iter = 1` and `gamma = 0.5`.
5. The dashboard estimates business-interruption impacts, not physical damages.
