import subprocess
import re
import sys
import argparse
from pathlib import Path
from typing import List
import config
from matplotlib import pyplot as plt
import seaborn as sns
import shutil
import json
from itertools import product

# TODO: Clean up CLI
# TODO: Implement analyze_result(), for seed sweep analysis
# TODO: More analysis functions such as get_min_distance
# TODO: Issue where it doesn't print the exception message in main() when wrong blif specified
# TODO: Omit unnecessary VPR command flags such as gen_post_implementation_netlist -> Cause of long runtime
# TODO: Change name for MICRO_ROOT, reorganize benchmark directory
# TODO: Parse number of blocks from resource.txt
# TODO: Elaborate on the 'default' key in SDC formatting in config.py. Is it really necessary? A better way to organize the configuration of SDCs?
# TODO: Fix wildcard import
# TODO: Running multiple tests at once: If a list is given in the command line, iterate over the list of test configs.

def construct_sdc(test_config: dict):
    '''
    Constructs multiple SDCs with different parameter values and returns a Path object to the generated SDC directory.
    
    Args: 
        test_config (dict): A dictionary of a test case description.
    
    Returns:
        Path: Directory in which the SDCs are saved.
    '''
    # Define out_dir (e.g. ./results/timing/create_clock_rca/sdc)
    out_dir = config.RESULTS_DIR / 'timing' / test_config['type'] / 'sdc'

    # Remove any existing SDC files
    if out_dir.exists():
        shutil.rmtree(out_dir)  # Delete all subdirectories and files
        print(f"Cleaned existing directory: {out_dir}")

    # Create out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Arguments
    sdc_template = test_config['sdc'].strip() # SDC template
    params = test_config['param'] # Parameters

    # SDC template has no parameters to change
    if params is None:
        out_filename = test_config['type'] + '.sdc'
        out_filepath = out_dir / out_filename
        
        with open(out_filepath, 'w') as out_sdc:
            out_sdc.write(sdc_template)
        
        print(f"Generated SDC: {out_filepath}")
    
    # Replace parameter values in the SDC template
    else:
        # Create a list of parameter values (list of lists)
        param_values = []
        param_names = []
        for param in params:
            param_names.append(param['name'])
            param_values.append(param['values'])

        # Unpack the list and get the cartesian product of the lists
        param_combinations = product(*param_values)

        for p_combination in param_combinations:

            new_constraint = sdc_template # Copy the SDC template
            filename_parts = [] # List of file name parts

            for i in range(len(param_names)):
                # Replace the parameter placeholder with a value
                new_constraint = new_constraint.replace(param_names[i], str(p_combination[i]))
                
                # Add the parameter name and value to the file name
                filename_parts.append(f"{param_names[i].strip('<>')}-{p_combination[i]}")
    
            # Create file name (e.g. period-10.0_delay-10.0.sdc)
            out_filepath = out_dir / ("_".join(filename_parts)+".sdc")
            
            # Output the generated SDC
            with open(out_filepath, 'w') as out_sdc:
                out_sdc.write(new_constraint)
                
            print(f"Generated SDC: {out_filepath}")
                
    print(f"SDC Generation for {test_config['type']} Complete.\n")       
             
    return out_dir

# No need for synthesis. All SDCs are blif-specific.
def run_synthesis(test_config: dict):
    '''
    Synthesizes a circuit described in Verilog using Parmys or Odin II.
    
    Args:
      test_config (dict): A dictionary of a test case description.
    
    Returns:
      Path: Path to the created blif file
    '''
    blif_list = []
    
    for test in test_config:
        # Prepare arguments for parmys/odin
        architecture_path = ARCH_FILE
        verilog_path = MICRO_ROOT / test['circuit']
        frontend = test['frontend']
        output_path = RESULTS_DIR / 'blif' / f"{test['type']}.blif"
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

def run_vpr(test_config: dict, sdc_dir: str=None, seed: int=1, **kwargs):
    '''
    Run place and route on the given test case with VPR.
    VPR will generate post-implementation netlists and timing analysis files that can be analyzed later on. 
    
    Args:
        test_config (dict): A dictionary of a single test case description.
        sdc_dir (str): The directory where SDC files are located. 
        seed (int): Use the given seed for placement.
        **kwargs: Keyword arguments for VPR.
            use_params (str): Use parameters in the post-synthesis netlist. Set to 'off' for OpenSTA.
            placement_type (str): Choose 'timing_driven' or 'analytical' placement.
            place_algorithm (str): Choose 'criticality_timing' or 'slack_timing' for placement.
            place_agent_algorithm (str): Choose the RL agent algorithm 'e_greedy' or 'softmax' for placement.
            analytical_solver (str): Choose 'qp-hybrid' or 'lp-b2b' for analytical placement.
            ap_timing_tradeoff (float): Any number between 0.0 for wirelength minimzation and 1.0 for timing optimization. 
            hold (Bool): Turn on hold analysis using '--routing_budgets_algorithm yoyo'.
            num_workers (int): Number of parallel workers VPR may use.
      
    Returns:
        result_dir (Path): Run results are stored here.
        
    '''
    blif_file = MICRO_ROOT / test_config['blif'] # BLIF file

    # Get SDC files in 'sdc_dir' 
    sdc_list = get_sdc_list(sdc_dir)

    # Create a directory where the VPR output files will be moved to
    # kwargs['placement_type'] is 
    result_dir, kwargs['placement_type'] = create_result_dir(base_dir=RESULTS_DIR/'timing'/test_config['type'], seed=seed, **kwargs)

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
        
        # Make VPR summary and parse VPR timing reports
        timing_summary, hold_rpt, setup_rpt, skew_hold_rpt, skew_setup_rpt = make_vpr_summary(temp_dir)

        # Write parsed timing information to a new file
        save_vpr_timing_report(run_output_dir, sdc, timing_summary, hold_rpt, setup_rpt, skew_hold_rpt, skew_setup_rpt)

        # Save the distribution plot to the result directory
        save_path_distribution(setup_rpt, run_output_dir)
        
    return result_dir

def get_sdc_list(sdc_dir: str=None):
    '''
    Returns a list of SDC files located under the provided 'sdc_dir'.
    There will always be a None object in the list for baseline testing.

    Args:
        sdc_dir (str): The directory in which the SDC files are located.
    Returns:
        list: A list of Path objects pointing to the SDC files.
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

def create_result_dir(base_dir: Path, seed: int, **kwargs):
    '''
    Creates a directory where the timing reports will be saved. 
    The directory will have a unique name based on the combination of the seed, 
    placement algorithm, and other VPR parameters used to run the test.

    Args:
        base_dir (Path): The result directory is a child directory of base_dir.
        seed (int): Seed for placement in VPR.
        **kwargs:
            placement_type (str): Choose 'timing_driven' or 'analytical' placement.
            place_algorithm (str): Choose 'criticality_timing' or 'slack_timing' for placement.
            analytical_solver (str): Choose 'qp-hybrid' or 'lp-b2b' for analytical placement.
            hold (bool): Whether to enable hold analysis.
    Returns:
        Path: Path to the created result directory
        str: The updated '--placement_type' option for VPR
    '''
    folder_name = f"seed{seed:02d}"

    placement_type = kwargs.get('placement_type', 'timing_driven')
    place_algorithm = kwargs.get('place_algorithm', 'criticality_timing')
    analytical_solver = kwargs.get('analytical_solver', 'lp-b2b')
    hold = kwargs.get('hold', False)

    # Invalid placement type specified, resort to timing driven placement
    if placement_type not in ('timing_driven', 'analytical'):
        print(f"Invalid placement type {placement_type} specified. Using timing-driven \
        placement instead.")
        placement_type = 'timing_driven'  # Modify the VPR arguments
        # This part exists because this function is the first to be called within 'run_vpr'
        # This function returns placement_type so that the caller can override its placement_type if it was invalid

    # Add the VPR run parameters for the base folder name
    if placement_type == "timing_driven":
        folder_name += "_t-driven"

        if place_algorithm == "criticality_timing":
            folder_name += "_criticality"
        else:
            folder_name += "_slack"

    elif placement_type == "analytical":
        folder_name += "_analytical"
        folder_name += f"_{analytical_solver}"

    if hold:
        folder_name += "_hold"

    # Add a number to prevent overwriting exisitng result directories
    i = 0
    while i < 100:
        new_folder_name = f"{folder_name}{i:02d}"
        full_path = base_dir / new_folder_name

        if not full_path.exists():
            full_path.mkdir(parents=True)
            return full_path, placement_type

        i += 1

    raise RuntimeError(f"Could not create result directory under {base_dir} after {MAX_RETRIES} attempts. Please remove any stale result directories.")

def build_vpr_command(test_config: dict, sdc: str=None, seed: int=1, **kwargs):
    '''
    Creates a command for VPR execution.

    Args: 
        test_config (dict): A dictionary of a test case description.
        sdc (Path): The path to an SDC file.
        seed (int): The seed to run VPR on.
        **kwargs: Keyword arguments for VPR.
            use_params (str): Use parameters in the post-synthesis netlist. Set to 'off' for OpenSTA.
            placement_type (str): Choose 'timing_driven' or 'analytical' placement.
            place_algorithm (str): Choose 'criticality_timing' or 'slack_timing' for placement.
            place_agent_algorithm (str): Choose the RL agent algorithm 'e_greedy' or 'softmax' for placement.
            analytical_solver (str): Choose 'qp-hybrid' or 'lp-b2b' for analytical placement.
            ap_timing_tradeoff (float): Any number between 0.0 for wirelength minimzation and 1.0 for timing optimization. 
            hold (Bool): Turn on hold analysis using '--routing_budgets_algorithm yoyo'.
            num_workers (int): Number of parallel workers VPR may use.
    Returns:
        List: List of the command pieces.
        Str: Name of the graphics file generated by VPR.
        Path: The VPR run directory.
    '''
    # BLIF file
    blif_file = MICRO_ROOT / test_config['blif']
    # FPGA architecture file
    architecture_file = ARCH_FILE
    # Device size
    layout = test_config['layout']
    # Directory that VPR will output its results to
    temp_dir = RESULTS_DIR / 'timing' / test_config['type'] / 'vpr'
    # timing_summary = temp_dir / 'timing_summary.txt' # Timing summary

    assert blif_file.exists()
    assert architecture_file.exists()

    # Get kwargs
    # Timing-driven placement vs Analytical placement
    placement_type = kwargs.get('placement_type', 'timing_driven')
    # Placement algorithm for timing-driven placement
    place_algo = kwargs.get('place_algorithm', 'criticality_timing')
    # RL agent algorithm
    place_agent_algo = kwargs.get('place_agent_algorithm', 'softmax')
    # Analytical solver
    analytical_solver = kwargs.get('analytical_solver', 'lp-b2b')
    # Timing tradeoff for analytical placement
    ap_timing_tradeoff = str(kwargs.get('ap_timing_tradeoff', '0.5'))
    # Use yoyo for hold tests, disable for normal setup tests
    budgets_algo = 'yoyo' if kwargs.get('hold') else 'disable'
    # Use parameters when generating post-implementation netlist
    use_params = kwargs.get('use_params', 'on')
    # Number of timing paths to report
    num_paths = str(kwargs.get('num_paths', '100'))
    # Number of parallel workers VPR can use
    num_workers = kwargs.get('num_workers', '1')

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
        '--timing_report_skew', 'on',
        '--num_workers', f'{num_workers}'
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
    if use_params == 'off':
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
        cmd += ['--auto', '2']  # You don't have to click any buttons to continue
        graphics_file = f"{sdc.name if sdc else 'default_sdc'}.png"
        cmd += ['--graphics_commands', f'save_graphics {graphics_file};']

    return cmd, graphics_file if test_config.get('graphics') else None, temp_dir

def save_vpr_timing_report(result_dir: Path, sdc: Path, timing_summary: list, hold_rpt: list, setup_rpt: list, skew_hold_rpt: list, skew_setup_rpt: list):
    '''
    Writes the parsed VPR timing report to the result directory.

    Args:
        result_dir (Path): Where the timing reports will be saved.
        sdc (Path): The path to the SDC used to run VPR.
        timing_summary (list): List of timing summary contents returned by 'make_vpr_summary()'.
        hold_rpt (list): List of hold report contents returned by 'make_vpr_summary()'.
        setup_rpt (list): List of setup report contents returned by 'make_vpr_summary()'.
        skew_hold_rpt (list): List of skew hold report contents returned by 'make_vpr_summary()'.
        skew_setup_rpt (list): List of skew setup report contents returned by 'make_vpr_summary()'.
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

def make_json(test_config: dict, result_dir: Path, seed: int, **kwargs):
    '''
    Creates a JSON file in the 'result_dir' containing the test parameters. 

    Args:
        test_config (dict): Dictionary of a test case configuration.
        result_dir (Path): The JSON file will be saved under this directory.
        seed (int): Seed for placement in VPR
        **kwargs: Keyword arguments for VPR.
            use_params (str): Use parameters in the post-synthesis netlist. Set to 'off' for OpenSTA.
            placement_type (str): Choose 'timing_driven' or 'analytical' placement.
            place_algorithm (str): Choose 'criticality_timing' or 'slack_timing' for placement.
            place_agent_algorithm (str): Choose the RL agent algorithm 'e_greedy' or 'softmax' for placement.
            analytical_solver (str): Choose 'qp-hybrid' or 'lp-b2b' for analytical placement.
            ap_timing_tradeoff (float): Any number between 0.0 for wirelength minimzation and 1.0 for timing optimization. 
            hold (Bool): Turn on hold analysis using '--routing_budgets_algorithm yoyo'.

    '''
    # Get kwargs
    placement_type = kwargs.get('placement_type', 'timing_driven')
    place_algorithm = kwargs.get('place_algorithm', 'criticality_timing')
    place_agent_algorithm = kwargs.get('place_agent_algorithm', 'softmax')
    analytical_solver = kwargs.get('analytical_solver', 'lp-b2b')
    ap_timing_tradeoff = str(kwargs.get('ap_timing_tradeoff', '0.5'))
    hold = kwargs.get('hold')
    use_params = kwargs.get('use_params', 'on')
    
    # Save the run parameters in a dictionary format
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
    
    # Dump to a JSON file
    config_path = result_dir / "config.json"
    with open(config_path, 'w') as f:
        json.dump(run_params, f, indent=4)

def run_opensta(test_config: dict, liberty_file: Path, tcl_file: Path=None):
    '''
    Run OpenSTA to perform post-implementation timing analysis. 
    
    Args:
        test_config (dict): A dictionary describing a test case configuration.
        liberty_file (Path): Path to liberty file to be used for OpenSTA.
        tcl_file (Path): A test-specific TCL file for timing reports. Runs default TCL if none specified.
    '''
    vpr_out_dir = RESULTS_DIR / 'timing' / test_config['type'] / 'vpr' # VPR output directory
    temp_dir = RESULTS_DIR / test_config['type'] / 'opensta' # OpenSTA output directory
    top_level_module = test_config['top_level_module'] # Top level module of the circuit
    
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
        raise

def make_vpr_summary(temp_dir: Path):
    '''
    This function does the following: 
    - Writes a timing summary based on the output file 'vpr.out'.
    - Parses VPR timing reports by calling the function 'parse_timing_report()'.
    
    Args:
        temp_dir (Path): The path given to VPR with the option '--temp_dir'. The directory where VPR run results are saved.
    
    Returns:
        timing_summary (list): A summary of 'vpr.out'.
        hold_report (list): A list of hold paths.
        setup_report (list): A list of setup paths.
        skew_hold_report (list): A list of skew hold paths.
        skew_setup_report (list): A list of skew setup paths.
    '''
    # TODO: Parse number of constrained vs unconstrained paths.
    # TODO: Parse VPR run time

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
        vpr_out_content = f.read()
    
    # Match and parse timing metrics from 'vpr.out'
    global_net = re.search(r"Number of global nets:\s+(\d+)", vpr_out_content) 
    routed_net = re.search(r"Number of routed nets \(nonglobal\):\s+(\d+)", vpr_out_content)
    wirelength = re.search(r"Total wirelength:\s+(\d+)", vpr_out_content)
    cpd = re.search(r"Final critical path delay \(least slack\):\s+([\d\.]+)", vpr_out_content)
    sWNS = re.search(r"Final setup Worst Negative Slack \(sWNS\):\s+([\d\.\-eE]+)", vpr_out_content)
    sTNS = re.search(r"Final setup Total Negative Slack \(sTNS\):\s+([\d\.\-eE]+)", vpr_out_content)
    hWNS = re.search(r"Final hold Worst Negative Slack \(hWNS\):\s+([\d\.\-eE]+)", vpr_out_content)
    hTNS = re.search(r"Final hold Total Negative Slack \(hTNS\):\s+([\d\.\-eE]+)", vpr_out_content)
    num_sdc = re.search(r"Applied (\d+) SDC commands", vpr_out_content) 
    num_sdc_clock = re.search(r"Timing constraints created (\d+) clocks", vpr_out_content)
    num_netlist_clock = re.search(r"Netlist contains (\d+) clocks", vpr_out_content)

    # Parse netlist clock information, iterates in case multiple clocks exist in the design
    netlist_clk_info = []  # Contains the existing netlist clocks

    for match in re.finditer(r"Netlist Clock '([^']+)' Fanout: (\d+) pins.*?, (\d+) blocks", vpr_out_content):
        netlist_clk_info.append({
            'name': match.group(1),
            'fanout_pins': int(match.group(2)),
            'fanout_blocks': int(match.group(3))
        })

    # Parse constrained clock information, iterates in case multiple clocks were constrained
    constrained_clk = []  # Contains the clocks that were constrained

    for match in re.finditer(r"Constrained Clock\s+(.*)", vpr_out_content):
        constrained_clk.append(match.group(1))

    # Join the constrained clock list to form a single string
    constrained_clk_str = '  \n'.join(constrained_clk)

    # Assign values to timing result variables
    total_nets = int(global_net.group(1)) + int(routed_net.group(1))
    wirelength = wirelength.group(1)
    cpd = cpd.group(1)
    fmax = 1000 / float(cpd) if float(cpd) > 0 else 0
    sWNS = sWNS.group(1)
    sTNS = sTNS.group(1)
    hWNS = hWNS.group(1)
    hTNS = hTNS.group(1)
    num_sdc = num_sdc.group(1) if num_sdc else 'N/A'
    num_sdc_clock = num_sdc_clock.group(1) if num_sdc_clock else 'N/A'
    num_netlist_clock = num_netlist_clock.group(1)

    # Condition for timing being met
    # Both setup and hold slack should be non-negative.
    timing_met = True if (float(sWNS) >= 0 and float(hWNS) >= 0) else False
    
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
                      f'Critical path delay: {cpd}ns', f'Fmax: {fmax}MHz', f'sWNS: {sWNS}', f'sTNS: {sTNS}',
                      f'hWNS: {hWNS}', f'hTNS: {hTNS}', 
                      f'Timing met: {timing_met}', f'Number of SDCs Applied: {num_sdc}',
                      f'Number of constrained clocks: {num_sdc_clock}',
                      f'List of constrained clocks:\n{constrained_clk_str}\n' 
                      f'Number of netlist clocks: {num_netlist_clock}', f'Netlist clock information:\n{netlist_clk_info}']
    
    return timing_summary, hold_report, setup_report, skew_hold_report, skew_setup_report

def parse_timing_report(file_path: Path, is_skew: bool=False):
    ''' 
    Parses the detailed timing report written by VPR and adds each reported timing path to a list.
    
    Args:
        file_path (Path): Path to the timing report.
        is_skew (Bool): True if the file is a skew report, false otherwise. 
    Returns:
        list: A list of the parsed timing path information.
    '''
    rpt_content = Path(file_path).read_text()
    
    # 1. Partition the rpt_content by 'Path' or 'Skew Path'
    delimiter = r"#Skew Path \d+" if is_skew else r"#Path \d+"
    path_blocks = re.split(delimiter, rpt_content)[1:]
    
    all_paths = []
    
    for block in path_blocks:
        # Do not parse if skew == 0
        if is_skew:
            skew = re.search(r"skew\s+([\d\.\-eE]+)", block)
            if skew and float(skew.group(1)) == 0.0:
                continue

        path_info = []
        
        # Parse startpoint & endpoint
        startpoint = re.search(r"Startpoint:\s+(.*)", block)
        endpoint = re.search(r"Endpoint\s+:\s+(.*)", block)

        # Extract numerical data (typically from 'Incr' or 'Path' columns)
        # Use findall to handle multiple occurrences (e.g., Launch vs. Capture paths)
        # and select the appropriate match based on the context
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

        # Write timing path information to a list
        path_info = [
            f"Startpoint: {startpoint}\n",
            f"Endpoint  : {endpoint}\n",
            f"  Rise Edge: {rise_edge}, Latency: {latency}, Uncertainty: {uncertainty}\n",
            f"  Required: {req_time}, Arrival: {arr_time}\n",
            f"  {slack_str}\n",
            f"{'-'*60}\n"
        ]
        # Extend each path information to the list 'all_paths'
        all_paths.extend(path_info)
        
    return all_paths
    
def get_opensta_timing():
    pass

def get_min_distance(place_file: Path):
    '''
    Returns the minimum of the average distances to all four peripheries of the FPGA.
    
    Args:
        place_file (Path): Placement file containing the X, Y coordinates of each clusters.
        
    Returs:
        float: The minimum of the average distance to the four peripheries
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

def was_sdc_parsed(temp_dir: Path):
    '''
    Inspects 'vpr.out' to check if SDC was properly parsed.
    
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

def save_path_distribution(timing_report: list, save_dir: Path):
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
    pass

def main():
    '''
    '''
    # Argument Parser
    parser = argparse.ArgumentParser(description="Execute the Timing Benchmark")

    # Test config
    parser.add_argument('--test', type=str, required=True, 
                        help="Test configuration name defined in config.py (e.g., create_clock_rca).")

    # Seed and SDC
    # TODO: Implement the analyze_result step where it analyzes/summarizes the seed sweep results after VPR
    # parser.add_argument('--analyze_result', type=str, action='store_true', help="Analyze benchmark results")
    parser.add_argument('--seed', type=int, nargs='+', default=[1], help="Seed for placement (e.g., 1 3 5).") 
    parser.add_argument('--sdc_dir', type=str, default=None,
                        help="SDC directory. Specifying it will override the generated SDCs.")

    # VPR algorithm
    parser.add_argument('--placement_type', choices=['timing_driven', 'analytical'], 
                        default='timing_driven', help="Choose placement type.")
    parser.add_argument('--place_algorithm', choices=['criticality_timing', 'slack_timing'], 
                        default='criticality_timing', help="Choose timing-driven placement algorithm.")
    parser.add_argument('--place_agent_algorithm', choices=['e_greedy', 'softmax'],
                        default='softmax', help="Choose RL agent algorithm.")
    parser.add_argument('--analytical_solver', choices=['qp-hybrid', 'lp-b2b'], 
                        default='qp-hybrid', help="Choose analytical solver.")
    parser.add_argument('--ap_timing_tradeoff', type=float, default=0.5, 
                        help="Analytical placement timing tradeoff (0.0~1.0).")
    parser.add_argument('--hold', action='store_true', help="Activate hold analysis with yoyo.")
    parser.add_argument('--num_paths', type=int, default=100, help="Number of paths to include in the report.")

    # Misc
    parser.add_argument('--use_params', choices=['on', 'off'], help="Use parameters in the post-synthesis netlist.")
    parser.add_argument('--num_workers', type=int, default=1, help="Control how many parallel workers VPR may use")

    # Parse arguments
    args = parser.parse_args()

    # Get the configuration dictionary from config.py
    try:
        test_config = getattr(config, args.test)
    except AttributeError:
        print(f"Error: '{args.test}' doesn't exist in 'config.py'.")
        sys.exit(1)

    # Prepare SDC directory
    try:
        # Use the given SDC directory, if not given, create sdc based on template
        sdc_dir = args.sdc_dir if args.sdc_dir else construct_sdc(test_config)
    except Exception as e:
        print(f"Error during SDC generation: {e}")
        sys.exit(1)

    # Run VPR
    # TODO: If a list is given for the test_config, then iterate over the list too. 
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
                num_paths=args.num_paths,
                num_workers=args.num_workers
            )
    # TODO: There is an issue where e doesn't print.
    except Exception as e:
        print(f"Error during VPR run: {e}")
        sys.exit(1)


if __name__ == "__main__":
    #main()
    construct_sdc(config.create_clock_rca)
    