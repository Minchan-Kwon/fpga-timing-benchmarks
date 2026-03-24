import os
import random
from itertools import product
from itertools import combinations
import shutil
import argparse

#PATH CONFIGURATION
##################################################################################################################################################
script_dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir_path)
intermediate_dir = os.path.join(parent_dir, "auto_generated", "sdc_files")
temp_output_path = os.path.join(script_dir_path, "outputs")

#PARAMETERS
##################################################################################################################################################
FILTER_TYPE = {"singular", "value", "pattern", "compound"}
OBJ_TYPE = ["cell", "clock", "pin", "port", "net"]
PATTERNS = {
    "clock": ["clk*", "clk_gen", "clock", "clk1"],
    "port": ["data*", "*in", "*out", "valid_in"],
    "pin": ["u1/*", "*/Q", "u2/D", "*/clk"],
    "cell": ["inst*", "reg_*", "*_buffer"],
    "net": ["net*", "n[0-9]*", "*_data"]
    }
#HELPER FUNCTIONS
##################################################################################################################################################
def choose_object_type():
    '''
    Returns a random choice from list OBJ_TYPE = ["clock", "port", "pin", "cell", "net"]
    '''
    return random.choice(OBJ_TYPE)

def choose_filter_type():
    '''
    Returns a random choice from list FILTER_TYPE = ["singular", "value", "pattern", "compound"]
    '''
    return random.choice(FILTER_TYPE)

def generate_filter(filter_type, object_type):
    '''
    Generates a filter expression for get_ variants
    
    Args: 
        filter_type: a filter type(string) returned by choose_filter_type()
        object_type: an string in the list ["clock", "port", "pin", "cell", "net"]
    
    Returns:
        A filter expression string
    '''
    
    if filter_type == "singular":
        if not PROPERTIES[object_type]["boolean"]:  #If no "boolean" property exists
            return generate_filter("value", object_type) #Create a filter expression with the property "value"
            
        return random.choice(PROPERTIES[object_type]["boolean"]) 
    
    
    elif filter_type == "value":
        if not PROPERTIES[object_type]["value"]:    #If no "value" property exists
            return generate_filter("pattern", object_type) #Create a filter expression with the property "pattern"
            
        op = random.choice(["==", "!="])
        prop = random.choice(list(PROPERTIES[object_type]["value"].keys()))
        
        if PROPERTIES[object_type]["value"][prop]: 
            val = random.choice(PROPERTIES[object_type]["value"][prop])
        else:
            val = "1" #Default value
        return f'{prop}{op}"{val}"'
    
    
    elif filter_type == "pattern":
        if not PROPERTIES[object_type]["pattern"]:  #If no "pattern" property exists
            return generate_filter("singular", object_type) #Create a filter expression with the property "singular", may be dangerous if no properties exist for the object_type
            
        op = random.choice(["=~", "!~"])
        prop = random.choice((PROPERTIES[object_type]["pattern"]))
        
        if PATTERNS[object_type]:
            pat = random.choice(PATTERNS[object_type])
        else:
            pat = "*" #Default pattern
        return f'{prop}{op}"{pat}"'

    
    elif filter_type == "compound":
        new_filter1 = random.choice(["singular", "value", "pattern"]) 
        new_filter2 = random.choice(["singular", "value", "pattern"])
        
        #This recursion is guaranteed to find a property
        expr1 = generate_filter(new_filter1, object_type)
        expr2 = generate_filter(new_filter2, object_type)
        op = random.choice(["&&", "||"])
        
        return f"({expr1}){op}({expr2})"
        
def generate_pattern(object_type):
    '''
    Args:
        object_type: a string in the list ["clock", "port", "pin", "cell", "net"]
        
    Returns: 
        A pattern that belongs to the object type (string)
        Currently only returns one pattern but should be able to return lists as well
    '''
    if object_type not in PATTERNS or not PATTERNS[object_type]: #Invalid object_type or pattern non-existent
        return "*" 
    
    return random.choice(PATTERNS[object_type])
    

#GENERATOR FUNCTIONS
##################################################################################################################################################
def generate_create_clock():
    '''
    create_clock -period <float>
            (-name <string>)?
            (-waveform {<float> <float>})?
            (-add)?
            (<pin_list>)?
    '''
    # List containing all possible combinations of options
    commands = []
    optional_flags = ["-name", "-waveform", "-add", "pin_list"]
    pin_list = ["[get_ports clk1]", "[get_pins *clk*]"]
    period = 10.0
    
    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            base_pieces = [f"create_clock -period {period}"]
            
            if "-name" in option_combination:
                base_pieces.append(f"-name clk_{period}")
                
            if "-waveform" in option_combination:
                rise_time = round(random.uniform(0, period/2))
                fall_time = round(random.uniform(period/2, period))
                base_pieces.append(f"-waveform {{{rise_time} {fall_time}}}")
                
            if "-add" in option_combination:
                base_pieces.append("-add")

            if "pin_list" in option_combination: 
                # A list of pins driven by the clock
                for pin in pin_list:
                    pin_iter_pieces = base_pieces + [pin]
                    commands.append(" ".join(pin_iter_pieces))
            else:
                commands.append(" ".join(base_pieces))
        
    return commands             

def generate_get_ports():
    '''
    Optional: -regexp, -nocase(Legal only with -regexp), -quiet
    '''
    commands = [] #List containing all possible combinations of options
    
    optional_flags = ["-regexp", "-nocase", "-quiet"]

    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):
            
            #The option -nocase is only valid with -regexp
            if "-nocase" in option_combination and "-regexp" not in option_combination:
                continue 
                
            pieces = ["get_ports"]

            if "-regexp" in option_combination:
                pieces.append("-regexp")
                
            if "-nocase" in option_combination:
                pieces.append("-nocase")

            if "-quiet" in option_combination:
                pieces.append("-quiet")
                
            #A list of port name patterns
            pattern = generate_pattern("port")
            pieces.append(pattern)
            
            #Join the options to create a proper command
            pieces = " ".join(pieces)
            #Add create_clock prerequisites
            pieces = ("create_clock -period 10 -name clk [get_ports clk]\n" + pieces)
            commands.append(pieces)
            
    return commands

def generate_get_clocks():
    '''
    Optional: -regexp, -nocase(Legal only with -regexp), -quiet
    '''
    commands = [] #List containing all possible combinations of options
    optional_flags = ["-regexp", "-nocase", "-quiet"]

    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):

            #Constraint: -nocase is only valid with -regexp
            if "-nocase" in option_combination and "-regexp" not in option_combination:
                continue

            pieces = ["get_clocks"]

            if "-regexp" in option_combination:
                pieces.append("-regexp")

            if "-nocase" in option_combination:
                pieces.append("-nocase")

            if "-quiet" in option_combination:
                pieces.append("-quiet")

            pattern = generate_pattern("clock")
            pieces.append(pattern)
            
            #Join the options to create a proper command
            pieces = " ".join(pieces)
            #Add create_clock prerequisites
            pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n" + 
                      "create_clock -period 10 -name clk2 [get_ports clk2]\n" + 
                      "create_clock -period 10 -name clk_gen [get_ports clk_gen]\n" +
                      "create_clock -period 10 -name clock [get_ports clock]\n" + 
                      pieces)
            commands.append(pieces)

    return commands
    
def generate_get_pins():
    '''
    Required:
    Optional: -hierarchical, -hsc, -filter, -regexp, -nocase(Valid only with -regexp), -quiet, -of_objects, patterns
    Note: -hierarchical cannot be used with -of_objects
    '''
    commands = [] #List containing all possible combinations of options
    optional_flags = ["-hierarchical", "-hsc", "-filter", "-regexp", "-nocase", "-quiet", "-of_objects", "patterns"]

    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):

            #Constraint 1: -nocase is only valid with -regexp
            if "-nocase" in option_combination and "-regexp" not in option_combination:
                continue #Skip this invalid combination

            pieces = ["get_pins"]

            if "-regexp" in option_combination:
                pieces.append("-regexp")

            if "-nocase" in option_combination:
                pieces.append("-nocase")

            if "-quiet" in option_combination:
                pieces.append("-quiet")

            pattern = generate_pattern("pin")
            pieces.append(pattern)

            
            #Join the options to create a proper command
            pieces = " ".join(pieces)
            #Add create_clock prerequisites
            pieces = ("create_clock -period 10 -name clk [get_ports clk]\n" + pieces)
            commands.append(pieces)

    return commands

def generate_set_input_delay():
    '''
    set_input_delay (-rise)?
                (-fall)?
                (-max)?
                (-min)?
                (-clock <clock>)?
                (-clock_fall)?
                <delay: float>
                <pin/port list>

    Note
    -clock_fall should be used with -clock
    -max, -min are exclusive
    -reference_pin cannot be used with latency options
    
    '''
    commands = []
    optional_flags = ["-rise", "-fall", "-max", "-min", "-clock", "-clock_fall"]
    clock_list = ["[get_clocks src]", "[get_clocks {src_clk}]", "src", "{src_clk}"]
    port_list = ["[get_ports port1]", "[get_ports {port2}]", "{port1}", "port2"]
        
    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            
            if "-clock_fall" in option_combination and "-clock" not in option_combination:
                continue
            if "-max" in option_combination and "-min" in option_combination:
                continue
        
            # Delay value required
            pieces = [f"set_input_delay", "1.0"]

            if "-rise" in option_combination:
                pieces.append("-rise")
        
            if "-fall" in option_combination:
                pieces.append("-fall")
            
            if "-max" in option_combination:
                pieces.append("-max")
            
            if "-min" in option_combination:
                pieces.append("-min")

            if "-clock" in option_combination:
                for clock in clock_list:
                    clock_iter_pieces = pieces.copy()
                    clock_iter_pieces.append(f"-clock {clock}")
                    
                    if "-clock_fall" in option_combination:
                        clock_iter_pieces.append("-clock_fall")
                    
                    # Fix the port to 'port1' for simplicity
                    clock_iter_pieces.append("[get_ports port1]")
                    
                    clock_iter_pieces = " ".join(clock_iter_pieces)
                    clock_iter_pieces = ("create_clock -period 10 -name src [get_ports src_clk]\n"
                                            + clock_iter_pieces)
                    commands.append(clock_iter_pieces)
                        
            else:
                for port in port_list:
                    port_iter_pieces = pieces.copy()
                    port_iter_pieces.append(f"{port}")
                    #Join the options to create a proper command
                    port_iter_pieces = " ".join(port_iter_pieces)
                    #Add create_clock prerequisites
                    port_iter_pieces = ("create_clock -period 10 -name src [get_ports src_clk]\n"
                                + port_iter_pieces)
                    commands.append(port_iter_pieces)
                
    return commands

def generate_set_output_delay():
    '''
    set_output_delay (-rise)?
                 (-fall)?
                 (-max)?
                 (-min)?
                 (-clock <clock>)?
                 (-clock_fall)?
                 <delay: float>
                 <pin/port list>

    Note
    -clock_fall should be used with -clock
    -max, -min are exclusive
    -reference_pin cannot be used with latency options
    '''
    commands = []
    optional_flags = ["-rise", "-fall", "-max", "-min", "-clock", "-clock_fall"]
    clock_list = ["[get_clocks src_clk]", "[get_clocks {src_clk}]", "src_clk", "{src_clk}"]
    port_list = ["[get_ports port1]", "[get_ports {port2}]", "{port1}", "port2"]
        
    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            
            if "-clock_fall" in option_combination and "-clock" not in option_combination:
                continue
            if "-max" in option_combination and "-min" in option_combination:
                continue
        
            #Delay value required
            pieces = [f"set_output_delay", "1.0"]

            if "-rise" in option_combination:
                pieces.append("-rise")
        
            if "-fall" in option_combination:
                pieces.append("-fall")
            
            if "-max" in option_combination:
                pieces.append("-max")
            
            if "-min" in option_combination:
                pieces.append("-min")

            if "-clock" in option_combination:
                for clock in clock_list:
                    clock_iter_pieces = pieces.copy()
                    clock_iter_pieces.append(f"-clock {clock}")
                    
                    if "-clock_fall" in option_combination:
                        clock_iter_pieces.append("-clock_fall")
                    
                    # Fix the port to 'port1' for simplicity
                    clock_iter_pieces.append("[get_ports port1]")
                    
                    clock_iter_pieces = " ".join(clock_iter_pieces)
                    clock_iter_pieces = ("create_clock -period 10 [get_ports src_clk]\n"
                                            + clock_iter_pieces)
                    commands.append(clock_iter_pieces)
                        
            else:
                for port in port_list:
                    port_iter_pieces = pieces.copy()
                    port_iter_pieces.append(f"{port}")
                    #Join the options to create a proper command
                    port_iter_pieces = " ".join(port_iter_pieces)
                    #Add create_clock prerequisites
                    port_iter_pieces = ("create_clock -period 10 [get_ports src_clk]\n"
                                + port_iter_pieces)
                    commands.append(port_iter_pieces)
    
    return commands
    
def generate_set_clock_latency():
    '''
    set_clock_latency (-source)?
                  (-rise)?
                  (-fall)?
                  (-min)?
                  (-max)?
                  <latency: float>
                  <clocks, ports, pins>

    Required options: delay, objects
    '''
    commands = []
    optional_flags = ["-source", "-rise", "-fall", "-max", "-min"]
    object_list = ["[get_clocks clk1]", "clk2", "[get_clocks clk*]", "[get_pins out1.clk[0]]", "[get_pins out1/clk[0]]"]    
        
    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            
            if "-max" in option_combination and "-min" in option_combination:
                continue
            if "-rise" in option_combination and "-fall" in option_combination:
                continue
            
            pieces = ["set_clock_latency", "1.5"]
            
            #Handle optional arguments
            if "-source" in option_combination:
                pieces.append("-source")
                
            if "-rise" in option_combination:
                pieces.append("-rise")
                
            if "-fall" in option_combination:
                pieces.append("-fall")
                
            if "-max" in option_combination:
                pieces.append("-max")
                
            if "-min" in option_combination:
                pieces.append("-min")

            for obj in object_list:
                obj_iter_pieces = pieces.copy()
                obj_iter_pieces.append(obj)
                obj_iter_pieces = " ".join(obj_iter_pieces)
                obj_iter_pieces = ("create_clock -period 10 [get_ports clk1]\n"
                                    "create_clock -period 20 [get_ports clk2]\n"
                                    + obj_iter_pieces)
                commands.append(obj_iter_pieces)
                
    return commands

def generate_set_clock_uncertainty():  
    '''
    set_clock_uncertainty (-from <clock>)?
                      (-to <clock>)?
                      (-rise)?
                      (-fall)?
                      (-setup)?
                      (-hold)?
                      <uncertainty: float>
                      <clocks, ports, pins>
    '''
    commands = [] #List containing all possible combinations of options
    optional_flags = ["-from", "-to", "-rise", "-fall", "-setup", "-hold", "objects"]
    object_list = ["[get_pins {$dff~0^Q~0.clk[0]}]", "[get_clocks clk*]", "clk1"]
    
    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            
            if "-rise" in option_combination and "-fall" in option_combination:
                continue
            if "-setup" in option_combination and "-hold" in option_combination:
                continue
            
            pieces = ["set_clock_uncertainty", "0.05"] 
            
            if "-from" in option_combination:
                pieces.append(f"-from [get_clocks clk1]")

            if "-to" in option_combination:
                pieces.append(f"-to [get_clocks clk2]")
            
            if "-rise" in option_combination:
                pieces.append("-rise")
                
            if "-fall" in option_combination:
                pieces.append("-fall")
                
            if "-setup" in option_combination:
                pieces.append("-setup")
                
            if "-hold" in option_combination:
                pieces.append("-hold")
            
            if "objects" in option_combination:
                for obj in object_list:
                    obj_iter_pieces = pieces.copy()
                    obj_iter_pieces.append(obj)
                    obj_iter_pieces = " ".join(obj_iter_pieces)
                    obj_iter_pieces = ("create_clock -period 10 [get_ports clk1]\n"
                                    "create_clock -period 20 [get_ports clk2]\n"
                                    + obj_iter_pieces)
                    commands.append(obj_iter_pieces)
            else:
                # Join the options to create a proper command
                pieces = " ".join(pieces)
                # Add create_clock prerequisites
                pieces = ("create_clock -period 10 [get_ports clk1]\n"
                            "create_clock -period 20 [get_ports clk2]\n"
                            + pieces)
                commands.append(pieces)
                
    return commands

def generate_set_false_path():
    '''
    set_false_path (-setup)?
               (-hold)?
               (-rise)?
               (-fall)?
               (-from <from_list>)?
               (-to <to_list>)?
    '''
    commands = []
    
    optional_flags = ["-setup", "-hold", "-rise", "-fall", "-from", "-to"]
    
    from_list = ["[get_clocks clk1]", "clk1"] 
    to_list = ["[get_clocks clk2]", "clk2"] 
    
    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):
            
            # Mutually exclusive options
            if "-setup" in option_combination and "-hold" in option_combination:
                continue
            if "-rise" in option_combination and "-fall" in option_combination:
                continue
            
            pieces = ["set_false_path"] # Temporary list to store command options  
            
            from_obj = random.choice(from_list)
            to_obj = random.choice(to_list)
            
            if "-setup" in option_combination:
                pieces.append("-setup")
                
            if "-hold" in option_combination:
                pieces.append("-hold")
                
            if "-rise" in option_combination:
                pieces.append("-rise")
                
            if "-fall" in option_combination:
                pieces.append("-fall")
                
            if "-from" in option_combination:
                pieces.append(f"-from {from_obj}")

            if "-to" in option_combination:
                pieces.append(f"-to {to_obj}")
                
            #Join the options to create a proper command
            pieces = " ".join(pieces)
            #Add create_clock prerequisites
            pieces = ("create_clock -period 5.0 clk1\n"
                      "create_clock -period 8.0 clk2\n"
                      + pieces)
            commands.append(pieces)
    
    return commands

def generate_set_max_delay():
    '''
    set_max_delay (-rise)?
                (-fall)?
                (-from <from_list>)?
                (-to <to_list>)?
                <delay: float>
    '''
    commands = [] #List containing all possible combinations of options
    
    optional_flags = ["-rise", "-fall", "-from", "-to"]
    
    from_list = ["[get_clocks clk1]", "[get_ports port1]", "clk1", "[get_ports clk1]"] 
    to_list = ["[get_clocks clk2]", "[get_ports port2]", "clk2", "[get_ports clk2]"] 

    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            
            pieces = ["set_max_delay", "0.5"] 
            
            if "-rise" in option_combination:
                pieces.append("-rise")
                
            if "-fall" in option_combination:
                pieces.append("-fall")
                
            if "-from" in option_combination or "-to" in option_combination:
                for i in range(len(from_list)):
                    iter_pieces = pieces.copy()
                    
                    if "-from" in option_combination:
                        iter_pieces.append(f"-from {from_list[i]}")

                    if "-to" in option_combination:
                        iter_pieces.append(f"-to {to_list[i]}")

                    #Join the options to create a proper command
                    iter_pieces = " ".join(iter_pieces)
                    #Add create_clock prerequisites
                    iter_pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                                    "create_clock -period 20 -name clk2 [get_ports clk2]\n"
                                    + iter_pieces)
                    commands.append(iter_pieces)
            else:
                #Join the options to create a proper command
                pieces = " ".join(pieces)
                #Add create_clock prerequisites
                pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                            "create_clock -period 20 -name clk2 [get_ports clk2]\n"
                            + pieces)
                commands.append(pieces)
    
    return commands
    
def generate_set_min_delay():
    '''
    set_min_delay (-rise)?
              (-fall)?
              (-from <from_list>)?
              (-to <to_list>)?
              <delay: float>
    '''
    commands = [] #List containing all possible combinations of options
    
    optional_flags = ["-rise", "-fall", "-from", "-to"]
    
    from_list = ["[get_clocks clk1]", "[get_ports port1]", "clk1", "[get_ports clk1]"] 
    to_list = ["[get_clocks clk2]", "[get_ports port2]", "clk2", "[get_ports clk2]"] 

    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):
            
            pieces = ["set_min_delay", "0.5"] 
            
            if "-rise" in option_combination:
                pieces.append("-rise")
                
            if "-fall" in option_combination:
                pieces.append("-fall")
                
            if "-from" in option_combination or "-to" in option_combination:
                for i in range(len(from_list)):
                    iter_pieces = pieces.copy()
                    
                    if "-from" in option_combination:
                        iter_pieces.append(f"-from {from_list[i]}")

                    if "-to" in option_combination:
                        iter_pieces.append(f"-to {to_list[i]}")

                    #Join the options to create a proper command
                    iter_pieces = " ".join(iter_pieces)
                    #Add create_clock prerequisites
                    iter_pieces = ("create_clock -period 10 clk1\n"
                                    "create_clock -period 20 clk2\n"
                                    + iter_pieces)
                    commands.append(iter_pieces)
            else:
                #Join the options to create a proper command
                pieces = " ".join(pieces)
                #Add create_clock prerequisites
                pieces = ("create_clock -period 10 clk1\n"
                            "create_clock -period 20 clk2\n"
                            + pieces)
                commands.append(pieces)
    
    return commands

def generate_set_multicycle_path():
    '''
    set_multicycle_path (-setup)?
                    (-hold)?
                    (-rise)?
                    (-fall)?
                    (-from <from_list>)?
                    (-to <to_list>)?
                    <path_multiplier: float>

    -setup, -hold are mutually exclusive
    -rise, -fall are mutually exclusive
    -from variants, -through variants, -to variants are mutually exclusive within each other
    '''
    commands = [] #List containing all possible combinations of options

    optional_flags = ["-setup", "-hold", "-rise", "-fall", "-from", "-to"]
    
    from_list = ["[get_clocks clk1]", "[get_pins {$dff~1^Q~0.D[0]}]", "[get_ports port1]", "[get_cells {$dff~1^Q~0}]"] #Clocks, instances, pins, ports
    to_list = ["[get_clocks clk2]", "[get_pins {port2.Q[0]}]", "[get_ports port2]", "[get_cells {port2}]"] #Clocks, instances, pins, ports
    
    for j in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, j):

            if "-setup" in option_combination and "-hold" in option_combination:
                continue
            if "-rise" in option_combination and "-fall" in option_combination:
                continue
            pieces = ["set_multicycle_path", "2"]
                
            if "-setup" in option_combination:
                pieces.append("-setup")
                    
            if "-hold" in option_combination:
                pieces.append("-hold")
                    
            if "-rise" in option_combination:
                pieces.append("-rise")
                    
            if "-fall" in option_combination:
                pieces.append("-fall")
                    
            if "-from" in option_combination:
                if "-to" in option_combination:
                    for i in range(len(from_list)):
                        from_iter_pieces = pieces.copy()
                        from_iter_pieces.extend([f"-from {from_list[i]}", f"-to {to_list[i]}"])
                        from_iter_pieces = " ".join(from_iter_pieces)
                        from_iter_pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                                    "create_clock -period 20 -name clk2 [get_ports clk2]\n"
                                    + from_iter_pieces)
                        commands.append(from_iter_pieces)
                else: 
                    for from_obj in from_list:
                        from_iter_pieces = pieces.copy()
                        from_iter_pieces.append(f"-from {from_obj}")
                        from_iter_pieces = " ".join(from_iter_pieces)
                        from_iter_pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                                    "create_clock -period 20 -name clk2 [get_ports clk2]\n"
                                    + from_iter_pieces)
                        commands.append(from_iter_pieces)
                
            elif "-to" in option_combination:
                for to_obj in to_list:
                    to_iter_pieces = pieces.copy()
                    to_iter_pieces.append(f"-to {to_obj}")
                    to_iter_pieces = " ".join(to_iter_pieces)
                    to_iter_pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                                    "create_clock -period 20 -name clk2 [get_ports clk2]\n"
                                    + to_iter_pieces)
                    commands.append(to_iter_pieces)

            else:
                #Join the options to create a proper command
                pieces = " ".join(pieces)
                #Add create_clock prerequisites
                pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                        "create_clock -period 20 -name clk2 [get_ports clk2]\n"
                        + pieces)
                commands.append(pieces)
    
    return commands

def generate_get_cells():
    '''
    -of_objects and -hierarchcial are mutually exclusive
    '''
    commands = []
    optional_flags = ["-hierarchical", "-hsc", "-filter", "-regexp", "-nocase", "-quiet", "-of_objects", "patterns"]
    
    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):
            
            #Constraint 1: -nocase is only valid with -regexp
            if "-nocase" in option_combination and "-regexp" not in option_combination:
                continue
            
            #Constraint 2: -hierarchical and -of_objects are mutually exclusive
            if "-hierarchical" in option_combination and "-of_objects" in option_combination:
                continue
                
            pieces = ["get_cells"]
            
            if "-hierarchical" in option_combination:
                pieces.append("-hierarchical")

            if "-hsc" in option_combination:
                #FIXME: Do not make this random.
                separator = random.choice(SEPARATOR)
                pieces.append(f"-hsc {separator}")

            if "-filter" in option_combination:
                #Filter expression with object type "cell"
                filter_type = choose_filter_type()
                expr = generate_filter(filter_type, "cell")
                pieces.append(f"-filter {expr}")

            if "-regexp" in option_combination:
                pieces.append("-regexp")
                
            if "-nocase" in option_combination:
                pieces.append("-nocase")

            if "-quiet" in option_combination:
                pieces.append("-quiet")

            if "-of_objects" in option_combination:
                #FIXME: Do not make this random.
                #The name or list of pins or nets.
                pin_net_list = random.choice(PINS + NETS)
                pieces.append(f"-of_objects {pin_net_list}")
                
            if "patterns" in option_combination:
                #A list of cell name patterns
                pattern = generate_pattern("cell")
                pieces.append(pattern)

            commands.append(" ".join(pieces))
    
    return commands
    
def generate_get_nets():
    '''
    -hierarchical, -of_objects mutually exclusive
    '''
    commands = []
    optional_flags = ["-hierarchical", "-hsc", "-filter", "-regexp", "-nocase", "-quiet", "-of_objects", "patterns"]
    
    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):

            #Constraint 1: -nocase is only valid with -regexp
            if "-nocase" in option_combination and "-regexp" not in option_combination:
                continue
            
            #Constraint 2: -hierarchical and -of_objects are mutually exclusive
            if "-hierarchical" in option_combination and "-of_objects" in option_combination:
                continue
                
            pieces = ["get_nets"]
            
            if "-hierarchical" in option_combination:
                pieces.append("-hierarchical")

            if "-hsc" in option_combination:
                #FIXME: Do not make this random.
                separator = random.choice(SEPARATOR)
                pieces.append(f"-hsc {separator}")

            if "-filter" in option_combination:
                #Filter expression with object type "net"
                filter_type = choose_filter_type()
                expr = generate_filter(filter_type, "net")
                pieces.append(f"-filter {expr}")

            if "-regexp" in option_combination:
                pieces.append("-regexp")
                
            if "-nocase" in option_combination:
                pieces.append("-nocase")

            if "-quiet" in option_combination:
                pieces.append("-quiet")

            if "-of_objects" in option_combination:
                #FIXME: Do not make this random.
                #The name or list of pins or instances.
                pin_inst_list = random.choice(PINS + INSTANCES)
                pieces.append(f"-of_objects {pin_inst_list}")
                
            if "patterns" in option_combination:
                #FIXME: Do not make this random.
                #A list of net name patterns
                pattern = generate_pattern("net")
                pieces.append(pattern)

            commands.append(" ".join(pieces))
    
    return commands 

def generate_create_generated_clock():
    '''
    create_generated_clock (-name <string>)?
                        -source <pin>
                       (-divide_by <integer>)?
                       (-multiply_by <integer>)?
                       (-add)?
                       <pin_list>

    source pin: a pin in the fanout of the master clock that is the source of the generated clock
    '''
    commands = []
    optional_flags = ["-name", "-divide_by", "-multiply_by", "-add"]
    exclusive_options = ["-divide_by", "-multiply_by"]
    
    for i in range(len(optional_flags) + 1):
        for option_combination in combinations(optional_flags, i):
            
            if "-divide_by" in option_combination and "-multiply_by" in option_combination:
                continue
            
            pieces = ["create_generated_clock -source src_clk"]

            target_pins = ["{$dff~2^Q~0}", "{$dff~2^Q~0.Q*}", "[get_pins $dff~2^Q~0.Q]", "[get_pins $dff~2^Q~0.Q[0]]", "[get_pins {$dff~2^Q~0.Q[0]}]", "[get_nets $dff~2^Q~0]"]

            if "-name" in option_combination:
                pieces.append(f"-name clk_gen")
                
            if "-divide_by" in option_combination:
                factor = 2
                pieces.append(f"-divide_by {factor}")
                
            if "-multiply_by" in option_combination:
                factor = 2
                pieces.append(f"-multiply_by {factor}")
                
            if "-add" in option_combination:
                pieces.append("-add")
                
            for pin in target_pins:
                pin_iter_pieces = pieces.copy()
                pin_iter_pieces.append(pin)
                
                cmd = " ".join(pin_iter_pieces)
                cmd = ("create_clock -period 10 [get_ports src_clk]\n"
                        + cmd)
                commands.append(cmd)
                    
    return commands

def generate_all_inputs():
    return ["all_inputs", "all_inputs -no_clocks"]

def generate_all_outputs():
    return ["all_outputs"]

def generate_set_clock_groups():
    '''
    set_clock_groups (-name <string>)?
                 (-logically_exclusive)?
                 (-physically_exclusive)?
                 (-asynchronous)?
                 (-allow_paths)?
                 -group <clocks>
    '''
    
    commands = []
    optional_flags = ["-name", "-logically_exclusive", "-physically_exclusive", "-asynchronous", "-allow_paths", "-exclusive"]
    exclusive_options = ["-logically_exclusive", "-physically_exclusive", "-asynchronous", "-exclusive"]
    
    for num_groups in [1, 2]: 
        
        for i in range(len(optional_flags) + 1):
            for option_combination in combinations(optional_flags, i):
                
                if sum(1 for opt in exclusive_options if opt in option_combination) > 1:
                    continue
                # '-name' doesn't support more than one groups
                if "-name" in option_combination and num_groups != 1:
                    continue
                
                pieces = ["set_clock_groups"] 
                
                if "-logically_exclusive" in option_combination:
                    pieces.append("-logically_exclusive")
                    
                if "-physically_exclusive" in option_combination:
                    pieces.append("-physically_exclusive")
                
                if "-asynchronous" in option_combination:
                    pieces.append("-asynchronous")
                    
                if "-allow_paths" in option_combination:
                    pieces.append("-allow_paths")
                
                if num_groups == 1: #Choose one clock group
                    if "-name" in option_combination:
                        pieces.append("-name grp_name")
                    pieces.append(f"-group clk1")
                    
                if num_groups == 2: #Choose two clock groups
                        pieces.append(f"-group clk1 -group clk2")

                #Join the options to create a proper command
                pieces = " ".join(pieces)
                #Add create_clock prerequisites
                pieces = ("create_clock -period 10 [get_pins clk1]\n"
                          "create_clock -period 10 [get_pins clk2]\n"
                          + pieces)
                commands.append(pieces)
            
    return commands

def generate_all_clocks():
    return ["create_clock -period 10 -name clk1 [get_ports clk1]\ncreate_clock -period 10 -name clk2 [get_ports clk2]\nall_clocks"]

def generate_set_operating_conditions():
    '''
    -analysis_type single|bc_wc|on_chip_variation is supposed to be mutually exclusive
    'condition' is used for single
    '-min', '-max' are used for 'bc_wc' and 'on_chip_variation' 
    '''
    commands = []
    
    #-analysis_type single
    single_options = ["condition", "-library"]
    
    for i in range(len(single_options) + 1):
        for option_combination in combinations(single_options, i):
            pieces = ["set_operating conditions", "-analysis_type single"]
            
            if "condition" in option_combination:
                #FIXME: Do not make this random
                condition = random.choice(OPERATING_CONDITIONS)
                pieces.append(condition)
                
            if "-library" in option_combination:
                #FIXME: Do not make this random
                library = random.choice(LIBRARIES)
                pieces.append(f"-library {library}")
            
            commands.append(" ".join(pieces))
    
    analysis_type = ["bc_wc", "on_chip_variation"]
    multi_options = ["-min", "max", "-min_library", "-max_library"]
    
    for type in analysis_type: 
        for i in range(len(multi_options) + 1):
            for option_combination in combinations(multi_options, i):
                pieces = ["set_operating_conditions", f"-analysis_type {type}"]
                
                if "-min" in option_combination:
                    #FIXME: Do not make this random
                    min_condition = random.choice(OPERATING_CONDITIONS)
                    pieces.append(f"-min {min_condition}")
                    
                if "-max" in option_combination:
                    #FIXME: Do not make this random
                    max_condition = random.choice(OPERATING_CONDITIONS)
                    pieces.append(f"-max {max_condition}")
                    
                if "-min_libary" in option_combination:
                    #FIXME: Do not make this random
                    min_library = random.choice(LIBRARIES)
                    pieces.append(f"-min_library {min_library}")
                
                if "-max_libary" in option_combination:
                    #FIXME: Do not make this random
                    max_library = random.choice(LIBRARIES)
                    pieces.append(f"-max_library {max_library}")
                
                commands.append(" ".join(pieces))

def generate_all_registers():
    '''
    -cells, -data_pins, -clock_pins, -async_pins, -output_pins are mutually exclusive 
    '''
    commands = []
    all_options = ["-clock", "-cells", "-data_pins", "-clock_pins", "-async_pins", "-output_pins", "-level_sensitive", "-edge_triggered"]
    
    return_type_options = ["-cells", "-data_pins", "-clock_pins", "-async_pins", "-output_pins"]

    for i in range(len(all_options) + 1):
        for option_combination in combinations(all_options, i):
            
            #Check for mutual exclusion 
            exclusive_count = sum(1 for option in option_combination if option in return_type_options)
            if exclusive_count > 1:
                continue 
            
            if "-level_sensitive" in option_combination and "-edge_triggered" in option_combination:
                continue

            pieces = ["all_registers"]
            
            if "-clock" in option_combination:
                #FIXME: Do not make this random.
                clk = random.choice(CLOCKS)
                pieces.append(f"-clock {clk}")
                
            if "-level_sensitive" in option_combination:
                pieces.append("-level_sensitive")
                
            if "-edge_triggered" in option_combination:
                pieces.append("-edge_triggered")
                
            #Join the options to create a proper command
            pieces = " ".join(pieces)
            #Add create_clock prerequisites
            pieces = ("create_clock -period 10 -name clk1 [get_ports clk1]\n"
                      "create_clock -period 5 -name clk2 [get_ports clk2]\n"
                      + pieces)
            commands.append(pieces)
    
    return commands

def generate_set_disable_timing():
    '''
    set_disable_timing (-from <from_port>)?
                   (-to <to_port>)?
                   <cell, instance, port, pin>
    A cell should be referred to using the library name and a hierarchical separator
    '''
    
    commands = []
    optional_flags = ["-from", "-to"] 
    from_port = ["[get_ports d_in_1]", "d_in_2"]
    to_port = ["[get_ports d_out_1]", "d_in_2"]
    objects = ["[get_cells d_out_2]", "[get_ports d_in_1]", "[get_pins d_out_1.out[0]]", "[get_pins d_out_1*]"]
    
    for obj in objects:
        for i in range(len(optional_flags) + 1):
            for option_combination in combinations(optional_flags, i):
                
                pieces = ["set_disable_timing"]
                
                if "-from" in option_combination:
                    if "-to" in option_combination:
                        for i in range(len(from_port)):
                            from_iter_pieces = pieces.copy()
                            from_iter_pieces.append(f"-from {from_port[i]} -to {to_port[i]}")
                            from_iter_pieces.append(obj)
                            from_iter_pieces = " ".join(from_iter_pieces)
                            from_iter_pieces = ("create_clock -period 10 clk\n" + from_iter_pieces)
                            commands.append(from_iter_pieces)
                    else:
                        for f_port in from_port:
                            from_iter_pieces = pieces.copy()
                            from_iter_pieces.append(f"-from {f_port}")
                            from_iter_pieces.append(obj)
                            from_iter_pieces = " ".join(from_iter_pieces)
                            from_iter_pieces = ("create_clock -period 10 clk\n" + from_iter_pieces)
                            commands.append(from_iter_pieces)
                
                if "-to" in option_combination:
                    for t_port in to_port:
                        to_iter_pieces = pieces.copy()
                        to_iter_pieces.append(f"-to {t_port}")
                        to_iter_pieces.append(obj)
                        to_iter_pieces = " ".join(to_iter_pieces)
                        to_iter_pieces = ("create_clock -period 10 clk\n" + to_iter_pieces)
                        commands.append(to_iter_pieces)

                # both '-from' and '-to' not in option_combination
                else: 
                    base_pieces = pieces.copy()
+                   base_pieces.append(obj)
+                   base_pieces = " ".join(base_pieces)
+                   base_pieces = ("create_clock -period 10 clk\n" + base_pieces)
+                   commands.append(base_pieces)

    return commands


#Reference
##################################################################################################################################################
GENERATORS = {
    "create_clock": generate_create_clock,
    "get_ports": generate_get_ports,
    "get_clocks": generate_get_clocks,
    "get_pins": generate_get_pins,
    "set_input_delay": generate_set_input_delay,
    "set_output_delay": generate_set_output_delay,
    "set_clock_latency": generate_set_clock_latency,
    "set_clock_uncertainty": generate_set_clock_uncertainty,
    "set_false_path": generate_set_false_path,
    "set_max_delay": generate_set_max_delay,
    "set_min_delay": generate_set_min_delay,
    "set_multicycle_path": generate_set_multicycle_path,
    "get_cells": generate_get_cells,
    "get_nets": generate_get_nets,
    "create_generated_clock": generate_create_generated_clock,
    "all_inputs": generate_all_inputs,
    "all_outputs": generate_all_outputs,
    "set_clock_groups": generate_set_clock_groups,
    "all_clocks": generate_all_clocks,
    "set_operating_conditions": generate_set_operating_conditions,
    "all_registers": generate_all_registers,
    "set_disable_timing": generate_set_disable_timing
}
    
    
#The generate function
##################################################################################################################################################
def generate_files(list_of_commands, batch):
    '''
    Args
    list_of_commands: list of commands we want to generate
    batch: batches for each command
    
    Returns
    .sdc files with commands specified by the input
    '''
    
    for command in list_of_commands:
        if command not in GENERATORS:
            print(f"Command '{command}' not supported. Skipped")
            continue
        
        output_dir = os.path.join(intermediate_dir, str(command))
        
        # Delete output directory if it already exists
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)  # Delete all subdirectories and files
            print(f"Cleaned existing directory: {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(batch):
            gen_commands = GENERATORS[command]() #the list text contains all the commands
            for j in range(len(gen_commands)):
                filename = os.path.join(output_dir, f"{command}_{j}.sdc")
                with open(filename, "w") as f: 
                    f.write(gen_commands[j] + "\n")
        print(f"Generated {len(gen_commands)} {command} files to {output_dir}")

#Main
##################################################################################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDC to generate.")
    parser.add_argument('--sdc_name', type=str, required=True, help="Type of SDC to generate.")
    
    args = parser.parse_args()
    sdc_name = args.sdc_name
    
    generate_files([sdc_name], batch = 1)