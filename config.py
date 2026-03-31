from pathlib import Path

# DIRECTORIES
# Edit 'VTR_ROOT' to the actual path to VTR on your local machine.

VTR_ROOT = Path('~/work/vtr-verilog-to-routing').expanduser()
BENCHMARK_ROOT = Path(__file__).parent
MICRO_ROOT = BENCHMARK_ROOT / 'fpga_timing_benchmarks' / 'benchmarks' / 'basic' / 'netlist_files'
ARCH_DIR = BENCHMARK_ROOT / 'arch'
RESULTS_DIR = BENCHMARK_ROOT / 'results'
SYNTHESIS_DIR = RESULTS_DIR / 'blif'
SYNTAX_DIR = BENCHMARK_ROOT / 'auto_generated'

ARCH_FILE = ARCH_DIR / 'k6_frac_N10_frac_chain_mem32K_40nm.xml'
LIBERTY_FILE = VTR_ROOT / 'vtr_flow' / 'primitives.lib'

# BASIC TIMING SUITE CONFIGURATION

# TIMING_TESTS: A list of per constraint timing test configurations
# The items of the list 'TIMING_TESTS' are dictionaries that define
# a single test case.

# Dictionary Format:
# 'type' (str): A unique name for a test case. Used to create the output directory.
# 'blif' (str): Path to the BLIF file to test, relative to 'MICRO_ROOT'.
# 'top_level_module' (str): Name of the top level module of the design.
# 'sdc' (str): A template for the SDC to test. Use placeholders '<param_name>' 
#              to substitute with varying values.
# 'param' (list|None): A list of dictionaries for parameter sweeping. Each dictionary
#                      must have keys 'name' and 'values'.
#   'name': The placeholder string in the SDC template to be replaced.
#   'default': Default value for the parameter. Set to 'None' if no other parameter
#              sweeping is required.
#   'values': A list of values to iterate through when creating the SDCs.
# 'layout' (str): Fixed device layout as defined in the architecture description file (.xml).
# 'graphics' (bool): Enable VPR graphics and save PnR results as a PNG.

# 1. create_clock
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

create_clock_timing = [create_clock_rca]

# 2. create_generated_clock
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
    'graphics': False
}

create_generated_clock_clock_divider = {
    'type': 'create_generated_clock_clock_divider',
    'blif': 'create_generated_clock/clock_divider.blif',
    'top_level_module': 'clock_divider',
    'sdc': """
create_clock -period 10.0 {clk}
set_clock_latency -source 5.0 {clk}
create_clock -period 10.0 {$dff~641^Q~0}
    """.strip(),
    'param': None,
    'layout': 'vtr_medium',
    'graphics': False
}

TIMING_TESTS = [create_clock_rca]

# SYNTAX TEST CONFIGURATION

# 'SYNTAX_TESTS': A list of syntax test configurations.
# Elements in the list 'SYNTAX_TESTS' are dictionaries, defining each syntax test case.

# Dictionary Format:
# 'type' (str): A unique name for the test. Used for result tracking.
# 'blif' (str): The name of the BLIF file to be processed by VPR.
# 'sdc_name' (str): Name of the timing constraint targeted for syntax validation.

create_clock = {
    'type': 'create_clock',
    'blif': 'create_clock_netlist.blif',
    'sdc_name': 'create_clock'
}

create_generated_clock = {
    'type': 'create_generated_clock',
    'blif': 'create_generated_clock_netlist.blif',
    'sdc_name': 'create_generated_clock'
}

set_input_delay = {
    'type': 'set_input_delay',
    'blif': 'set_input_delay_netlist.blif',
    'sdc_name': 'set_input_delay'
}

set_output_delay = {
    'type': 'set_output_delay',
    'blif': 'set_output_delay_netlist.blif',
    'sdc_name': 'set_output_delay'
}

set_clock_latency = {
    'type': 'set_clock_latency',
    'blif': 'set_clock_latency_netlist.blif',
    'sdc_name': 'set_clock_latency'
}

set_clock_uncertainty = {
    'type': 'set_clock_uncertainty',
    'blif': 'set_clock_uncertainty_netlist.blif',
    'sdc_name': 'set_clock_uncertainty'
}

set_false_path = {
    'type': 'set_false_path',
    'blif': 'set_false_path_netlist.blif',
    'sdc_name': 'set_false_path'
}

set_max_delay = {
    'type': 'set_max_delay',
    'blif': 'set_max_delay_netlist.blif',
    'sdc_name': 'set_max_delay'
}

set_min_delay = {
    'type': 'set_min_delay',
    'blif': 'set_min_delay_netlist.blif',
    'sdc_name': 'set_min_delay'
}

set_multicycle_path = {
    'type': 'set_multicycle_path',
    'blif': 'set_multicycle_path_netlist.blif',
    'sdc_name': 'set_multicycle_path'
}

set_clock_groups = {
    'type': 'set_clock_groups',
    'blif': 'set_clock_groups_netlist.blif',
    'sdc_name': 'set_clock_groups'
}

set_disable_timing = {
    'type': 'set_disable_timing',
    'blif': 'set_disable_timing_netlist.blif',
    'sdc_name': 'set_disable_timing'
}

# 'run_syntax.py' will run every test in this list when given '--sdc_name all'
SYNTAX_TESTS = [create_clock, create_generated_clock, set_input_delay, set_output_delay,
                set_clock_latency, set_clock_uncertainty, set_false_path,
                set_min_delay, set_max_delay, set_multicycle_path, set_clock_groups,
                set_disable_timing]
