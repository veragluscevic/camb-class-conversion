# Highlights

- **T_tot: Rui's script uses CLASS's radiation-inclusive total, which differs from CAMB's matter-only convention by ~3% at k>30.** She used CLASS's `d_tot` which includes photons and massless neutrinos. Meanwhile, CAMB's "total" column is matter-only: (Omega_cdm * d_cdm + Omega_b * d_b) / (Omega_cdm + Omega_b). 

- **d_dmeff vs. d_cdm: Rui's script used d_cdm for d_dmeff.** With Omega_dmeff = 1e-15, the two agree at low k but differ by up to 7.6% at k ~ 38 h/Mpc (13.6% in the power spectrum). This is because of the dmeff-baryon scattering drag.
