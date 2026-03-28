# Running the Syntax Suite

Follow the steps below to generate SDC files and run the syntax validation tests. <br>

First, open ```config.py``` and replace the value of ```VTR_ROOT``` with the absolute path to VTR in your local machine. You do not need to make changes to the other path variables in ```config.py``` since they are relative to this repository.

After that, set up a virtual environment using this command: ```source <PATH_TO_VTR>/.venv/bin/activate```. You will need to replace '\<PATH_TO_VTR>' with the absolute path to VTR. 


## 1. Command-line Options
This is a description of the command-line options for executing the script ```run_syntax.py```.

```--stage <string>``` <br>
 - **generate**: Generates SDCs for testing in the future. <br>
 - **test**: Runs VPR with the BLIF netlist files and the SDCs that were generated. 

```--sdc_name <string>```<br>
 - **\<sdc_name\>**: Name of the SDC to test/generate. <br>
 - **all**: Run/generate all test cases listed in ```SYNTAX_TESTS```, which is defined in ```config.py```.


## 2. Generating SDC Files
The following command will generate test cases for the 'create_clock' constraint by invoking the ```generate_files()``` function in ```generate_sdc.py```.

```bash
python run_syntax.py --stage generate --sdc_name create_clock
```

The command below will generate test cases for all the SDCs listed in ```SYNTAX_TESTS```, defined in ```config.py```. To finetune which SDCs to generate/test, add or remove the SDCs listed in ```SYNTAX_TESTS```.

```bash
python run_syntax.py --stage generate --sdc_name all
```

Running the 'generate' process will create a number of SDCs compatible with the BLIF netlist files included in the suite. The generated files are saved to ```./auto_generated/sdc_files/<sdc_name>```. If the target directory already exists, the script will overwrite the existing files with the newly generated SDCs.

## 3. Testing SDC Syntax
Once the SDCs are generated, you can test if the SDC parser can properly parse the constraint 'create_clock' with the following command. You can type any other SDC as long as they were generated beforehand.

```bash
python run_syntax.py --stage test --sdc_name create_clock
```

You can also run the test for all the constraints listed in the list ```SYNTAX_TESTS``` in ```config.py```. 

```bash
python run_syntax.py --stage test --sdc_name all
```

The script will run VPR until the packing stage with the BLIF netlists provided in this suite and the generated SDCs.

## 4. Viewing the Results
The script will keep track of any errors reported by VPR. All output files are saved to ```./results/syntax/<sdc_name>```. This path is saved as the variable ```RESULTS_DIR``` in ```config.py```. If you wish to change where the output will be saved, change the value of ```RESULTS_DIR```.

The script generates the following summary and log files: 

 - **error_log.txt**: Contains the SDC and error logs reported by VPR during execution.
 - **passed_test.txt**: Lists all SDCs that passed the syntax check successfully.
 - **summary.csv**: Provides a summary of how many SDCs have passed or failed the test.
