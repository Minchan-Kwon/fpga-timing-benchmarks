# Auto Generated Suite

This is a benchmark suite automatically generated to test a CAD tool's ability to parse Synopsys Design Constraints.
It is a collection of all valid combinations of SDCs and their corresponding RTL files written in Verilog. 
The specific commands included in this benchmark are listed in the [syntax document](./docs/syntax/README.md).

![auto-gen-syntax-suite.png](.auto_generated/images/Syntax-Suite.png)

All of the SDCs in this suite have been generated using generate_sdc.py included in the repository. 
This Python script will exhaustively generate SDCs that fit the syntax description. 
We then pass the SDCs through OpenSTA to filter out any invalid SDCs that may have been generated. 
This suite is made up of the valid SDCs and the RTL files that go along with them in the CAD flow.  

