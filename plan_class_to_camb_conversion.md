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
- **When `Omega_dmeff` is negligible** (e.g., 1e-15 for validation), `d_dmeff` and `d_cdm` agree at low k but diverge at high k. At k < 1 h/Mpc, they agree to ~10 significant digits. However, at k > 5 h/Mpc, dmeff-baryon scattering suppresses `d_dmeff` relative to `d_cdm` by up to ~7.6% (at k ≈ 38 h/Mpc). This occurs because the scattering drag term in the dmeff perturbation equation depends on σ_dmeff × n_b (the cross-section times baryon number density), not on Ω_dmeff — so it persists even with negligible dmeff density. Using `d_dmeff` for the CDM column at these scales introduces a systematic deviation from standard CDM transfer functions, while `d_cdm` (via `--use-cdm_column`) matches the CAMB ΛCDM reference to <0.25% at all k. Numerically verified on 2026-02-24.
- The cosmological parameters (h, Omega_cdm, Omega_b) could in principle be auto-extracted from the CLASS background file at z=0 (rho_b/rho_crit, rho_cdm/rho_crit, H₀×c/100), but this has not been implemented — they remain command-line arguments.
- **CAMB does NOT take absolute values of transfer functions.** In standard ΛCDM at z=99, all density perturbations δ_i in synchronous gauge maintain the same sign throughout evolution (δ < 0 in CLASS convention), so −δ/k² is naturally always positive. There is no `abs()` call in CAMB. However, in dmeff models with significant scattering, **dark acoustic oscillations (DAOs)** cause d_dmeff to oscillate through zero and change sign. For the n=2, m=1e-2 GeV, σ=7.1e-24 model, d_dmeff crosses zero 5 times between k = 22.8 and 181 h/Mpc, producing negative values in −d_dmeff/(kh)². Rui used `np.abs()` as a **pragmatic compatibility choice** — downstream tools (e.g., MUSIC) expect CAMB-format files to have all-positive density transfer functions and may crash on negative values. For power spectrum ratios P(k) ∝ T², the sign doesn't matter (T² = |T|²). For initial conditions that use T(k) directly to set the density field, `abs()` discards the phase information of the DAOs, which is physically incorrect but may be necessary for tool compatibility.
- **Rui used t_dmeff (not t_cdm) for velocities**, even though she used d_cdm for densities. Her hardcoded column indices (10, 11 in 0-indexed) map to t_b and t_dmeff respectively in her Omega_cdm=0 CLASS runs. This is physically correct: dmeff IS the dark matter, so its velocity should populate the CDM velocity slot regardless of which density column is used.


## Decision Log

- Decision: Keep synchronous gauge for velocities; do NOT reconstruct Newtonian-gauge CDM velocity.
  Rationale: User explicitly requested this. In synchronous gauge, θ_cdm = 0 by construction. The script will output v_CDM = 0 for CDM-only runs. For dmeff runs, θ_dmeff ≠ 0, so v_CDM (populated from θ_dmeff) will be nonzero. This means the CDM validation case will NOT match `test_transfer_z99.dat` in the v_CDM column (CAMB gives a nonzero Newtonian-gauge value), but that is accepted.
  Date: 2026-02-23
  Status: **Superseded** by the two-gauge approach (2026-02-24).

- Decision: Use d_cdm (only) for the "CDM" output column.
  Rationale: User requested this for the initial version. The dmeff density will be revisited later.
  Date: 2026-02-23
  Status: **Superseded** by the `--dmeff_column` flag (2026-02-24).

- Decision: Default to `d_dmeff` for the CDM density column when present; override with `--use-cdm_column` to force `d_cdm`. Velocities always use `t_dmeff` when present, regardless of the flag.
  Rationale: In dmeff runs, dmeff IS the dark matter. The `--use-cdm_column` flag only affects density columns (d_cdm vs d_dmeff) for comparison/validation purposes. Velocities always use t_dmeff because that is the physical dark matter velocity — matching Rui's approach, where she used d_cdm for density but t_dmeff for velocity.
  Date: 2026-02-24 (updated from earlier `--dmeff_column` flag)

- Decision: Zero out all non-essential columns. Only compute k/h, CDM, baryon, total, v_CDM, v_b, and v_b-v_c. All other columns (photon, nu, mass_nu, no_nu, total_de, Weyl) are zero placeholders.
  Rationale: MUSIC only reads columns 0, 1, 2, 6, 10, 11. Photon and nu columns were previously computed but disagreed with CAMB by up to 70% in the acoustic regime and are not used downstream. Removing unnecessary computations simplifies the script. Supersedes the earlier decision to populate photon/nu/Weyl.
  Date: 2026-02-24

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
| 1      | CDM    | 0.16%         | d_dmeff if present, else d_cdm (sync) |
| 2      | baryon | 0.24%         | sync-gauge d_b            |
| 6      | total  | 0.17%         | Ω-weighted d_dm + d_b    |
| 10     | v_CDM  | 0.17%         | always t_dmeff if present, else t_cdm (Newt) |
| 11     | v_b    | 0.19%         | Newtonian-gauge t_b       |
| 12     | v_b-v_c| derived       | v_b − v_cdm               |

Columns 3 (photon), 4 (nu), 5 (mass_nu), 7 (no_nu), 8 (total_de), 9 (Weyl) are zero placeholders for format compliance. They are not used by MUSIC. The script was simplified to remove unnecessary computations of photon, neutrino, and Weyl columns (previously computed but unreliable and unused downstream).


## Context and Orientation

This workspace lives at the repository root. Key files:

- `rui_camb.py` — Rui's original conversion script for WDM/dmeff. See the "Analysis of Rui's conversion script" subsection below for a detailed breakdown. DO NOT MODIFY.

- `vg_camb.py` — The user's earlier adaptation of Rui's script for CDM. Superseded by `class_to_camb.py`.

- `plot_test.py` — Testing/validation plotter. Compares a CLASS conversion output against a reference file. Two-panel figure: LHS shows (|T_camb| − |T_class|)² / T_cdm², RHS shows T² for both files plus a CDM reference. Supports argparse: `-i` (column index), `--class-file`, `--camb-file`, `-s` (save to `plots/`).

- `KEY-COMMANDS.md` — Quick reference for key commands (running CLASS, conversion, plotter).

- `highlights_to_share.md` — Summary of key findings for collaborators.

### Analysis of Rui's conversion script (`rui_camb.py`)

Rui's script is the predecessor to `class_to_camb.py`. Understanding it is essential because it established the conventions our script follows and because its limitations motivated our rewrite.

**Naming conventions in Rui's filenames.** Rui's file names encode the CLASS run configuration, not the code used. "camb" means CLASS was run with `format = camb` (CLASS performs the T = −δ/k² rescaling internally) — it does NOT mean actual CAMB was used. "class" means CLASS was run with `format = class` (raw δ and θ values). "sync" means synchronous gauge. "new" means Newtonian gauge. The variable name `data_camb_sync` in Rui's script is therefore misleading — it holds CLASS output, not CAMB output. No actual CAMB software is used anywhere in the pipeline.

**Two-file strategy.** Rui uses two CLASS transfer function runs plus a background file. The first is a synchronous-gauge run with `format = camb`, which provides density transfer functions already rescaled to CAMB convention. This file cannot include velocity transfer functions because CLASS's CAMB format does not support them (CLASS errors out if `vTk` is requested with `format = camb`). The second is a Newtonian-gauge run with `format = class`, which provides raw velocity divergences θ_i(k,z). A background file from the Newtonian-gauge run provides H(z) for the velocity conversion formula v = (1+z)·θ/(kh²·H). Our script follows the same two-gauge strategy but uses `format = class` for both runs and performs all rescaling itself.

**Density columns: Rui uses d_cdm, not d_dmeff.** The `format = camb` output from CLASS with dmeff enabled has 10 columns. The column layout (verified using `output/CDM_class_sync_CAMBFORMATtk.dat`) is: 0:k/h, 1:T_cdm, 2:T_dmeff, 3:T_idm_dr, 4:T_b, 5:T_g, 6:T_ur, 7:T_idr, 8:T_ncdm, 9:T_tot. Rui reads column 1 (T_cdm) for the CDM output — the dmeff column (column 2) is present but skipped. This means Rui's output uses the standard CDM transfer function, which does not include dmeff-baryon scattering effects.

**Total column: radiation-inclusive.** Rui uses CLASS's `T_tot` (column 9) directly for the CAMB "total" column. CLASS's total includes radiation (photons + massless neutrinos), not just matter. At z=99, this introduces a ~2.9% systematic error compared to CAMB's matter-only total convention. Numerically verified: CLASS's T_tot deviates from CAMB's total by up to 2.97%, while our matter-only calculation (Ω_cdm·T_cdm + Ω_b·T_b)/(Ω_cdm + Ω_b) matches CAMB to 0.22%. This is a known difference between Rui's output and ours. Confirmed in the CLASS source code: `delta_rho` is accumulated over all species including photons (line 6677) and neutrinos (line 6774) in `perturb_total_stress_energy()` in `source/perturbations.c`, then `delta_tot = delta_rho / rho_tot` (line 7512) excludes Lambda but not radiation. The `format = camb` output simply rescales this same `delta_tot` as `−delta_tot/k²` without recomputing a matter-only total.

**Velocity columns: hardcoded indices, but correctly using t_dmeff.** Rui uses columns 10 and 11 (0-indexed) from the Newtonian-gauge `format = class` file. In her runs with Omega_cdm = 0 (all DM is dmeff), the CLASS Newtonian file does not contain t_cdm (since has_cdm = FALSE). The column layout is: ..., 10:t_b, 11:t_dmeff, .... So `data_class_new[i,11]` reads t_dmeff (which she assigns to `vc`) and `data_class_new[i,10]` reads t_b (assigned to `vb`). Despite using d_cdm for densities, Rui correctly uses t_dmeff for velocities — dmeff IS the dark matter, so its velocity should populate the CDM velocity slot. Our script now follows this same convention: velocities always use t_dmeff when present, regardless of the `--use-cdm_column` flag. The fragility of Rui's hardcoded indices (which would break if the column layout changed, e.g., with d_fld present) is why our script parses headers by name.

**Columns zeroed out.** Rui sets 7 of 13 CAMB columns to zero: photon (3), nu (4), mass_nu (5), no_nu (7), total_de (8), Weyl (9), v_b-v_c (12). Only 6 columns carry physical content: k/h, CDM, baryon, total, v_CDM, v_b — the same 6 that MUSIC reads. Our script now follows the same approach, zeroing out all non-essential columns. We additionally compute v_b-v_c (col 12) as it is trivially derived from cols 10 and 11.

**CAMB output as template.** We believe Rui used actual CAMB output only as a comparison template to validate the column layout and conventions for CDM-only runs — not as an input to the conversion pipeline. The 13-column format, column ordering, and sign conventions all follow CAMB's output structure, but the data itself comes entirely from CLASS.

**`np.abs()` usage.** Rui wraps all populated density and velocity columns in `np.abs()`. For standard CDM perturbations (which are always positive in CAMB convention), this is a no-op. However, for dmeff models with dark acoustic oscillations, the transfer function oscillates and changes sign at high k (see Surprises & Discoveries above). Rui's `np.abs()` is a pragmatic compatibility choice for downstream tools that expect all-positive CAMB-format files, not a reflection of the CAMB convention itself. The cosmological parameters h=0.7 and z=99 are hardcoded with no command-line interface.

- `test_transfer_z99.dat` (also in `data_tk/`) — A 13-column CAMB transfer function file at z=99 for a standard ΛCDM cosmology (h=0.7, Ω_cdm=0.239, Ω_b=0.047, Ω_Λ=0.714). Generated by actual CAMB. This is the validation reference. It has 213 data rows and 13 columns: k/h, CDM, baryon, photon, nu, mass_nu, total, no_nu, total_de, Weyl, v_CDM, v_b, v_b-v_c.

- `inis/minimal_syncronous.ini` — CLASS parameter file for the **synchronous-gauge** run. Set to `format = class`, `gauge = synchronous`, `output = ..., mTk, vTk`. Root is `output/n2_1e-2GeV_7.1e-24_sync_`.

- `inis/minimal_newtonian.ini` — CLASS parameter file for the **Newtonian-gauge** run. Same cosmology but with `gauge = newtonian` and root `output/n2_1e-2GeV_7.1e-24_newt_`. Produces the velocity transfer functions used for CAMB columns 10–12.

- CDM-only ini variants (`inis/minimal_syncronous_CDMonly.ini`, `inis/minimal_newtonian_CDMonly.ini`) are also available for validation runs without dmeff.

- `output/` — Contains all CLASS output files. Filenames encode the run: e.g., `n2_1e-2GeV_7.1e-24_sync_tk.dat` (sync gauge transfer functions), `n2_1e-2GeV_7.1e-24_newt_tk.dat` (Newtonian gauge), `n2_1e-2GeV_7.1e-24_sync_background.dat` (background). CDM-only outputs use `CDM_class_sync_*` / `CDM_class_newt_*` prefixes.

- `data_tk/` — Reference transfer function files from Rui, used for comparison (e.g., `idm_n2_1e-2GeV_envelope_z99_Tk.dat`).

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

3. **Converter.** From the sync-gauge file, compute density columns (T = −δ/(kh)² for CDM and baryon) and the total matter column (Ω-weighted CDM + baryon). From the Newtonian-gauge file, compute velocity columns (v = (1+z)·θ/(kh²·H)). Velocities always use t_dmeff when present; the `--use-cdm_column` flag only affects density columns. All other columns (photon, nu, mass_nu, no_nu, total_de, Weyl) are zero placeholders. If `d_dmeff` or `t_dmeff` exists in a CLASS file, the script uses it; otherwise it falls back to `d_cdm`/`t_cdm` gracefully.

The script is invoked as (see also `KEY-COMMANDS.md`):

    python class_to_camb.py output/n2_1e-2GeV_7.1e-24_sync_tk.dat output/n2_1e-2GeV_7.1e-24_newt_tk.dat output/n2_1e-2GeV_7.1e-24_sync_background.dat -o test_n2_envelope.dat

All cosmological parameters (--h, --omega_cdm, --omega_b, --z) have sensible defaults matching the current cosmology. Use `--use-cdm_column` to force d_cdm for densities (velocities always use t_dmeff when present).


## Concrete Steps

### Milestone 1: Density columns (0–9)

Create `class_to_camb.py` with the header parser and density conversion using a synchronous-gauge CLASS file. Velocity columns set to zero initially. Validate density columns 0–6 and Weyl (col 9) against `test_transfer_z99.dat`. **Completed**: CDM, baryon, total agree to <0.2%.

### Milestone 2: Velocity columns (10–12)

Add velocity conversion using the background H(z) spline. Initially used sync-gauge velocities, giving v_CDM = 0 (θ_cdm = 0 in sync gauge). **Completed** with the caveat that sync-gauge velocities disagree with CAMB's Newtonian-gauge convention.

### Milestone 3: Generality test

Verify the script works on both CDM-only (14-column) and dmeff (16-column) CLASS outputs. **Completed**: header parser correctly handles both layouts.

### Milestone 4: Two-gauge approach

Following Rui's approach, the script now accepts two CLASS transfer files:
- Synchronous gauge (`inis/minimal_syncronous.ini`, `gauge = synchronous`) → density columns
- Newtonian gauge (`inis/minimal_newtonian.ini`, `gauge = newtonian`) → velocity columns

Both CLASS runs use `format = class`. Validation command:

    python class_to_camb.py output/CDM_class_sync_CDMonly_tk.dat output/CDM_class_newt_CDMonly_tk.dat \
        output/CDM_class_sync_CDMonly_background.dat --use-cdm_column -o test_CDM.dat

**Completed**: all MUSIC-relevant columns now agree with CAMB to <0.25%.


## Validation and Acceptance

The primary acceptance test is a quantitative comparison of the output against `test_transfer_z99.dat`. Since the k-grids differ (213 vs 845 points), the comparison requires interpolation. The script `plot_test.py` (already in the repo) demonstrates this technique.

Acceptance criteria (all met with two-gauge approach):
- **CDM, baryon, total** (cols 1, 2, 6): agree with `test_transfer_z99.dat` to <0.25%.
- **v_CDM, v_b** (cols 10, 11): agree to <0.25% (using Newtonian-gauge CLASS).
- **v_b-v_c** (col 12): derived from cols 10 and 11.
- **Photon, nu, mass_nu, no_nu, total_de, Weyl** (cols 3, 4, 5, 7, 8, 9): zero placeholders. Not used by MUSIC.
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

    def class_to_camb(tk_sync_file, tk_newt_file, bg_file, h, omega_cdm, omega_b,
                      z, output_file, use_dmeff=True):
        """Main conversion: read two CLASS transfer files (sync gauge for densities,
        Newtonian gauge for velocities) + background, compute 13 CAMB columns, write output.
        If use_dmeff=True (default), uses d_dmeff for the CDM density column when present.
        Velocities always use t_dmeff when present, regardless of use_dmeff."""

Command-line interface via argparse with three positional args (sync transfer file, Newtonian transfer file, background file) and optional flags for cosmological parameters, output path, and `--use-cdm_column`.


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
