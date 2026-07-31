module clk_skew (
    input wire clk,
    input wire rstn,
    input wire d_in,
    output reg capture
);
    reg launch;

    // Launch flip-flop
    always @(posedge clk) begin
        if (!rstn) begin
            launch <= 1'b0;
        end
        else begin
            launch <= d_in;
        end
    end

    // Capture flip-flop
    always @(posedge clk) begin
        if (!rstn) begin
            capture <= 1'b0;
        end
        else begin
            capture <= launch;
        end
    end
endmodule