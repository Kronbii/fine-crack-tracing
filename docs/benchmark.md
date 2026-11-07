Synthetic benchmark: 25 images per preset, 768 x 768 px, tolerance 3 px.

| preset | tracer | F1 | mean dist (px) | length error | width error (px) | junctions found | ms |
|---|---|---|---|---|---|---|---|
| clean | v0.1 ORB, y-order | 0.15 | 6.48 | -65.7% | – | – | 1757 |
| clean | v0.1 Shi-Tomasi + MST | 0.28 | 5.51 | -55.6% | – | – | 16 |
| clean | plain skeleton | 1.00 | 0.38 | +2.0% | 0.30 | 92% | 43 |
| clean | v1 corners | 1.00 | 0.30 | -0.3% | 0.28 | 92% | 53 |
| clean | v1 auto | 1.00 | 0.31 | -0.3% | 0.28 | 92% | 53 |
| ragged | v0.1 ORB, y-order | 0.12 | 6.73 | -50.0% | – | – | 9 |
| ragged | v0.1 Shi-Tomasi + MST | 0.19 | 6.19 | -51.5% | – | – | 10 |
| ragged | plain skeleton | 0.95 | 1.06 | +20.8% | 1.22 | 95% | 72 |
| ragged | v1 corners | 0.99 | 0.58 | +0.8% | 0.98 | 87% | 62 |
| ragged | v1 auto | 0.99 | 0.50 | +0.1% | 0.95 | 89% | 62 |
| broken | v0.1 ORB, y-order | 0.07 | 4.77 | -79.8% | – | – | 8 |
| broken | v0.1 Shi-Tomasi + MST | 0.18 | 4.44 | -74.2% | – | – | 12 |
| broken | plain skeleton | 0.92 | 0.52 | -10.0% | 0.34 | 78% | 47 |
| broken | v1 corners | 0.95 | 0.52 | -5.3% | 0.46 | 66% | 64 |
| broken | v1 auto | 0.95 | 0.56 | -4.0% | 0.47 | 70% | 56 |
| realistic | v0.1 ORB, y-order | 0.06 | 6.00 | -77.8% | – | – | 9 |
| realistic | v0.1 Shi-Tomasi + MST | 0.16 | 5.96 | -62.3% | – | – | 9 |
| realistic | plain skeleton | 0.89 | 4.12 | +15.0% | 1.14 | 93% | 79 |
| realistic | v1 corners | 0.95 | 0.73 | -1.3% | 0.94 | 75% | 60 |
| realistic | v1 auto | 0.95 | 0.72 | -1.6% | 0.91 | 81% | 59 |
| all | v0.1 ORB, y-order | 0.10 | 6.15 | -68.3% | – | – | 446 |
| all | v0.1 Shi-Tomasi + MST | 0.20 | 5.56 | -60.9% | – | – | 12 |
| all | plain skeleton | 0.94 | 1.52 | +6.9% | 0.75 | 90% | 60 |
| all | v1 corners | 0.97 | 0.54 | -1.5% | 0.66 | 80% | 60 |
| all | v1 auto | 0.97 | 0.52 | -1.5% | 0.65 | 83% | 57 |
