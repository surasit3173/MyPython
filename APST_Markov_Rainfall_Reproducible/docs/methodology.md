# Scientific Methodology: Daily Rainfall Markov Chain Analysis

## 1. Rainfall State Classification
Daily precipitation $R_t$ at time $t$ (days) is discretized into a binary state sequence $S_t \in \{0, 1\}$ using a wet day threshold $T$ (default $T = 0.1\text{ mm/day}$):

$$S_t = \begin{cases} 0 \quad (\text{Dry day}) & \text{if } R_t < T \\ 1 \quad (\text{Wet day}) & \text{if } R_t \ge T \end{cases}$$

## 2. First-Order Markov Transition Probabilities
The first-order Markov chain assumes that the state on day $t$ depends only on the state of the immediately preceding day $t-1$:

$$P_{ij} = \mathbb{P}(S_t = j \mid S_{t-1} = i), \quad i,j \in \{0, 1\}$$

The sample estimates are calculated as:

$$P_{00} = \frac{N_{00}}{N_{00} + N_{01}}, \quad P_{01} = \frac{N_{01}}{N_{00} + N_{01}}$$

$$P_{10} = \frac{N_{10}}{N_{10} + N_{11}}, \quad P_{11} = \frac{N_{11}}{N_{10} + N_{11}}$$

Subject to exact probability invariants:
$$P_{00} + P_{01} = 1.0, \quad P_{10} + P_{11} = 1.0$$

## 3. Stationary Probability Distribution
The long-term stationary distribution $\boldsymbol{\pi} = [\pi_0, \pi_1]$ satisfies $\boldsymbol{\pi} \mathbf{P} = \boldsymbol{\pi}$:

$$\pi_1 = \frac{P_{01}}{P_{01} + P_{10}}, \quad \pi_0 = \frac{P_{10}}{P_{01} + P_{10}}$$

Where $\pi_1$ represents the long-term unconditional probability of a wet day.

## 4. Expected Spell Lengths
Under a first-order Markov process, dry and wet spell durations follow geometric distributions with expected lengths:

$$\mathbb{E}[D] = \frac{1}{P_{01}}, \quad \mathbb{E}[W] = \frac{1}{P_{10}} = \frac{1}{1 - P_{11}}$$

## 5. Model Order Selection (AIC / BIC)
To verify that a 1st-order Markov chain is appropriate relative to an independent model (Order 0) or higher-order model (Order 2), Akaike Information Criterion (AIC) and Bayesian Information Criterion (BIC) are evaluated:

$$\text{AIC} = -2\ln(L) + 2k$$
$$\text{BIC} = -2\ln(L) + k \ln(N)$$

where $L$ is the likelihood function, $k$ is the number of parameters, and $N$ is the total transition sample size.
