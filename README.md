# 🏞️ Seepage Flow Simulator in Earth Dams

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Plotly](https://img.shields.io/badge/Plotly-Visualization-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/)

**A browser-based, interactive numerical tool for analyzing 2D steady-state seepage through isotropic earth dams using the Finite Difference Method (FDM).**

[Report Bug](https://github.com/biswajeet-bishoyi/Seepage-Flow-Simulator-in-Earth-Dams/issues) • [Request Feature](https://github.com/biswajeet-bishoyi/Seepage-Flow-Simulator-in-Earth-Dams/issues)

</div>

---

## 🌟 Overview

The **Seepage Flow Simulator in Earth Dams** solves the 2D Laplace equation ($\nabla^2 h = 0$) using numerical finite difference discretizations with Successive Over-Relaxation (SOR) and sparse solvers. It visualizes the free-surface phreatic line, calculates equipotential lines and streamlines, and performs geotechnical stability checks against hydraulic heave and piping failure.

---

## 🚀 Key Features

- **⚡ FDM Laplace Solver**: Gauss-Seidel with Successive Over-Relaxation (SOR) and SciPy sparse direct solver fallback for rapid mesh convergence.
- **🌊 Casagrande Phreatic Line**: Parabolic free surface approximation with entrance and exit correction transitions.
- **🗺️ Interactive Flow Net Visualization**: Head contour color flood, equipotential lines, and orthogonal streamlines rendered in Plotly.
- **🛡️ Geotechnical Safety Analytics**: Computes downstream exit gradient ($i_e$), piping factor of safety (FS), critical hydraulic gradient ($i_{cr}$), and heave risk classification.
- **💻 Dual Interface**:
  - Interactive web dashboard via **Streamlit**.
  - Programmatic headless computations via **FastAPI** REST endpoints.

---

## 📐 Mathematical Formulation

| Phenomenon | Governing Formulation |
|---|---|
| **Laplace Equation** | $\frac{\partial^2 h}{\partial x^2} + \frac{\partial^2 h}{\partial y^2} = 0$ |
| **Seepage Discharge** | $q = \frac{k (H_u^2 - H_d^2)}{2 L}$ |
| **Casagrande Parabola** | $y(x) = \sqrt{y_0^2 + 2 y_0 x}$ |
| **Critical Gradient** | $i_{cr} = \frac{G_s - 1}{1 + e} \approx 1.0$ |
| **Piping Factor of Safety** | $\text{FS} = \frac{i_{cr}}{i_e}$ |

### Safety Risk Classification
- **🟢 Low Risk (FS ≥ 4.0)**: Normal operational condition.
- **🟡 Moderate Risk (2.0 ≤ FS < 4.0)**: Routine periodic inspection recommended.
- **🟠 High Risk (1.5 ≤ FS < 2.0)**: Detailed engineering review required.
- **🔴 Critical Risk (FS < 1.5)**: Immediate toe drain / relief well intervention required.

---

## 🏛️ Architecture & Separation of Concerns

- `engine/`: Pure numerical solvers (zero external I/O, zero plotting dependencies).
- `viz/`: Plotly figure generation and vector styling.
- `ui/`: Streamlit interactive dashboard and FastAPI REST backend.
- `tests/`: Verification against analytical benchmark solutions.

---

## 🛠️ Quick Start

### 1. Setup Environment
```bash
git clone https://github.com/biswajeet-bishoyi/Seepage-Flow-Simulator-in-Earth-Dams.git
cd Seepage-Flow-Simulator-in-Earth-Dams

python -m venv .venv
# Windows
.\.venv\Scriptsctivate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Launch Streamlit UI
```bash
streamlit run ui/app.py
```

### 3. Launch FastAPI REST Server
```bash
uvicorn ui.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Verification Tests
```bash
pytest tests/ -v
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
Developed by <a href="https://github.com/biswajeet-bishoyi">Biswajeet Bishoyi</a>
</div>
