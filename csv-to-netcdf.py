"""
csv_to_obs_netcdf.py
Convert Athabasca observed discharge CSV to the NetCDF format
expected by SUMMA's read_flowobs.f90.
"""
import pandas as pd
import xarray as xr

# Read CSV, keeping only the two real columns
df = pd.read_csv(
    "my_domain/settings/Athabasca_sedi_3_streamflow_processed.csv",
    usecols=[0, 1],
    names=["datetime", "discharge_cms"],
    header=0,
    parse_dates=["datetime"],
)

# Build an xarray Dataset with a time dimension and q_obs variable
ds = xr.Dataset(
    {"q_obs": ("time", df["discharge_cms"].values)},
    coords={"time": df["datetime"].values},
)
ds["q_obs"].attrs["units"] = "m3 s-1"
ds["q_obs"].attrs["long_name"] = "observed discharge"

out_path = "my_domain/mizuroute_inputs/Athabasca_sedi_3_streamflow_observations.nc"
ds.to_netcdf(out_path)
print(f"Wrote {out_path}")
print(ds)