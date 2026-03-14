#!/usr/bin/env python3
"""
Compute wind-work power time series and total energy input from wind stress forcing.

Primary (physical) definition used:
    Power(t) = ∬ (tau_x * u_surf + tau_y * v_surf) dA
    Energy    = ∫ Power(t) dt

If surface velocities are not provided, the script can optionally compute
proxy diagnostics (NOT energy):
    I(t) = ∬ |tau| dA          [N]
    S(t) = ∬ |tau|^2 dA        [N^2 m^2]

All files are assumed big-endian float64 (MITgcm-style) unless --dtype is given.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np


def read_bin(path: Path, shape: Tuple[int, ...], dtype: str, order: str) -> np.ndarray:
    data = np.fromfile(path, dtype=dtype)
    expected = int(np.prod(shape))
    if data.size != expected:
        raise ValueError(
            f"Size mismatch for {path}: got {data.size} values, expected {expected}"
        )
    return data.reshape(shape, order=order)


def read_delx_dely(dx_path: Path, dy_path: Path, nx: int, ny: int, dtype: str) -> np.ndarray:
    dx = np.fromfile(dx_path, dtype=dtype)
    dy = np.fromfile(dy_path, dtype=dtype)

    if dx.size == nx:
        delx = dx.reshape((nx,))
    elif dx.size == nx * ny:
        delx = dx.reshape((nx, ny), order="F")
    else:
        raise ValueError(f"Unexpected dx size {dx.size}; expected {nx} or {nx*ny}")

    if dy.size == ny:
        dely = dy.reshape((ny,))
    elif dy.size == nx * ny:
        dely = dy.reshape((nx, ny), order="F")
    else:
        raise ValueError(f"Unexpected dy size {dy.size}; expected {ny} or {nx*ny}")

    if delx.ndim == 1 and dely.ndim == 1:
        area = delx[:, None] * dely[None, :]
    else:
        # If both are 2D, multiply elementwise (assume same shape)
        area = delx * dely

    return area


def load_tau(path: Path, nx: int, ny: int, nt: int, dtype: str) -> np.ndarray:
    # make_wind_forcing_local writes data as (t,y,x)
    raw = read_bin(path, (nt, ny, nx), dtype=dtype, order="C")
    # return as (nx, ny, nt)
    return raw.transpose(2, 1, 0)


def load_surface_velocity(
    path: Path,
    nx: int,
    ny: int,
    nt: int,
    nz: int,
    dtype: str,
    order: str,
    k_surf: int,
) -> np.ndarray:
    if path.suffix in {".npy"}:
        arr = np.load(path)
    else:
        shape = (nt, nz, ny, nx)
        arr = read_bin(path, shape, dtype=dtype, order=order)

    if arr.ndim == 3:
        # Already (nt, ny, nx)
        surf = arr
    elif arr.ndim == 4:
        surf = arr[:, k_surf, :, :]
    else:
        raise ValueError(f"Unexpected velocity array ndim {arr.ndim}")

    return surf.transpose(2, 1, 0)  # (nx, ny, nt)


def main() -> None:
    p = argparse.ArgumentParser(description="Wind power and energy from MITgcm wind stress")

    p.add_argument("--tau", required=True, type=Path, help="merid_*.bin wind stress file")
    p.add_argument("--nx", required=True, type=int)
    p.add_argument("--ny", required=True, type=int)
    p.add_argument("--nt", required=True, type=int)

    p.add_argument("--dx", required=True, type=Path, help="delX binary file")
    p.add_argument("--dy", required=True, type=Path, help="delY binary file")
    p.add_argument("--bathy", type=Path, help="bathymetry file for ocean mask (negative = ocean)")

    p.add_argument("--uvel", type=Path, help="surface UVEL (nt,nz,ny,nx) or (nt,ny,nx)")
    p.add_argument("--vvel", type=Path, help="surface VVEL (nt,nz,ny,nx) or (nt,ny,nx)")
    p.add_argument("--nz", type=int, default=1, help="number of vertical levels if 4D")
    p.add_argument("--k_surf", type=int, default=0, help="surface level index (0 = top)")

    p.add_argument("--dt", type=float, help="time step between wind records [s]")
    p.add_argument("--end_time_hours", type=float, help="end_time in hours (if dt not given)")

    p.add_argument("--dtype", default=">f8", help="numpy dtype, default >f8")
    p.add_argument("--order", default="F", help="Fortran order for velocity files, default F")
    p.add_argument("--save_csv", type=Path, help="optional path to save time series CSV")

    args = p.parse_args()

    if args.dt is None:
        if args.end_time_hours is None:
            raise ValueError("Provide --dt (seconds) or --end_time_hours")
        args.dt = (args.end_time_hours * 3600.0) / (args.nt - 1)

    area = read_delx_dely(args.dx, args.dy, args.nx, args.ny, args.dtype)

    if args.bathy is not None:
        bathy = read_bin(args.bathy, (args.nx, args.ny), dtype=args.dtype, order="F")
        mask = bathy < 0
        area = area * mask

    tau_y = load_tau(args.tau, args.nx, args.ny, args.nt, args.dtype)
    tau_x = np.zeros_like(tau_y)

    have_vel = args.uvel is not None and args.vvel is not None

    if have_vel:
        u = load_surface_velocity(
            args.uvel, args.nx, args.ny, args.nt, args.nz, args.dtype, args.order, args.k_surf
        )
        v = load_surface_velocity(
            args.vvel, args.nx, args.ny, args.nt, args.nz, args.dtype, args.order, args.k_surf
        )

        power = (tau_x * u + tau_y * v) * area[:, :, None]
        power_t = power.sum(axis=(0, 1))  # W
        energy_total = np.trapz(power_t, dx=args.dt)  # J

        print("Power time series [W] (first 5):", power_t[:5])
        print("Total energy input [J]:", energy_total)

        if args.save_csv:
            t = np.arange(args.nt) * args.dt
            out = np.column_stack([t, power_t])
            header = "time_s,power_W"
            np.savetxt(args.save_csv, out, delimiter=",", header=header, comments="")
            print(f"Saved CSV: {args.save_csv}")

    else:
        # Proxy diagnostics (NOT energy)
        tau_mag = np.sqrt(tau_x ** 2 + tau_y ** 2)
        impulse_t = (tau_mag * area[:, :, None]).sum(axis=(0, 1))
        stress2_t = ((tau_mag ** 2) * area[:, :, None]).sum(axis=(0, 1))

        print("No surface velocities provided. Reporting proxy diagnostics:")
        print("I(t)=∬|tau| dA [N] (first 5):", impulse_t[:5])
        print("S(t)=∬|tau|^2 dA [N^2 m^2] (first 5):", stress2_t[:5])

        if args.save_csv:
            t = np.arange(args.nt) * args.dt
            out = np.column_stack([t, impulse_t, stress2_t])
            header = "time_s,impulse_N,stress2_N2m2"
            np.savetxt(args.save_csv, out, delimiter=",", header=header, comments="")
            print(f"Saved CSV: {args.save_csv}")


if __name__ == "__main__":
    main()
