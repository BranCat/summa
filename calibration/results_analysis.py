"""
compare_my_segment.py - compare simulated flow at ONE mizuRoute segment with observed discharge.

Workflow:
    1. python summa_python_interface.py     # runs SUMMA + mizuRoute, writes the coupled NetCDF
    2. edit the SETTINGS block below         # file paths + the segId you want
    3. python calibration/results_analysis.py

Output:
    - KGE (2009) with r / alpha / beta, NSE, PBIAS printed to screen
    - <OUT_PREFIX>.png : hydrograph + scatter
    - <OUT_PREFIX>.csv : date, sim, obs (the aligned daily series used for the metrics)
"""

# ============================ SETTINGS (edit these) ============================
import os
from pathlib import Path
# default: <repo>/my_domain — override with the SUMMA_DOMAIN environment variable
DOMAIN    = os.environ.get("SUMMA_DOMAIN", str(Path(__file__).resolve().parent.parent / "my_domain"))

# Q_reach is written to the *_timestep.nc file (the *_day.nc file has only SUMMA land variables)
SIM_FILE  = f"{DOMAIN}/work/run_1_calibrated_timestep.nc"
OBS_FILE  = f"{DOMAIN}/settings/Athabasca_sedi_3_streamflow_processed.csv"   # NetCDF or CSV
TOPO_FILE = None           # mizuRoute topology.nc; only needed if the output has no reachID.
                           # None = search DOMAIN for a NetCDF that contains segId

OUT_DIR   = f"{DOMAIN}/work/segment_comparison"   # where the PNG and CSV are written

SEG_ID    = 222            # segId of the segment to compare (the ID value, NOT the array position)

# ---- time range to evaluate (both dates included) ----
#   "01/01/2015" (MM/DD/YYYY) or "2015-01-01" both work; None = use all overlapping data
START     = "01/01/2014"
END       = "12/31/2019"

SPINUP_DAYS = 122          # days dropped from the start of the SIMULATION (0 = keep all);
                           # applies on top of START, so a START inside spin-up is moved later

SIM_VAR   = "Q_reach"      # routed flow variable in SIM_FILE [m3/s]
OBS_VAR   = None           # None = auto-detect (q_obs, discharge, ...); or give the name
METHOD    = None           # Q_reach has a 'method' dimension (one slot per routing scheme).
                           # None = first slot with valid data; or an index, e.g. 0, 1, 2 ...

OUT_PREFIX = None          # None = automatic, e.g. seg222_20150101-20191231
# ===============================================================================

import os
import sys
import glob
import numpy as np
import pandas as pd
import xarray as xr


def die(msg):
    sys.exit("ERROR: " + msg)


def parse_date(value, label):
    if value is None:
        return None
    try:
        return pd.to_datetime(value, format="%m/%d/%Y") if "/" in str(value) else pd.to_datetime(value)
    except Exception:
        die(f'{label} = "{value}" is not a date; use "MM/DD/YYYY" (e.g. "01/01/2015") or "YYYY-MM-DD"')


def find_topology():
    """Return TOPO_FILE, or search DOMAIN for a NetCDF that has a segId variable."""
    if TOPO_FILE:
        if not os.path.exists(TOPO_FILE):
            die(f"TOPO_FILE not found: {TOPO_FILE}")
        return TOPO_FILE
    cands = sorted(glob.glob(f"{DOMAIN}/**/*.nc", recursive=True),
                   key=lambda f: ("topo" not in os.path.basename(f).lower(), f))
    for f in cands:
        if os.path.abspath(f) == os.path.abspath(SIM_FILE):
            continue
        try:
            with xr.open_dataset(f) as d:
                if "segId" in d.variables:
                    return f
        except Exception:
            pass
    die(f"the output has no reachID and no topology file (NetCDF with segId) was found under {DOMAIN}; "
        "set TOPO_FILE to your mizuRoute topology.nc")


start = parse_date(START, "START")
end   = parse_date(END, "END")
if start is not None and end is not None and start > end:
    die(f"START ({start.date()}) is after END ({end.date()})")


# ---------- 1. simulated flow at SEG_ID ----------
if not os.path.exists(SIM_FILE):
    die(f"SIM_FILE not found: {SIM_FILE}")
if not os.path.exists(OBS_FILE):
    die(f"OBS_FILE not found: {OBS_FILE}")
sim_ds = xr.open_dataset(SIM_FILE)
if SIM_VAR not in sim_ds:
    die(f"{SIM_VAR} not in {SIM_FILE}. Variables: {sorted(sim_ds.data_vars)}")
q = sim_ds[SIM_VAR]
if "time" not in q.dims:
    die(f"{SIM_VAR} has no time dimension; dims = {q.dims}")
seg_dim = next((d for d in q.dims if d.lower() in ("seg", "segment", "reach", "reachid", "nseg")), None)
if seg_dim is None:
    others = [d for d in q.dims if d != "time"]
    if len(others) != 1:
        die(f"cannot tell which dimension of {SIM_VAR} is the segment: dims = {q.dims}")
    seg_dim = others[0]

# any extra dimension (e.g. 'method' = routing scheme): pick one slot
method_note = ""
for d in [d for d in q.dims if d not in ("time", seg_dim)]:
    n = q.sizes[d]
    labels = [str(v) for v in q[d].values] if d in q.coords else [str(i) for i in range(n)]
    # summary of each slot so the choice is visible
    print(f"{SIM_VAR} has a '{d}' dimension with {n} slot(s)  (stats over all segments):")
    valid = []
    for i in range(n):
        v = q.isel({d: i}).values
        v = v[np.isfinite(v) & (v > -9000)]
        valid.append(v.size)
        print(f"   {d}={i} ({labels[i]}): " + (f"mean {v.mean():.4g}, max {v.max():.4g}" if v.size else "no valid data"))
    if METHOD is None:
        good = [i for i in range(n) if valid[i] > 0]
        if not good:
            die(f"every '{d}' slot of {SIM_VAR} is empty or fill values")
        pick_i = good[0]
    else:
        pick_i = int(METHOD)
        if not 0 <= pick_i < n:
            die(f"METHOD = {METHOD} but '{d}' has only {n} slot(s) (0..{n-1})")
        if valid[pick_i] == 0:
            die(f"'{d}'={pick_i} has no valid data; choose another METHOD")
    print(f"   -> using {d}={pick_i}" + ("" if METHOD is not None else "  (set METHOD to choose another)"))
    method_note = f", {d}={pick_i}"
    q = q.isel({d: pick_i})
units = q.attrs.get("units", "?")

# segIds in output order: reachID in the output, otherwise segId in the topology file
id_var = next((v for v in ["reachID", "segId", "seg_id", "reach_id"]
               if v in sim_ds.variables and sim_ds[v].dims == (seg_dim,)), None)
if id_var:
    seg_ids = sim_ds[id_var].values.astype(int)
    id_source = f"{id_var} (output)"
else:
    topo_path = find_topology()
    with xr.open_dataset(topo_path) as topo:
        seg_ids = topo["segId"].values.astype(int)
    id_source = f"segId in {os.path.basename(topo_path)}"
    if len(seg_ids) != q.sizes[seg_dim]:
        die(f"output has {q.sizes[seg_dim]} segments but {topo_path} has {len(seg_ids)} "
            "(network pruned by seg_outlet?) - need reachID in the output")

where = np.where(seg_ids == SEG_ID)[0]
if where.size == 0:
    die(f"segId {SEG_ID} not found. First few segIds: {sorted(seg_ids.tolist())[:15]} ...")
ix = int(where[0])

sim = q.isel({seg_dim: ix}).to_series()
sim = sim.where(sim > -9000)                              # mask fill values
sim = sim.resample("D").mean()                            # hourly -> daily mean
if SPINUP_DAYS:
    sim = sim[sim.index >= sim.index[0] + pd.Timedelta(days=SPINUP_DAYS)]
sim.name = "sim"

# ---------- 2. observed flow ----------
if OBS_FILE.lower().endswith((".csv", ".txt")):
    df = pd.read_csv(OBS_FILE)
    low = {c.lower().strip(): c for c in df.columns}
    # date column: by name first, otherwise the first column that parses as dates
    tcol = next((low[k] for k in ["date", "datetime", "time", "date_time", "timestamp"] if k in low), None)
    if tcol is None:
        for c in df.columns:
            if pd.to_datetime(df[c].astype(str), errors="coerce").notna().mean() > 0.9:
                tcol = c
                break
    if tcol is None:
        die(f"cannot find a date column in {OBS_FILE}: {list(df.columns)}")
    # discharge column: OBS_VAR, else by name, else the last numeric column that isn't the date
    if OBS_VAR:
        if OBS_VAR not in df.columns:
            die(f'OBS_VAR "{OBS_VAR}" not in {OBS_FILE}: {list(df.columns)}')
        vcol = OBS_VAR
    else:
        vcol = next((low[k] for k in ["discharge", "discharge_cms", "q_obs", "qobs", "streamflow",
                                      "flow", "value", "q", "obs"] if k in low), None)
        if vcol is None:
            nums = [c for c in df.select_dtypes("number").columns if c != tcol]
            if not nums:
                die(f"no numeric discharge column in {OBS_FILE}: {list(df.columns)}; set OBS_VAR")
            vcol = nums[-1]
    obs = pd.Series(pd.to_numeric(df[vcol], errors="coerce").values,
                    index=pd.to_datetime(df[tcol]), dtype=float)
    obs = obs[obs.index.notna()]
    print(f"observed     : column '{vcol}' by date column '{tcol}' from {os.path.basename(OBS_FILE)}")
else:
    obs_ds = xr.open_dataset(OBS_FILE)
    name = OBS_VAR or next((v for v in ["q_obs", "Q_obs", "qobs", "discharge", "streamflow", "flow", "Q"]
                            if v in obs_ds), None)
    if name is None:
        die(f"cannot tell which variable is discharge in {OBS_FILE}: {sorted(obs_ds.data_vars)}; set OBS_VAR")
    obs = obs_ds[name].squeeze().to_series().astype(float)
obs = obs.where(obs >= 0).resample("D").mean()
obs.name = "obs"

# ---------- 3. align on common days ----------
both = pd.concat([sim, obs], axis=1, sort=True)
sim_span = f"{sim.dropna().index[0].date()} .. {sim.dropna().index[-1].date()}"
obs_span = f"{obs.dropna().index[0].date()} .. {obs.dropna().index[-1].date()}"
if start is not None: both = both[both.index >= start]
if end   is not None: both = both[both.index <= end]
both = both.dropna()
if len(both) < 30:
    die(f"only {len(both)} days with both sim and obs in the requested range "
        f"{start.date() if start is not None else 'start'} .. {end.date() if end is not None else 'end'}\n"
        f"       simulation (after spin-up) covers {sim_span}\n       observations cover {obs_span}")

# tell the user if the requested range was cut short by the data
got0, got1 = both.index[0], both.index[-1]
if start is not None and got0 > start + pd.Timedelta(days=1):
    print(f"note: requested START {start.date()}, but data only begin {got0.date()} "
          f"(sim after spin-up: {sim_span}; obs: {obs_span})")
if end is not None and got1 < end - pd.Timedelta(days=1):
    print(f"note: requested END {end.date()}, but data only reach {got1.date()} "
          f"(sim after spin-up: {sim_span}; obs: {obs_span})")
missing = (got1 - got0).days + 1 - len(both)
if missing > 0:
    print(f"note: {missing} days inside the period have no sim or no obs and were skipped")

if OUT_PREFIX is None:
    OUT_PREFIX = f"seg{SEG_ID}_{got0:%Y%m%d}-{got1:%Y%m%d}"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PREFIX = os.path.join(OUT_DIR, OUT_PREFIX)

s, o = both["sim"].values, both["obs"].values

# ---------- 4. metrics ----------
r     = np.corrcoef(s, o)[0, 1]
alpha = s.std() / o.std()
beta  = s.mean() / o.mean()
kge   = 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)
nse   = 1 - np.sum((s - o) ** 2) / np.sum((o - o.mean()) ** 2)
pbias = 100 * (s.sum() - o.sum()) / o.sum()

print(f"simulated    : {SIM_VAR} [{units}] from {os.path.basename(SIM_FILE)}")
print(f"segment      : segId {SEG_ID} (column {ix} of {len(seg_ids)}, IDs from {id_source}{method_note})")
print(f"period       : {both.index[0].date()} .. {both.index[-1].date()}  ({len(both)} days)")
print(f"KGE          : {kge:.4f}   (r={r:.3f}, alpha={alpha:.3f}, beta={beta:.3f})")
print(f"NSE          : {nse:.4f}")
print(f"PBIAS        : {pbias:.1f} %")
print(f"mean sim/obs : {s.mean():.4g} / {o.mean():.4g} m3/s")
print(f"max  sim/obs : {s.max():.4g} / {o.max():.4g} m3/s")
if beta > 30 or beta < 1 / 30:
    print(f"\n!! simulated mean is x{beta:.3g} the observed - a reach choice cannot cause this; "
          "check runoff/area units at the SUMMA->mizuRoute coupling (x1000 = m/s vs mm/s, x1e6 = km2 vs m2)")

both.to_csv(f"{OUT_PREFIX}.csv", index_label="date")

# ---------- 5. plot ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.5), gridspec_kw={"width_ratios": [3, 1]})
a1.plot(both.index, o, color="black", lw=1, label="observed")
a1.plot(both.index, s, color="tab:blue", lw=1, alpha=0.85, label=f"simulated (segId {SEG_ID})")
a1.set_ylabel("discharge (m$^3$/s)")
a1.set_title(f"segId {SEG_ID}   KGE={kge:.3f}  NSE={nse:.3f}  PBIAS={pbias:.1f}%")
a1.legend(frameon=False)
lim = [0, max(s.max(), o.max()) * 1.05]
a2.scatter(o, s, s=4, alpha=0.4, color="tab:blue")
a2.plot(lim, lim, "k--", lw=0.8)
a2.set_xlim(lim); a2.set_ylim(lim)
a2.set_xlabel("observed (m$^3$/s)"); a2.set_ylabel("simulated (m$^3$/s)")
fig.tight_layout()
fig.savefig(f"{OUT_PREFIX}.png", dpi=150)
print(f"\nwrote {OUT_PREFIX}.png and {OUT_PREFIX}.csv")