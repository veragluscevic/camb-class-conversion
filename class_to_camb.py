#!/usr/bin/env python
"""Convert CLASS transfer function output to CAMB 13-column format."""

import argparse
import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline


def parse_class_header(filepath):
    """Read a CLASS transfer file and return (column_name_to_index dict, data array).

    Parses the last comment line to extract column names like 'd_cdm', 't_b', 'phi'.
    The first column 'k (h/Mpc)' is mapped to 'k'.
    """
    last_comment = None
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('#'):
                last_comment = line
            else:
                break

    # Parse "N:name" tokens from the header line
    col_map = {}
    for token in last_comment.strip().lstrip('#').split():
        if ':' not in token:
            continue
        idx_str, name = token.split(':', 1)
        idx = int(idx_str) - 1  # convert to 0-based
        if name == 'k (h/Mpc)':
            name = 'k'
        col_map[name] = idx

    data = np.loadtxt(filepath)
    return col_map, data


def read_background_hubble(filepath, z):
    """Read a CLASS background file, interpolate H(z), return H in 1/Mpc."""
    bg = np.loadtxt(filepath)
    z_bg = bg[:, 0]
    H_bg = bg[:, 3]
    # CLASS background is sorted from high z to low z; flip for spline
    sort = np.argsort(z_bg)
    spline = InterpolatedUnivariateSpline(z_bg[sort], H_bg[sort])
    return float(spline(z))


def get_col(data, col_map, name, fallback=None):
    """Safely retrieve a column by name, returning fallback (zeros) if absent."""
    if name in col_map:
        return data[:, col_map[name]]
    if fallback is not None:
        return fallback
    return np.zeros(len(data))


def class_to_camb(tk_file, bg_file, h, omega_cdm, omega_b, z, output_file):
    """Main conversion: read CLASS files, compute 13 CAMB columns, write output."""
    col_map, data = parse_class_header(tk_file)
    H_z = read_background_hubble(bg_file, z)

    k = data[:, col_map['k']]  # h/Mpc
    kh = k * h  # 1/Mpc
    kh2 = kh ** 2

    # Density transfers: T_CAMB = -delta / (k*h)^2
    d_cdm = get_col(data, col_map, 'd_cdm')
    d_b = get_col(data, col_map, 'd_b')
    d_g = get_col(data, col_map, 'd_g')
    d_ur = get_col(data, col_map, 'd_ur')
    phi = get_col(data, col_map, 'phi')
    psi = get_col(data, col_map, 'psi')

    T_cdm = -d_cdm / kh2
    T_b = -d_b / kh2
    T_g = -d_g / kh2
    T_ur = -d_ur / kh2

    # Total matter (CDM + baryons only, excluding radiation).
    # Can't use CLASS's d_tot because it includes radiation (~3% at z=99).
    omega_m = omega_cdm + omega_b
    d_total = (omega_cdm * d_cdm + omega_b * d_b) / omega_m
    T_total = -d_total / kh2

    # Weyl potential: -(phi + psi) / 2
    T_weyl = -(phi + psi) / 2.0

    # Zeroed columns
    zeros = np.zeros(len(k))
    T_mass_nu = zeros
    T_no_nu = zeros
    T_total_de = zeros

    # Velocity columns: v = (1+z) * theta / (kh^2 * H(z))
    vel_factor = (1.0 + z) / (kh2 * H_z)

    # v_CDM: use t_dmeff if present (nonzero for dmeff runs), else t_cdm (zero in sync gauge)
    if 't_dmeff' in col_map:
        theta_cdm = data[:, col_map['t_dmeff']]
    else:
        theta_cdm = get_col(data, col_map, 't_cdm')
    v_cdm = vel_factor * theta_cdm

    # v_b: baryon velocity from t_b
    theta_b = get_col(data, col_map, 't_b')
    v_b = vel_factor * theta_b

    v_bc = v_b - v_cdm

    # TRUSTED columns (validated against CAMB to <0.2%):
    #   0  k/h        — directly from CLASS
    #   1  CDM        — from d_cdm, validated
    #   2  baryon     — from d_b, validated
    #   6  total      — matter-only weighted sum, validated
    #   11 v_b        — from t_b (sync gauge; differs from CAMB's Newtonian gauge)
    #   12 v_b-v_c    — derived from v_b and v_CDM
    #
    # NOT TRUSTWORTHY — filled for format compliance but not validated for use:
    #   3  photon     — sync-gauge d_g; oscillation phase differs from CAMB by up to ~70%
    #   4  nu         — sync-gauge d_ur; same oscillation-phase issue as photon
    #   5  mass_nu    — hardcoded zero (CLASS doesn't provide this)
    #   7  no_nu      — hardcoded zero (would need Omega-weighted combination)
    #   8  total_de   — hardcoded zero (would need dark energy perturbations)
    #   9  Weyl       — from phi+psi; ~0.2% vs CAMB but not used by MUSIC
    #   10 v_CDM      — zero in sync gauge for CDM-only; nonzero only for dmeff runs
    #
    # MUSIC only reads columns 0, 1, 2, 6, 10, 11 — all others are discarded.
    output = np.column_stack([
        k,          # 0: k/h
        T_cdm,      # 1: CDM
        T_b,        # 2: baryon
        T_g,        # 3: photon          (not trustworthy)
        T_ur,       # 4: nu              (not trustworthy)
        T_mass_nu,  # 5: mass_nu         (zero placeholder)
        T_total,    # 6: total
        T_no_nu,    # 7: no_nu           (zero placeholder)
        T_total_de, # 8: total_de        (zero placeholder)
        T_weyl,     # 9: Weyl            (not used by MUSIC)
        v_cdm,      # 10: v_CDM
        v_b,        # 11: v_b
        v_bc,       # 12: v_b-v_c
    ])

    header = ('{0:^15s} {1:^15s} {2:^15s} {3:^15s} {4:^15s} {5:^15s} '
              '{6:^15s} {7:^15s} {8:^15s} {9:^15s} {10:^15s} {11:^15s} '
              '{12:^15s}').format(
        'k/h', 'CDM', 'baryon', 'photon', 'nu', 'mass_nu',
        'total', 'no_nu', 'total_de', 'Weyl', 'v_CDM', 'v_b', 'v_b-v_c')

    np.savetxt(output_file, output, fmt='%15.6e', header=header)
    print(f"Wrote {len(k)} rows to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert CLASS transfer functions to CAMB 13-column format.')
    parser.add_argument('tk_file',
                        help='CLASS transfer function file (with density+velocity)')
    parser.add_argument('bg_file',
                        help='CLASS background file')
    parser.add_argument('--h', type=float, default=0.7,
                        help='Dimensionless Hubble parameter (default: 0.7)')
    parser.add_argument('--omega_cdm', type=float, default=0.239,
                        help='CDM density parameter (default: 0.239)')
    parser.add_argument('--omega_b', type=float, default=0.047,
                        help='Baryon density parameter (default: 0.047)')
    parser.add_argument('--z', type=float, default=99.0,
                        help='Redshift (default: 99)')
    parser.add_argument('-o', '--output', default='CDM_Tk.dat',
                        help='Output filename (default: CDM_Tk.dat)')
    args = parser.parse_args()

    class_to_camb(args.tk_file, args.bg_file, args.h,
                  args.omega_cdm, args.omega_b, args.z, args.output)


if __name__ == '__main__':
    main()
