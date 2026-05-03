# 🌊 Seepage Flow Simulator in Earth Dams

A **browser-based, interactive numerical tool** for visualizing and analyzing 2D steady-state seepage through isotropic earth dams.

Solves the **Laplace Equation (∇²h = 0)** using the Finite Difference Method (FDM) and renders flow nets, equipotential lines, streamlines, and safety analytics — all in real-time within a browser.

## ✨ Features

- **FDM Laplace Solver** — Gauss-Seidel with SOR + sparse direct solver fallback
- **Casagrande Phreatic Line** — Parabolic free surface approximation
- **Flow Net Visualization** — Equipotential lines, streamlines, head color flood
- **Safety Analytics** — Exit gradient, piping FS, heave check, risk classification
- **Interactive UI** — Real-time parameter adjustment via Streamlit
- **REST API** — FastAPI backend for programmatic access

## 🚀 Quick Start

### 1. Setup Environment

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Streamlit App

```bash
streamlit run ui/app.py
```

### 3. Run the FastAPI Server

```bash
uvicorn ui.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## 📐 Architecture

```
engine/     → Pure numerical logic (no I/O, no plotting)
viz/        → Visualization layer (Plotly figures)
ui/         → Streamlit app + FastAPI backend
tests/      → Unit & verification tests
```

**The Iron Rule:** Physics changes never affect `/viz` or `/ui`. UI redesigns never affect `/engine`.

## 🧮 Mathematical Core

| Equation | Formula |
|----------|---------|
| Laplace | ∂²h/∂x² + ∂²h/∂y² = 0 |
| Discharge | q = k(H_u² − H_d²) / (2L) |
| Phreatic | y(x) = √(a₀² + 2·a₀·x) |
| Critical Gradient | i_cr = (G_s − 1)/(1 + e) ≈ 1.03 |
| Factor of Safety | FS = i_cr / i_e |

## 📊 Safety Risk Levels

| FS Range | Risk | Action |
|----------|------|--------|
| FS ≥ 4.0 | 🟢 LOW | No action |
| 2.0 ≤ FS < 4.0 | 🟡 MODERATE | Annual inspection |
| 1.5 ≤ FS < 2.0 | 🟠 HIGH | Engineer review |
| FS < 1.5 | 🔴 CRITICAL | Immediate intervention |

## 📝 License

Internal Engineering Project — Geotechnical Engineering Team
