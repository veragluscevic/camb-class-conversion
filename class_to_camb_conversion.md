# CLASS-to-CAMB Transfer Function Conversion Script

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This document must be maintained in accordance with `.agent/PLANS.md`.


## Purpose / Big Picture

The dwarf-galaxy simulation pipeline requires transfer function files in CAMB's 13-column format so that MUSIC (a cosmological initial-conditions generator) can ingest them. The transfer functions themselves are computed by a modified version of CLASS (the "dmeff" branch, which supports dark-matter–baryon scattering). CLASS outputs transfer functions in its own format, which MUSIC cannot read directly. This plan delivers a Python script (`class_to_camb.py`) that reads CLASS output files and writes a single CAMB-format file suitable for MUSIC.

After this change, a user can run CLASS twice — once in synchronous gauge and once in Newtonian gauge, both with `format = class` and `output = ..., mTk, vTk` — then run `class_to_camb.py` to produce a file like `test_transfer_z99.dat` — a 13-column CAMB transfer file with density and velocity transfer functions. The script works for both standard CDM runs and dmeff runs without any code changes; it auto-detects the species present by parsing the CLASS header. No `format = camb` CLASS option is used; the script performs all conversions itself.

The validation target is `test_transfer_z99.dat`, a CAMB-generated CDM transfer file at z=99. The script's CDM output closely reproduces its column values (<0.25% for all MUSIC-relevant columns).


## Progress

- [x] Milestone 1: Core conversion logic (density-only) — produce columns 0–9 and validate against `test_transfer_z99.dat`.
- [x] Milestone 2: Add velocity conversion — produce columns 10–12 and validate.
- [x] Milestone 3: Generality — confirm the script works on both CDM-only and dmeff CLASS outputs.
- [x] Milestone 4: Two-gauge approach — use synchronous gauge for densities, Newtonian gauge for velocities.


## Surprises & Discoveries

- The CLASS transfer file for this cosmology (with dmeff enabled but Omega_dmeff negligible) has 16 columns including `d_dmeff`, `t_dmeff`, `d_fld`, `t_fld`. The `t_fld` column contains NaN values, but it is not needed for conversion so this is harmless.
- The `d_fld` column is all zeros (no dark energy perturbations in CLASS's fluid approximation at z=99).
- **CAMB uses a mixed-gauge convention**: density columns use synchronous gauge, velocity columns use Newtonian gauge. This was discovered by examining Rui's original script (`rui_camb.py`), which uses two separate CLASS runs — one in each gauge — and confirmed by reading the MUSIC source code (`transfer_camb.cc`).
- **A single Newtonian-gauge CLASS run cannot work for densities.** In Newtonian gauge, δ_cdm → −2Ψ ≈ const at low k (no k² suppression), so dividing by k² gives T_cdm ~ 2.3×10¹⁰ vs CAMB's 2.4×10⁵. The formula T = −δ/k² is only valid in synchronous gauge where δ ~ k² on super-horizon scales.
- **Gauge transformation from Newtonian to synchronous is numerically destructive** for densities: it involves subtracting two nearly equal O(1) numbers to recover a residual of O(10⁻⁵), losing ~5 significant digits.
- **Photon and neutrino columns (3, 4) are not trustworthy**: the sync-gauge photon transfer function disagrees with CAMB by up to ~70% in the acoustic oscillation range (5×10⁻³ < k < 0.1 h/Mpc). This is the intrinsic CAMB-vs-CLASS difference amplified because the photon perturbation is a tiny residual of canceling oscillatory terms in that range. CDM/baryon/total are not affected because they don't oscillate.
- **MUSIC discards most columns.** Reading the MUSIC source code (`transfer_camb.cc`), MUSIC only uses columns 0 (k/h), 1 (CDM), 2 (baryon), 6 (total), 10 (v_CDM), 11 (v_b). All other columns — including photon, nu, mass_nu, no_nu, total_de, Weyl, v_b-v_c — are read into `dummy` and discarded. The photon/neutrino disagreement has no practical impact.
- **CLASS's `d_tot` includes radiation**, not just matter. At z=99, radiation is ~3% of the non-Λ energy density, so using `d_tot` for CAMB's "total" column would introduce a ~3% systematic error. The matter-only total must be computed manually as (Ω_cdm·δ_cdm + Ω_b·δ_b)/(Ω_cdm + Ω_b), which is why omega_cdm and omega_b are still required as parameters.
- All CLASS runs use `format = class` (not `format = camb`). The conversion from CLASS's δ to CAMB's T = −δ/(kh)² is done by the script, not by CLASS.
- The cosmological parameters (h, Omega_cdm, Omega_b) could in principle be auto-extracted from the CLASS background file at z=0 (rho_b/rho_crit, rho_cdm/rho_crit, H₀×c/100), but this has not been implemented — they remain command-line arguments.


## Decision Log

- Decision: Keep synchronous gauge for velocities; do NOT reconstruct Newtonian-gauge CDM velocity.
  Rationale: User explicitly requested this. In synchronous gauge, θ_cdm = 0 by construction. The script will output v_CDM = 0 for CDM-only runs. For dmeff runs, θ_dmeff ≠ 0, so v_CDM (populated from θ_dmeff) will be nonzero. This means the CDM validation case will NOT match `test_transfer_z99.dat` in the v_CDM column (CAMB gives a nonzero Newtonian-gauge value), but that is accepted.
  Date: 2026-02-23
  Status: **Superseded** by the two-gauge approach (2026-02-24).

- Decision: Use d_cdm (only) for the "CDM" output column.
  Rationale: User requested this for the initial version. The dmeff density will be revisited later.
  Date: 2026-02-23

- Decision: Match Rui's output style — zero out columns that CLASS cannot directly provide (mass_nu, no_nu, total_de) and populate only the columns Rui populated: k/h, CDM, baryon, total, v_CDM, v_b. Additionally populate photon, nu, and Weyl since CLASS provides these directly and `test_transfer_z99.dat` has them.
  Rationale: User wants to match Rui's script as closely as possible, but also wants to match `test_transfer_z99.dat` as a validation test. Populating photon/nu/Weyl gets us closer to the CAMB reference. Columns that require combining multiple species with density fractions (no_nu, total_de) are zeroed because Rui zeroed them and the exact CAMB definitions are ambiguous.
  Date: 2026-02-23

- Decision: Parse CLASS header to find columns by name, not by hard-coded index.
  Rationale: CLASS column layout changes depending on which species are present (e.g., d_dmeff/t_dmeff columns appear only when Omega_dmeff > 0, and d_fld/t_fld may or may not be present). Hard-coded indices were the root cause of the bugs in `vg_camb.py`.
  Date: 2026-02-23

- Decision: Use two CLASS runs — synchronous gauge for densities, Newtonian gauge for velocities.
  Rationale: CAMB's output format uses synchronous gauge for density transfer functions and Newtonian gauge for velocity transfer functions. A single Newtonian-gauge run cannot produce correct density columns (δ^Newt doesn't have the k² suppression that T = −δ/k² requires). A single synchronous-gauge run gives v_CDM = 0 (θ_cdm = 0 by construction). Rui's original script uses the same two-run approach. Both runs use `format = class`, not `format = camb`.
  Date: 2026-02-24


## Outcomes & Retrospective

All four milestones complete. The script `class_to_camb.py` now takes two CLASS transfer function files (synchronous gauge for densities, Newtonian gauge for velocities) plus a background file. All MUSIC-relevant columns validated against CAMB reference to <0.25%:

| Column | Name   | Max deviation | Source                    |
|--------|--------|---------------|---------------------------|
| 0      | k/h    | exact         | CLASS k-grid              |
| 1      | CDM    | 0.16%         | sync-gauge d_cdm          |
| 2      | baryon | 0.24%         | sync-gauge d_b            |
| 6      | total  | 0.17%         | Ω-weighted d_cdm + d_b   |
| 10     | v_CDM  | 0.17%         | Newtonian-gauge t_cdm     |
| 11     | v_b    | 0.19%         | Newtonian-gauge t_b       |

Columns 3 (photon), 4 (nu), 5 (mass_nu), 7 (no_nu), 8 (total_de), 9 (Weyl), 12 (v_b-v_c) are filled for format compliance but are not trustworthy or not used by MUSIC (see comments in `class_to_camb.py`).


## Context and Orientation

This workspace lives at the repository root. Key files:

- `rui_camb.py` — Rui's original conversion script for WDM/dmeff. It reads three files (a sync-gauge density file, a Newtonian-gauge velocity file, and a CLASS background file), converts CLASS velocity divergences θ to CAMB's velocity convention, and writes a 13-column CAMB file. This script uses hard-coded column indices, which break when the CLASS column layout changes. DO NOT MODIFY.

- `vg_camb.py` — The user's earlier adaptation of Rui's script for CDM. Superseded by `class_to_camb.py`.

- `test_transfer_z99.dat` (also in `data_tk/`) — A 13-column CAMB transfer function file at z=99 for a standard ΛCDM cosmology (h=0.7, Ω_cdm=0.239, Ω_b=0.047, Ω_Λ=0.714). Generated by actual CAMB. This is the validation reference. It has 213 data rows and 13 columns: k/h, CDM, baryon, photon, nu, mass_nu, total, no_nu, total_de, Weyl, v_CDM, v_b, v_b-v_c.

- `minimal.ini` — CLASS parameter file for the **synchronous-gauge** run. Set to `format = class`, `gauge = synchronous`, `output = tCl,pCl,lCl,mPk, mTk, vTk`. Root is `output/CDM_class_V`. Cosmology matches `test_transfer_z99.dat`.

- `minimal_newtonian.ini` — CLASS parameter file for the **Newtonian-gauge** run. Same as `minimal.ini` but with `gauge = newtonian` and `root = output/CDM_class_N`. Produces the velocity transfer functions used for CAMB columns 10–12.

- `output/CDM_class_Vtk.dat` — Synchronous-gauge CLASS transfer function output at z=99. Used for density columns.

- `output/CDM_class_Ntk.dat` — Newtonian-gauge CLASS transfer function output at z=99. Used for velocity columns.

- `output/CDM_class_Vbackground.dat` — CLASS background file. Column 4 (1-indexed) is H(z) in 1/Mpc units.

- `class_dmeff_rui_used/` — The dmeff CLASS source code. DO NOT MODIFY.

### Key physics: the conversion formulas

"Transfer functions" describe how density and velocity perturbations of each species depend on wavenumber k at a given redshift z. CAMB and CLASS compute the same physics but output in different conventions.

**Density conversion.** CLASS outputs the fractional overdensity δ_i(k,z) directly. CAMB outputs the "rescaled transfer function" T_i = −δ_i / k² where k is in Mpc⁻¹. Since CLASS reports k in h/Mpc, the conversion is:

    T_CAMB_i = −d_CLASS_i / (k_CLASS · h)²

where k_CLASS is the k column from CLASS (in h/Mpc) and h is the dimensionless Hubble parameter (0.7 in our cosmology).

**Velocity conversion.** CLASS outputs the velocity divergence θ_i(k,z) (conformal-time convention). CAMB's velocity transfer function relates to θ by:

    v_CAMB_i = (1 + z) · θ_CLASS_i / ((k_CLASS · h)² · H(z))

where H(z) is the Hubble rate in Mpc⁻¹ (from the CLASS background file). Velocities must come from a **Newtonian-gauge** CLASS run. In synchronous gauge, θ_cdm = 0 identically, so using sync-gauge velocities would incorrectly give v_CDM = 0.

**Weyl potential.** CAMB's Weyl column is −(ϕ + ψ)/2 where ϕ and ψ are the CLASS metric potentials (columns `phi` and `psi`). No k² rescaling is applied.

**Total matter.** CAMB's "total" column is the density-weighted matter transfer: (Ω_cdm·δ_cdm + Ω_b·δ_b) / (Ω_cdm + Ω_b), then rescaled by −1/(k·h)². This excludes radiation and dark energy.

### Output format

13 columns, whitespace-separated, one header line starting with `#`. Numeric format: `%15.6e` (matching Rui's script). Column order:

    k/h  CDM  baryon  photon  nu  mass_nu  total  no_nu  total_de  Weyl  v_CDM  v_b  v_b-v_c


## Plan of Work

The script `class_to_camb.py` reads three CLASS files — a synchronous-gauge transfer file (for densities), a Newtonian-gauge transfer file (for velocities), and a background file — plus cosmological parameters (h, Ω_cdm, Ω_b, z). It writes a single 13-column CAMB-format file.

The two-gauge approach is necessary because CAMB's output convention uses synchronous gauge for density transfer functions and Newtonian gauge for velocity transfer functions. Both CLASS runs use `format = class` (not `format = camb`); all conversions are performed by the script.

The script has three logical parts:

1. **Header parser.** Read a CLASS transfer file header line (the last `#`-prefixed line before data begins) and build a dictionary mapping column names (like `d_cdm`, `t_b`, `phi`) to 0-based column indices. This makes the script robust to CLASS column layout changes.

2. **Background reader.** Read the CLASS background file, extract the z and H(z) columns (columns 0 and 3, 0-indexed), build a spline, and evaluate H at the target redshift.

3. **Converter.** From the sync-gauge file, compute density columns (T = −δ/(kh)² for CDM, baryon, photon, neutrino), the total matter column (Ω-weighted CDM + baryon), and the Weyl potential. From the Newtonian-gauge file, compute velocity columns (v = (1+z)·θ/(kh²·H)). Columns that cannot be reliably populated (mass_nu, no_nu, total_de) are set to zero. If a column like `d_dmeff` or `t_dmeff` exists in a CLASS file, the script can use it; otherwise it falls back gracefully.

The script is invoked as:

    python class_to_camb.py output/CDM_class_Vtk.dat output/CDM_class_Ntk.dat output/CDM_class_Vbackground.dat --h 0.7 --omega_cdm 0.239 --omega_b 0.047 --z 99 -o CDM_Tk.dat

All parameters have sensible defaults matching the current cosmology.


## Concrete Steps

### Milestone 1: Density columns (0–9)

Create `class_to_camb.py` with the header parser and density conversion using a synchronous-gauge CLASS file. Velocity columns set to zero initially. Validate density columns 0–6 and Weyl (col 9) against `test_transfer_z99.dat`. **Completed**: CDM, baryon, total agree to <0.2%.

### Milestone 2: Velocity columns (10–12)

Add velocity conversion using the background H(z) spline. Initially used sync-gauge velocities, giving v_CDM = 0 (θ_cdm = 0 in sync gauge). **Completed** with the caveat that sync-gauge velocities disagree with CAMB's Newtonian-gauge convention.

### Milestone 3: Generality test

Verify the script works on both CDM-only (14-column) and dmeff (16-column) CLASS outputs. **Completed**: header parser correctly handles both layouts.

### Milestone 4: Two-gauge approach

Following Rui's approach, the script now accepts two CLASS transfer files:
- Synchronous gauge (`minimal.ini`, `gauge = synchronous`) → density columns
- Newtonian gauge (`minimal_newtonian.ini`, `gauge = newtonian`) → velocity columns

Both CLASS runs use `format = class`. Validation command:

    python class_to_camb.py output/CDM_class_Vtk.dat output/CDM_class_Ntk.dat \
        output/CDM_class_Vbackground.dat \
        --h 0.7 --omega_cdm 0.239 --omega_b 0.047 --z 99 -o CDM_Tk.dat

**Completed**: all six MUSIC-relevant columns now agree with CAMB to <0.25%.


## Validation and Acceptance

The primary acceptance test is a quantitative comparison of the output against `test_transfer_z99.dat`. Since the k-grids differ (213 vs 845 points), the comparison requires interpolation. The script `plot_test.py` (already in the repo) demonstrates this technique.

Acceptance criteria (all met with two-gauge approach):
- **CDM, baryon, total** (cols 1, 2, 6): agree with `test_transfer_z99.dat` to <0.25%.
- **v_CDM, v_b** (cols 10, 11): agree to <0.25% (using Newtonian-gauge CLASS).
- **Weyl** (col 9): agrees to ~0.2% (not used by MUSIC).
- **Photon, nu** (cols 3, 4): NOT trustworthy — up to 70% deviation in acoustic regime. Not used by MUSIC.
- **mass_nu, no_nu, total_de** (cols 5, 7, 8): zero (matching Rui's convention). Not used by MUSIC.
- Output file has exactly 13 columns and a header that MUSIC can parse.


## Idempotence and Recovery

The script is stateless and can be re-run any number of times. It overwrites the output file if it already exists. No side effects on input files.


## Interfaces and Dependencies

Python standard library plus numpy and scipy (both already available in the user's environment). No new dependencies.

In `class_to_camb.py`, the key functions:

    def parse_class_header(filepath):
        """Read a CLASS transfer file and return (column_name_to_index dict, data array).
        Parses the last comment line to extract column names like 'd_cdm', 't_b', 'phi'."""

    def read_background_hubble(filepath, z):
        """Read a CLASS background file, interpolate H(z), return H in 1/Mpc."""

    def class_to_camb(tk_sync_file, tk_newt_file, bg_file, h, omega_cdm, omega_b, z, output_file):
        """Main conversion: read two CLASS transfer files (sync gauge for densities,
        Newtonian gauge for velocities) + background, compute 13 CAMB columns, write output."""

Command-line interface via argparse with three positional args (sync transfer file, Newtonian transfer file, background file) and optional flags for cosmological parameters and output path.


## Artifacts and Notes

CAMB column values at first k-point from `test_transfer_z99.dat` (for validation):

    k/h=1.00899e-05  CDM=2.42511e+05  baryon=2.42511e+05  photon=3.23347e+05
    nu=3.23347e+05  mass_nu=0  total=2.42511e+05  no_nu=2.42511e+05
    total_de=2.52164e+05  Weyl=-6.04576e-01  v_CDM=2.41398e+05
    v_b=2.41398e+05  v_b-v_c=3.76643e-01

CLASS column values at first k-point from `CDM_class_Vtk.dat` (with dmeff, 16 columns):

    k=1.009e-05  d_g=-1.613e-05  d_b=-1.210e-05  d_cdm=-1.210e-05
    d_dmeff=-1.210e-05  d_fld=0  d_ur=-1.613e-05  d_tot=-1.221e-05
    phi=6.124e-01  psi=5.968e-01  t_g=-1.541e-13  t_b=-1.318e-16
    t_dmeff=-8.878e-19  t_fld=nan  t_ur=-1.641e-13  t_tot=-6.075e-15

Density conversion check: -d_cdm / (k*h)² = 1.210e-05 / (1.009e-05 * 0.7)² = 1.210e-05 / 4.989e-11 = 2.425e+05 ✓
Weyl check: -(phi+psi)/2 = -(0.6124 + 0.5968)/2 = -0.6046 ✓ (matches CAMB's -0.6046)
