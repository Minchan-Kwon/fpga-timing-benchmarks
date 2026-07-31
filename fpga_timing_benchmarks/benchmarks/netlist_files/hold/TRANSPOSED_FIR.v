///////////////////////////////////////////////////
// 48-tap transposed FIR filter design
// Author: Minchan Kwon
///////////////////////////////////////////////////

module TRANSPOSED_FIR(
    input               clk,
    input               rstn,
    input signed [13:0] c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15,
    input signed [13:0] c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31,
    input signed [13:0] c32, c33, c34, c35, c36, c37, c38, c39, c40, c41, c42, c43, c44, c45, c46, c47,
    input        [13:0] ext_input_mem_din,
    input               ext_input_mem_nwrt,
    output       [23:0] ext_output_mem_do
);

    wire       rNWRT, wNWRT;
    wire       rNCE,  wNCE;
    wire [7:0] rADDR, wADDR;

    wire [13:0] trans_din_mem;

    wire [23:0] trans_dout_fir;

    fir_control_48tap CONTROL(
        .clk   (clk),
        .rstn  (rstn),
        .rNWRT (rNWRT),
        .wNWRT (wNWRT),
        .rNCE  (rNCE),
        .wNCE  (wNCE),
        .rADDR (rADDR),
        .wADDR (wADDR)
    );

    rflp256x14mx4 TRANS_INPUT_MEM(
        .NWRT (rNWRT & ext_input_mem_nwrt), 
        .DIN  (ext_input_mem_din), 
        .RA   (rADDR[7:2]), 
        .CA   (rADDR[1:0]), 
        .NCE  (rNCE), 
        .CLK  (clk), 
        .DO   (trans_din_mem)
    );

    transpose_48tap_fir TRANS_FIR(
        .clk    (clk), 
        .rstn   (rstn), 
        .d_in   (trans_din_mem[13:0]), 
        .c0(c0), .c1(c1), .c2(c2), .c3(c3), .c4(c4), .c5(c5), .c6(c6), .c7(c7),
        .c8(c8), .c9(c9), .c10(c10), .c11(c11), .c12(c12), .c13(c13), .c14(c14), .c15(c15),
        .c16(c16), .c17(c17), .c18(c18), .c19(c19), .c20(c20), .c21(c21), .c22(c22), .c23(c23),
        .c24(c24), .c25(c25), .c26(c26), .c27(c27), .c28(c28), .c29(c29), .c30(c30), .c31(c31),
        .c32(c32), .c33(c33), .c34(c34), .c35(c35), .c36(c36), .c37(c37), .c38(c38), .c39(c39),
        .c40(c40), .c41(c41), .c42(c42), .c43(c43), .c44(c44), .c45(c45), .c46(c46), .c47(c47),
        .result (trans_dout_fir)
    );

    rflp256x24mx4 TRANS_OUTPUT_MEM(
        .NWRT (wNWRT), 
        .DIN  (trans_dout_fir), 
        .RA   (wADDR[7:2]), 
        .CA   (wADDR[1:0]), 
        .NCE  (wNCE), 
        .CLK  (clk), 
        .DO   (ext_output_mem_do)
    );

endmodule

module fir_control_48tap(
    input        clk,
    input        rstn,
    output reg   rNWRT,
    output reg   wNWRT,
    output reg   rNCE,
    output reg   wNCE,
    output [7:0] rADDR,
    output [7:0] wADDR
);
    reg [8:0] addr_counter;
    reg       start_flag;

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
            if (!start_flag) begin
                start_flag <= 1'b1;
            end
            else if (addr_counter <= 9'd305) begin
                addr_counter <= addr_counter + 1'b1;
            end

            rNWRT <= 1'b1;
            if (addr_counter < 9'd255) begin
                rNCE <= 1'b0;
            end
            else begin
                rNCE <= 1'b1;
            end

            if (addr_counter >= 9'd49 && addr_counter < 9'd305) begin
                wNWRT <= 1'b0;
                wNCE  <= 1'b0;
            end
            else begin
                wNWRT <= 1'b1;
                wNCE  <= 1'b1;
            end
        end
    end

    assign rADDR = addr_counter[7:0];
    assign wADDR = addr_counter[7:0] - 8'd50;

endmodule

module round_unit(
    input  signed [27:0] in,
    output signed [21:0] out
);
    assign out = in[4] ? in[26:5] + 1'b1 : in[26:5];
endmodule

module transpose_48tap_fir(
    input                clk,
    input                rstn,
    input  signed [13:0] d_in,
    input  signed [13:0] c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15,
    input  signed [13:0] c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31,
    input  signed [13:0] c32, c33, c34, c35, c36, c37, c38, c39, c40, c41, c42, c43, c44, c45, c46, c47,
    output signed [23:0] result
);
    reg signed [13:0] x0;
    reg signed [23:0] x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15;
    reg signed [23:0] x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31;
    reg signed [23:0] x32, x33, x34, x35, x36, x37, x38, x39, x40, x41, x42, x43, x44, x45, x46, x47;
    reg signed [23:0] d_out;
    
    wire signed [27:0] mul_0_out, mul_1_out, mul_2_out, mul_3_out, mul_4_out, mul_5_out, mul_6_out, mul_7_out;
    wire signed [27:0] mul_8_out, mul_9_out, mul_10_out, mul_11_out, mul_12_out, mul_13_out, mul_14_out, mul_15_out;
    wire signed [27:0] mul_16_out, mul_17_out, mul_18_out, mul_19_out, mul_20_out, mul_21_out, mul_22_out, mul_23_out;
    wire signed [27:0] mul_24_out, mul_25_out, mul_26_out, mul_27_out, mul_28_out, mul_29_out, mul_30_out, mul_31_out;
    wire signed [27:0] mul_32_out, mul_33_out, mul_34_out, mul_35_out, mul_36_out, mul_37_out, mul_38_out, mul_39_out;
    wire signed [27:0] mul_40_out, mul_41_out, mul_42_out, mul_43_out, mul_44_out, mul_45_out, mul_46_out, mul_47_out;
    
    wire signed [21:0] round_0_out, round_1_out, round_2_out, round_3_out, round_4_out, round_5_out, round_6_out, round_7_out;
    wire signed [21:0] round_8_out, round_9_out, round_10_out, round_11_out, round_12_out, round_13_out, round_14_out, round_15_out;
    wire signed [21:0] round_16_out, round_17_out, round_18_out, round_19_out, round_20_out, round_21_out, round_22_out, round_23_out;
    wire signed [21:0] round_24_out, round_25_out, round_26_out, round_27_out, round_28_out, round_29_out, round_30_out, round_31_out;
    wire signed [21:0] round_32_out, round_33_out, round_34_out, round_35_out, round_36_out, round_37_out, round_38_out, round_39_out;
    wire signed [21:0] round_40_out, round_41_out, round_42_out, round_43_out, round_44_out, round_45_out, round_46_out, round_47_out;
    
    wire signed [23:0] adder_0_out, adder_1_out, adder_2_out, adder_3_out, adder_4_out, adder_5_out, adder_6_out, adder_7_out;
    wire signed [23:0] adder_8_out, adder_9_out, adder_10_out, adder_11_out, adder_12_out, adder_13_out, adder_14_out, adder_15_out;
    wire signed [23:0] adder_16_out, adder_17_out, adder_18_out, adder_19_out, adder_20_out, adder_21_out, adder_22_out, adder_23_out;
    wire signed [23:0] adder_24_out, adder_25_out, adder_26_out, adder_27_out, adder_28_out, adder_29_out, adder_30_out, adder_31_out;
    wire signed [23:0] adder_32_out, adder_33_out, adder_34_out, adder_35_out, adder_36_out, adder_37_out, adder_38_out, adder_39_out;
    wire signed [23:0] adder_40_out, adder_41_out, adder_42_out, adder_43_out, adder_44_out, adder_45_out, adder_46_out;

    always @(posedge clk) begin
        if (!rstn) begin
            x0 <= 14'b0;
            x1 <= 24'b0; x2 <= 24'b0; x3 <= 24'b0; x4 <= 24'b0;
            x5 <= 24'b0; x6 <= 24'b0; x7 <= 24'b0; x8 <= 24'b0;
            x9 <= 24'b0; x10 <= 24'b0; x11 <= 24'b0; x12 <= 24'b0;
            x13 <= 24'b0; x14 <= 24'b0; x15 <= 24'b0; x16 <= 24'b0;
            x17 <= 24'b0; x18 <= 24'b0; x19 <= 24'b0; x20 <= 24'b0;
            x21 <= 24'b0; x22 <= 24'b0; x23 <= 24'b0; x24 <= 24'b0;
            x25 <= 24'b0; x26 <= 24'b0; x27 <= 24'b0; x28 <= 24'b0;
            x29 <= 24'b0; x30 <= 24'b0; x31 <= 24'b0; x32 <= 24'b0;
            x33 <= 24'b0; x34 <= 24'b0; x35 <= 24'b0; x36 <= 24'b0;
            x37 <= 24'b0; x38 <= 24'b0; x39 <= 24'b0; x40 <= 24'b0;
            x41 <= 24'b0; x42 <= 24'b0; x43 <= 24'b0; x44 <= 24'b0;
            x45 <= 24'b0; x46 <= 24'b0; x47 <= 24'b0;
            d_out <= 24'b0;
        end
        else begin
            x0 <= d_in;
            x1 <= round_47_out;
            x2 <= adder_0_out;  x3 <= adder_1_out;  x4 <= adder_2_out;  x5 <= adder_3_out;
            x6 <= adder_4_out;  x7 <= adder_5_out;  x8 <= adder_6_out;  x9 <= adder_7_out;
            x10 <= adder_8_out; x11 <= adder_9_out; x12 <= adder_10_out; x13 <= adder_11_out;
            x14 <= adder_12_out; x15 <= adder_13_out; x16 <= adder_14_out; x17 <= adder_15_out;
            x18 <= adder_16_out; x19 <= adder_17_out; x20 <= adder_18_out; x21 <= adder_19_out;
            x22 <= adder_20_out; x23 <= adder_21_out; x24 <= adder_22_out; x25 <= adder_23_out;
            x26 <= adder_24_out; x27 <= adder_25_out; x28 <= adder_26_out; x29 <= adder_27_out;
            x30 <= adder_28_out; x31 <= adder_29_out; x32 <= adder_30_out; x33 <= adder_31_out;
            x34 <= adder_32_out; x35 <= adder_33_out; x36 <= adder_34_out; x37 <= adder_35_out;
            x38 <= adder_36_out; x39 <= adder_37_out; x40 <= adder_38_out; x41 <= adder_39_out;
            x42 <= adder_40_out; x43 <= adder_41_out; x44 <= adder_42_out; x45 <= adder_43_out;
            x46 <= adder_44_out; x47 <= adder_45_out;
            d_out <= adder_46_out;
        end
    end

    assign mul_0_out = x0 * c0;   assign mul_1_out = x0 * c1;   assign mul_2_out = x0 * c2;   assign mul_3_out = x0 * c3;
    assign mul_4_out = x0 * c4;   assign mul_5_out = x0 * c5;   assign mul_6_out = x0 * c6;   assign mul_7_out = x0 * c7;
    assign mul_8_out = x0 * c8;   assign mul_9_out = x0 * c9;   assign mul_10_out = x0 * c10; assign mul_11_out = x0 * c11;
    assign mul_12_out = x0 * c12; assign mul_13_out = x0 * c13; assign mul_14_out = x0 * c14; assign mul_15_out = x0 * c15;
    assign mul_16_out = x0 * c16; assign mul_17_out = x0 * c17; assign mul_18_out = x0 * c18; assign mul_19_out = x0 * c19;
    assign mul_20_out = x0 * c20; assign mul_21_out = x0 * c21; assign mul_22_out = x0 * c22; assign mul_23_out = x0 * c23;
    assign mul_24_out = x0 * c24; assign mul_25_out = x0 * c25; assign mul_26_out = x0 * c26; assign mul_27_out = x0 * c27;
    assign mul_28_out = x0 * c28; assign mul_29_out = x0 * c29; assign mul_30_out = x0 * c30; assign mul_31_out = x0 * c31;
    assign mul_32_out = x0 * c32; assign mul_33_out = x0 * c33; assign mul_34_out = x0 * c34; assign mul_35_out = x0 * c35;
    assign mul_36_out = x0 * c36; assign mul_37_out = x0 * c37; assign mul_38_out = x0 * c38; assign mul_39_out = x0 * c39;
    assign mul_40_out = x0 * c40; assign mul_41_out = x0 * c41; assign mul_42_out = x0 * c42; assign mul_43_out = x0 * c43;
    assign mul_44_out = x0 * c44; assign mul_45_out = x0 * c45; assign mul_46_out = x0 * c46; assign mul_47_out = x0 * c47;

    round_unit R0(.in(mul_0_out), .out(round_0_out));   round_unit R1(.in(mul_1_out), .out(round_1_out));
    round_unit R2(.in(mul_2_out), .out(round_2_out));   round_unit R3(.in(mul_3_out), .out(round_3_out));
    round_unit R4(.in(mul_4_out), .out(round_4_out));   round_unit R5(.in(mul_5_out), .out(round_5_out));
    round_unit R6(.in(mul_6_out), .out(round_6_out));   round_unit R7(.in(mul_7_out), .out(round_7_out));
    round_unit R8(.in(mul_8_out), .out(round_8_out));   round_unit R9(.in(mul_9_out), .out(round_9_out));
    round_unit R10(.in(mul_10_out), .out(round_10_out)); round_unit R11(.in(mul_11_out), .out(round_11_out));
    round_unit R12(.in(mul_12_out), .out(round_12_out)); round_unit R13(.in(mul_13_out), .out(round_13_out));
    round_unit R14(.in(mul_14_out), .out(round_14_out)); round_unit R15(.in(mul_15_out), .out(round_15_out));
    round_unit R16(.in(mul_16_out), .out(round_16_out)); round_unit R17(.in(mul_17_out), .out(round_17_out));
    round_unit R18(.in(mul_18_out), .out(round_18_out)); round_unit R19(.in(mul_19_out), .out(round_19_out));
    round_unit R20(.in(mul_20_out), .out(round_20_out)); round_unit R21(.in(mul_21_out), .out(round_21_out));
    round_unit R22(.in(mul_22_out), .out(round_22_out)); round_unit R23(.in(mul_23_out), .out(round_23_out));
    round_unit R24(.in(mul_24_out), .out(round_24_out)); round_unit R25(.in(mul_25_out), .out(round_25_out));
    round_unit R26(.in(mul_26_out), .out(round_26_out)); round_unit R27(.in(mul_27_out), .out(round_27_out));
    round_unit R28(.in(mul_28_out), .out(round_28_out)); round_unit R29(.in(mul_29_out), .out(round_29_out));
    round_unit R30(.in(mul_30_out), .out(round_30_out)); round_unit R31(.in(mul_31_out), .out(round_31_out));
    round_unit R32(.in(mul_32_out), .out(round_32_out)); round_unit R33(.in(mul_33_out), .out(round_33_out));
    round_unit R34(.in(mul_34_out), .out(round_34_out)); round_unit R35(.in(mul_35_out), .out(round_35_out));
    round_unit R36(.in(mul_36_out), .out(round_36_out)); round_unit R37(.in(mul_37_out), .out(round_37_out));
    round_unit R38(.in(mul_38_out), .out(round_38_out)); round_unit R39(.in(mul_39_out), .out(round_39_out));
    round_unit R40(.in(mul_40_out), .out(round_40_out)); round_unit R41(.in(mul_41_out), .out(round_41_out));
    round_unit R42(.in(mul_42_out), .out(round_42_out)); round_unit R43(.in(mul_43_out), .out(round_43_out));
    round_unit R44(.in(mul_44_out), .out(round_44_out)); round_unit R45(.in(mul_45_out), .out(round_45_out));
    round_unit R46(.in(mul_46_out), .out(round_46_out)); round_unit R47(.in(mul_47_out), .out(round_47_out));

    assign adder_0_out = x1 + round_46_out;   assign adder_1_out = x2 + round_45_out;
    assign adder_2_out = x3 + round_44_out;   assign adder_3_out = x4 + round_43_out;
    assign adder_4_out = x5 + round_42_out;   assign adder_5_out = x6 + round_41_out;
    assign adder_6_out = x7 + round_40_out;   assign adder_7_out = x8 + round_39_out;
    assign adder_8_out = x9 + round_38_out;   assign adder_9_out = x10 + round_37_out;
    assign adder_10_out = x11 + round_36_out; assign adder_11_out = x12 + round_35_out;
    assign adder_12_out = x13 + round_34_out; assign adder_13_out = x14 + round_33_out;
    assign adder_14_out = x15 + round_32_out; assign adder_15_out = x16 + round_31_out;
    assign adder_16_out = x17 + round_30_out; assign adder_17_out = x18 + round_29_out;
    assign adder_18_out = x19 + round_28_out; assign adder_19_out = x20 + round_27_out;
    assign adder_20_out = x21 + round_26_out; assign adder_21_out = x22 + round_25_out;
    assign adder_22_out = x23 + round_24_out; assign adder_23_out = x24 + round_23_out;
    assign adder_24_out = x25 + round_22_out; assign adder_25_out = x26 + round_21_out;
    assign adder_26_out = x27 + round_20_out; assign adder_27_out = x28 + round_19_out;
    assign adder_28_out = x29 + round_18_out; assign adder_29_out = x30 + round_17_out;
    assign adder_30_out = x31 + round_16_out; assign adder_31_out = x32 + round_15_out;
    assign adder_32_out = x33 + round_14_out; assign adder_33_out = x34 + round_13_out;
    assign adder_34_out = x35 + round_12_out; assign adder_35_out = x36 + round_11_out;
    assign adder_36_out = x37 + round_10_out; assign adder_37_out = x38 + round_9_out;
    assign adder_38_out = x39 + round_8_out;  assign adder_39_out = x40 + round_7_out;
    assign adder_40_out = x41 + round_6_out;  assign adder_41_out = x42 + round_5_out;
    assign adder_42_out = x43 + round_4_out;  assign adder_43_out = x44 + round_3_out;
    assign adder_44_out = x45 + round_2_out;  assign adder_45_out = x46 + round_1_out;
    assign adder_46_out = x47 + round_0_out;

    assign result = d_out;
endmodule

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