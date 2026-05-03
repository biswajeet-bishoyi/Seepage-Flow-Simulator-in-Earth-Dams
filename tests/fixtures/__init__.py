"""
Analytical benchmark cases for solver verification.

Contains known closed-form solutions that the FDM solver should reproduce
within specified tolerances.
"""


# Case 1: Standard dam, moderate head
CASE_STANDARD = {
    "H_u": 20.0,
    "H_d": 0.0,
    "k": 1e-5,
    "L": 50.0,
    "W": 10.0,
    "m_u": 3.0,
    "m_d": 2.5,
    "Nx": 200,
    "Ny": 80,
    # Analytical: q = k * H_u² / (2*L) = 1e-5 * 400 / 100 = 4.0e-5
    "expected_q": 1e-5 * (20.0**2) / (2 * 50.0),
    "tolerance": 0.02,  # 2%
}

# Case 2: High head, high conductivity
CASE_HIGH_HEAD = {
    "H_u": 30.0,
    "H_d": 5.0,
    "k": 5e-5,
    "L": 80.0,
    "W": 15.0,
    "m_u": 3.0,
    "m_d": 2.5,
    "Nx": 200,
    "Ny": 80,
    # Analytical: q = 5e-5 * (900 - 25) / 160 = 2.734e-4
    "expected_q": 5e-5 * (30.0**2 - 5.0**2) / (2 * 80.0),
    "tolerance": 0.05,
}

# Case 3: Near-zero downstream head
CASE_LOW_DOWNSTREAM = {
    "H_u": 10.0,
    "H_d": 0.1,
    "k": 1e-6,
    "L": 30.0,
    "W": 8.0,
    "m_u": 2.5,
    "m_d": 2.0,
    "Nx": 150,
    "Ny": 60,
    # Analytical: q = 1e-6 * (100 - 0.01) / 60 = 1.6665e-6
    "expected_q": 1e-6 * (10.0**2 - 0.1**2) / (2 * 30.0),
    "tolerance": 0.05,
}

# Case 4: Equal heads (no flow)
CASE_ZERO_FLOW = {
    "H_u": 15.0,
    "H_d": 15.0,
    "k": 1e-5,
    "L": 40.0,
    "expected_q": 0.0,
}

ALL_CASES = [CASE_STANDARD, CASE_HIGH_HEAD, CASE_LOW_DOWNSTREAM]
