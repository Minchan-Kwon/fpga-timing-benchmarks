# Running the Timing Benchmark Suite

This document describes how to set up and run `run_benchmark.py`, which performs FPGA timing benchmarks by generating SDC files, running VPR place-and-route, and producing timing analysis reports.

## Prerequisites

### 1. Install `libtbb-dev`

To compile VPR with support for parallel workers, `libtbb-dev` must be installed on your system:

```bash
sudo apt install libtbb-dev
```

### 2. Configure `config.py`

Open `config.py` and set `VTR_ROOT` to the absolute path of your local VTR installation. The other path variables are relative to the repository root and do not need to be changed.

A dictionary describing a testcase should also be defined in `config.py`. For more information on how to define a test case in `config.py`, read [Defining a Test Case](#define_test_case).

### 3. Activate the Virtual Environment

Activate the VTR virtual environment before running the script:

```bash
source <PATH_TO_VTR>/.venv/bin/activate
```

Replace `<PATH_TO_VTR>` with the absolute path to your VTR installation.

---

## Command-line Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `--test` | `str` | *(required)* | Test configuration name defined in `config.py` (e.g., `create_clock_rca`). |
| `--seed` | `int [...]` | `1` | One or more placement seeds (e.g., `--seed 1 3 5`). VPR is run once per seed. |
| `--sdc_dir` | `str` | `None` | Path to an existing SDC directory. If specified, skips SDC generation and uses these files instead. |
| `--placement_type` | `timing_driven` \| `analytical` | `timing_driven` | Placement algorithm type. |
| `--place_algorithm` | `criticality_timing` \| `slack_timing` | `criticality_timing` | Timing-driven placement algorithm. |
| `--place_agent_algorithm` | `e_greedy` \| `softmax` | `softmax` | RL agent algorithm used during placement. |
| `--analytical_solver` | `qp-hybrid` \| `lp-b2b` | `qp-hybrid` | Solver to use for analytical placement. |
| `--ap_timing_tradeoff` | `float` | `0.5` | Timing tradeoff for analytical placement (`0.0` = wirelength, `1.0` = timing). |
| `--hold` | flag | `False` | Enables hold analysis using `--routing_budgets_algorithm yoyo`. |
| `--num_paths` | `int` | `100` | Number of timing paths to include in the report. |
| `--use_params` | flag | `False` | Uses parameters in the post-synthesis netlist. Disable for OpenSTA compatibility. |
| `--num_workers` | `int` | `1` | Number of parallel workers VPR may use. Argument `0` tells VPR to use as many workers as possible. Requires `libtbb-dev`. |

---

## Usage Examples

Run the benchmark for the `create_clock_rca` test case with default settings:

```bash
python run_benchmark.py --test create_clock_rca
```

Run with multiple seeds for a seed sweep:

```bash
python run_benchmark.py --test create_clock_rca --seed 1 3 5
```

Use analytical placement with the `lp-b2b` solver and a timing tradeoff of `0.8`:

```bash
python run_benchmark.py --test create_clock_rca --placement_type analytical --analytical_solver lp-b2b --ap_timing_tradeoff 0.8
```

Enable hold analysis with 4 parallel workers:

```bash
python run_benchmark.py --test create_clock_rca --hold --num_workers 4
```

Use a pre-existing SDC directory instead of generating new SDCs:

```bash
python run_benchmark.py --test create_clock_rca --sdc_dir ./my_sdc_files/
```

---

## Output Files

All results are saved under `./results/timing/<test_name>/<result_dir>/`, where `<result_dir>` encodes the run parameters (e.g., `seed01_t-driven_criticality00`). Each run directory contains the following files:

| File | Description |
|---|---|
| `config.json` | Records the experiment parameters used for the run. |
| `<sdc_name>_timing.txt` | Parsed timing summary (CPD, Fmax, WNS, TNS, clock info). |
| `<sdc_name>_setup.txt` | Parsed setup timing paths. |
| `<sdc_name>_hold.txt` | Parsed hold timing paths. |
| `<sdc_name>_skew_setup.txt` | Parsed setup skew paths. |
| `<sdc_name>_skew_hold.txt` | Parsed hold skew paths. |
| `arrival_time_distribution.png` | Histogram of path arrival times. |
| `slack_distribution.png` | Histogram of path slacks (with a zero-slack reference line). |

SDC files generated for the test are saved separately under `./results/timing/<test_name>/sdc/`.

---

## Internal Architecture

The diagram below summarizes how the functions in `run_benchmark.py` interact during a standard benchmark run.

```
main()
  │
  ├── construct_sdc(test_config)
  │     Reads the SDC template and parameter sweep values from the test
  │     configuration and generates one SDC file per parameter combination.
  │     Saves the SDCs to ./results/timing/<test_name>/sdc/ and returns
  │     the directory path.
  │
  └── run_vpr(test_config, sdc_dir, seed, **kwargs)
        │
        ├── get_sdc_list(sdc_dir)
        │     Collects all .sdc files in the given directory. Always prepends
        │     a None entry so VPR is also run once without any SDC (baseline).
        │
        ├── create_result_dir(base_dir, seed, **kwargs)
        │     Creates a uniquely named output directory based on the seed and
        │     placement parameters (e.g., seed01_t-driven_criticality00).
        │
        ├── make_json(test_config, result_dir, seed, **kwargs)
        │     Saves a config.json recording all experiment parameters
        │     to the result directory.
        │
        └── [for each SDC in sdc_list]
              │
              ├── build_vpr_command(test_config, sdc, seed, **kwargs)
              │     Assembles the full VPR CLI command from the test config
              │     and all keyword arguments (placement type, solver, hold, etc.).
              │
              ├── subprocess.run(cmd)   ← executes VPR
              │
              ├── was_sdc_parsed(temp_dir)
              │     Checks vpr.out to confirm the SDC was successfully found
              │     and parsed by VPR.
              │
              ├── make_vpr_summary(temp_dir)
              │     Parses vpr.out for top-level metrics (CPD, Fmax, WNS, TNS,
              │     constrained clocks). Calls parse_timing_report() for each
              │     detailed timing report file.
              │     │
              │     └── parse_timing_report(file_path, is_skew)
              │           Splits the VPR timing report by path blocks and
              │           extracts per-path data (startpoint, endpoint, arrival
              │           time, slack/skew) into a flat list.
              │
              ├── save_vpr_timing_report(result_dir, sdc, ...)
              │     Writes the parsed timing lists from make_vpr_summary()
              │     into human-readable .txt files in the result directory.
              │
              └── save_path_distribution(setup_rpt, run_output_dir)
                    Parses arrival times and slack values from the setup
                    timing report list and saves two histogram PNGs
                    (arrival_time_distribution.png, slack_distribution.png).
```

### Helper Functions

- **`run_synthesis(test_config)`** — Runs Parmys or Odin II to synthesize a Verilog design into a BLIF netlist. Not called by `main()` directly since all included test cases already use pre-synthesized BLIF files.
- **`run_opensta(test_config, liberty_file)`** — Runs OpenSTA on the post-implementation netlist and SDC generated by VPR for cross-validation of timing results. Not invoked by `main()` in the current flow.
- **`get_min_distance(place_file)`** — Parses a VPR `.place` file and computes the minimum average Manhattan distance from all placed logic blocks to each of the four FPGA peripheries. Useful for analyzing placement clustering behavior.
- **`analyze_result()`** — Placeholder for future seed sweep analysis across multiple result directories (not yet implemented).

---
<a id="define_test_case"></a>
## Defining a Test Case

Each timing benchmark test case is defined as a Python dictionary in `config.py` and passed to `run_benchmark.py` via `--test`. Below is the full dictionary format with a description of each field.

### Dictionary Format

```python
my_test = {
    'type':             str,        # Unique name for the test case. Used to name the output directory.
    'blif':             str,        # Path to the BLIF netlist, relative to MICRO_ROOT.
    'top_level_module': str,        # Top-level module name of the design.
    'sdc':              str,        # SDC template string. Use '<param_name>' as placeholders for parameter sweeping.
    'param':            list|None,  # List of parameter dictionaries for sweeping, or None if no parameters.
    'layout':           str,        # VPR device layout name as defined in the architecture .xml file.
    'graphics':         bool        # If True, saves a PNG of the placed-and-routed design via VPR graphics.
}
```

Each entry in `param` must follow this format:

```python
{
    'name':    str,        # The placeholder string in the SDC template to replace (e.g., '<period>').
    'default': any|None,   # Default value used for all other parameters while this one is swept.
                           # Set to None if this is the only parameter.
    'values':  list        # List of values to iterate through when generating SDC files.
}
```

### Example

The following test sweeps the clock period of a ripple-carry adder across five values. For each value in `values`, one SDC file is generated with `<period>` substituted.

```python
create_clock_rca = {
    'type': 'create_clock_rca',
    'blif': 'create_clock/rca.blif',
    'top_level_module': 'rca',
    'sdc': """
create_clock -period <period> {clk}
create_clock -period 1.0 -name irrelevant_clock
    """.strip(),
    'param': [{'name': '<period>', 'default': None, 'values': [1.0, 3.0, 5.0, 10.0, 12.0]}],
    'layout': 'vtr_medium',
    'graphics': False
}
```

This produces five SDC files under `./results/timing/create_clock_rca/sdc/`:

```
period_1.0.sdc
period_3.0.sdc
period_5.0.sdc
period_10.0.sdc
period_12.0.sdc
```

VPR is then run once per SDC (plus one baseline run without any SDC), for a total of six VPR invocations per seed.

### No Parameter Sweep

If the SDC does not require any parameter substitution, set `param` to `None`. A single SDC file named `<type>.sdc` will be generated directly from the template string.

```python
create_generated_clock_clock_divider_base = {
    'type': 'create_generated_clock_clock_divider_base',
    'blif': 'create_generated_clock/clock_divider.blif',
    'top_level_module': 'clock_divider',
    'sdc': """
create_clock -period 10.0 clk
set_clock_latency -source 5.0 [get_clocks clk]
create_generated_clock -source [get_clocks clk] -divide_by 2 {*641*.Q*}
    """.strip(),
    'param': None,
    'layout': 'vtr_medium',
    'graphics': True
}
```

---

## To Be Implemented

The following features are noted as pending in the codebase.

| Priority | Location | Description |
|---|---|---|
| High | `main()` | **Multi-config iteration** — When `--test` resolves to a list of test configurations in `config.py`, `run_vpr()` should iterate over each config in the list rather than treating the whole list as a single test case. |
| High | `config.py` | **Benchmark selection** — Identify and finalize the set of benchmark circuits to use for the timing experiments. |
| Medium | `make_vpr_summary()` | **Parse constrained vs. unconstrained path counts** — Extract and report how many timing paths are constrained vs. unconstrained from `vpr.out`. |
| Medium | `make_vpr_summary()` | **Parse VPR runtime** — Extract and record the total VPR execution time from `vpr.out`. |
| Medium | Top-level | **Additional analysis functions** — Expand placement analysis utilities beyond the current `get_min_distance()`, for example functions that compute other spatial metrics from the `.place` file. |
| Low | `analyze_result()` | **Implement `analyze_result()`** — Build out the full implementation to compare timing results across seeds and/or test configurations (e.g., averaging CPD, WNS, TNS over multiple seeds). |
