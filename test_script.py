import sys
sys.path.append('.')
from engine.laplace_solver import solve_laplace, create_grid
from engine.phreatic import compute_phreatic_line_for_dam, phreatic_to_grid_indices
from engine.safety import compute_exit_gradient

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

ie = compute_exit_gradient(h, dx)
print(f"L = {L}, dx = {dx}")
print(f"Exit Gradient: {ie}")
