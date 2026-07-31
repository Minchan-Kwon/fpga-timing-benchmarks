module clk_latency (
    input      clk,
    input      clk_late,
    input      rstn,
    input      d_in,
    output reg capture
);
    reg launch;

    // Launch FF
    always @(posedge clk) begin
        if (!rstn) begin
            launch <= 1'b0;
        end
        else begin
            launch <= d_in;
        end
    end

    // Capture FF
    always @(posedge clk_late) begin
        if (!rstn) begin
            capture <= 1'b0;
        end
        else begin
            capture <= launch;
        end
    end
endmodule