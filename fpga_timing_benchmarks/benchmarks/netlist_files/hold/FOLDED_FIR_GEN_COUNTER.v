///////////////////////////////////////////////////
// 8-tap folded FIR filter design
// clk_slow is derived from clk_fast via a counter
// Author: Minchan Kwon
///////////////////////////////////////////////////

module FOLDED_FIR(
    input               clk_fast,
    input               rstn,
    input signed [13:0] c0, c1, c2, c3, c4, c5, c6, c7,
    input        [13:0] ext_input_mem_din,
    input               ext_input_mem_nwrt,
    output       [23:0] ext_output_mem_do
);

    // Memory Controller Wires
    wire       sync;
    wire       rNWRT, wNWRT;
    wire       rNCE,  wNCE;
    wire [7:0] rADDR, wADDR;

    // FIR Controller Wires
    wire       MUX_ACC, MUX_OUT;
    wire [2:0] MUX_X, MUX_COEF;

    // Memory Wires
    wire [13:0] din_mem;

    // FIR Wires
    wire [13:0] din_delayed;
    wire [23:0] dout_fir;

    // Clock divider
    // Divide by 8
    wire clk_slow;
    
    clk_div_8 clk_divider(.clk_in(clk_fast), .rstn(rstn), .clk_out(clk_slow));

    // Delay Line
    delay_line X_delay(.clk(clk_slow), .rstn(rstn), .sel(MUX_X), .d_in(din_mem), .d_out(din_delayed));

    // Controller
    mem_control MEM_CONTROL(
        .clk        (clk_slow),
        .rstn       (rstn),
        .start_flag (sync),
        .rNWRT      (rNWRT),
        .wNWRT      (wNWRT),
        .rNCE       (rNCE),
        .wNCE       (wNCE),
        .rADDR      (rADDR),
        .wADDR      (wADDR)
    );

    fir_control FIR_CONTROL(
        .clk        (clk_fast),
        .rstn       (rstn),
        .start_flag (sync),
        .MUX_ACC    (MUX_ACC),
        .MUX_OUT    (MUX_OUT),
        .MUX_X      (MUX_X),
        .MUX_COEF   (MUX_COEF)
    );

    // Input Memory
    rflp256x14mx4 INPUT_MEM(
        .NWRT (rNWRT & ext_input_mem_nwrt), 
        .DIN  (ext_input_mem_din),          
        .RA   (rADDR[7:2]), 
        .CA   (rADDR[1:0]),
        .NCE  (rNCE), 
        .CLK  (clk_slow), 
        .DO   (din_mem)
    );

    // FIR Filter
    folded_8tap_fir FIR(
        .clk(clk_fast),
        .rstn(rstn),
        .MUX_ACC(MUX_ACC),
        .MUX_OUT(MUX_OUT),
        .MUX_COEF(MUX_COEF),
        .d_in(din_delayed),
        .c0(c0), .c1(c1), .c2(c2), .c3(c3),
        .c4(c4), .c5(c5), .c6(c6), .c7(c7),
        .result(dout_fir)
    );

    // Write Memory
    rflp256x24mx4 OUTPUT_MEM(
        .NWRT (wNWRT), 
        .DIN  (dout_fir), 
        .RA   (wADDR[7:2]), 
        .CA   (wADDR[1:0]), 
        .NCE  (wNCE), 
        .CLK  (clk_slow), 
        .DO   (ext_output_mem_do) 
    );

endmodule

module mem_control(
    input        clk,  // Slow clock
    input        rstn,
    output reg   start_flag,
    output reg   rNWRT,
    output reg   wNWRT,
    output reg   rNCE,
    output reg   wNCE,
    output [7:0] rADDR,
    output [7:0] wADDR

);
    reg [8:0] addr_counter;

    always @(posedge clk) begin
        if (!rstn) begin
            rNWRT <= 1'b1;
            wNWRT <= 1'b1;
            rNCE  <= 1'b1;
            wNCE  <= 1'b1;
            addr_counter <= 9'b0;
            start_flag <= 1'b0;
        end
        else begin
            // Set start_flag to 1
            if (!start_flag) begin
                start_flag <= 1'b1;
            end
            // Counter Increment Logic
            // Must stop counting after accessing memory address 255
            else if (addr_counter <= 9'd265) begin
                addr_counter <= addr_counter + 1'b1;
            end

            // Read Memory Control
            rNWRT <= 1'b1; // Always Read Mode
            // Read memory is enabled until address 255 is accessed.
            // Memory is disabled afterwards to block illegal access.
            if (addr_counter < 9'd255) begin
                rNCE <= 1'b0;   // Turns on the moment addr_counter == 255
            end
            else begin
                rNCE <= 1'b1;
            end

            // Write Memory Control
            // Wait 10 cycles for the output to become valid.
            // Disable write memory after memory write to address 255 occurs.
            if (addr_counter >= 9'd9 && addr_counter < 9'd265) begin
                wNWRT <= 1'b0;
                wNCE  <= 1'b0;      // High when addr_counter is between 10-265
            end
            else begin
                // The memory is disabled after the counter becomes 265 (255 + 10).
                wNWRT <= 1'b1;
                wNCE  <= 1'b1;
            end
        end
    end

    assign rADDR = addr_counter[7:0];
    assign wADDR = addr_counter[7:0] - 8'd10;

endmodule

module folded_8tap_fir(
    input                clk, // Fast clock
    input                rstn,
    input                MUX_ACC,
    input                MUX_OUT,
    input          [2:0] MUX_COEF,
    input  signed [13:0] d_in,
    input  signed [13:0] c0, c1, c2, c3, c4, c5, c6, c7,
    output signed [23:0] result
);
    // Registers
    reg signed [13:0] coef;
    reg signed [13:0] X_n;
    reg signed [24:0] acc;
    reg signed [24:0] d_out;
    
    // Wires
    wire signed [13:0] coef_mux;
    wire signed [27:0] product;
    wire signed [21:0] product_round;
    wire signed [24:0] acc_mux;
    wire signed [24:0] out_mux;


    // Sequential Logic
    always @(posedge clk) begin
        if (!rstn) begin
            coef  <= 14'b0;
            X_n   <= 14'b0;
            acc   <= 25'b0;
            d_out <= 25'b0;
        end
        else begin
            coef  <= coef_mux;
            X_n   <= d_in;
            acc   <= product_round + acc_mux;
            d_out <= out_mux;
        end
    end

    // Coefficient MUX
    assign coef_mux = (MUX_COEF == 3'b000) ? c0 :
                      (MUX_COEF == 3'b001) ? c1 :
                      (MUX_COEF == 3'b010) ? c2 :
                      (MUX_COEF == 3'b011) ? c3 :
                      (MUX_COEF == 3'b100) ? c4 :
                      (MUX_COEF == 3'b101) ? c5 :
                      (MUX_COEF == 3'b110) ? c6 :
                      (MUX_COEF == 3'b111) ? c7 : 14'bx;

    // Multiplication
    assign product = coef * X_n;

    // Rounding Units
    round_unit R0(.in(product), .out(product_round));

    // Accumulation MUX
    assign acc_mux = MUX_ACC ? acc : 0;
    
    // Output MUX
    assign out_mux = MUX_OUT ? d_out : acc;

    // Output Assignment
    assign result = d_out;

endmodule

module round_unit(
    input  signed [27:0] in,
    output signed [21:0] out
);
    assign out = in[4] ? in[26:5] + 1'b1 : in[26:5];
endmodule

module fir_control(
    input            clk,  // Fast clock
    input            rstn,
    input            start_flag,
    output reg       MUX_ACC,
    output reg       MUX_OUT,
    output reg [2:0] MUX_X,
    output reg [2:0] MUX_COEF
);
    reg [2:0] counter;
    reg RUN;

    always @(posedge clk) begin
        if (!rstn) begin
            counter <= 1'b0;
        end
        else if (start_flag) begin
            counter <= counter + 1'b1;
        end
    end

    always @(*) begin
        if (counter == 3'b1) begin
            MUX_ACC = 1'b0;
            MUX_OUT = 1'b0;
        end
        else begin
            MUX_ACC = 1'b1;
            MUX_OUT = 1'b1;
        end
    end

    assign MUX_X = counter;
    assign MUX_COEF = counter;

endmodule

module delay_line(
    input                clk,  // Slow clock
    input                rstn,
    input          [2:0] sel,
    input  signed [13:0] d_in,
    output signed [13:0] d_out
);
    // The numbers represent k in X[n-k]
    reg signed [13:0] X_n0, X_n1, X_n2, X_n3, X_n4, X_n5, X_n6, X_n7;

    // Delay line clocked by 'clk_slow'
    always @(posedge clk) begin
        if (!rstn) begin
            X_n0 <= 14'b0;
            X_n1 <= 14'b0;
            X_n2 <= 14'b0;
            X_n3 <= 14'b0;
            X_n4 <= 14'b0;
            X_n5 <= 14'b0;
            X_n6 <= 14'b0;
            X_n7 <= 14'b0;
        end
        else begin
            X_n0 <= d_in;
            X_n1 <= X_n0;
            X_n2 <= X_n1;
            X_n3 <= X_n2;
            X_n4 <= X_n3;
            X_n5 <= X_n4;
            X_n6 <= X_n5;
            X_n7 <= X_n6;
        end
    end

    // 8-to-1 MUX
    // Must be driven by a proper select signal from the control unit
    assign d_out = (sel == 3'b000) ? X_n0 :
                   (sel == 3'b001) ? X_n1 :
                   (sel == 3'b010) ? X_n2 :
                   (sel == 3'b011) ? X_n3 :
                   (sel == 3'b100) ? X_n4 :
                   (sel == 3'b101) ? X_n5 :
                   (sel == 3'b110) ? X_n6 :
                   (sel == 3'b111) ? X_n7 : 14'bx;

endmodule

module rflp256x14mx4(
    output reg [13:0] DO,
    input [13:0] DIN,
    input [5:0] RA,
    input [1:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array declaration with synthesis attribute
    (* ram_style = "block" *) reg [13:0] array [0:255];
    
    // Concatenate Row Address and Column Address to form the 8-bit address
    wire [7:0] addr = {RA, CA};

    // Synchronous read and write operations for BRAM inference
    always @(posedge CLK) begin
        if (!NCE) begin // Active low chip enable
            if (!NWRT) begin
                // Write operation: Active low write enable
                array[addr] <= DIN;
            end else begin
                // Read operation
                DO <= array[addr];
            end
        end
    end

endmodule

`timescale 1ns / 10ps

module rflp256x24mx4(
    output reg [23:0] DO,
    input [23:0] DIN,
    input [5:0] RA,
    input [1:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array declaration with synthesis attribute
    (* ram_style = "block" *) reg [23:0] array [0:255];
    
    // Concatenate Row Address and Column Address to form the 8-bit address
    wire [7:0] addr = {RA, CA};

    // Synchronous read and write operations for BRAM inference
    always @(posedge CLK) begin
        if (!NCE) begin // Active low chip enable
            if (!NWRT) begin
                // Write operation: Active low write enable
                array[addr] <= DIN;
            end else begin
                // Read operation
                DO <= array[addr];
            end
        end
    end

endmodule

module clk_div_8 (
    input  wire clk_in,
    input  wire rstn,
    output wire clk_out
);

    // 3-bit counter for divide-by-8
    reg [2:0] counter;

    always @(posedge clk_in) begin
        if (!rstn) begin
            counter <= 3'b000;
        end 
        else begin
            counter <= counter + 1'b1;
        end
    end

    // MSB toggles every 4 cycles, providing a divide-by-8 clock
    assign clk_out = counter[2];

endmodule