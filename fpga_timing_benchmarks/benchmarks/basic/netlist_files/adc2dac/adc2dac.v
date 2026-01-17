module adc_to_dac(
    input clk,
    input [7:0] adc_data,
    output reg [7:0] dac_data
);
     reg [7:0] temp;

     always @(posedge clk) begin
        temp <= adc_data;
        dac_data <= temp; //Simple data processing
     end

endmodule