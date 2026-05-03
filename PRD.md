# PRD.md — Seepage Flow Simulator in Earth Dams
**Product Requirements Document**
Version: 1.0 | Status: Draft | Classification: Internal Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Functional Requirements](#2-functional-requirements)
3. [Technical Requirements](#3-technical-requirements)
4. [Mathematical Core](#4-mathematical-core)
5. [Safety Analytics](#5-safety-analytics)
6. [User Experience & Animation](#6-user-experience--animation)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Acceptance Criteria](#8-acceptance-criteria)
9. [Glossary](#9-glossary)

---

## 1. Executive Summary

### 1.1 Project Purpose

The **Seepage Flow Simulator** is a web-based, interactive numerical tool for visualizing and analyzing 2D steady-state seepage through isotropic earth dams. It targets geotechnical engineers, graduate students, and dam safety analysts who require rapid, visual, and quantitative insight into internal flow behavior without running full finite-element software packages.

The tool solves the Laplace Equation (∇²h = 0) over a discretized 2D domain using the Finite Difference Method (FDM) and renders the resulting hydraulic head distribution as flow nets, equipotential lines, streamlines, and animated particle paths — all in real time within a browser.

### 1.2 Problem Statement

Seepage-induced failure (piping, internal erosion) is among the leading causes of earth dam collapse. Existing tools (e.g., SEEP/W, PLAXIS) require paid licenses, steep learning curves, and offline operation. Practitioners and educators lack a lightweight, shareable, browser-native tool for rapid scenario exploration and teaching.

### 1.3 Success Metrics

| Metric | Target |
|---|---|
| Solver convergence time (300×100 grid) | < 3 seconds |
| UI parameter update → re-render latency | < 500 ms |
| Exit gradient warning accuracy vs. analytical | ±5% |
| Phreatic line RMSE vs. Casagrande | < 0.02 × H_u |
| Concurrent users supported (hosted) | ≥ 50 |

---

## 2. Functional Requirements

### 2.1 Input Panel

The application shall expose the following input controls. All inputs must support both slider interaction and direct numeric entry. Each change triggers an immediate re-computation cycle.

#### 2.1.1 Hydraulic Boundary Inputs

| Parameter | Symbol | Unit | Default | Allowed Range | Validation Rule |
|---|---|---|---|---|---|
| Upstream Head | H_u | m | 20.0 | 1.0 – 100.0 | Must satisfy H_u > H_d |
| Downstream Head | H_d | m | 2.0 | 0.0 – 99.0 | Must satisfy H_d < H_u |
| Hydraulic Conductivity | k | m/s | 1×10⁻⁵ | 1×10⁻⁹ – 1×10⁻³ | Log-scale slider; scientific notation display |
| Dam Crest Width | W | m | 10.0 | 5.0 – 50.0 | — |
| Upstream Slope (H:V) | m_u | — | 3.0 | 1.5 – 5.0 | — |
| Downstream Slope (H:V) | m_d | — | 2.5 | 1.5 – 5.0 | — |
| Dam Base Width | L | m | auto-computed | Read-only | L = W + m_u × H_u + m_d × H_u |

**Validation Error Display:** Inline red badge beneath the offending field with a plain-language description (e.g., "H_u must be greater than H_d").

#### 2.1.2 Grid Resolution Control

| Control | Default | Range | Effect |
|---|---|---|---|
| Grid Columns (Nx) | 200 | 50 – 500 | Horizontal FDM nodes |
| Grid Rows (Ny) | 80 | 20 – 200 | Vertical FDM nodes |

A "Precision Mode" toggle locks Nx = 400, Ny = 150 for high-fidelity output at the cost of compute time.

### 2.2 Real-Time Output — Seepage Discharge

The application shall calculate and prominently display the seepage discharge per unit width using Darcy's Law and the Dupuit–Forchheimer assumption:

```
q = k × (H_u² − H_d²) / (2 × L)
```

Where L is the effective seepage path length (dam base width).

**Display Requirements:**
- Numerical value in m²/s, formatted in scientific notation (e.g., `3.42 × 10⁻⁶ m²/s`)
- Qualitative rating badge: **Low / Moderate / High / Critical** based on configurable thresholds
- A time-series sparkline that records q values across the last 20 parameter changes in the session

### 2.3 Phreatic Line — Casagrande's Solution

The application shall dynamically compute and overlay the phreatic surface (free surface / line of seepage) using **Casagrande's parabolic approximation**:

**Step 1 — Find the focus point (downstream toe)**
```
a₀ = √(d² + H_u²) − d
```
Where d = horizontal distance from upstream toe to the point where the upstream slope intersects the reservoir level.

**Step 2 — Parabola equation**
```
y(x) = √(a₀² + 2·a₀·x)     for 0 ≤ x ≤ L
```

**Display Requirements:**
- Rendered as a bold dashed blue line over the flow net visualization
- Dynamically redrawn on every parameter change
- Accompanied by a data table: x-coordinate vs. y-coordinate at 10 evenly spaced stations
- Highlight the exit point at the downstream slope with a red marker dot

### 2.4 Head Distribution Visualization

After FDM solution:
- **Equipotential Lines:** Contour lines of equal hydraulic head h, drawn at N_eq equally spaced head intervals (user-configurable, default: 10)
- **Streamlines:** Orthogonal to equipotential lines; computed via the stream function ψ, rendered as solid colored lines
- **Color Flood Map:** Smooth gradient flood fill of the head field (blue = high head, red = low head) using a diverging colormap

### 2.5 Session Management

| Feature | Behavior |
|---|---|
| Export PNG | Captures current visualization canvas |
| Export CSV | Exports full h[x,y] matrix, phreatic line coordinates, q value |
| Reset Defaults | Restores all inputs to documented defaults |
| Share URL | Encodes current parameters into a shareable URL hash |

---

## 3. Technical Requirements

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser / Client                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │  /ui         │   │  /viz        │   │  State Manager   │ │
│  │  React Input │──▶│  Plotly      │◀──│  (Zustand /      │ │
│  │  Dashboard   │   │  Canvas      │   │   Redux)         │ │
│  └──────┬───────┘   └──────────────┘   └──────────────────┘ │
│         │ WebWorker / API call                               │
└─────────┼───────────────────────────────────────────────────┘
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    /engine (Python or JS)                    │
│  ┌──────────────────────┐   ┌──────────────────────────┐    │
│  │  laplace_solver.py   │   │  darcy.py                │    │
│  │  (FDM + Gauss-Seidel)│   │  (q, gradient, phreatic) │    │
│  └──────────────────────┘   └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Deployment Options (two tracks):**

| Track | Frontend | Backend/Engine | Hosting |
|---|---|---|---|
| A — Full Stack | React (Vite) | Python FastAPI + NumPy/SciPy | Vercel (FE) + Railway/Render (BE) |
| B — Pure Frontend | React (Vite) | JavaScript (math.js + custom FDM) | Vercel / GitHub Pages |

Track B is preferred for zero-latency deployment. Track A is required if grid sizes > 300×100 are needed.

### 3.2 Backend / Engine (Python — Track A)

**Required Packages:**

```bash
numpy>=1.24.0
scipy>=1.11.0
fastapi>=0.111.0
uvicorn>=0.29.0
pydantic>=2.0.0
```

**Solver API Endpoint:**

```
POST /api/solve
Content-Type: application/json

Request Body:
{
  "H_u": float,
  "H_d": float,
  "k": float,
  "W": float,
  "m_u": float,
  "m_d": float,
  "Nx": int,
  "Ny": int
}

Response Body:
{
  "h_grid": [[float]],       // shape: Ny × Nx
  "q": float,
  "phreatic_x": [float],
  "phreatic_y": [float],
  "exit_gradient": float,
  "piping_risk": "LOW" | "MODERATE" | "HIGH" | "CRITICAL"
}
```

### 3.3 Frontend (React — Track A & B)

**Required Packages:**

```bash
react@18+
plotly.js@2.30+          # visualization
@radix-ui/react-slider   # accessible sliders
zustand@4+               # state management
tailwindcss@3+           # styling
```

**Component Tree:**

```
<App>
  ├── <InputPanel>
  │     ├── <HeadSlider name="H_u" />
  │     ├── <HeadSlider name="H_d" />
  │     ├── <LogSlider  name="k"   />
  │     ├── <DamGeometryInputs />
  │     └── <GridResolutionControl />
  ├── <ResultsBar>
  │     ├── <DischargeDisplay q={q} />
  │     ├── <ExitGradientGauge ie={ie} />
  │     └── <RiskBadge level={risk} />
  └── <VisualizationCanvas>
        ├── <FlowNetPlot />
        ├── <PhreatricLineOverlay />
        └── <ParticleAnimationLayer />
```

### 3.4 Alternative: Streamlit (Rapid Prototype)

For internal use / proof-of-concept, a Streamlit app (`app.py`) shall be maintained as an alternative to the React frontend. All engine functions are shared.

```bash
streamlit>=1.35.0
plotly>=5.22.0
```

### 3.5 Visualization Library Requirements

| Feature | Library | Requirement |
|---|---|---|
| Contour / flood plots | Plotly (`go.Contour`) | Sub-200ms render for 200×80 grid |
| Streamline traces | Plotly (`ff.create_streamline`) | Seeded from upstream boundary |
| Particle animation | Plotly (`go.Scatter` + `frames`) | ≥ 24 fps |
| Export to PNG | Plotly `downloadImage` API | ≥ 300 DPI |

---

## 4. Mathematical Core

### 4.1 Governing Equation

For steady-state, 2D, isotropic, saturated seepage through a homogeneous porous medium, the hydraulic head h(x, y) satisfies the **Laplace Equation**:

```
∂²h/∂x² + ∂²h/∂y² = 0
```

This is derived from the continuity equation (∇·v = 0) combined with Darcy's Law (v = −k·∇h).

### 4.2 Domain Geometry and Grid Discretization

The 2D domain spans [0, L] × [0, H_dam], where H_dam = H_u.

Uniform spacing:
```
Δx = L / (Nx − 1)
Δy = H_dam / (Ny − 1)
```

Node coordinates:
```
x_i = i · Δx       for i = 0, 1, …, Nx−1
y_j = j · Δy       for j = 0, 1, …, Ny−1
```

Finite difference approximation (central differences, second order):
```
∂²h/∂x² ≈ (h[i+1,j] − 2·h[i,j] + h[i−1,j]) / Δx²
∂²h/∂y² ≈ (h[i,j+1] − 2·h[i,j] + h[i,j−1]) / Δy²
```

Setting the discretized Laplacian to zero and rearranging:
```
h[i,j] = (α²·(h[i+1,j] + h[i−1,j]) + h[i,j+1] + h[i,j−1]) / (2·(α² + 1))

where α = Δy / Δx  (aspect ratio)
```

This is the **update stencil** applied iteratively over all interior nodes.

### 4.3 Boundary Conditions

| Boundary | Location | Type | Value |
|---|---|---|---|
| Upstream face | x = 0, all j | Dirichlet | h = H_u |
| Downstream face | x = L, all j | Dirichlet | h = H_d |
| Dam base | y = 0, all i | Neumann (no-flow) | ∂h/∂y = 0 → h[i,0] = h[i,1] |
| Free surface | y = y_phreatic(x) | Dirichlet + kinematic | h = y (approximated via Casagrande) |

The free surface is handled via the **fixed-domain approximation**: nodes above the phreatic line are masked out (h set to the local elevation y_j), and the active domain is the saturated zone below.

### 4.4 Iterative Solver — Gauss-Seidel with SOR

The preferred solver is **Successive Over-Relaxation (SOR)**, which accelerates Gauss-Seidel convergence:

```
h_new[i,j] = (α²·(h[i+1,j] + h[i−1,j]) + h[i,j+1] + h[i,j−1]) / (2·(α² + 1))

h[i,j] ← h[i,j] + ω · (h_new[i,j] − h[i,j])
```

Where ω is the relaxation factor:
- ω = 1.0 → standard Gauss-Seidel
- 1.0 < ω < 2.0 → SOR (recommended ω ≈ 1.5–1.8 for typical dam geometries)

**Convergence criterion:**
```
max|h_new[i,j] − h_old[i,j]| < ε = 1×10⁻⁵ m
```

**Maximum iterations:** 10,000 (with early termination on convergence).

**Fallback:** If convergence is not achieved within max iterations, display a warning banner and return the best available solution.

**Alternative (Track A):** Use `scipy.sparse.linalg.spsolve` for direct solution of the assembled linear system Ah = b — O(N log N) complexity, avoiding iteration entirely.

### 4.5 Flow Net Calculation

**Equipotential spacing:**
```
Δh = (H_u − H_d) / N_d

where N_d = number of potential drops (default: 12)
```

**Stream function ψ:** Computed by integrating Darcy velocities:
```
v_x = −k · ∂h/∂x    (central differences on solved h field)
v_y = −k · ∂h/∂y

ψ[i,j] = ψ[i,j−1] + v_x[i,j] · Δy    (integration upward from base)
```

Streamlines are iso-contours of ψ, spaced at Δψ = q / N_f, where N_f = number of flow tubes (default: 6).

The flow net validity check ensures: **N_f / N_d ≈ constant** (square flow nets criterion).

---

## 5. Safety Analytics

### 5.1 Exit Gradient Monitoring

The **exit gradient** i_e is the hydraulic gradient at the downstream toe of the dam, where seepage exits the embankment. This is the primary indicator of **piping failure risk**.

**Calculation:**
```
i_e = |∂h/∂x|_{x=L}  =  (h[Nx−1, j] − h[Nx−2, j]) / Δx

averaged over the saturated zone at x = L
```

**Failure Criterion (Terzaghi's Critical Gradient):**
```
i_cr = (G_s − 1) / (1 + e)

Typical values: G_s = 2.65 (specific gravity), e = 0.6 (void ratio)
→  i_cr ≈ 1.0 for most granular soils
```

**Factor of Safety against Piping:**
```
FS_piping = i_cr / i_e
```

### 5.2 Risk Classification

| FS_piping | Risk Level | UI Color | Recommended Action |
|---|---|---|---|
| FS ≥ 4.0 | LOW | Green | No action required |
| 2.0 ≤ FS < 4.0 | MODERATE | Yellow | Monitor; inspect annually |
| 1.5 ≤ FS < 2.0 | HIGH | Orange | Engineer review required |
| FS < 1.5 | CRITICAL | Red | Immediate intervention |

### 5.3 Safety Dashboard Panel

The UI shall display a dedicated **Safety Analytics Panel** containing:

1. **Exit Gradient Gauge:** Radial gauge chart with needle, scale 0 → 2.0, colored zones per table above
2. **FS_piping Numeric Display:** Large font with color coding
3. **Heave Check (upstream):** Vertical gradient at upstream face vs. critical gradient; F_S_heave = i_cr / i_upstream
4. **Seepage Velocity Display:**
   ```
   v_s = k · i_e / n     (n = porosity, default 0.35)
   ```
5. **Alert Banner:** Auto-displayed when FS_piping < 1.5, with a description of likely failure mechanism and recommended remediation measures (filter toe drain, relief wells, upstream blanket)

### 5.4 Sensitivity Analysis (Advanced Feature)

A "What-If" panel allows the user to vary one parameter while holding others fixed and plot FS_piping vs. the swept variable (line chart). Supported sweeps: k, H_u, downstream slope m_d.

---

## 6. User Experience & Animation

### 6.1 Layout

The application uses a two-panel responsive layout:

```
┌──────────────────────┬──────────────────────────────────────┐
│  LEFT PANEL          │  RIGHT PANEL                         │
│  (30% width)         │  (70% width)                         │
│                      │                                      │
│  Input Controls      │  Main Visualization Canvas           │
│  ─────────────────   │  (Flow Net + Phreatic Line)          │
│  Results Summary     │  ─────────────────────────────────── │
│  ─────────────────   │  Safety Analytics Panel              │
│  Safety Dashboard    │  (Exit Gradient + FS Gauge)          │
└──────────────────────┴──────────────────────────────────────┘
```

On mobile (< 768px): single-column layout; visualization below inputs.

### 6.2 Particle Animation Requirements

| Property | Specification |
|---|---|
| Animation type | Moving particle tracers following streamlines |
| Number of particles | 30–80 (auto-scaled to flow domain width) |
| Particle speed | Proportional to local Darcy velocity magnitude |
| Frame rate | 30 fps target; 24 fps minimum |
| Particle color | Velocity magnitude mapped to colormap (viridis) |
| Particle size | 6px diameter dots |
| Trail length | 8 frames (fade-out effect) |
| Seeding location | Uniformly distributed along upstream face, below phreatic line |
| Loop behavior | Particles respawn at upstream face when they exit downstream |

**Implementation:** Plotly `animation` frames with `frame.duration = 33ms`, or a `requestAnimationFrame` loop updating a Canvas 2D overlay for performance.

### 6.3 Streamline Animation Alternative

When particle count > 60 (performance mode), replace individual particles with **shifting streamlines** (animated dash offset):

```css
stroke-dasharray: 10 5;
animation: dash-move 2s linear infinite;

@keyframes dash-move {
  from { stroke-dashoffset: 0; }
  to   { stroke-dashoffset: -30; }
}
```

Speed of animation is proportional to local k × i (Darcy velocity).

### 6.4 Interaction Behavior

| User Action | System Response |
|---|---|
| Move any slider | Pause animation → Recompute h field → Update all overlays → Resume animation |
| Click on canvas point (x, y) | Show tooltip: h value, velocity vector, hydraulic gradient at that node |
| Double-click dam geometry | Enter geometry edit mode with draggable slope handles |
| Toggle "Show Equipotentials" | Instantly hide/show contour layer (no recompute) |
| Toggle "Show Streamlines" | Instantly hide/show streamline layer |
| Toggle "Animate Flow" | Start/stop particle or streamline animation |

### 6.5 Color Scheme and Accessibility

- All risk colors pass WCAG AA contrast ratio (≥ 4.5:1)
- Colorblind-safe palette option: replace viridis with cividis
- Dark mode support via CSS custom properties

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | FDM solve for 200×80 grid < 2 seconds (Python), < 500ms (JS) |
| Performance | Full UI re-render on parameter change < 300ms |
| Reliability | Application must not crash on invalid inputs; graceful error display |
| Scalability | API must handle concurrent requests via async (FastAPI + asyncio) |
| Security | All inputs sanitized server-side; no eval of user strings |
| Accessibility | ARIA labels on all sliders and result panels; keyboard-navigable |
| Browser Support | Chrome 120+, Firefox 120+, Safari 17+, Edge 120+ |
| Responsiveness | Functional on tablets (768px+); read-only on mobile (< 768px) |
| Offline | Core JS solver (Track B) must function without internet after first load |

---

## 8. Acceptance Criteria

### 8.1 Functional Acceptance Tests

| ID | Test | Pass Condition |
|---|---|---|
| FAT-01 | Set H_u=20m, H_d=0, k=1e-5, L=50m | q within ±2% of analytical: q = k·H_u²/(2L) = 4.0×10⁻⁵ m²/s |
| FAT-02 | Phreatic line at x=L/2 | y within ±5% of Casagrande value |
| FAT-03 | Set H_u=H_d | q displays 0.00; no solver crash |
| FAT-04 | Critical exit gradient case (H_u=30, H_d=0, L=20) | Risk badge shows CRITICAL; alert banner appears |
| FAT-05 | Export CSV | File contains h_grid, phreatic_x, phreatic_y, q, exit_gradient |
| FAT-06 | Animation toggle | Particles visible and moving within 1 second of enable |
| FAT-07 | Grid Nx=500, Ny=200 | Solve completes without crash; result displayed |

### 8.2 Performance Acceptance Tests

| ID | Test | Pass Condition |
|---|---|---|
| PAT-01 | 200×80 grid, Track A (Python) | API response < 2000ms |
| PAT-02 | 200×80 grid, Track B (JavaScript) | In-browser solve < 500ms |
| PAT-03 | Rapid slider drag (10 changes/sec) | No UI freeze; debounce 200ms |
| PAT-04 | Animation at 80 particles | Sustained ≥ 24fps on mid-tier laptop |

---

## 9. Glossary

| Term | Definition |
|---|---|
| FDM | Finite Difference Method — numerical technique for solving PDEs by replacing derivatives with finite differences on a discrete grid |
| Laplace Equation | ∇²h = 0; governing PDE for steady-state, incompressible, irrotational flow in porous media |
| Hydraulic Head | h = p/(ρg) + z; total energy per unit weight of water at a point |
| Darcy's Law | v = −k·∇h; linear relationship between seepage velocity and hydraulic gradient |
| Phreatic Line | Free surface of seepage; upper boundary of saturated zone within the dam body |
| Casagrande's Method | Parabolic approximation for locating the phreatic line in earth dams |
| Exit Gradient | Hydraulic gradient at the downstream toe; primary piping risk indicator |
| Piping | Internal erosion caused by seepage forces exceeding soil resistance; catastrophic failure mode |
| SOR | Successive Over-Relaxation; iterative solver acceleration technique |
| Flow Net | Graphical representation of seepage as orthogonal equipotential and streamline families |
| Equipotential Line | Contour of constant hydraulic head h |
| Streamline | Path followed by a fluid particle; everywhere tangent to the velocity vector |
| Stream Function | ψ; scalar function whose iso-contours are streamlines |
| i_cr | Critical hydraulic gradient = (G_s−1)/(1+e) ≈ 1.0; value above which piping initiates |
| FS_piping | Factor of safety against piping = i_cr / i_e |

---

*End of PRD.md — Seepage Flow Simulator in Earth Dams*
*Document Owner: Geotechnical Engineering Team | Next Review: Quarterly*
