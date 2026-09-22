"""
calibrate_summa.py

Two example calibration harnesses built on summa_python_interface.J().
Start with Option A to confirm the whole pipeline works end-to-end
before adding SPOTPY's extra machinery (Option B).
"""

from summa_python_interface import J, PARAM_NAMES

# TODO: replace with real, physically sensible bounds for each parameter
PARAM_BOUNDS = {
    "k_soil":    (0.01, 2.0),
    "theta_sat": (0.3,  0.6),
    "vGn_n":     (1.1,  3.0),
}


# ─────────────────────────────────────────────────────────────────
# Option A: scipy.optimize — simplest possible end-to-end test.
# Good first step: confirms the Fortran<->C<->Python chain actually
# works before layering on SPOTPY's sampling algorithms.
# ─────────────────────────────────────────────────────────────────
def run_scipy_optimize():
    from scipy.optimize import minimize

    x0     = [(lo + hi) / 2 for (lo, hi) in
              (PARAM_BOUNDS[p] for p in PARAM_NAMES)]
    bounds = [PARAM_BOUNDS[p] for p in PARAM_NAMES]

    # NOTE: minimize() minimizes. If SUMMA's objective is something you
    # want to *maximize* (e.g. KGE, NSE), wrap it as `lambda p: -J(p)`.
    result = minimize(lambda p: -J(p), x0=x0, bounds=bounds, method="Nelder-Mead")

    print("Optimal parameters:")
    for name, val in zip(PARAM_NAMES, result.x):
        print(f"  {name:12s} = {val:.4f}")
    print(f"Objective value: {result.fun:.4f}")
    return result


# ─────────────────────────────────────────────────────────────────
# Option B: SPOTPY — since evaluate_objective already computes the
# objective internally (rather than returning a raw simulated time
# series), the SPOTPY setup class just passes that value straight
# through simulation()/objectivefunction() rather than computing its
# own likelihood from obs vs sim.
# ─────────────────────────────────────────────────────────────────
class spot_setup:
    def __init__(self):
        import spotpy
        self.params = [
            spotpy.parameter.Uniform(name, low=lo, high=hi)
            for name, (lo, hi) in PARAM_BOUNDS.items()
        ]

    def parameters(self):
        import spotpy
        return spotpy.parameter.generate(self.params)

    def simulation(self, vector):
        # vector is ordered the same as self.params / PARAM_NAMES
        return [J(list(vector))]

    def evaluation(self):
        # SUMMA already computed the objective internally, so there's
        # no separate "observed" series to compare against here —
        # this is just a placeholder SPOTPY's API requires.
        return [0.0]

    def objectivefunction(self, simulation, evaluation, params=None):
        # simulation[0] is KGE from SUMMA (higher is better, 1 is perfect).
        # spotpy.algorithms.sceua sets optimization_direction="minimize",
        # so return -KGE: minimising -KGE maximises KGE. Drop the minus
        # sign only if you switch to a sampler that maximises.
        return -simulation[0]


def run_spotpy(n_runs=100):
    import spotpy
    setup = spot_setup()
    sampler = spotpy.algorithms.sceua(setup, dbname="summa_calib", dbformat="csv")
    sampler.sample(n_runs)
    return sampler


if __name__ == "__main__":
    print("Running Option A (scipy.optimize) as a first smoke test...")
    run_scipy_optimize()