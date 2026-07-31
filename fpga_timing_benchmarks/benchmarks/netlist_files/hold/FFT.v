///////////////////////////////////////////////////
// 8-point pipelined FFT module
// Author: Minchan Kwon
///////////////////////////////////////////////////

module FFT(
    input             clk,
    input             rstn,
    input      [31:0] in,
    output reg [31:0] out
);
    // Control Unit Wires
    wire [1:0] TF_MUX_1;
    wire       TF_MUX_2;
    wire       BU_MUX_1, BU_MUX_2, BU_MUX_3;

    // Wires for inter-stage connections
    wire signed [31:0] S1_SHFT_IN, S2_SHFT_IN, S3_SHFT_IN;
    
    wire signed [31:0] BU_S1_C1, BU_S1_C2;
    wire signed [31:0] BU_S2_C1, BU_S2_C2;
    wire signed [31:0] BU_S3_C1, BU_S3_C2;

    wire signed [31:0] S1_CM_IN, S2_CM_IN;  // Input to the multiplier
    wire signed [31:0] S1_CM_OUT, S2_CM_OUT;  // Output from the multiplier
    wire signed [31:0] S3_OUT;  // Output from stage 3

    // Regs
    reg signed [31:0] TF_1, TF_2;  // Twiddle factors

    // Stage 1 shift registers and input buffer
    reg signed [31:0] S1_SHFT1, S1_SHFT2, S1_SHFT3, S1_SHFT4;
    reg signed [31:0] S1_BUF;
    
    // Stage 2 shift registers and input buffer
    reg signed [31:0] S2_SHFT1, S2_SHFT2;
    reg signed [31:0] S2_BUF;
    
    // Stage 3 shift register and input buffer
    reg signed [31:0] S3_SHFT1;
    reg signed [31:0] S3_BUF;

    // CONTROL UNIT
    ControlUnit CONTROL(
        .clk(clk),
        .rstn(rstn),
        .TF_MUX_1(TF_MUX_1),
        .TF_MUX_2(TF_MUX_2),
        .BU_MUX_1(BU_MUX_1),
        .BU_MUX_2(BU_MUX_2),
        .BU_MUX_3(BU_MUX_3)
    );

    // ================= STAGE 1 =================
    // Modules
    ButterflyUnit BU_S1(
        .A(S1_SHFT4),
        .B(S1_BUF),
        .C1(BU_S1_C1),
        .C2(BU_S1_C2)
    );

    ComplexMultiplier CM_S1(
        .C(S1_CM_IN),
        .T(TF_1),
        .O(S1_CM_OUT)
    );

    // Multiplexer for shift registers and multiplier
    assign S1_SHFT_IN = BU_MUX_1 ? BU_S1_C2 : S1_BUF;
    assign S1_CM_IN   = BU_MUX_1 ? BU_S1_C1 : S1_SHFT4;

    // Buffer and shift registers
    always @(posedge clk) begin
        if (!rstn) begin
            S1_SHFT1 <= 32'b0;
            S1_SHFT2 <= 32'b0;
            S1_SHFT3 <= 32'b0;
            S1_SHFT4 <= 32'b0;
            S1_BUF   <= 32'b0;
        end
        else begin
            S1_SHFT1 <= S1_SHFT_IN;
            S1_SHFT2 <= S1_SHFT1;
            S1_SHFT3 <= S1_SHFT2;
            S1_SHFT4 <= S1_SHFT3;
            S1_BUF   <= in;
        end
    end

    // Twiddle factor multiplexer
    always @(*) begin
        case(TF_MUX_1)
            2'b00:   TF_1 = 32'h40000000;
            2'b01:   TF_1 = 32'h2D41D2BF;
            2'b10:   TF_1 = 32'h0000C000;
            2'b11:   TF_1 = 32'hD2BFD2BF;
            default: TF_1 = 32'h40000000;
        endcase
    end

    // ================= STAGE 2 =================
    // Modules
    ButterflyUnit BU_S2(
        .A(S2_SHFT2),
        .B(S2_BUF),
        .C1(BU_S2_C1),
        .C2(BU_S2_C2)
    );
    
    ComplexMultiplier CM_S2(
        .C(S2_CM_IN),
        .T(TF_2),
        .O(S2_CM_OUT)
    );

    // Multiplexer for shift registers and multiplier
    assign S2_SHFT_IN = BU_MUX_2 ? BU_S2_C2 : S2_BUF;
    assign S2_CM_IN   = BU_MUX_2 ? BU_S2_C1 : S2_SHFT2;

    // Buffer and shift registers
    always @(posedge clk) begin
        if (!rstn) begin
            S2_SHFT1 <= 32'b0;
            S2_SHFT2 <= 32'b0;
            S2_BUF   <= 32'b0;
        end
        else begin
            S2_SHFT1 <= S2_SHFT_IN;
            S2_SHFT2 <= S2_SHFT1;
            S2_BUF   <= BU_MUX_1 ? BU_S1_C1 : S1_CM_OUT;  // Bypass
        end
    end    

    // Twiddle factor multiplexer
    always @(*) begin
        case(TF_MUX_2)
            1'b0:    TF_2 = 32'h40000000;
            1'b1:    TF_2 = 32'h0000C000;
            default: TF_2 = 32'h40000000;
        endcase
    end

    // ================= STAGE 3 =================
    // Modules
    ButterflyUnit BU_S3(
        .A(S3_SHFT1),
        .B(S3_BUF),
        .C1(BU_S3_C1),
        .C2(BU_S3_C2)
    );

    // Multiplexer for shift registers and multiplier
    assign S3_SHFT_IN = BU_MUX_3 ? BU_S3_C2 : S3_BUF;
    assign S3_OUT     = BU_MUX_3 ? BU_S3_C1 : S3_SHFT1;

    // Buffer, shift registers, and final output
    always @(posedge clk) begin
        if (!rstn) begin
            S3_SHFT1 <= 32'b0;
            S3_BUF   <= 32'b0;
            out      <= 32'b0;
        end
        else begin
            S3_SHFT1 <= S3_SHFT_IN;
            S3_BUF   <= BU_MUX_2 ? BU_S2_C1 : S2_CM_OUT;  // Bypass
            out      <= S3_OUT;
        end
    end

endmodule

module ControlUnit(
    input            clk,
    input            rstn,
    output reg [1:0] TF_MUX_1,
    output reg       TF_MUX_2,
    output reg       BU_MUX_1,
    output reg       BU_MUX_2,
    output reg       BU_MUX_3
);
    reg [2:0] counter;
    reg       RUN;

    wire [2:0] next_counter = (RUN) ? (counter + 1'b1) : counter;

    always @(posedge clk) begin
        if (!rstn) begin
            counter <= 3'b0;
            RUN     <= 1'b0;

            BU_MUX_1 <= 1'b0;
            BU_MUX_2 <= 1'b1;     
            BU_MUX_3 <= 1'b0;
            TF_MUX_1 <= 2'b00;
            TF_MUX_2 <= 1'b0;
        end
        else begin
            RUN     <= 1'b1;
            counter <= next_counter;

            // MUX control signals
            BU_MUX_1 <= next_counter[2];
            BU_MUX_2 <= ~(next_counter[1] ^ next_counter[0]);
            BU_MUX_3 <= next_counter[0];

            TF_MUX_1 <= {2{~next_counter[2]}} & next_counter[1:0]; 
            TF_MUX_2 <= next_counter[1];
        end
    end

endmodule

module ComplexMultiplier(
    input  [31:0] C,
    input  [31:0] T,
    output [31:0] O
);
    wire signed [32:0] O_R, O_I;
    wire signed [15:0] C_R, C_I, T_R, T_I;

    // Assign Real/Imaginary Bits 
    assign {C_R, C_I} = C;
    assign {T_R, T_I} = T;

    // Multiplication
    assign O_R = C_R*T_R - C_I*T_I;  // Real
    assign O_I = C_R*T_I + C_I*T_R;  // Imaginary

    assign O = {O_R[29:14], O_I[29:14]};
endmodule

module ButterflyUnit(
    input  [31:0] A,
    input  [31:0] B,
    output [31:0] C1,
    output [31:0] C2
);  
    wire signed [16:0] C1_R_SUM, C1_I_SUM;
    wire signed [16:0] C2_R_SUM, C2_I_SUM;

    // C1: Addition
    assign C1_R_SUM = $signed(A[31:16]) + $signed(B[31:16]);
    assign C1_I_SUM = $signed(A[15:0]) + $signed(B[15:0]);

    // C2: Subtraction
    assign C2_R_SUM = $signed(A[31:16]) - $signed(B[31:16]);
    assign C2_I_SUM = $signed(A[15:0]) - $signed(B[15:0]);

    // Truncate
    assign C1 = {C1_R_SUM[16:1], C1_I_SUM[16:1]};
    assign C2 = {C2_R_SUM[16:1], C2_I_SUM[16:1]};
endmodule