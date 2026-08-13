///////////////////////////////////////////////////
// 16-point 2D DCT module
// Author: Minchan Kwon
///////////////////////////////////////////////////

module DCT_2D (
    input          clk,
    input          rstn,
    input  [127:0] RAM_IN_DIN,
    input          RAM_IN_NWRT,
    output [191:0] RAM_OUT_DO
);

    // Wires
    // Control signals
    wire [13:0] ADDR_READ, ADDR_WRT;
    wire        NCE_READ, NCE_WRT;
    wire        SEL_LoF;
    wire        EN_TP1, EN_TP2;
    
    // Datapath
    wire  [16*8-1:0] DCT1_IN;
    wire [12*10-1:0] DCT1_OUT;
    wire [16*10-1:0] TP1_OUT;
    wire [12*12-1:0] DCT2_OUT;
    wire [12*12-1:0] TP2_OUT;

    // Control Unit
    DCTControl CONTROL(
        .clk(clk),
        .rstn(rstn),
        .ADDR_READ(ADDR_READ),
        .ADDR_WRT(ADDR_WRT),
        .NCE_READ(NCE_READ),
        .NCE_WRT(NCE_WRT),
        .SEL_LoF(SEL_LoF),
        .EN_TP1(EN_TP1),
        .EN_TP2(EN_TP2)
    );

    // Input RAM
    rflp16384x128mx16 RAM_IN(
        .DO(DCT1_IN),
        .DIN(RAM_IN_DIN),
        .RA(ADDR_READ[13:4]),
        .CA(ADDR_READ[3:0]),
        .NWRT(RAM_IN_NWRT),
        .NCE(NCE_READ),
        .CLK(clk)
    );

    // 1D-DCT module
    // 16x1 Vector -> 12x1 Vector
    DCT1 DCT_1D(.X(DCT1_IN), .Z(DCT1_OUT));

    // First transposed memory
    // 16x16
    TPMEM1 TPMEM1(
        .i_data(DCT1_OUT),
        .i_enable(EN_TP1),
        .i_clk(clk),
        .i_Reset(rstn),
        .o_data(TP1_OUT)
    );

    // 2D-DCT module
    // 16x1 Vector -> 12x1 Vector
    DCT2 DCT_2D(.X(TP1_OUT), .sel(SEL_LoF), .Z(DCT2_OUT));

    // Second transposed memory
    // 12x12
    TPMEM2 TPMEM2(
        .i_data(DCT2_OUT),
        .i_enable(EN_TP2),
        .i_clk(clk),
        .i_Reset(rstn),
        .o_data(TP2_OUT)
    );

    // Output RAM
    rflp16384x192mx16 RAM_OUT(
        .DO(RAM_OUT_DO),
        .DIN({TP2_OUT, 48'b0}),
        .RA(ADDR_WRT[13:4]),
        .CA(ADDR_WRT[3:0]),
        .NWRT(1'b0),
        .NCE(NCE_WRT),
        .CLK(clk)
    );

endmodule

module DCT1 #(
    parameter IN_BW = 8,   // Input data bit width
    parameter OUT_BW = 10  // output data bit width
    // The width of the coefficients is fixed at 0.5 format
)(
    input   [16*IN_BW-1:0] X,
    output [12*OUT_BW-1:0] Z
);  
    // Input vector elements
    wire signed [IN_BW:0] x0, x1, x2, x3, x4, x5, x6, x7;
    wire signed [IN_BW:0] x8, x9, x10, x11, x12, x13, x14, x15;

    // 6-bit coefficients
    wire signed [6-1:0] c0, c1, c2, c3, c4, c5, c6, c7;
    wire signed [6-1:0] c8, c9, c10, c11, c12, c13, c14, c15;

    // DCT output
    // Pre-truncation (12.5 format)
    // Element-wise product requires 7 bits for integer,
    // 5 bits for decimal, and 1 sign bit (8.5 format).
    // This is because the coefficients are all less than 0.5.
    // Summing the products requires log(16) = 4 additional bits.
    wire signed [16:0] m0, m1, m2, m3, m4, m5, m6, m7;
    wire signed [16:0] m8, m9, m10, m11, m12, m13, m14, m15;
    // Post-truncation
    wire signed [OUT_BW-1:0] z0, z1, z2, z3, z4, z5, z6, z7;
    wire signed [OUT_BW-1:0] z8, z9, z10, z11, z12, z13, z14, z15;

    // Coefficient values
    // These values are from the filt_coeff_T.txt file
    assign c1 = 6'b001011;
    assign c2 = 6'b001011;
    assign c3 = 6'b001011;
    assign c4 = 6'b001010;
    assign c5 = 6'b001010;
    assign c6 = 6'b001001;
    assign c7 = 6'b001001;
    assign c8 = 6'b001000;
    assign c9 = 6'b000111;
    assign c10 = 6'b000110;
    assign c11 = 6'b000101;
    assign c12 = 6'b000100;
    assign c13 = 6'b000011;
    assign c14 = 6'b000010;
    assign c15 = 6'b000001;

    // Sign extend the inputs (inputs are positive pixel magnitudes)
    assign x0  = {1'b0, X[16*IN_BW-1:15*IN_BW]};
    assign x1  = {1'b0, X[15*IN_BW-1:14*IN_BW]};
    assign x2  = {1'b0, X[14*IN_BW-1:13*IN_BW]};
    assign x3  = {1'b0, X[13*IN_BW-1:12*IN_BW]};
    assign x4  = {1'b0, X[12*IN_BW-1:11*IN_BW]};
    assign x5  = {1'b0, X[11*IN_BW-1:10*IN_BW]};
    assign x6  = {1'b0, X[10*IN_BW-1:9*IN_BW]};
    assign x7  = {1'b0, X[ 9*IN_BW-1:8*IN_BW]};
    assign x8  = {1'b0, X[ 8*IN_BW-1:7*IN_BW]};
    assign x9  = {1'b0, X[ 7*IN_BW-1:6*IN_BW]};
    assign x10 = {1'b0, X[ 6*IN_BW-1:5*IN_BW]};
    assign x11 = {1'b0, X[ 5*IN_BW-1:4*IN_BW]};
    assign x12 = {1'b0, X[ 4*IN_BW-1:3*IN_BW]};
    assign x13 = {1'b0, X[ 3*IN_BW-1:2*IN_BW]};
    assign x14 = {1'b0, X[ 2*IN_BW-1:1*IN_BW]};
    assign x15 = {1'b0, X[ 1*IN_BW-1:0]};

    // Get the multiplication results
    // The odd parts and even parts have their own patterns
    assign m0 = c8*(x0+x1+x2+x3+x4+x5+x6+x7+x8+x9+x10+x11+x12+x13+x14+x15);
    assign m1 = c1*(x0-x15) + c3*(x1-x14) + c5*(x2-x13) + c7*(x3-x12) + c9*(x4-x11) + c11*(x5-x10) + c13*(x6-x9) + c15*(x7-x8);
    assign m2 = c2*(x0+x15-x7-x8) + c6*(x1+x14-x6-x9) + c10*(x2+x13-x5-x10) + c14*(x3+x12-x4-x11);
    assign m3 = c3*(x0-x15) + c9*(x1-x14) + c15*(x2-x13) - c11*(x3-x12) - c5*(x4-x11) - c1*(x5-x10) - c7*(x6-x9) - c13*(x7-x8);
    assign m4 = c4*(x0+x15+x7+x8) + c12*(x1+x14+x6+x9) - c12*(x2+x13+x5+x10) - c4*(x3+x12+x4+x11);
    assign m5 = c5*(x0-x15) + c15*(x1-x14) - c7*(x2-x13) - c3*(x3-x12) - c13*(x4-x11) + c9*(x5-x10) + c1*(x6-x9) + c11*(x7-x8);
    assign m6 = c6*(x0+x15-x7-x8) - c14*(x1+x14-x6-x9) - c2*(x2+x13-x5-x10) - c10*(x3+x12-x4-x11);
    assign m7 = c7*(x0-x15) - c11*(x1-x14) - c3*(x2-x13) + c15*(x3-x12) + c1*(x4-x11) + c13*(x5-x10) - c5*(x6-x9) - c9*(x7-x8);
    assign m8 = c8*(x0+x15+x7+x8) - c8*(x1+x14+x6+x9) - c8*(x2+x13+x5+x10) + c8*(x3+x12+x4+x11);
    assign m9 = c9*(x0-x15) - c5*(x1-x14) - c13*(x2-x13) + c1*(x3-x12) - c15*(x4-x11) - c3*(x5-x10) + c11*(x6-x9) + c7*(x7-x8);
    assign m10 = c10*(x0+x15-x7-x8) - c2*(x1+x14-x6-x9) + c14*(x2+x13-x5-x10) + c6*(x3+x12-x4-x11);
    assign m11 = c11*(x0-x15) - c1*(x1-x14) + c9*(x2-x13) + c13*(x3-x12) - c3*(x4-x11) + c7*(x5-x10) + c15*(x6-x9) - c5*(x7-x8);

    // Truncate the results
    assign z0  = m0[15:6];
    assign z1  = m1[15:6];
    assign z2  = m2[15:6];
    assign z3  = m3[15:6];
    assign z4  = m4[15:6];
    assign z5  = m5[15:6];
    assign z6  = m6[15:6];
    assign z7  = m7[15:6];
    assign z8  = m8[15:6];
    assign z9  = m9[15:6];
    assign z10 = m10[15:6];
    assign z11 = m11[15:6];

    // Assign to output
    // Output Q-format is 11.0
    assign Z = {z0, z1, z2, z3, z4, z5, z6, z7, z8, z9, z10, z11};

endmodule

module DCT2 #(
    parameter IN_BW = 10,    // Input data bit width
    parameter OUT_BW = 12  // output data bit width
    // The width of the coefficients is fixed at 1.7 format
)(
    input signed [16*IN_BW-1:0]  X,
    input                        sel,
    output       [12*OUT_BW-1:0] Z
);  
    // Input vector elements
    wire signed [IN_BW-1:0] x0, x1, x2, x3, x4, x5, x6, x7;
    wire signed [IN_BW-1:0] x8, x9, x10, x11, x12, x13, x14, x15;

    // 6-bit coefficients
    wire signed [6-1:0] c0, c1, c2, c3, c4, c5, c6, c7;
    wire signed [6-1:0] c8, c9, c10, c11, c12, c13, c14, c15;
    // 11.0 * 1.5 = 12.5 = 11.5
    // DCT output
    // Pre-truncation
    // Element-wise product requires 10 bits for integer,
    // 5 bits for decimal, and 1 sign bit (10.5 format).
    // This is because the coefficients are all less than 0.5.
    // Summing the products requires log(16) = 4 additional bits.
    wire signed [IN_BW+7+4-1:0] m0, m1, m2, m3, m4, m5, m6, m7;
    wire signed [IN_BW+7+4-1:0] m8, m9, m10, m11, m12, m13, m14, m15;
    // Post-truncation, pre-overflow detection
    wire signed [OUT_BW:0] z0, z1, z2, z3, z4, z5, z6, z7;
    wire signed [OUT_BW:0] z8, z9, z10, z11, z12, z13, z14, z15;
    wire signed [OUT_BW:0] z0_0, z0_1;

    // Post overflow compensation
    wire signed [OUT_BW-1:0] z0c, z1c, z2c, z3c, z4c, z5c, z6c, z7c;
    wire signed [OUT_BW-1:0] z8c, z9c, z10c, z11c, z12c, z13c, z14c, z15c;

    // Coefficient values
    // These values are from the filt_coeff_T.txt file
    assign c1 = 6'b001011;
    assign c2 = 6'b001011;
    assign c3 = 6'b001011;
    assign c4 = 6'b001010;
    assign c5 = 6'b001010;
    assign c6 = 6'b001001;
    assign c7 = 6'b001001;
    assign c8 = 6'b001000;
    assign c9 = 6'b000111;
    assign c10 = 6'b000110;
    assign c11 = 6'b000101;
    assign c12 = 6'b000100;
    assign c13 = 6'b000011;
    assign c14 = 6'b000010;
    assign c15 = 6'b000001;

    // Inputs are signed sum of products
    assign x0  = X[16*IN_BW-1:15*IN_BW];
    assign x1  = X[15*IN_BW-1:14*IN_BW];
    assign x2  = X[14*IN_BW-1:13*IN_BW];
    assign x3  = X[13*IN_BW-1:12*IN_BW];
    assign x4  = X[12*IN_BW-1:11*IN_BW];
    assign x5  = X[11*IN_BW-1:10*IN_BW];
    assign x6  = X[10*IN_BW-1:9*IN_BW];
    assign x7  = X[ 9*IN_BW-1:8*IN_BW];
    assign x8  = X[ 8*IN_BW-1:7*IN_BW];
    assign x9  = X[ 7*IN_BW-1:6*IN_BW];
    assign x10 = X[ 6*IN_BW-1:5*IN_BW];
    assign x11 = X[ 5*IN_BW-1:4*IN_BW];
    assign x12 = X[ 4*IN_BW-1:3*IN_BW];
    assign x13 = X[ 3*IN_BW-1:2*IN_BW];
    assign x14 = X[ 2*IN_BW-1:1*IN_BW];
    assign x15 = X[ 1*IN_BW-1:0];

    // Get the multiplication results
    // The odd parts and even parts have their own patterns
    assign m0 = c8*(x0+x1+x2+x3+x4+x5+x6+x7+x8+x9+x10+x11+x12+x13+x14+x15);
    assign m1 = c1*(x0-x15) + c3*(x1-x14) + c5*(x2-x13) + c7*(x3-x12) + c9*(x4-x11) + c11*(x5-x10) + c13*(x6-x9) + c15*(x7-x8);
    assign m2 = c2*(x0+x15-x7-x8) + c6*(x1+x14-x6-x9) + c10*(x2+x13-x5-x10) + c14*(x3+x12-x4-x11);
    assign m3 = c3*(x0-x15) + c9*(x1-x14) + c15*(x2-x13) - c11*(x3-x12) - c5*(x4-x11) - c1*(x5-x10) - c7*(x6-x9) - c13*(x7-x8);
    assign m4 = c4*(x0+x15+x7+x8) + c12*(x1+x14+x6+x9) - c12*(x2+x13+x5+x10) - c4*(x3+x12+x4+x11);
    assign m5 = c5*(x0-x15) + c15*(x1-x14) - c7*(x2-x13) - c3*(x3-x12) - c13*(x4-x11) + c9*(x5-x10) + c1*(x6-x9) + c11*(x7-x8);
    assign m6 = c6*(x0+x15-x7-x8) - c14*(x1+x14-x6-x9) - c2*(x2+x13-x5-x10) - c10*(x3+x12-x4-x11);
    assign m7 = c7*(x0-x15) - c11*(x1-x14) - c3*(x2-x13) + c15*(x3-x12) + c1*(x4-x11) + c13*(x5-x10) - c5*(x6-x9) - c9*(x7-x8);
    assign m8 = c8*(x0+x15+x7+x8) - c8*(x1+x14+x6+x9) - c8*(x2+x13+x5+x10) + c8*(x3+x12+x4+x11);
    assign m9 = c9*(x0-x15) - c5*(x1-x14) - c13*(x2-x13) + c1*(x3-x12) - c15*(x4-x11) - c3*(x5-x10) + c11*(x6-x9) + c7*(x7-x8);
    assign m10 = c10*(x0+x15-x7-x8) - c2*(x1+x14-x6-x9) + c14*(x2+x13-x5-x10) + c6*(x3+x12-x4-x11);
    assign m11 = c11*(x0-x15) - c1*(x1-x14) + c9*(x2-x13) + c13*(x3-x12) - c3*(x4-x11) + c7*(x5-x10) + c15*(x6-x9) - c5*(x7-x8);

    // Truncate the results
    assign z0_1  = m0[17:5];  // DC output
    assign z0_0  = m0[15:3];  // Non-DC output
    assign z0 = sel ? z0_1 : z0_0;
    assign z1  = m1[15:3];
    assign z2  = m2[15:3];
    assign z3  = m3[15:3];
    assign z4  = m4[15:3];
    assign z5  = m5[15:3];
    assign z6  = m6[15:3];
    assign z7  = m7[15:3];
    assign z8  = m8[15:3];
    assign z9  = m9[15:3];
    assign z10 = m10[15:3];
    assign z11 = m11[15:3];

    // Overflow compensation
    assign z0c  = (z0[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z0[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z0[OUT_BW-1:0];
    assign z1c  = (z1[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z1[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z1[OUT_BW-1:0];
    assign z2c  = (z2[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z2[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z2[OUT_BW-1:0];
    assign z3c  = (z3[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z3[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z3[OUT_BW-1:0];
    assign z4c  = (z4[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z4[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z4[OUT_BW-1:0];
    assign z5c  = (z5[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z5[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z5[OUT_BW-1:0];
    assign z6c  = (z6[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z6[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z6[OUT_BW-1:0];
    assign z7c  = (z7[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z7[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z7[OUT_BW-1:0];
    assign z8c  = (z8[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z8[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z8[OUT_BW-1:0];
    assign z9c  = (z9[OUT_BW:OUT_BW-1]  == 2'b01) ? 12'b0111_1111_1111 : (z9[OUT_BW:OUT_BW-1]  == 2'b10) ? 12'b1000_0000_0000 : z9[OUT_BW-1:0];
    assign z10c = (z10[OUT_BW:OUT_BW-1] == 2'b01) ? 12'b0111_1111_1111 : (z10[OUT_BW:OUT_BW-1] == 2'b10) ? 12'b1000_0000_0000 : z10[OUT_BW-1:0];
    assign z11c = (z11[OUT_BW:OUT_BW-1] == 2'b01) ? 12'b0111_1111_1111 : (z11[OUT_BW:OUT_BW-1] == 2'b10) ? 12'b1000_0000_0000 : z11[OUT_BW-1:0];

    // Assign to output
    assign Z = {z0c, z1c, z2c, z3c, z4c, z5c, z6c, z7c, z8c, z9c, z10c, z11c};

endmodule

module DCTControl(
    input         clk,
    input         rstn,
    output [13:0] ADDR_READ,
    output [13:0] ADDR_WRT,
    output        NCE_READ,
    output        NCE_WRT,
    output        SEL_LoF,
    output        EN_TP1,  // The enable signal to start the internal counter in TPMEM1
    output        EN_TP2   // The enable signal to start the internal counter in TPMEM2
);
    reg        RUN;
    reg [14:0] counter;  // 15-bit counter

    // Counter logic
    always @(posedge clk) begin
        if (!rstn) begin
            RUN     <= 1'b0;
            counter <= 15'b0;
        end
        else begin
            if (!RUN) begin
                // start
                RUN <= 1'b1;
            end
            else begin
                // Running
                if (counter == 35 + 16*1024) begin
                    // Termination condition
                    // Final write to the output RAM finishes after 
                    // (36+16*1024)th cycle. The counter value at
                    // the (36+16*1024)th cycle is 35+16*1024.
                    RUN     <= 1'b0;
                    counter <= 15'b0;
                end
                else begin
                    counter <= counter + 1'b1;
                end
            end
        end
    end


// RAM NCE
assign NCE_READ = (counter >= 16*1024);
assign NCE_WRT  = (counter <= 34) | (counter >= 35 + 16*1024) | (~RUN);

// Address
assign ADDR_READ = counter[13:0];
assign ADDR_WRT  = counter[13:0] - 14'd35;

// TPMEM Enable
assign EN_TP1 = (counter >= 15'b1);
assign EN_TP2 = (counter >= 15'd18);

// DC Signal select
assign SEL_LoF = ((counter) % 16 == 2);
endmodule

module TPMEM1
#( parameter BW = 10,
   parameter SIZE = 12 )
   // SIZE stands for the number of elements in the input vector
   // Unlike TPMEM2, TPMEM1 is still has a shape of 16x16.
(  input        [SIZE*BW-1:0] i_data,
   input                      i_enable,
   input                      i_clk,
   input                      i_Reset,
   output reg     [16*BW-1:0] o_data
);

reg [5-1:0]         counter;
reg [16*BW-1:0]     array   [16-1:0];       // Array to store data
reg [16*BW-1:0]     data_out;               // Data that has been read

wire [16*BW-1:0]    col     [16-1:0];       // Column-wise data
wire [4-1:0]        index = counter[4-1:0]; // Address

// Counter and IO 
always @(posedge i_clk) begin
    if (!i_Reset) begin
        counter <= 5'b0;
        o_data <= {16*BW{1'b0}};
    end
    else begin
        o_data <= data_out;
        if (i_enable)
            counter <= counter + 5'b1;
    end
end

// Read the data
always @(*) begin
    if (counter[4] == 1'b0) begin
        // MSB of counter == 0: Row-wise read
        data_out = array[index];
    end
    else begin
        // MSB of counter == 1: Column-wise read
        data_out = col[index];
    end
end

// Write the input data
genvar r, c;
generate
    for (r = 0; r < 16; r = r + 1) begin : gen_write_row
        for (c = 0; c < 16; c = c + 1) begin : gen_write_col
            always @(posedge i_clk) begin
                if (~i_Reset) begin
                    // Reset the array
                    array[r][(16-c)*BW-1 -: BW] <= {BW{1'b0}};
                end
                else if (i_enable) begin
                    // MSB of counter == 0: Row-wise write
                    // Access the array with the variable 'c'
                    // instead of the dynamic register value 'index'
                    if (counter[4] == 1'b0 && index == r) begin
                        if (c < SIZE) begin
                            array[r][(16-c)*BW-1 -: BW] <= i_data[(SIZE-c)*BW-1 -: BW];
                        end
                        else begin
                            // Write 0s to the invalid rows
                            array[r][(16-c)*BW-1 -: BW] <= {BW{1'b0}};
                        end
                    end
                    // MSB of counter == 1: column-wise write
                    // Access the array with the variable 'c'
                    // instead of the dynamic register value 'index'
                    else if (counter[4] == 1'b1 && index == c) begin
                        if (r < SIZE) begin
                            array[r][(16-c)*BW-1 -: BW] <= i_data[(SIZE-r)*BW-1 -: BW];
                        end
                        else begin
                            // Write 0s to the invalid rows
                            array[r][(16-c)*BW-1 -: BW] <= {BW{1'b0}};
                        end
                    end
                end
            end
        end
    end
endgenerate

// Column-wise data assignment
// 'col' is an array of the transposed data
// Column-wise read is available by accessing col[]
assign col[ 0] = {{array[0][16*BW-1:15*BW]},{array[1][16*BW-1:15*BW]},{array[2][16*BW-1:15*BW]},{array[3][16*BW-1:15*BW]},{array[4][16*BW-1:15*BW]},{array[5][16*BW-1:15*BW]},{array[6][16*BW-1:15*BW]},{array[7][16*BW-1:15*BW]},{array[8][16*BW-1:15*BW]},{array[9][16*BW-1:15*BW]},{array[10][16*BW-1:15*BW]},{array[11][16*BW-1:15*BW]},{array[12][16*BW-1:15*BW]},{array[13][16*BW-1:15*BW]},{array[14][16*BW-1:15*BW]},{array[15][16*BW-1:15*BW]}} ; 
assign col[ 1] = {{array[0][15*BW-1:14*BW]},{array[1][15*BW-1:14*BW]},{array[2][15*BW-1:14*BW]},{array[3][15*BW-1:14*BW]},{array[4][15*BW-1:14*BW]},{array[5][15*BW-1:14*BW]},{array[6][15*BW-1:14*BW]},{array[7][15*BW-1:14*BW]},{array[8][15*BW-1:14*BW]},{array[9][15*BW-1:14*BW]},{array[10][15*BW-1:14*BW]},{array[11][15*BW-1:14*BW]},{array[12][15*BW-1:14*BW]},{array[13][15*BW-1:14*BW]},{array[14][15*BW-1:14*BW]},{array[15][15*BW-1:14*BW]}} ; 
assign col[ 2] = {{array[0][14*BW-1:13*BW]},{array[1][14*BW-1:13*BW]},{array[2][14*BW-1:13*BW]},{array[3][14*BW-1:13*BW]},{array[4][14*BW-1:13*BW]},{array[5][14*BW-1:13*BW]},{array[6][14*BW-1:13*BW]},{array[7][14*BW-1:13*BW]},{array[8][14*BW-1:13*BW]},{array[9][14*BW-1:13*BW]},{array[10][14*BW-1:13*BW]},{array[11][14*BW-1:13*BW]},{array[12][14*BW-1:13*BW]},{array[13][14*BW-1:13*BW]},{array[14][14*BW-1:13*BW]},{array[15][14*BW-1:13*BW]}} ; 
assign col[ 3] = {{array[0][13*BW-1:12*BW]},{array[1][13*BW-1:12*BW]},{array[2][13*BW-1:12*BW]},{array[3][13*BW-1:12*BW]},{array[4][13*BW-1:12*BW]},{array[5][13*BW-1:12*BW]},{array[6][13*BW-1:12*BW]},{array[7][13*BW-1:12*BW]},{array[8][13*BW-1:12*BW]},{array[9][13*BW-1:12*BW]},{array[10][13*BW-1:12*BW]},{array[11][13*BW-1:12*BW]},{array[12][13*BW-1:12*BW]},{array[13][13*BW-1:12*BW]},{array[14][13*BW-1:12*BW]},{array[15][13*BW-1:12*BW]}} ; 
assign col[ 4] = {{array[0][12*BW-1:11*BW]},{array[1][12*BW-1:11*BW]},{array[2][12*BW-1:11*BW]},{array[3][12*BW-1:11*BW]},{array[4][12*BW-1:11*BW]},{array[5][12*BW-1:11*BW]},{array[6][12*BW-1:11*BW]},{array[7][12*BW-1:11*BW]},{array[8][12*BW-1:11*BW]},{array[9][12*BW-1:11*BW]},{array[10][12*BW-1:11*BW]},{array[11][12*BW-1:11*BW]},{array[12][12*BW-1:11*BW]},{array[13][12*BW-1:11*BW]},{array[14][12*BW-1:11*BW]},{array[15][12*BW-1:11*BW]}} ; 
assign col[ 5] = {{array[0][11*BW-1:10*BW]},{array[1][11*BW-1:10*BW]},{array[2][11*BW-1:10*BW]},{array[3][11*BW-1:10*BW]},{array[4][11*BW-1:10*BW]},{array[5][11*BW-1:10*BW]},{array[6][11*BW-1:10*BW]},{array[7][11*BW-1:10*BW]},{array[8][11*BW-1:10*BW]},{array[9][11*BW-1:10*BW]},{array[10][11*BW-1:10*BW]},{array[11][11*BW-1:10*BW]},{array[12][11*BW-1:10*BW]},{array[13][11*BW-1:10*BW]},{array[14][11*BW-1:10*BW]},{array[15][11*BW-1:10*BW]}} ; 
assign col[ 6] = {{array[0][10*BW-1: 9*BW]},{array[1][10*BW-1: 9*BW]},{array[2][10*BW-1: 9*BW]},{array[3][10*BW-1: 9*BW]},{array[4][10*BW-1: 9*BW]},{array[5][10*BW-1: 9*BW]},{array[6][10*BW-1: 9*BW]},{array[7][10*BW-1: 9*BW]},{array[8][10*BW-1: 9*BW]},{array[9][10*BW-1: 9*BW]},{array[10][10*BW-1: 9*BW]},{array[11][10*BW-1: 9*BW]},{array[12][10*BW-1: 9*BW]},{array[13][10*BW-1: 9*BW]},{array[14][10*BW-1: 9*BW]},{array[15][10*BW-1: 9*BW]}} ;
assign col[ 7] = {{array[0][ 9*BW-1: 8*BW]},{array[1][ 9*BW-1: 8*BW]},{array[2][ 9*BW-1: 8*BW]},{array[3][ 9*BW-1: 8*BW]},{array[4][ 9*BW-1: 8*BW]},{array[5][ 9*BW-1: 8*BW]},{array[6][ 9*BW-1: 8*BW]},{array[7][ 9*BW-1: 8*BW]},{array[8][ 9*BW-1: 8*BW]},{array[9][ 9*BW-1: 8*BW]},{array[10][ 9*BW-1: 8*BW]},{array[11][ 9*BW-1: 8*BW]},{array[12][ 9*BW-1: 8*BW]},{array[13][ 9*BW-1: 8*BW]},{array[14][ 9*BW-1: 8*BW]},{array[15][ 9*BW-1: 8*BW]}} ;
assign col[ 8] = {{array[0][ 8*BW-1: 7*BW]},{array[1][ 8*BW-1: 7*BW]},{array[2][ 8*BW-1: 7*BW]},{array[3][ 8*BW-1: 7*BW]},{array[4][ 8*BW-1: 7*BW]},{array[5][ 8*BW-1: 7*BW]},{array[6][ 8*BW-1: 7*BW]},{array[7][ 8*BW-1: 7*BW]},{array[8][ 8*BW-1: 7*BW]},{array[9][ 8*BW-1: 7*BW]},{array[10][ 8*BW-1: 7*BW]},{array[11][ 8*BW-1: 7*BW]},{array[12][ 8*BW-1: 7*BW]},{array[13][ 8*BW-1: 7*BW]},{array[14][ 8*BW-1: 7*BW]},{array[15][ 8*BW-1: 7*BW]}} ; 
assign col[ 9] = {{array[0][ 7*BW-1: 6*BW]},{array[1][ 7*BW-1: 6*BW]},{array[2][ 7*BW-1: 6*BW]},{array[3][ 7*BW-1: 6*BW]},{array[4][ 7*BW-1: 6*BW]},{array[5][ 7*BW-1: 6*BW]},{array[6][ 7*BW-1: 6*BW]},{array[7][ 7*BW-1: 6*BW]},{array[8][ 7*BW-1: 6*BW]},{array[9][ 7*BW-1: 6*BW]},{array[10][ 7*BW-1: 6*BW]},{array[11][ 7*BW-1: 6*BW]},{array[12][ 7*BW-1: 6*BW]},{array[13][ 7*BW-1: 6*BW]},{array[14][ 7*BW-1: 6*BW]},{array[15][ 7*BW-1: 6*BW]}} ; 
assign col[10] = {{array[0][ 6*BW-1: 5*BW]},{array[1][ 6*BW-1: 5*BW]},{array[2][ 6*BW-1: 5*BW]},{array[3][ 6*BW-1: 5*BW]},{array[4][ 6*BW-1: 5*BW]},{array[5][ 6*BW-1: 5*BW]},{array[6][ 6*BW-1: 5*BW]},{array[7][ 6*BW-1: 5*BW]},{array[8][ 6*BW-1: 5*BW]},{array[9][ 6*BW-1: 5*BW]},{array[10][ 6*BW-1: 5*BW]},{array[11][ 6*BW-1: 5*BW]},{array[12][ 6*BW-1: 5*BW]},{array[13][ 6*BW-1: 5*BW]},{array[14][ 6*BW-1: 5*BW]},{array[15][ 6*BW-1: 5*BW]}} ; 
assign col[11] = {{array[0][ 5*BW-1: 4*BW]},{array[1][ 5*BW-1: 4*BW]},{array[2][ 5*BW-1: 4*BW]},{array[3][ 5*BW-1: 4*BW]},{array[4][ 5*BW-1: 4*BW]},{array[5][ 5*BW-1: 4*BW]},{array[6][ 5*BW-1: 4*BW]},{array[7][ 5*BW-1: 4*BW]},{array[8][ 5*BW-1: 4*BW]},{array[9][ 5*BW-1: 4*BW]},{array[10][ 5*BW-1: 4*BW]},{array[11][ 5*BW-1: 4*BW]},{array[12][ 5*BW-1: 4*BW]},{array[13][ 5*BW-1: 4*BW]},{array[14][ 5*BW-1: 4*BW]},{array[15][ 5*BW-1: 4*BW]}} ; 
assign col[12] = {{array[0][ 4*BW-1: 3*BW]},{array[1][ 4*BW-1: 3*BW]},{array[2][ 4*BW-1: 3*BW]},{array[3][ 4*BW-1: 3*BW]},{array[4][ 4*BW-1: 3*BW]},{array[5][ 4*BW-1: 3*BW]},{array[6][ 4*BW-1: 3*BW]},{array[7][ 4*BW-1: 3*BW]},{array[8][ 4*BW-1: 3*BW]},{array[9][ 4*BW-1: 3*BW]},{array[10][ 4*BW-1: 3*BW]},{array[11][ 4*BW-1: 3*BW]},{array[12][ 4*BW-1: 3*BW]},{array[13][ 4*BW-1: 3*BW]},{array[14][ 4*BW-1: 3*BW]},{array[15][ 4*BW-1: 3*BW]}} ; 
assign col[13] = {{array[0][ 3*BW-1: 2*BW]},{array[1][ 3*BW-1: 2*BW]},{array[2][ 3*BW-1: 2*BW]},{array[3][ 3*BW-1: 2*BW]},{array[4][ 3*BW-1: 2*BW]},{array[5][ 3*BW-1: 2*BW]},{array[6][ 3*BW-1: 2*BW]},{array[7][ 3*BW-1: 2*BW]},{array[8][ 3*BW-1: 2*BW]},{array[9][ 3*BW-1: 2*BW]},{array[10][ 3*BW-1: 2*BW]},{array[11][ 3*BW-1: 2*BW]},{array[12][ 3*BW-1: 2*BW]},{array[13][ 3*BW-1: 2*BW]},{array[14][ 3*BW-1: 2*BW]},{array[15][ 3*BW-1: 2*BW]}} ; 
assign col[14] = {{array[0][ 2*BW-1: 1*BW]},{array[1][ 2*BW-1: 1*BW]},{array[2][ 2*BW-1: 1*BW]},{array[3][ 2*BW-1: 1*BW]},{array[4][ 2*BW-1: 1*BW]},{array[5][ 2*BW-1: 1*BW]},{array[6][ 2*BW-1: 1*BW]},{array[7][ 2*BW-1: 1*BW]},{array[8][ 2*BW-1: 1*BW]},{array[9][ 2*BW-1: 1*BW]},{array[10][ 2*BW-1: 1*BW]},{array[11][ 2*BW-1: 1*BW]},{array[12][ 2*BW-1: 1*BW]},{array[13][ 2*BW-1: 1*BW]},{array[14][ 2*BW-1: 1*BW]},{array[15][ 2*BW-1: 1*BW]}} ;
assign col[15] = {{array[0][ 1*BW-1: 0*BW]},{array[1][ 1*BW-1: 0*BW]},{array[2][ 1*BW-1: 0*BW]},{array[3][ 1*BW-1: 0*BW]},{array[4][ 1*BW-1: 0*BW]},{array[5][ 1*BW-1: 0*BW]},{array[6][ 1*BW-1: 0*BW]},{array[7][ 1*BW-1: 0*BW]},{array[8][ 1*BW-1: 0*BW]},{array[9][ 1*BW-1: 0*BW]},{array[10][ 1*BW-1: 0*BW]},{array[11][ 1*BW-1: 0*BW]},{array[12][ 1*BW-1: 0*BW]},{array[13][ 1*BW-1: 0*BW]},{array[14][ 1*BW-1: 0*BW]},{array[15][ 1*BW-1: 0*BW]}} ;


endmodule

module TPMEM2
#( parameter BW = 12,
   parameter SIZE = 12 )
    // SIZE stands for the number of elements in the input vector
    // BW stays at 12 - the matlab code expects 12-bit integers

(  input        [SIZE*BW-1:0] i_data,
   input                      i_enable,
   input                      i_clk,
   input                      i_Reset,
   output reg   [SIZE*BW-1:0] o_data
);

reg [5-1:0]         counter;
reg [SIZE*BW-1:0]   array   [SIZE-1:0];      // Array to store data
reg [SIZE*BW-1:0]   data_out;                // Data that has been read       

wire [SIZE*BW-1:0]  col     [SIZE-1:0];      // Column-wise data
wire [4-1:0]        index = counter[4-1:0];  // Address

// Counter and IO 
always @(posedge i_clk) begin
    if (!i_Reset) begin
        counter <= 5'b0;
        o_data <= {SIZE*BW{1'b0}};
    end
    else begin
        o_data <= data_out;
        if (i_enable)
            counter <= counter + 5'b1;
    end
end

// Read the data
always @(*) begin
    if (index < SIZE) begin
        // Valid index (0 ~ SIZE-1)
        if (counter[4] == 1'b0) begin
            // MSB of counter == 0: Row-wise read
            data_out = array[index];
        end
        else begin
            // MSB of counter == 1: Column-wise read
            data_out = col[index];
        end
    end
    else begin
        // Invalid index
        // Output 0 when index is invalid
        data_out = {SIZE*BW{1'b0}};
    end
end

// Write the input data
genvar r, c;
generate
    for (r = 0; r < SIZE; r = r + 1) begin : gen_write_row
        for (c = 0; c < SIZE; c = c + 1) begin : gen_write_col
            always @(posedge i_clk) begin
                if (~i_Reset) begin
                    // Reset the array
                    array[r][(SIZE-c)*BW-1 -: BW] <= {BW{1'b0}};
                end
                else if (i_enable && index < SIZE) begin
                    // MSB of counter == 0: Row-wise write
                    // Access the array with the variable 'c'
                    // instead of the dynamic register value 'index'
                    if (counter[4] == 1'b0 && index == r) begin
                        array[r][(SIZE-c)*BW-1 -: BW] <= i_data[(SIZE-c)*BW-1 -: BW];
                    end
                    // MSB of counter == 1: column-wise write
                    // Access the array with the variable 'c'
                    // instead of the dynamic register value 'index'
                    else if (counter[4] == 1'b1 && index == c) begin
                        array[r][(SIZE-c)*BW-1 -: BW] <= i_data[(SIZE-r)*BW-1 -: BW];
                    end
                end
            end
        end
    end
endgenerate

// Column-wise data assignment
// 'col' is an array of the transposed data
// Column-wise read is available by accessing col[]
generate
    for (c = 0; c < SIZE; c = c + 1) begin : gen_col
        for (r = 0; r < SIZE; r = r + 1) begin : gen_row
            assign col[c][(SIZE-r)*BW-1 -: BW] = array[r][(SIZE-c)*BW-1 -: BW];
        end
    end
endgenerate

endmodule

`timescale 1ns / 10ps

module rflp16384x128mx16(
    output reg [127:0] DO,
    input [127:0] DIN,
    input [9:0] RA,
    input [3:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array
    (* ram_style = "block" *) reg [127:0] array [0:16383];
    
    // Concatenate Row Address and Column Address to form the full 14-bit address
    wire [13:0] addr = {RA, CA};

    // Synchronous read and write operations for BRAM inference
    always @(posedge CLK) begin
        if (!NCE) begin
            if (!NWRT) begin
                // Write operation
                array[addr] <= DIN;
            end else begin
                // Read operation
                DO <= array[addr];
            end
        end
    end

endmodule

`timescale 1ns / 10ps

module rflp16384x192mx16(
    output reg [191:0] DO,
    input [191:0] DIN,
    input [9:0] RA,
    input [3:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array 
    (* ram_style = "block" *) reg [191:0] array [0:16383];
    
    // Concatenate Row Address and Column Address to form the full 14-bit address
    wire [13:0] addr = {RA, CA};

    // Synchronous read and write operations for BRAM inference
    always @(posedge CLK) begin
        if (!NCE) begin
            if (!NWRT) begin
                // Write operation
                array[addr] <= DIN;
            end else begin
                // Read operation
                DO <= array[addr];
            end
        end
    end

endmodule