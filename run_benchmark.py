import os
import subprocess
import re
import csv
import sys
import argparse
import random
from pathlib import Path
import pathlib
from string import Template
from subprocess import Popen, PIPE, TimeoutExpired
from typing import List
import config
from config import *
from matplotlib import pyplot as plt
from matplotlib import colors
import seaborn as sns
import math
import shutil
import json

# TODO: Write better comments
# TODO: use try-except for error handling
# TODO: Clean up code, especially function arguments
# TODO: Make CLI runnable
# TODO: Implement analyze_result(), for seed sweep analysis

def construct_sdc(test_config):
    '''
    Constructs multiple SDCs with different parameter values and returns a list of generated SDC file names.
    
    Args: 
        test_config (dict): A dictionary of test case description.
    
    Returns:
        Directory in which the SDCs are saved.
    '''
    # List contains generated sdc file names
    generated_sdc_list = []

    # Define out_dir (e.g. ./results/timing/create_clock_rca/sdc)
    out_dir = RESULTS_DIR / 'timing' / test_config['type'] / 'sdc'

    # Remove any existing SDC files
    if out_dir.exists(): 
        shutil.rmtree(out_dir)  # Delete all subdirectories and files
        print(f"Cleaned existing directory: {out_dir}")
    
    # Create out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Arguments
    sdc_template = test_config['sdc'] # SDC template
    params = test_config['param'] # Parameters
    
    # SDC template has no parameters to change
    if params is None: 
        out_filename = test_config['type'] + '.sdc'
        out_filepath = out_dir / out_filename
        
        with open(out_filepath, 'w') as out_sdc:
            out_sdc.write(sdc_template)
        
        generated_sdc_list.append(out_filepath)
        print(f"Generated SDC: {out_filepath}")
    
    # Replace parameter values in the SDC template
    else: 
        # Save default value for all params
        defaults = {p['name']: p['default'] for p in params} 
        
        # Iterate over all params
        for param in params:
            param_name = param['name']
            
            # Iterate over all values of each param
            for val in param['values']:
                current_values = defaults.copy()  # Copy the default values to 'current_values'
                current_values[param_name] = val  # Substitute default value of current param
                
                new_constraint = sdc_template  # Copy sdc template
                filename_parts = []  # List for file name generation
                
                # Substitute the parameters in the SDC with actual values
                for p_name, p_val in current_values.items():
                    str_val = str(p_val)
                    new_constraint = new_constraint.replace(p_name, str_val)
                    
                    # Remove '<>' from filename_parts
                    clean_name = p_name.strip('<>')
                    filename_parts.append(f"{clean_name}_{str_val}")
                
                # Create file name (e.g. period_10.0.sdc)
                out_filename = "_".join(filename_parts) + ".sdc"
                out_filepath = out_dir / out_filename
                
                # Output the generated SDC
                with open(out_filepath, 'w') as out_sdc:
                    out_sdc.write(new_constraint)
                
                # Save the out file path to a list
                generated_sdc_list.append(out_filepath)
                print(f"Generated SDC: {out_filepath}")
                
    print(f"SDC Generation for {test_config['type']} Complete.\n")       
             
    return out_dir

# No need for synthesis. All SDCs are blif-specific. 
def run_synthesis(test_config):
    '''
    Synthesizes circuit described in Verilog using Parmys or Odin II.
    
    Args:
      test_cases (list): 
    
    Returns:
      Path to created blif file
    '''
    blif_list = []
    
    for test in test_cases:
        # Prepare arguments for parmys/odin
        architecture_path = ARCH_FILE
        verilog_path = MICRO_ROOT / test['circuit']
        frontend = test['frontend']
        output_path = RESULTS_DIR / 'blif' / f'{test['type']}.blif'
        temp_dir = RESULTS_DIR / 'blif' / 'temp'
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Commands to run synthesis
        cmd = []
        
        if frontend == 'parmys':
            cmd = [
                f'{VTR_ROOT}/vtr_flow/scripts/run_vtr_flow.py',
                f'{verilog_path}',
                f'{architecture_path}',
                '-starting_stage', 'parmys',
                '-ending_stage', 'parmys',
                '-temp_dir', f'{temp_dir}'
            ]
            print(f"Running Parmys to synthesize {test['circuit']}")
        
        elif frontend == 'odin':
            cmd = [
                f'{VTR_ROOT}/odin_ii/odin_ii',
                '-a', f'{architecture_path}',
                '-V', f'{verilog_path}',
                '-o', f'{output_path}'
            ]
            print(f"Running Odin II to synthesize {test['circuit']}")
            
        else:
            print("Unknown Synthesis Tool")
        try:
            result = subprocess.run(cmd, check=True, capture_output= True, text=True)
            print(f"Synthesis Complete: {output_path.name}")
            blif_list.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"Error during synthesis with {frontend}")
            print(f"Command: {e.cmd}")
            print(f"Exit Code: {e.returncode}")
            print(f"Stderr: {e.stderr}")
    
    return blif_list

def run_vpr(test_config, sdc_dir=None, seed=1, **kwargs):
    '''
    Run place and route on the given test case with VPR.
    VPR will generate post-implementation netlists and timing analysis files that can be analyzed later on. 
    
    Args:
        test_config (dict): A dictionary of a single test case description.
        sdc_dir (str): The directory where SDC files are located. 
        seed (int): Use the given seed for placement.
        use_params (Bool): Use parameters in the post-synthesis netlist. Set to False for OpenSTA
        placement_type (str): Choose 'timing_driven' or 'analytical' placement.
        place_algorithm (str): Choose 'criticality_timing' or 'slack_timing' for placement.
        place_agent_algorithm (str): Choose the RL agent algorithm 'e_greedy' or 'softmax' for placement.
        analytical_solver (str): Choose 'qp-hybrid' or 'lp-b2b' for analytical placement.
        ap_timing_tradeoff (float): Any number between 0.0 for wirelength minimzation and 1.0 for timing optimization. 
        hold (Bool): Turn on hold analysis using '--routing_budgets_algorithm yoyo'.
      
    Returns:
        test_cases (list): The 
        temp_dir (Path): 
        
    '''
    blif_file = MICRO_ROOT / test_config['blif'] # BLIF file

    # Get SDC files in 'sdc_dir' 
    sdc_list = get_sdc_list(sdc_dir)

    # Create a directory where the VPR output files will be moved to
    result_dir, kwargs = create_result_dir(base_dir=RESULTS_DIR/'timing'/test_config['type'], seed=seed, **kwargs)

    # Write the experiment parameters as a JSON file
    make_json(test_config=test_config, result_dir=result_dir, seed=seed, **kwargs)

    # Run the test for all the SDCs in 'sdc_dir'
    for sdc in sdc_list:

        cmd, graphics_file, temp_dir = build_vpr_command(test_config=test_config, sdc=sdc, seed=seed, **kwargs)

        # Run VPR with the prepared command
        try:
            sdc_label = sdc.name if sdc else 'Default'
            print(f"Running VPR\nBLIF: {blif_file.name}, SDC: {sdc_label}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"STDERR: {result.stderr}\n")
        except subprocess.CalledProcessError as e:
            print(f"VPR Failed: {e}\n")
            print(f"STDOUT: {e.stdout}\n")
            #print(f"STDERR: {e.stderr}\n")
            raise

        # Print whether SDC was found
        _ = was_sdc_parsed(temp_dir)

        # Directory where each individual test results are saved
        run_output_dir = result_dir / f"{sdc.name if sdc else 'default_sdc'}"
        run_output_dir.mkdir(parents=True)
        
        # Move the graphics file from 'temp_dir' to the result directory
        if test_config['graphics'] == True:
            png_file = temp_dir / graphics_file
            png_file.rename(run_output_dir / graphics_file)
        
        # Get timing results
        timing_summary, hold_rpt, setup_rpt, skew_hold_rpt, skew_setup_rpt = make_vpr_summary(temp_dir)

        # Write parsed timing information to a new file
        save_vpr_timing_report(run_output_dir, sdc, timing_summary, hold_rpt, setup_rpt, skew_hold_rpt, skew_setup_rpt)

        # Save the distribution plot to the result directory
        save_path_distribution(setup_rpt, run_output_dir)
        
    return test_config, temp_dir

def get_sdc_list(sdc_dir=None):
    '''
    Returns a list of SDC files located under the provided 'sdc_dir'.
    There will always be a None object in the list for baseline testing.

    Args:
        sdc_dir (str): The directory in which the SDC files are located
    Returns:
        sdc_list (list): A list of Path objects
    '''

    if sdc_dir is None:
        return [None] # No SDCs in the directory, use VPR's default constraint

    # Convert to Path object
    sdc_dir = Path(sdc_dir)

    if sdc_dir.is_file():
        return [sdc_dir]
    elif sdc_dir.is_dir():
        sdc_list = list(sdc_dir.glob("*.sdc"))
        if not sdc_list:
            print(f"Warning: No SDC files found in {sdc_dir}")
        sdc_list.insert(0,None)
        return sdc_list
    else:
        print(f"Error: Path {sdc_dir} does not exit.")
        return [None]

def create_result_dir(base_dir, seed, **kwargs):
    '''
    Creates a directory where the timing reports will be saved. 
    seed, placement_type, place_algorithm, hold

    seed01_t-driven_criticality_hold
    seed10_analytical_slack 
    Args:
        base_dir (Path): 
    '''
    folder_name = f"seed{seed:02d}"

    placement_type = kwargs.get('placement_type', 'timing_driven')
    place_algorithm = kwargs.get('place_algorithm', 'criticality_timing')
    analytical_solver = kwargs.get('analytical_solver', 'lp-b2b')
    hold = kwargs.get('hold', False)

    # New folder name
    if placement_type == "timing_driven":
        folder_name += "_t-driven"

        if place_algorithm == "criticality_timing":
            folder_name += "_criticality"
        else:
            folder_name += "_slack"

    elif placement_type == "analytical":
        folder_name += "_analytical"
        folder_name += f"_{analytical_solver}"
    
    else:  # Invalid placement type specified, resort to timing driven placement
        print(f"Invalid placement type {placement_type} specified. Using timing-driven \
        placement instead.")
        kwargs['placement_type'] = 'timing_driven'  # Modify the VPR arguments

    if hold:
        folder_name += "_hold"

    i = 0

    while True:
        new_folder_name = f"{folder_name}{i:02d}"
        full_path = base_dir / new_folder_name

        if not full_path.exists():
            full_path.mkdir(parents=True)
            return full_path, kwargs

        i += 1

def build_vpr_command(test_config, sdc=None, seed=1, **kwargs):
    '''
    Creates a command for VPR execution.

    Args: 
        test_config (dict): 
        sdc (Path): 
        seed (int): 
        kwargs:   
    '''
    # Path definitions
    blif_file = MICRO_ROOT / test_config['blif'] # BLIF file
    architecture_file = ARCH_FILE # FPGA architecture file
    layout = test_config['layout'] # Device size
    temp_dir = RESULTS_DIR / 'timing' / test_config['type'] / 'vpr' # Directory that VPR will output its results to
    # timing_summary = temp_dir / 'timing_summary.txt' # Timing summary

    assert blif_file.exists()
    assert architecture_file.exists()

    # Get kwargs
    placement_type = kwargs.get('placement_type', 'timing_driven')  # Timing-driven placement vs Analytical placement
    place_algo = kwargs.get('place_algorithm', 'criticality_timing')  # Placement algorithm for timing-driven placement
    place_agent_algo = kwargs.get('place_agent_algorithm', 'softmax')  # RL agent algorithm
    analytical_solver = kwargs.get('analytical_solver', 'lp-b2b')  # Analytical solver 
    ap_timing_tradeoff = str(kwargs.get('ap_timing_tradeoff', '0.5'))  # Timing tradeoff for analytical placement
    budgets_algo = 'yoyo' if kwargs.get('hold') else 'disable'  # Use yoyo for hold tests, disable for normal setup tests
    use_params = kwargs.get('use_params', False)  # Use parameters when generating post-implementation netlist
    num_paths = str(kwargs.get('num_paths', '100'))  # Number of timing paths to report

    # Build the default VPR command
    cmd = [
        f'{VTR_ROOT}/vtr_flow/scripts/run_vtr_flow.py',
        f'{blif_file}',
        f'{architecture_file}',
        '-starting_stage', 'abc', # Start from ABC (Skip synthesis)
        '-temp_dir', f'{temp_dir}', # Output directory
        '--write_block_usage', 'resources.txt', # Write FPGA resource usage as 'resources.txt'
        '--device', f'{layout}',
        '--write_timing_summary', 'timing_summary.txt',
        '--generate_net_timing_report', 'on',
        # Options for post-implementation timing analysis with OpenSTA
        '--gen_post_synthesis_netlist', 'on',
        '--timing_report_skew', 'on'
    ]

    # Add optional VPR arguments
    # Timing-driven placement
    if placement_type == 'timing_driven':
        cmd += [
            '--place_algorithm', f'{place_algo}',
            '--place_agent_algorithm', f'{place_agent_algo}',
            '--routing_budgets_algorithm', f'{budgets_algo}'
        ]
    # Analytical placement
    elif placement_type == 'analytical':
        cmd += [
            '--analytical_place',
            '--ap_analytical_solver', f'{analytical_solver}',
            '--ap_timing_tradeoff', f'{ap_timing_tradeoff}',
            '--routing_budgets_algorithm', f'{budgets_algo}',
            '--route_chan_width', '100',  # This ensure VPR won't fail during the routing stage
            '--route', '--analysis'  # Forces VPR to run routing and analysis stages
        ]
    # Wrong placement type
    else: 
        print(f"Wrong placment type specified: {placement_type}, resorting to timing_driven placement.")

    # Seed
    if seed:
        cmd += ['--seed', f'{seed}']

    # Do not use parameters in post-synthesis netlist (flag for OpenSTA)
    if use_params is False:
        cmd += ['--post_synth_netlist_module_parameters', 'off']
    
    # Configure how many timing paths to report 
    if num_paths != '100':
        cmd += ['--timing_report_npaths', f'{num_paths}']

    # Specify SDC file
    if sdc is not None:
        cmd += ['--sdc_file', rf'{sdc}']
        cmd += ['--gen_post_implementation_sdc', 'on']

    # Save VPR graphics
    if test_config['graphics'] == True:
        cmd += ['--disp', 'on']
        graphics_file = f"{sdc.name if sdc else 'default_sdc'}.png"
        cmd += ['--graphics_commands', f'save_graphics {graphics_file};']

    return cmd, graphics_file if test_config.get('graphics') else None, temp_dir

def save_vpr_timing_report(result_dir, sdc, timing_summary, hold_rpt, setup_rpt, skew_hold_rpt, skew_setup_rpt):
    '''
    Saves the parsed VPR timing report to the result directory.
    Args:
        result_dir (Path):
        sdc (Path): 
    '''
    # Write parsed timing information to a new file
    sdc_name = sdc.stem if sdc else 'default_sdc'
    with open(result_dir / f'{sdc_name}_timing.txt', 'w') as f:
        f.writelines('\n'.join(timing_summary))
    with open(result_dir / f'{sdc_name}_hold.txt', 'w') as f:
        f.writelines(hold_rpt)
    with open(result_dir / f'{sdc_name}_setup.txt', 'w') as f:
        f.writelines(setup_rpt)
    with open(result_dir / f'{sdc_name}_skew_hold.txt', 'w') as f:
        f.writelines(skew_hold_rpt)
    with open(result_dir / f'{sdc_name}_skew_setup.txt', 'w') as f:
        f.writelines(skew_setup_rpt)

def make_json(test_config, result_dir, seed, **kwargs):
    '''
    Creates a JSON file in the 'result_dir' containing the test parameters. 

    Args:
        test_config (dict): 
        result_dir (Path):
        seed (int):
        kwargs(): 
    '''

    # Get kwargs
    placement_type = kwargs.get('placement_type', 'timing_driven')
    place_algorithm = kwargs.get('place_algorithm', 'criticality_timing')
    place_agent_algorithm = kwargs.get('place_agent_algorithm', 'softmax')
    analytical_solver = kwargs.get('analytical_solver', 'lp-b2b')
    ap_timing_tradeoff = str(kwargs.get('ap_timing_tradeoff', '0.5'))
    hold = kwargs.get('hold')
    use_params = kwargs.get('use_params', 'False')
    
    # 2. Save the run parameters in a dictionary format
    if placement_type == 'timing_driven':
        run_params = {
            "test_case": test_config['type'],
            "sdc_template": test_config['sdc'],
            "seed": seed,
            "use_params": use_params,
            "placement_type": placement_type,
            "place_algorithm": place_algorithm,
            "place_agent_algorithm": place_agent_algorithm,
            "hold": hold
        }
    elif placement_type == 'analytical':
        run_params = {
            "test_case": test_config['type'],
            "sdc_template": test_config['sdc'],
            "seed": seed,
            "use_params": use_params,
            "placement_type": placement_type,
            "analytical_solver": analytical_solver,
            "ap_timing_tradeoff": ap_timing_tradeoff,
            "hold": hold
        }
    
    # 3. Dump to a JSON file
    config_path = result_dir / "config.json"
    with open(config_path, 'w') as f:
        json.dump(run_params, f, indent=4)

def run_opensta(test_cases, liberty_file, tcl_file=None):
    '''
    Run OpenSTA to perform post-implementation timing analysis. 
    
    Args:
        test_cases (list): A list of timing test configurations.
        liberty_file (Path): Path to liberty file to be used for OpenSTA.
        tcl_file (Path): A test-specific TCL file for timing reports. Runs default TCL if none specified.
    Returns:
    
    '''
    for test in test_cases:
        vpr_out_dir = RESULTS_DIR / test['type'] / 'vpr' # VPR output directory
        temp_dir = RESULTS_DIR / test['type'] / 'opensta' # OpenSTA output directory
        top_level_module = test['top_level_module'] # Top level module of the circuit
        
        # Make the directory to run OpenSTA in
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the post-implementation netlist, SDC and SDF from VPR
        post_implementation_netlist = next(vpr_out_dir.glob('*post_synthesis.v'), None)
        post_implementation_sdc = next(vpr_out_dir.glob('*post_synthesis.sdc'), None)
        post_implementation_sdf = next(vpr_out_dir.glob('*post_synthesis.sdf'), None)
        
        if tcl_file is None: 
            # Path to the TCL file to configure timing analysis
            tcl_file = temp_dir / 'run_opensta.tcl'
            
            # Fill the TCL file with OpenSTA commands
            with open(tcl_file, 'w') as f:
                # Read a skeleton liberty file
                # Note: The 'primitive.lib' file only contains timing characteristics of LUTs and FFs. 
                f.write(f"read_liberty {liberty_file}\n")
                f.write(f"read_verilog {post_implementation_netlist}\n") # Verilog file
                f.write(f"link_design {top_level_module}\n") # Link the top module
                f.write(f"read_sdf {post_implementation_sdf}\n") # SDF file
                f.write(f"read_sdc {post_implementation_sdc}\n") # SDC file
                
                f.write("report_checks "
                    "-group_path_count 100 "
                    "-digits 3 "
                    "-path_delay max "
                    "> open_sta_report_timing.setup.rpt\n")
                f.write("report_checks "
                    "-group_path_count 100 "
                    "-digits 3 "
                    "-path_delay min "
                    "> open_sta_report_timing.hold.rpt\n")
                f.write("report_wns\n")
                f.write("report_tns\n")
                f.write("report_checks "
                        "-unconstrained "
                        "> open_sta_report_unconstrained.rpt\n")
                f.write("report_clock_min_period")
        
        cmd = ["sta",
               "-exit",
               "-no_splash",
               tcl_file]
        
        # Run the subprocess
        try:
            print("Running OpenSTA\n")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"STDERR: {result.stderr}\n")
        except subprocess.CalledProcessError as e:
            print(f"OpenSTA Failed: {e}\n")
            print(f"STDOUT: {e.stdout}\n")
            print(f"STDERR: {e.stderr}\n")
            raise

def make_vpr_summary(temp_dir):
    '''
    Parses timing analysis results from VPR and outputs the timing summary to a .txt file. 
    
    Args:
        temp_dir (Path): 
    
    Returns:
        A list of timing results
    ''' 
    # File paths to parse
    vpr_out_file = temp_dir / 'vpr.out'
    skew_hold_file = temp_dir / 'report_skew.hold.rpt'
    skew_setup_file = temp_dir / 'report_skew.setup.rpt'
    timing_hold_file = temp_dir / 'report_timing.hold.rpt'
    timing_setup_file = temp_dir / 'report_timing.setup.rpt'
    unconstrained_hold_file = temp_dir / 'report_unconstrained_timing.hold.rpt'
    unconstrained_setup_file = temp_dir / 'report_unconstrained_timing.setup.rpt'
    report_clk_file = temp_dir / 'report_clk.out'
     
    # Parse timing information from 'vpr.out' using regex
    # 'vpr.out' has information on 'total nets', 'total wirelength', 'critical path delay', 'TNS', 'WNS', 'netlist clocks'
    with open(vpr_out_file, 'r') as f:
        content = f.read()
    
    # Match and parse timing metrics
    global_net = re.search(r"Number of global nets:\s+(\d+)", content) 
    routed_net = re.search(r"Number of routed nets \(nonglobal\):\s+(\d+)", content)
    wirelength = re.search(r"Total wirelength:\s+(\d+)", content)
    cpd = re.search(r"Final critical path delay \(least slack\):\s+([\d\.]+)", content)
    sWNS = re.search(r"Final setup Worst Negative Slack \(sWNS\):\s+([\d\.\-eE]+)", content)
    sTNS = re.search(r"Final setup Total Negative Slack \(sTNS\):\s+([\d\.\-eE]+)", content)
    hWNS = re.search(r"Final hold Worst Negative Slack \(hWNS\):\s+([\d\.\-eE]+)", content)
    hTNS = re.search(r"Final hold Total Negative Slack \(hTNS\):\s+([\d\.\-eE]+)", content)
    num_sdc = re.search(r"Applied (\d+) SDC commands", content) 
    num_sdc_clock = re.search(r"Timing constraints created (\d+) clocks", content)
    num_netlist_clock = re.search(r"Netlist contains (\d+) clocks", content)

    # Parse netlist clock information, iterates in case multiple clocks exist in the design
    netlist_clk_info = [] # Contains the existing netlist clocks

    for match in re.finditer(r"Netlist Clock '([^']+)' Fanout: (\d+) pins.*?, (\d+) blocks", content):
        netlist_clk_info.append({
            'name': match.group(1),
            'fanout_pins': int(match.group(2)),
            'fanout_blocks': int(match.group(3))
        }) 

    # Parse constrained clock information, iterates in case multiple clocks were constrained
    constrained_clk = [] # Contains the clocks that were constrained
    
    for match in re.finditer(r"Constrained Clock\s+(.*)", content):
        constrained_clk.append(match.group(1))

    constrained_clk_str = '  \n'.join(constrained_clk)
    
    # Transform datatype
    total_nets = int(global_net.group(1)) + int(routed_net.group(1))
    wirelength = int(wirelength.group(1))
    cpd = float(cpd.group(1))
    fmax = 1000 / cpd
    
    sWNS = float(sWNS.group(1))
    sTNS = float(sTNS.group(1))
    hWNS = float(hWNS.group(1))
    hTNS = float(hTNS.group(1))
    timing_met = True if (sWNS >= 0 and hWNS >= 0) else False
    
    num_sdc = int(num_sdc.group(1)) if num_sdc else 'N/A'
    num_sdc_clock = int(num_sdc_clock.group(1)) if num_sdc_clock else 'N/A'
    num_netlist_clock = int(num_netlist_clock.group(1))
    
    '''
    We should parse the following:
        for how many paths:
            path number
            start point, end point and its clocks
            clock rising edge, clock source latency, clock input latency, clock uncertainty, 
            data arrival time, data required time, slack met? 
    '''
    
    # Parse detailed hold analysis
    hold_report = parse_timing_report(timing_hold_file, is_skew=False)
    
    # Parse detailed setup analysis
    setup_report = parse_timing_report(timing_setup_file, is_skew=False)

    # Parse skew hold
    skew_hold_report = parse_timing_report(skew_hold_file, is_skew=True)
    
    # Parse skew setup
    skew_setup_report = parse_timing_report(skew_setup_file, is_skew=True)

    # Write timing summary that we have parsed
    timing_summary = [f'Number of global nets: {global_net.group(1)}', f'Number of routed nets: {routed_net.group(1)}', 
                      f'Total number of nets: {total_nets}', f'Wirelength: {wirelength}', 
                      f'Critical path delay: {cpd}', f'Fmax: {fmax}MHz', f'sWNS: {sWNS}', f'sTNS: {sTNS}',
                      f'hWNS: {hWNS}', f'hTNS: {hTNS}', 
                      f'Timing met: {timing_met}', f'Number of SDCs Applied: {num_sdc}',
                      f'Number of constrained clocks: {num_sdc_clock}',
                      f'List of constrained clocks:\n{constrained_clk_str}\n' 
                      f'Number of netlist clocks: {num_netlist_clock}', f'Netlist clock information:\n{netlist_clk_info}']
    
    return timing_summary, hold_report, setup_report, skew_hold_report, skew_setup_report

def parse_timing_report(file_path, is_skew=False):
    ''' 
    Parses the detailed timing report written by VPR.
    
    Args:
        file_path (Path): Path to the timing report.
        is_skew (Bool): True if the file is a skew report, false otherwise. 
    Returns:
        list: A list of the parsed timing paths.
    '''
    content = Path(file_path).read_text()
    
    # 1. Partition the content by 'Path' or 'Skew Path'
    delimiter = r"#Skew Path \d+" if is_skew else r"#Path \d+"
    path_blocks = re.split(delimiter, content)[1:]
    
    all_paths = []
    
    for block in path_blocks:
        # Do not parse if skew == 0
        if is_skew:
            skew = re.search(r"skew\s+([\d\.\-eE]+)", block)
            if skew and float(skew.group(1)) == 0.0:
                continue

        path_info = []
        
        # Startpoint & Endpoint
        startpoint = re.search(r"Startpoint:\s+(.*)", block)
        endpoint = re.search(r"Endpoint\s+:\s+(.*)", block)

        # 수치 데이터 추출 (Incr이나 Path 컬럼에서 값 추출)
        # 여러 번 등장할 경우(Launch/Capture)를 대비해 findall 후 적절한 위치 선정
        rise_edge = re.findall(r"clock .* \(rise edge\)\s+([\d\.]+)", block)
        latency = re.findall(r"clock source latency\s+([\d\.]+)", block)
        uncertainty = re.search(r"clock uncertainty\s+([\d\.]+)", block)
        
        req_time = re.search(r"data required time\s+([\d\.]+)", block)
        arr_time = re.search(r"data arrival time\s+([\d\.]+)", block)
        slack = re.search(r"slack \((MET|VIOLATED)\)\s+([\d\.\-]+)", block)
        
        startpoint = startpoint.group(1).strip() if startpoint else 'N/A'
        endpoint = endpoint.group(1).strip() if endpoint else 'N/A'
        rise_edge = rise_edge[-1] if rise_edge else 'N/A'
        latency = latency[-1] if latency else 'N/A'
        uncertainty = uncertainty.group(1) if uncertainty else 'N/A'
        req_time = req_time.group(1) if req_time else 'N/A'
        arr_time = arr_time.group(1) if arr_time else 'N/A'

        # Decide if report includes Slack vs Skew 
        if is_skew:
            slack_str = f"Skew: {skew.group(1)}"
        else:
            slack_met = slack.group(1) if slack else "N/A"
            slack_val = slack.group(2) if slack else "0.000"
            slack_str = f"Slack: {slack_val} ({slack_met})"
        
        # Write timing information
        path_info = [
            f"Startpoint: {startpoint}\n",
            f"Endpoint  : {endpoint}\n",
            f"  Rise Edge: {rise_edge}, Latency: {latency}, Uncertainty: {uncertainty}\n",
            f"  Required: {req_time}, Arrival: {arr_time}\n",
            f"  {slack_str}\n",
            f"{'-'*60}\n"
        ]

        all_paths.extend(path_info)
        
    return all_paths
    
def get_opensta_timing():
    '''
    
    '''

def get_min_distance(place_file):
    '''
    Computes the minimum of the average distance from each block to all four peripheries of the FPGA.
    
    Args:
        place_file (Path): Placement file containing the X, Y coordinates of each clusters.
        
    Returs:
        float: The minimum average distance to the peripheries
    '''
    # Read placement file
    assert place_file.exists()
    content = place_file.read_text()
    
    # Parse FPGA layout size 
    array_size = re.search(r"Array size:\s+(\d+)\s+x\s+(\d+)", content)
    W = int(array_size.group(1)) # FPGA width
    H = int(array_size.group(2)) # FPGA height
    
    # Add distance if (x,y) tells you its a logic block
    north_distance = 0
    south_distance = 0
    east_distance = 0
    west_distance = 0
    
    block_count = 0
    lines = content.splitlines()
    
    # For each line (block) in the placement(.place) file
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('Netlist_File') or line.startswith('Array size'):
            continue
        
        # Parse x, y coordinates of a block
        columns = line.split()
        block_name = columns[0]
        x = int(columns[1])
        y = int(columns[2])
        
        # If block is IO, do not calculate distance
        if x == W + 1 or y == H + 1 or x == 0 or y == 0:
            continue

        # Keep track of the number of blocks
        block_count += 1
        
        # Accumulate distance
        north_distance += (H - y)
        south_distance += y
        east_distance += (W - x)
        west_distance += x
    
    # Compute the average
    north_distance /= block_count
    south_distance /= block_count
    east_distance /= block_count
    west_distance /= block_count
    
    min_distance = min(north_distance, south_distance, east_distance, west_distance)
    return min_distance

def was_sdc_parsed(temp_dir):
    '''
    Inspects vpr.out to check if SDC was properly parsed.
    
    Args:
        temp_dir (Path): Directory in which the VPR log file is located.
    
    Returns:
        bool: True if SDC was parsed, false if otherwise.
    '''
    pattern = r"SDC file '.*?' not found"
    
    with open(temp_dir / 'vpr.out','r') as f:
        content = f.read()
    
    if re.search(pattern, content):
        print("SDC file was not found for the previous test.\n")
        return False
    print("SDC file was found for the previous test.\n")
    return True

def save_path_distribution(timing_report, save_dir):
    '''
    Creates histograms representing the distribution of timing paths over the path delay,
    and saves them as two separate PNG files (Arrival Time and Slack).
    
    Args:
        timing_report (list): List of timing paths parsed by the function 'parse_timing_report'.
        save_dir (Path): The Path object indicating where the plots will be saved.
    '''
    arrival_times = []
    slacks = []

    numeric_pattern = r"[-+]?\d*\.?\d+"

    # Parse the text data into float arrays
    # Iterate by 6 because timing_report is a flattened list (extended by 6 lines per path)
    for i in range(0, len(timing_report), 6):
        try:
            # timing_report[i+3] format: "  Required: {req_time}, Arrival: {arr_time}\n"
            arrival_part = timing_report[i+3].split("Arrival:")[1]
            arr_match = re.search(numeric_pattern, arrival_part)
            
            # timing_report[i+4] format: "  Slack: {slack_val} ({slack_met})\n" OR "  Skew: {skew_val}\n"
            # Search the line directly without split() to safely handle both Slack and Skew
            slack_match = re.search(numeric_pattern, timing_report[i+4])

            if arr_match and slack_match:
                arrival_times.append(float(arr_match.group()))
                slacks.append(float(slack_match.group()))
            
        except (IndexError, ValueError, AttributeError) as e:
            print(f"Warning: Skipping a path due to parsing error. Details: {e}")
            continue

    if not arrival_times or not slacks:
        print("Error: No valid timing data could be parsed for the histograms.")
        return

    # Ensure save_dir exists before trying to save files
    save_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    # Plot and save arrival time distribution
    plt.figure(figsize=(8, 6))  # Create a new standalone figure
    sns.histplot(
        arrival_times, 
        kde=True, 
        color="#2A9D8F", 
        edgecolor='black',
        alpha=0.7,
        bins='auto'
    )
    plt.title("Arrival Time Distribution", fontsize=14, fontweight='bold')
    plt.xlabel("Arrival Time", fontsize=12)
    plt.ylabel("Count (Number of Paths)", fontsize=12)
    plt.tight_layout()
    
    arr_filepath = save_dir / "arrival_time_distribution.png"
    plt.savefig(arr_filepath, dpi=300)
    plt.close()

    # Plot and save slack distribution
    plt.figure(figsize=(8, 6))  # Create a new standalone figure
    sns.histplot(
        slacks, 
        kde=True, 
        color="#E76F51",
        edgecolor='black',
        alpha=0.7,
        bins='auto'
    )
    plt.title("Slack Distribution", fontsize=14, fontweight='bold')
    plt.xlabel("Slack", fontsize=12)
    plt.ylabel("Count (Number of Paths)", fontsize=12)
    
    # Add a vertical line at Slack = 0
    plt.axvline(0, color='red', linestyle='--', linewidth=1.5, label='Zero')
    plt.legend()
    plt.tight_layout()
    
    slack_filepath = save_dir / "slack_distribution.png"
    plt.savefig(slack_filepath, dpi=300)
    plt.close()  # Close the second figure

    print(f"Plots successfully saved to:\n  - {arr_filepath}\n  - {slack_filepath}")
    
def visualize_result(test_cases, title, data, label):
    '''
    Create a histogram of given list
    
    Args:
        data (list): Y axis
        label (list): X axis 
    '''
    plt.bar(label, data)
    plt.xlabel("Delay Values")
    plt.ylabel("min_avg_distance")
    
    plot_path = RESULTS_DIR / test_cases[0]['type'] / 'plot.png'
    plt.savefig(plot_path)

def analyze_result():
    '''
    Given multiple experiment results (experiment result directories), compare or compute the average of various timing metrics
    This function can be used for seed sweep. 
    '''
    # TODO: Implement this function, however it is lower in priority.

def main():
    '''
    '''
    # Argument Parser
    parser = argparse.ArgumentParser(description="Execute the Timing Benchmark")

    # Test config
    parser.add_argument('--test', type=str, required=True, 
                        help="테스트할 설정 이름 (예: create_clock_rca)")

    # Seed and SDC
    parser.add_argument('--seed', type=int, nargs='+', default=[1], help="배치(Placement) 시드 값 목록 (예: --seed 1 2 3)") # Should be list
    parser.add_argument('--sdc_dir', type=str, help="", default=None) # The flow should be able to run without any sdcs.

    # VPR algorithm
    parser.add_argument('--placement_type', choices=['timing_driven', 'analytical'], 
                        default='timing_driven', help="배치 유형 선택")
    parser.add_argument('--place_algorithm', choices=['criticality_timing', 'slack_timing'], 
                        default='criticality_timing', help="타이밍 기반 배치 알고리즘")
    parser.add_argument('--place_agent_algorithm', choices=['e_greedy', 'softmax'],
                        default='softmax')
    parser.add_argument('--analytical_solver', choices=['qp-hybrid', 'lp-b2b'], 
                        default='qp-hybrid', help="Analytical 배치 솔버")
    parser.add_argument('--ap_timing_tradeoff', type=float, default=0.5, 
                        help="Analytical 배치의 Timing tradeoff (0.0~1.0)")
    parser.add_argument('--hold', action='store_true', help="Hold 타임 분석 활성화")
    parser.add_argument('--num_paths', type=int, default=100, help="리포트할 타이밍 패스 개수")

    # Misc
    parser.add_argument('--use_params', action='store_true')

    args = parser.parse_args()  # Parse arguments

    # Get the configuration dictionary from config.py
    try:
        test_config = getattr(config, args.test)
    except AttributeError:
        print(f"Error: '{args.test}' doesn't exist in 'config.py'.")
        sys.exit(1)

    # SDC
    try:
        # Use the given SDC directory, if not given, create sdc based on template
        sdc_dir = args.sdc_dir if args.sdc_dir else construct_sdc(test_config)
    except Exception as e:
        print(f"Error during SDC generation: {e}")
        sys.exit(1)

    # Run VPR
    try:
        print(f"Running VPR for {args.test}")
        for seed in args.seed:
            # Run unconstrained test first
            run_vpr(
                test_config=test_config,
                sdc_dir = sdc_dir,
                seed=seed,
                placement_type=args.placement_type,
                place_algorithm=args.place_algorithm,
                place_agent_algorithm=args.place_agent_algorithm,
                analytical_solver=args.analytical_solver,
                ap_timing_tradeoff=args.ap_timing_tradeoff,
                hold=args.hold,
                use_params=args.use_params,
                num_paths=args.num_paths
            )
    except Exception as e:
        print(f"Error during VPR run: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
    '''
    test_sdc_dir = construct_sdc(config.create_clock_rca)
    run_vpr(test_config=config.create_clock_rca, sdc_dir=test_sdc_dir, seed=1, placement_type='analytical')
    '''


    '''
    parser = argparse.ArgumentParser(description="Run Timing Test")
    parser.add_argument('--algorithm')
    parser.add_argument('--sdc')
    parser.add_argument('--seed')
    # TODO: Finish implementing CLI
    
    
    set_clock_groups_sdc = construct_sdc(TEST_DICT['set_clock_groups'])
    for sdc in set_clock_groups_sdc:
        test_config, place_file, _ = run_vpr(TEST_DICT['set_clock_groups'], sdc, random_seed = False)
    #run_opensta(TEST_DICT['create_clock'], LIBERTY_FILE)
        #distance.append(get_min_distance(place_file))
    #visualize_result(test_config, distance, TEST_DICT['create_clock'][0]['param'][0]['values'])
    
    # Run baseline test without SDCs
    run_unconstrained_test([TEST_DICT['set_input_delay'][0]], random_seed=False, use_params=True, t_driven=False, hold=False)
    
    # Construct SDCs to test
    test_sdc = construct_sdc([TEST_DICT['set_input_delay'][0]])
    
    # Run experiment for all SDCs, parse 
    for sdc in test_sdc:
        test_config, place_file, temp_dir = run_vpr([TEST_DICT['set_input_delay'][0]], sdc, random_seed = False, use_params=True, t_driven=False, hold=False)
        
    # Run OpenSTA
    #run_opensta(TEST_DICT['set_input_delay'], LIBERTY_FILE)

    
    create_clock_sdc = construct_sdc(TEST_DICT['set_input_delay'])
    distance = []
    for sdc in create_clock_sdc:
        test_config, place_file, _ = run_vpr(TEST_DICT['set_input_delay'], sdc, random_seed=True)
        
        distance.append(get_min_distance(place_file))
        
    visualize_result(test_config, distance, TEST_DICT['set_input_delay'][0]['param'][0]['values'])
    '''
    