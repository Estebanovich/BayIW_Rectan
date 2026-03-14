# BayIW_Rectan — Internal Waves in a Rectangular Bay

**Master's Degree Thesis Project**

This project uses the [MITgcm](https://mitgcm.org/) ocean general circulation model to simulate the generation and propagation of **internal waves** in a rectangular bay under realistic oceanic conditions. A central goal of the thesis is to compare the wave dynamics produced under three different stratification profiles:

- **Realistic stratification** — temperature and salinity initialized from February climatological data
- **Linear stratification** — linearly varying density profile
- **Two-layer stratification** — idealized two-layer density structure

The simulations are also run with and without the bay geometry to isolate the bay's influence on internal wave behavior.

---

## Project Structure

```
BayIW_Rectan/
├── build/                        # MITgcm compilation directory
├── code/                         # Model configuration and size files
│   ├── SIZE.h                    # Grid decomposition parameters
│   ├── packages.conf             # Enabled MITgcm packages
│   ├── OBCS_OPTIONS.h            # Open boundary condition options
│   └── DIAGNOSTICS_SIZE.h        # Diagnostics buffer sizes
├── input/                        # Forcing, bathymetry, and preprocessing scripts
│   ├── *.bin                     # Binary input files (bathymetry, grid spacing, T/S, wind)
│   ├── *.ipynb                   # Jupyter notebooks for generating input files
│   └── *.py                      # Python scripts for input generation
├── run_expand/                   # Run directory — with bay geometry
│   ├── data                      # Main model parameter file
│   ├── data.diagnostics          # Diagnostics configuration
│   ├── data.obcs                 # Open boundary condition parameters
│   ├── data.pkg                  # Package switches
│   └── mnc_*/                    # NetCDF output directories
├── run_expand_nobay/             # Run directory — without bay (control case)
├── compile_and_run_expand.sh     # Script to compile and run both simulations
└── run_expands.sh                # Alternative run script
```

---

## Model Configuration

| Parameter | Value |
|---|---|
| Model | MITgcm |
| Grid type | Cartesian |
| Horizontal resolution | Variable (expanded grid: ~560 × 352 points) |
| Vertical levels | 50 (stretched: 1 m near surface to ~46 m at depth) |
| Time step | 30 s |
| Simulation duration | 432 000 s total (~5 days, two stages) |
| Equation of state | Linear |
| Free surface | Implicit |
| Lateral viscosity | 100 m² s⁻¹ |
| Vertical viscosity | 1 × 10⁻⁵ m² s⁻¹ |
| Coriolis parameter (f₀) | 6.97 × 10⁻⁵ s⁻¹ |

### Packages used

| Package | Purpose |
|---|---|
| OBCS | Open boundary conditions (Orlanski radiation + sponge layers) |
| Diagnostics | Output of density anomaly fields (`RHOAnoma`) |
| MNC | NetCDF output |

### Boundary conditions

Open boundaries are applied on the south, west, and east edges using **Orlanski radiation** conditions. A sponge layer of 10 grid cells damps spurious reflections near the boundaries.

### Forcing

- **Wind**: Periodic meridional wind forcing applied in stage 1 only (period = 1200 s, cycle = 216 000 s)
- **Initial T/S**: February climatological profiles (50 vertical levels, 560 × 352 horizontal)

---

## Simulation Cases

| Run directory | Bay geometry | Description |
|---|---|---|
| `run_expand/` | With bay | Primary case with rectangular bay bathymetry |
| `run_expand_nobay/` | Without bay | Control case — open coastal domain |

Both cases share the same model executable and physical parameters, and follow the same two-stage run strategy described below.

### Two-stage run strategy

Each simulation is run in two consecutive stages:

| Stage | `startTime` | `endTime` | `nIter0` | Wind forcing | Purpose |
|---|---|---|---|---|---|
| 1 — Forced | 0 s | 216 000 s (~2.5 days) | 0 | ON (periodic, 1200 s period) | Wind-driven internal wave generation |
| 2 — Free | 216 000 s | 432 000 s (~5 days total) | 7200 | OFF | Free propagation and decay after forcing stops |

Stage 1 starts from rest with the February climatological T/S initial conditions and applies periodic wind forcing. It writes a checkpoint (`ckptA`) at the end. Stage 2 restarts from that checkpoint (`pickupSuff='ckptA'`) with the wind forcing disabled, allowing the internal wave field to propagate and decay freely.

The `data` files committed to the repository correspond to **stage 1**. To run stage 2, update `&PARM03` to:
```
startTime=216000., endTime=432000., nIter0=7200, pickupSuff='ckptA',
```
and comment out the `meridWindFile`, `hydrogThetaFile`, and `hydrogSaltFile` lines in `&PARM05`.

---

## Input File Generation

The `input/` directory contains Jupyter notebooks used to prepare all binary input files:

| Notebook | Purpose |
|---|---|
| `bahia_01_expand*.ipynb` | Bay bathymetry generation and refinement |
| `make_binary_*.ipynb` | Convert bathymetry to MITgcm binary format |
| `make_T_S_binary_files*.ipynb` | Generate T/S initial conditions (realistic, linear, two-layer) |
| `make_wind_forcing*.ipynb` | Generate wind forcing fields |
| `check_output*.ipynb` | Post-processing and visualization of model output |
| `compute_wind_energy.ipynb` | Compute wind energy input to the ocean |

---

## How to Compile and Run

### Requirements

- MITgcm source tree (expected at `../../../` relative to this directory)
- Fortran compiler (`gfortran`) — build options configured for `darwin_arm64_gfortran`
- MPI (optional, for parallel runs)
- Python 3 with `numpy`, `netCDF4`, `matplotlib` (for preprocessing and analysis)

### Compilation and execution

```bash
bash compile_and_run_expand.sh
```

The script will interactively ask whether to:
1. Clean the `build/` directory before compiling
2. Enable MPI compilation
3. Clean run directories before execution
4. Run with MPI (and how many cores)

Both `run_expand/` (with bay) and `run_expand_nobay/` (without bay) are run sequentially by the script.

### Manual run (single case)

```bash
cd run_expand
cp ../build/mitgcmuv .
./mitgcmuv > output.txt
```

Or with MPI:

```bash
mpirun -np 4 ./mitgcmuv > output.txt
```

---

## Output

Model output is written as **NetCDF** files into `mnc_*/` subdirectories within each run directory. The primary diagnostic field is:

- `diag_rho` — density anomaly (`RHOAnoma`), output every 900 s

---

## Scientific Context

Internal waves are gravity waves that propagate along density interfaces within the ocean interior. Bays and coastal geometries can trap, reflect, and amplify these waves, leading to intensified mixing and energy dissipation. This project investigates:

1. How a rectangular bay modifies internal wave generation and propagation compared to an open coast
2. How the choice of stratification profile (realistic vs. idealized) affects the simulated wave field
3. The energy budget associated with wind-forced internal waves in the bay

---

## Author

Master's Degree Thesis — *[University name]*
