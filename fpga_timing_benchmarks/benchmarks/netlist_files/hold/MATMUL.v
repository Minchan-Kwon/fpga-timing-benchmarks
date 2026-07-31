///////////////////////////////////////////////////
// 64x64 matrix multiplier
// Author: Minchan Kwon
///////////////////////////////////////////////////

module MATMUL(
    input         clk,
    input         rstn,
    input         start,
    output        done,
    input  [7:0]  ext_mem_a_din,
    input         ext_mem_a_nwrt,
    input  [31:0] ext_mem_b_din,
    input         ext_mem_b_nwrt,
    output [21:0] ext_mem_c_do
);

    // Controller signals
    wire rNWRT, rNCE;
    wire wNWRT, wNCE;
    wire DELAY_EN;
    wire MUX_MAC;
    wire [1:0]  MUX_C_sel;

    wire [11:0] ADDR_A;
    wire [9:0]  ADDR_B;
    wire [11:0] ADDR_C;

    // SRAM Data outputs
    wire [7:0]  mem_a_q;
    wire [31:0] mem_b_q;

    // Input register outputs
    wire [7:0]  reg_a_out;
    wire [31:0] reg_b_out;

    // MAC outputs
    wire [21:0] mac0_out;
    wire [21:0] mac1_out;
    wire [21:0] mac2_out;
    wire [21:0] mac3_out;

    // Delay line wires
    wire [21:0] mac1_d0;
    wire [21:0] mac2_d0, mac2_d1;
    wire [21:0] mac3_d0, mac3_d1, mac3_d2;

    // Final MUX output to SRAM C
    wire [21:0] mux_c_out;

    // Controller
    controller CONTROL(
        .clk(clk),
        .rstn(rstn), 
        .start(start),
        .rNWRT(rNWRT),
        .rNCE(rNCE),
        .wNWRT(wNWRT),
        .wNCE(wNCE),
        .DELAY_EN(DELAY_EN),
        .MUX_MAC(MUX_MAC),
        .MUX_C(MUX_C_sel),
        .ADDR_A(ADDR_A),
        .ADDR_B(ADDR_B),
        .ADDR_C(ADDR_C),
        .DONE(done)
    );

    // MEM_A: RA 10-bit, CA 2-bit
    rflp4096x8mx4 MEM_A(
        .CLK(clk),
        .NCE(rNCE),
        .NWRT(rNWRT & ext_mem_a_nwrt), 
        .RA(ADDR_A[11:2]), 
        .CA(ADDR_A[1:0]), 
        .DIN(ext_mem_a_din),
        .DO(mem_a_q)
    );

    // MEM_B: RA 8-bit, CA 2-bit
    rflp1024x32mx4 MEM_B(
        .CLK(clk), 
        .NCE(rNCE), 
        .NWRT(rNWRT & ext_mem_b_nwrt), 
        .RA(ADDR_B[9:2]), 
        .CA(ADDR_B[1:0]), 
        .DIN(ext_mem_b_din),
        .DO(mem_b_q)
    );

    // MEM_C: RA 10-bit, CA 2-bit
    rflp4096x22mx4 MEM_C(
        .CLK(clk), 
        .NCE(wNCE), 
        .NWRT(wNWRT), 
        .RA(ADDR_C[11:2]), 
        .CA(ADDR_C[1:0]), 
        .DIN(mux_c_out), 
        .DO(ext_mem_c_do)
    );

    // Input Registers
    DFF_8b  A_IN_REG(
        .clk(clk), 
        .rstn(rstn), 
        .d(mem_a_q), 
        .q(reg_a_out)
    );

    DFF_32b B_IN_REG(
        .clk(clk),
        .rstn(rstn), 
        .d(mem_b_q), 
        .q(reg_b_out)
    );

    // MAC Units
    MAC M0(.clk(clk), .rstn(rstn), .sel(MUX_MAC), .A(reg_a_out), .B(reg_b_out[31:24]), .C(mac0_out));
    MAC M1(.clk(clk), .rstn(rstn), .sel(MUX_MAC), .A(reg_a_out), .B(reg_b_out[23:16]), .C(mac1_out));
    MAC M2(.clk(clk), .rstn(rstn), .sel(MUX_MAC), .A(reg_a_out), .B(reg_b_out[15:8]),  .C(mac2_out));
    MAC M3(.clk(clk), .rstn(rstn), .sel(MUX_MAC), .A(reg_a_out), .B(reg_b_out[7:0]),   .C(mac3_out));

    // MAC Delay Line
    DFF_22b M1_DELAY_0(.clk(clk), .rstn(rstn), .en(DELAY_EN), .d(mac1_out), .q(mac1_d0));

    DFF_22b M2_DELAY_0(.clk(clk), .rstn(rstn), .en(DELAY_EN), .d(mac2_out), .q(mac2_d0));
    DFF_22b M2_DELAY_1(.clk(clk), .rstn(rstn), .en(DELAY_EN), .d(mac2_d0),  .q(mac2_d1));

    DFF_22b M3_DELAY_0(.clk(clk), .rstn(rstn), .en(DELAY_EN), .d(mac3_out), .q(mac3_d0));
    DFF_22b M3_DELAY_1(.clk(clk), .rstn(rstn), .en(DELAY_EN), .d(mac3_d0),  .q(mac3_d1));
    DFF_22b M3_DELAY_2(.clk(clk), .rstn(rstn), .en(DELAY_EN), .d(mac3_d1),  .q(mac3_d2));

    // 4-to-1 MUX
    mux_4to1 MUX_C(
        .i0(mac0_out),
        .i1(mac1_d0), 
        .i2(mac2_d1),
        .i3(mac3_d2),
        .sel(MUX_C_sel), 
        .out(mux_c_out)
    );

endmodule

module mux_4to1(
    input  [21:0] i0,
    input  [21:0] i1,
    input  [21:0] i2,
    input  [21:0] i3,
    input  [1:0]  sel,
    output [21:0] out 
);
    assign out = (sel == 2'b00) ? i0 :
                 (sel == 2'b01) ? i1 :
                 (sel == 2'b10) ? i2 : i3;
endmodule

module MAC(
    input         clk,
    input         rstn,
    input         sel,
    input   [7:0] A,
    input   [7:0] B,
    output [21:0] C
);
    wire [21:0] p_product;
    wire [21:0] mux_out;
    reg  [21:0] acc;

    assign p_product = A * B;
    assign mux_out = (sel) ? acc : 22'b0;

    always @(posedge clk) begin
        if (!rstn) begin
            acc <= 22'b0;
        end
        else begin
            acc <= mux_out + p_product;
        end
    end

    assign C = acc;
endmodule

module controller(
    input         clk,
    input         rstn,
    input         start,
    output reg    rNWRT, rNCE,
    output reg    wNWRT, wNCE,
    output reg    DELAY_EN,
    output reg    MUX_MAC,
    output  [1:0] MUX_C,
    output [11:0] ADDR_A,
    output  [9:0] ADDR_B,
    output [11:0] ADDR_C,
    output reg    DONE
);
    reg RUN;
    reg [16:0] counter;

    // Reset and RUN Logic
    always @(posedge clk) begin
        if (!rstn) begin
            counter <= 17'b0;
            rNWRT <= 1'b1;
            rNCE <= 1'b1;
            wNWRT <= 1'b1;
            wNCE <= 1'b1;
            DELAY_EN <= 1'b0;   // DFF Enable
            MUX_MAC <= 1'b0;    // 0: Reset, 1: Accumulate
            RUN <= 1'b0;
            DONE <= 1'b0;
        end
        else begin
            // MM just started
            if (start) begin
                counter <= 17'b0;
                RUN <= 1'b1;
                DONE <= 1'b0;
                rNCE <= 1'b0;
                rNWRT <= 1'b1;
                wNWRT <= 1'b1;
                wNCE <= 1'b1;
                DELAY_EN <= 1'b0;
                MUX_MAC <= 1'b1;
            end
            // MM is running
            else if (RUN) begin
                // Increment Counter
                counter <= counter + 1'b1;

                // Disable Read
                if (counter == 17'd65535) begin
                    rNCE <= 1'b1;
                end

                // Don't write in the beginning
                if (counter[16:6]==11'b000_0000_0000) begin
                    if (counter[5:0] == 6'b00_0001) MUX_MAC <= 1'b0;
                    else MUX_MAC <= 1'b1;
                    wNWRT <= 1'b1;
                    wNCE <= 1'b1;
                    DELAY_EN <= 1'b0;
                end
                // Write, MUX_MAC, Delay Line Enable Logic
                else begin
                    if (counter[5:0] == 6'b00_0001) begin
                        MUX_MAC <= 1'b0;    // Reset accumulation to 0
                        wNWRT <= 1'b0;
                        wNCE <= 1'b0;
                        DELAY_EN <= 1'b1;
                    end
                    else if (counter[5:0] == 6'b00_0010) begin
                        MUX_MAC <= 1'b1;
                        wNWRT <= 1'b0;
                        wNCE <= 1'b0;
                        DELAY_EN <= 1'b1;
                    end
                    else if (counter[5:0] == 6'b00_0011) begin
                        MUX_MAC <= 1'b1;
                        wNWRT <= 1'b0;
                        wNCE <= 1'b0;
                        DELAY_EN <= 1'b1;
                    end
                    else if (counter[5:0] == 6'b00_0100) begin
                        MUX_MAC <= 1'b1;
                        wNWRT <= 1'b0;
                        wNCE <= 1'b0;
                        DELAY_EN <= 1'b1;
                    end
                    else begin
                        MUX_MAC <= 1'b1;
                        wNWRT <= 1'b1;
                        wNCE <= 1'b1;
                        DELAY_EN <= 1'b0;
                    end
                end

                // DONE Logic
                if (counter == 17'd65541) begin 
                    RUN <= 1'b0;
                    DONE <= 1'b1;
                    counter <= 17'b0;
                    wNWRT <= 1'b1;
                    wNCE <= 1'b1;
                    DELAY_EN <= 1'b0;
                    MUX_MAC <= 1'b0;
                end
            end
            // Reset is off, but haven't started yet
            else begin
                DONE <= 1'b0;
                counter <= 17'b0;
            end
        end
    end

    // Address Logic
    assign ADDR_A = {counter[15:10], counter[5:0]};
    assign ADDR_B = {counter[5:0], counter[9:6]};

    wire [9:0] c_upper = counter[15:6] - 10'b1;
    wire       c_offset_h = ~counter[1];
    wire       c_offset_l = counter[0];
    assign ADDR_C = {c_upper, c_offset_h, c_offset_l};

    // MUX Select Logic 
    // 4-to-1 MUX
    assign MUX_C = {c_offset_h, c_offset_l};

endmodule

module DFF_8b(
    input            clk,
    input            rstn,
    input      [7:0] d,
    output reg [7:0] q
);
    always @(posedge clk) begin
        if (!rstn) begin
            q <= 8'b0;
        end
        else begin
            q <= d;
        end
    end

endmodule

module DFF_22b(
    input             clk,
    input             rstn,
    input             en,
    input      [21:0] d,
    output reg [21:0] q
);
    always @(posedge clk) begin
        if (!rstn) begin
            q <= 22'b0;
        end
        else if (en) begin
            q <= d;
        end
    end

endmodule

module DFF_32b(
    input             clk,
    input             rstn,
    input      [31:0] d,
    output reg [31:0] q
);
    always @(posedge clk) begin
        if (!rstn) begin
            q <= 32'b0;
        end
        else begin
            q <= d;
        end
    end

endmodule

module rflp1024x32mx4(
    output reg [31:0] DO,
    input [31:0] DIN,
    input [7:0] RA,
    input [1:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array declaration 
    (* ram_style = "block" *) reg [31:0] array [0:1023];
    
    // Concatenate Row Address and Column Address to form the 10-bit address
    wire [9:0] addr = {RA, CA};

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

module rflp4096x8mx4(
    output reg [7:0] DO,
    input [7:0] DIN,
    input [9:0] RA,
    input [1:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array declaration
    (* ram_style = "block" *) reg [7:0] array [0:4095];
    
    // Concatenate Row Address and Column Address to form the 12-bit address
    wire [11:0] addr = {RA, CA};

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

module rflp4096x22mx4(
    output reg [21:0] DO,
    input [21:0] DIN,
    input [9:0] RA,
    input [1:0] CA,
    input NWRT,
    input NCE,
    input CLK
);

    // BRAM array declaration 
    (* ram_style = "block" *) reg [21:0] array [0:4095];
    
    // Concatenate Row Address and Column Address to form the 12-bit address
    wire [11:0] addr = {RA, CA};

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