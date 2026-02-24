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

    # Total matter: (Omega_cdm * delta_cdm + Omega_b * delta_b) / (Omega_cdm + Omega_b)
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

    # Velocity columns: zero for Milestone 1
    v_cdm = zeros
    v_b = zeros
    v_bc = zeros

    output = np.column_stack([
        k,          # 0: k/h
        T_cdm,      # 1: CDM
        T_b,        # 2: baryon
        T_g,        # 3: photon
        T_ur,       # 4: nu
        T_mass_nu,  # 5: mass_nu
        T_total,    # 6: total
        T_no_nu,    # 7: no_nu
        T_total_de, # 8: total_de
        T_weyl,     # 9: Weyl
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
