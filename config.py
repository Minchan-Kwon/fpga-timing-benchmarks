from pathlib import Path

# DIRECTORIES
# Edit 'VTR_ROOT' to the actual path to VTR on your local machine.

VTR_ROOT = Path('~/work/vtr-verilog-to-routing').expanduser()
BENCHMARK_ROOT = Path(__file__).parent
NETLIST_ROOT = BENCHMARK_ROOT / 'fpga_timing_benchmarks' / 'benchmarks' / 'netlist_files'
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
# 'blif' (str): Path to the BLIF file to test, relative to 'NETLIST_ROOT'.
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

# HOLD TEST CONFIGURATION

BASIC_generated = {
    'type': 'GENERATED_BASIC',
    'blif': 'hold/gen_clk.blif',
    'sdc': """
create_clock -period 3.5 [get_ports {clk}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': -1
}

BASIC_uncertainty = {
    'type': 'UNCERTAINTY_BASIC',
    'blif': 'hold/clk_uncertainty.v',
    'sdc': """
create_clock -period 2.1 {clk}
set_clock_uncertainty -to [get_clocks {clk}] <uncertainty>
    """,
    'param': [{'name': '<uncertainty>', 'values': [0.2, 0.3, 0.4, 0.5]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': -1
}

BASIC_latency = {
    'type': 'UNCERTAINTY_BASIC',
    'blif': 'hold/clk_latency.v',
    'sdc': """
create_clock -period 2.1 {clk}
set_clock_latency -to [get_clocks {clk_late}] <latency>
    """,
    'param': [{'name': '<latency>', 'values': [0.2, 0.3, 0.4, 0.5]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': -1
}

MATMUL = {
    'type': 'MATMUL_uncertainty',
    'blif': 'hold/MATMUL.v',
    'sdc': """
create_clock -period 8.8 [get_ports {clk}]
set_clock_uncertainty -to [get_clocks {clk}] <uncertainty>
    """,
    'param': [{'name': '<uncertainty>', 'values': [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 60
}

DCT = {
    'type': 'DCT_uncertainty',
    'blif': 'hold/2D_DCT.v',
    'sdc': """
create_clock -period 28.7 [get_ports {clk}]
set_clock_uncertainty -to [get_clocks {clk}] <uncertainty>
    """,
    'param': [{'name': '<uncertainty>', 'values': [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 112
}

FFT = {
    'type': 'FFT_uncertainty',
    'blif': 'hold/FFT.v',
    'sdc': """
create_clock -period 12.3 [get_ports {clk}]
set_clock_uncertainty -hold -to [get_clocks {clk}] <uncertainty>
    """,
    'param': [{'name': '<uncertainty>', 'values': [0.3]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 68
}

TRANSPOSED_FIR = {
    'type': 'TRANSPOSED_FIR_uncertainty',
    'blif': 'hold/TRANSPOSED_FIR.v',
    'sdc': """
create_clock -period 11.8 [get_ports {clk}]
set_clock_uncertainty -to [get_clocks {clk}] <uncertainty>
    """,
    'param': [{'name': '<uncertainty>', 'values': [0.3, 0.4, 0.5]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 96
}

FOLDED_FIR_COUNTER = {
    'type': 'FOLDED_FIR_COUNTER',
    'blif': 'hold/FOLDED_FIR_GEN_COUNTER.v',
    'sdc': """
create_clock -period 10.3 [get_ports {clk_fast}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 60
}

# SETUP TEST CONFIGURATION
# Large designs where optimizing for wirelength may not present the best timing results.

clstm_like_small = {
    'type': 'clstm_like_small_setup',
    'blif': 'setup/clstm_like.small.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [6.0, 6.8, 6.9, 7.0, 7.1, 7.2, 7.3, 7.4,
                                              7.5, 7.6, 7.7, 7.8, 7.9, 8.0, 9.0]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 100
}

bnn = {
    'type': 'bnn_setup',
    'blif': 'setup/bnn.blif',
    'sdc': """
create_clock -period <delay> {ap_clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<delay>', 'values': [9.93, 10.10, 10.27, 10.44,
                                             10.61, 10.78, 11.93, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 150
}


bnn_base = {
    'type': 'bnn_unconstrained',
    'blif': 'setup/bnn.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 150
}

# Takes way too long
gemm = {
    'type': 'gemm_setup',
    'blif': 'setup/gemm_layer.blif',
    'sdc': """
create_clock -period <period> {s00_axi_aclk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [4.0, 5.0, 5.5, 5.6, 5.7, 5.8, 5.9, 6.0, 7.0]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 100
}

gemm_base = {
    'type': 'gemm_base',
    'blif': 'setup/gemm_layer.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 100
}

robot_rl = {
    'type': 'robot_rl_setup',
    'blif': 'setup/robot_rl.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [7.01, 6.89, 6.76, 6.63, 6.50, 6.37, 7.87, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 96
}

robot_rl_base = {
    'type': 'robot_rl_base',
    'blif': 'setup/robot_rl.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 96
}

reduction_layer = {
    'type': 'reduction_layer_setup',
    'blif': 'setup/reduction_layer.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [7.05, 6.83, 6.79, 6.76, 6.73, 6.69, 6.66, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 116
}

reduction_layer_base = {
    'type': 'reduction_layer_base',
    'blif': 'setup/reduction_layer.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 116
}

softmax = {
    'type': 'softmax_setup',
    'blif': 'setup/softmax.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [10.36, 9.68, 9.57, 9.47, 9.37, 9.27, 9.16, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 116
}

softmax_base = {
    'type': 'softmax_base',
    'blif': 'setup/softmax.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 116
}

picorv32 = {
    'type': 'picorv32_setup',
    'blif': 'setup/picorv32.blif',
    'sdc': """
create_clock -period <period> {wb_clk_i}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [6.82, 6.39, 6.33, 6.27, 6.20, 6.14, 6.07, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 130
}

picorv32_base = {
    'type': 'picorv32_base',
    'blif': 'setup/picorv32.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 130
}

aes = {
    'type': 'aes_setup',
    'blif': 'setup/aes.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [6.93, 6.63, 6.59, 6.54, 6.50, 6.45, 6.41, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 86
}

aes_base = {
    'type': 'aes_base',
    'blif': 'setup/aes.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 86
}

aes_inv_cipher = {
    'type': 'aes_inv_cipher_setup',
    'blif': 'setup/aes_inv_cipher_top.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [7.1, 7.2, 7.3, 7.4, 7.5, 8.0, 9.0, 7.0, 6.0]}],
    'layout': 'vtr_large',
    'graphics': False,
    'route_chan_width': 100
}

axi_crossbar = {
    'type': 'axi_crossbar_setup',
    'blif': 'setup/axi_crossbar.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [6.69, 6.38, 6.34, 6.29, 6.24, 6.20, 6.15, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 54
}

axi_crossbar_base = {
    'type': 'axi_crossbar_base',
    'blif': 'setup/axi_crossbar.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 54
}

# Dual Clock Design with CPD = 3.2907ns
ethmac = {
    'type': 'ethmac_setup',
    'blif': 'setup/ethmac.blif',
    'sdc': """
create_clock -period <period1> {rx_clk}
create_clock -period <period2> {tx_clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period1>', 'values': [1.0, 2.0, 3.0, 4.0, 5.0]},
              {'name': '<period2>', 'values': [1.0, 2.0, 3.0, 4.0, 5.0]}],
    'layout': 'vtr_large',
    'graphics': False,
    'route_chan_width': 100
}
firfix = {
    'type': 'firfix_setup',
    'blif': 'setup/firfix.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [13.70, 13.41, 13.36, 13.32,
                                              13.28, 13.23, 13.19, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 46
}

firfix_base = {
    'type': 'firfix_base',
    'blif': 'setup/firfix.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 46
}

fpu = {
    'type': 'fpu_base',
    'blif': 'setup/fpu.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [213.22, 209.61, 209.06, 208.52,
                                              207.98, 207.45, 206.90, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 86
}

fpu_base = {
    'type': 'fpu_base',
    'blif': 'setup/fpu.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 86
}

# This design doesn't have a latch
ialu = {
    'type': 'ialu_base',
    'blif': 'setup/ialu.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [7.0, 8.0, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 9.0, 10.0]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 100
}

LU8PEEng_base = {
    'type': 'LU8PEEng_base',
    'blif': 'setup/LU8PEEng.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 110
}

LU8PEEng = {
    'type': 'LU8PEEng_setup',
    'blif': 'setup/LU8PEEng.blif',
    'sdc': """
create_clock -period <period> {clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [76.93, 74.88, 74.57, 74.26,
                                              73.96, 73.65, 73.34, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 110
}

mkPktMerge_base = {
    'type': 'mkPktMerge_base',
    'blif': 'setup/mkPktMerge.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 48
}

mkPktMerge = {
    'type': 'mkPktMerge_setup',
    'blif': 'setup/mkPktMerge.blif',
    'sdc': """
create_clock -period <period> {CLK}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [4.56, 4.22, 4.17, 4.12, 4.07, 4.01, 3.96, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 48
}

mkDelayWorker32B_base = {
    'type': 'mkDelayWorker32B_base',
    'blif': 'setup/mkDelayWorker32B.blif',
    'sdc': """
create_clock -period 0.0 *
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 50
}

mkDelayWorker32B = {
    'type': 'mkDelayWorker32B_setup',
    'blif': 'setup/mkDelayWorker32B.blif',
    'sdc': """
create_clock -period <period> {wciS0_Clk}
set_input_delay -clock * -max 0 [get_ports {*}]
set_output_delay -clock * -max 0 [get_ports {*}]
    """,
    'param': [{'name': '<period>', 'values': [8.31, 7.27, 7.11, 6.96, 6.80, 6.64, 6.48, 1000]}],
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': 50
}

# Stereovision is multiclock
stereovision3_base = {
    'type': 'stereovision3_base',
    'blif': 'setup/stereovision3.blif',
    'sdc': """

    """,
    'param': None,
    'layout': 'auto',
    'graphics': False,
    'route_chan_width': -1
}

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
