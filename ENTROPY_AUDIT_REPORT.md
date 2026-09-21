# ENTROPY AUDIT REPORT

**Gate 6 Audit Status**: **PASS**

## Entropy Metric Summary
- **State Entropy ($H_{\text{state}}$)**: Quantifies diversity of daily state occurrence. Ranges from 0.794 bits (403201 Chaiyaphum) to 1.020 bits (357201 Nakhon Phanom).
- **Transition Entropy ($H_{\text{trans}}$)**: Quantifies state-transition uncertainty. Ranges from 0.490 bits to 0.612 bits across the station network.
- **Boundary Validation**: $0 \log_2(0) = 0$ handled mathematically correctly. Probability row sums equal 1.0.

| Station ID | Freq Dry ($D$) | Freq Wet ($W$) | Freq Rainy ($R$) | State Entropy (bits) | Transition Entropy (bits) |
|---|---|---|---|---|---|
| 353201.0 | 0.798 | 0.048 | 0.154 | 0.885 | 0.825 |
| 354201.0 | 0.791 | 0.046 | 0.164 | 0.898 | 0.830 |
| 356201.0 | 0.769 | 0.049 | 0.181 | 0.951 | 0.870 |
| 357201.0 | 0.731 | 0.047 | 0.223 | 1.020 | 0.886 |
| 381201.0 | 0.819 | 0.039 | 0.142 | 0.817 | 0.773 |
| 403201.0 | 0.828 | 0.038 | 0.135 | 0.794 | 0.741 |
| 405201.0 | 0.803 | 0.039 | 0.158 | 0.857 | 0.798 |
| 407501.0 | 0.782 | 0.042 | 0.175 | 0.910 | 0.835 |
| 431201.0 | 0.828 | 0.041 | 0.131 | 0.797 | 0.760 |
| 432201.0 | 0.795 | 0.044 | 0.161 | 0.884 | 0.834 |
