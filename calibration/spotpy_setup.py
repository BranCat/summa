"""
spotpy_setup.py

Minimal SPOTPY setup wrapping the SUMMA/mizuRoute J(params) objective
function (summa_python_interface.py) for calibration.

J() already returns the final objective (KGE, computed internally by
SUMMA/mizuRoute) — so simulation() and objectivefunction() are thin
pass-throughs rather than doing their own computation.

IMPORTANT: parameter bounds below are placeholders — confirm actual
calibration ranges with Martyn before a real run.
"""

import spotpy
from summa_python_interface import J, PARAM_NAMES


class SummaSpotSetup:
    def __init__(self):
        # TODO: confirm real bounds with Martyn — these are placeholders
        self.params = [
            spotpy.parameter.Uniform("k_soil", low=1e-7, high=1e-4),
            spotpy.parameter.Uniform("theta_sat", low=0.35, high=0.65),
            spotpy.parameter.Uniform("vGn_n", low=1.2, high=4.0),
        ]

        # The vector SPOTPY passes is positional, and PARAM_NAMES assigns
        # meaning by position on the Fortran side - so the two must agree.
        assert [q.name for q in self.params] == list(PARAM_NAMES), \
            "SPOTPY parameter order does not match PARAM_NAMES"

    def parameters(self):
        return spotpy.parameter.generate(self.params)

    def simulation(self, vector):
        # vector order matches self.params order, which matches PARAM_NAMES
        return [J(list(vector))]

    def evaluation(self):
        # No separate "observed" series needed — J() already returns
        # the objective directly, so this is just a placeholder target.
        return [0.0]

    def objectivefunction(self, simulation, evaluation, params=None):
        # simulation[0] is KGE, computed inside SUMMA by get_kge() in
        # build/source/objfunc/metrics.f90. KGE is higher-is-better,
        # with 1 the perfect score.
        #
        # spotpy.algorithms.sceua sets optimization_direction="minimize",
        # so the sign is flipped here: minimising -KGE maximises KGE.
        # If you switch to a sampler that maximises, drop the minus sign.
        return -simulation[0]


if __name__ == "__main__":
    setup = SummaSpotSetup()

    # Quick smoke test: a handful of random samples, not a real calibration
    sampler = spotpy.algorithms.mc(setup, dbname="summa_spotpy_test", dbformat="csv")
    sampler.sample(5)  # 5 iterations — just confirming the plumbing works

    results = spotpy.analyser.load_csv_results("summa_spotpy_test")
    print(results)