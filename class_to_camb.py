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


def class_to_camb(tk_sync_file, tk_newt_file, bg_file, h, omega_cdm, omega_b,
                  z, output_file, use_dmeff=True):
    """Main conversion: read CLASS files, compute 13 CAMB columns, write output.

    Uses two CLASS transfer function files:
      - tk_sync_file: synchronous gauge (for density columns — CAMB convention)
      - tk_newt_file: Newtonian gauge (for velocity columns — CAMB convention)
    """
    sync_map, sync_data = parse_class_header(tk_sync_file)
    newt_map, newt_data = parse_class_header(tk_newt_file)
    H_z = read_background_hubble(bg_file, z)

    k = sync_data[:, sync_map['k']]  # h/Mpc
    kh = k * h  # 1/Mpc
    kh2 = kh ** 2

    # --- Density columns from synchronous gauge ---
    # CAMB density convention uses sync gauge: T = -delta_sync / (k*h)^2
    if use_dmeff and 'd_dmeff' in sync_map:
        d_dm = get_col(sync_data, sync_map, 'd_dmeff')
    else:
        d_dm = get_col(sync_data, sync_map, 'd_cdm')
    d_b = get_col(sync_data, sync_map, 'd_b')


    T_cdm = -d_dm / kh2
    T_b = -d_b / kh2
  
    # Total matter (DM + baryons only, excluding radiation).
    # Can't use CLASS's d_tot because it includes radiation (~3% at z=99).
    omega_m = omega_cdm + omega_b
    d_total = (omega_cdm * d_dm + omega_b * d_b) / omega_m
    T_total = -d_total / kh2

    # --- Velocity columns from Newtonian gauge ---
    # CAMB velocity convention uses Newtonian gauge: v = (1+z)*theta/(kh^2*H)
    vel_factor = (1.0 + z) / (kh2 * H_z)

    if 't_dmeff' in newt_map:
        theta_dm = get_col(newt_data, newt_map, 't_dmeff')
    else:
        theta_dm = get_col(newt_data, newt_map, 't_cdm')
    theta_b = get_col(newt_data, newt_map, 't_b')
    v_cdm = vel_factor * theta_dm
    v_b = vel_factor * theta_b

    zeros = np.zeros(len(k))
    T_g = zeros
    T_ur = zeros
    T_mass_nu = zeros
    T_no_nu = zeros
    T_total_de = zeros
    T_weyl = zeros
    v_bc = v_b - v_cdm
  

    # COMPUTED columns (validated against CAMB):
    #   0  k/h        — directly from CLASS
    #   1  CDM        — from d_dmeff if present, else d_cdm (sync gauge)
    #   2  baryon     — from sync-gauge d_b
    #   6  total      — matter-only weighted sum from sync gauge
    #   10 v_CDM      — always from t_dmeff if present, else t_cdm (Newtonian gauge)
    #   11 v_b        — from Newtonian-gauge t_b
    #   12 v_b-v_c    — derived from columns 11 and 10
    #
    # ZERO PLACEHOLDERS (format compliance only):
    #   3  photon, 4  nu, 5  mass_nu, 7  no_nu, 8  total_de, 9  Weyl
    #
    # MUSIC only reads columns 0, 1, 2, 6, 10, 11.
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
    parser.add_argument('tk_sync_file',
                        help='CLASS transfer function file in synchronous gauge (densities)')
    parser.add_argument('tk_newt_file',
                        help='CLASS transfer function file in Newtonian gauge (velocities)')
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
    parser.add_argument('--use-cdm_column', default=False,
                        action='store_true',
                        help='Force using d_cdm/t_cdm instead of d_dmeff/t_dmeff '
                             'for the CDM column (default: use dmeff if present)')
    args = parser.parse_args()

    class_to_camb(args.tk_sync_file, args.tk_newt_file, args.bg_file,
                  args.h, args.omega_cdm, args.omega_b, args.z, args.output,
                  use_dmeff=not args.use_cdm_column)


if __name__ == '__main__':
    main()
