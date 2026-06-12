import sys
sys.path.append('.')
from engine.laplace_solver import solve_laplace, create_grid
from engine.phreatic import compute_phreatic_line_for_dam, phreatic_to_grid_indices
from engine.safety import compute_exit_gradient
import numpy as np

H_u = 20.0
H_d = 2.0
W = 15.0
m_u = 3.0
m_d = 2.5
L = m_u*H_u + W + m_d*H_u

Nx = 200
Ny = 80

ph_x, ph_y = compute_phreatic_line_for_dam(H_u, H_d, L, m_u)
ph_j = phreatic_to_grid_indices(ph_y, ph_x, Nx, Ny, L, H_u)

h, _, _, _ = solve_laplace(H_u, H_d, L, Nx, Ny, phreatic_j=ph_j)
x, y, dx, dy = create_grid(Nx, Ny, L, H_u)

grad = (h[:, -2] - h[:, -1]) / dx
pos_grad = grad[grad > 0]
print("dx:", dx)
print("max grad:", np.max(pos_grad) if len(pos_grad)>0 else 0)
print("mean pos grad:", np.mean(pos_grad) if len(pos_grad)>0 else 0)

# Let's look at the bottom 10 nodes at the boundary
for j in range(10):
    print(f"j={j}, y={y[j]:.2f}, h_inside={h[j, -2]:.2f}, h_bound={h[j, -1]:.2f}, grad={grad[j]:.2f}")
