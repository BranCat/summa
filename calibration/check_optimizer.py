"""
check_optimizer.py - verify the SPOTPY wiring without running SUMMA.

Replaces J() with a fast analytic objective shaped like KGE (best = 1.0 at a
known point) and runs SCE-UA against the real SummaSpotSetup. If the sign
convention and the parameter ordering are correct, the search recovers the
target and reports a KGE near 1.0.

Run from the repository root:  python calibration/check_optimizer.py
"""

import sys, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spotpy
import spotpy_setup

TARGET = (5e-05, 0.50, 2.0)


def fake_J(params, penalty=-1e6):
    k, t, n = params
    d = ((math.log10(k) - math.log10(TARGET[0])) / 3) ** 2 \
      + ((t - TARGET[1]) / 0.3) ** 2 \
      + ((n - TARGET[2]) / 2.8) ** 2
    return 1.0 - d


if __name__ == "__main__":
    spotpy_setup.J = fake_J

    setup = spotpy_setup.SummaSpotSetup()
    sampler = spotpy.algorithms.sceua(setup, dbname="fake_calib", dbformat="ram")
    sampler.sample(300)

    best = min(sampler.getdata()["like1"])   # objectivefunction returns -KGE
    print()
    print("best KGE:", -best, "  (1.0 is perfect; target is recovered if close)")
    print("VERDICT :", "right direction" if -best > 0.9 else "WRONG DIRECTION")
