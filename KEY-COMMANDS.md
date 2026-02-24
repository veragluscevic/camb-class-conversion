# Key Commands

## Run CLASS
Both synchronous and Newtonian gauge runs are needed before running the conversion script!!
```bash
./class_dmeff_rui_used/class inis/minimal_syncronous.ini
./class_dmeff_rui_used/class inis/minimal_newtonian.ini
```

## Run conversion script (output will be saved at current location)
```bash
python class_to_camb.py output/n2_1e-2GeV_7.1e-24_sync_tk.dat output/n2_1e-2GeV_7.1e-24_newt_tk.dat output/n2_1e-2GeV_7.1e-24_sync_background.dat -o test_n2_envelope_dmeff-column.dat
```

## Run testing plotter (output will be saved in plots/)
```bash
python plot_test.py -i 1 --class-file test_n2_envelope.dat --camb-file data_tk/idm_n2_1e-2GeV_envelope_z99_Tk.dat -s
```

Options:
- `-i INDEX` — column index to plot (default: 1)
- `--class-file` — our conversion output (default: test_n2_envelope_dmeff-column.dat)
- `--camb-file` — reference file to compare against (default: data_tk/idm_n2_1e-2GeV_envelope_z99_Tk.dat)
- `-s [FILENAME]` — save plot to `plots/`; uses class filename if no name given
