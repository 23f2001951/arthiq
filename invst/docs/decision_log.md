# Architecture Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-20 | Quarterly Rebalance | Aligns with Indian 90-day earnings disclosure cadence and minimizes transaction costs. |
| 2026-09-20 | SQLite with WAL mode | Zero setup, single-user file-backed database handling ~1.5M price rows with sub-millisecond query performance. |
| 2026-09-20 | 25% Stock & 40% Sector Cap | Eliminates single-name blow-up risk while allowing high conviction tilts. |
| 2026-09-20 | Streamlit Frontend | Python-native, zero-JavaScript UI for immediate drilldown and visual inspection. |
| 2026-09-21 | Retain Deterministic Engine as Production Research Baseline | The ML layer failed to demonstrate positive out-of-sample alpha in untouched 2024–2026 test (-1.27% vs -0.02% base, delta -1.25%). Standalone ML IC is negative (-0.0909). ML remains conviction-tilt candidate only. |
| 2026-09-21 | Drawdown Phrasing Correction for $\gamma=0.50$ | Baseline MDD is -38.49% vs $\gamma=0.50$ MDD of -39.01%. $\gamma=0.50$ reduces drawdown amplification of aggressive tilts, but does not improve MDD vs deterministic baseline. |
| 2026-09-21 | Configuration Disambiguation (50/50 Blend vs $\gamma=0.50$) | 50/50 blend achieved 4.92% CAGR while pure $\gamma=0.50$ achieved 4.40% in separate experiments. The combined configuration (Platt + 50/50 + $\gamma=0.50$) must be explicitly backtested before recommending as default. |
| 2026-09-21 | Inconclusive High-VIX Regime Definition | Current sample contains 0 quarters with India VIX > 18. Claims of ML performance in high volatility are nullified; regime definition revision required. |
| 2026-09-21 | Permanent Freeze of 2024–2026 Partition | 2024–2026 was consumed as an untouched out-of-sample test and is permanently frozen against hyperparameter tuning or feature selection. |
| 2026-09-21 | V0.4 Normalized Additive Decision Function | Transition from purely multiplicative score to $\text{ArthScore} = w_F F + w_M M + w_E E + w_R R + w_H H$ with signal agreement and 'Thesis + Evidence' output. |
| 2026-09-21 | Milestone Naming Formalization | Rename milestone from 'Production ML' to 'V0.3.1 — Predictive Intelligence Diagnosis Complete', followed by 'V0.4 — Decision Intelligence & Robust Alpha Research'. |
| 2026-09-21 | Formal Model Registry Classifications | Formalize binary status: Deterministic V0.2.1 (BASELINE), Full 24 ML (REJECTED due to negative IC & inverted quintiles), Platt+50/50+$\gamma=0.50$ (REJECTED due to 4.25% CAGR underperforming baseline), Reverse Signal (RESEARCH), Fundamentals-only (CANDIDATE due to +0.0179 Rank IC and +4.99% L/S). |
| 2026-09-21 | Adoption of 8 Formal Model Promotion Gates | Mandate Gates 1 to 8: 1. Zero PIT Violations, 2. Positive IC & IC IR, 3. Cross-sectional Monotonicity ($Q5 > Q1$), 4. Temporal Stability, 5. Untouched Frozen Test Outperformance, 6. Economic Explanation, 7. Cost Robustness, 8. Net Portfolio Improvement. |
| 2026-09-21 | Hierarchical Thesis Architecture | Decouple opaque single-model probability into $\text{Portfolio Conviction} = \text{Investment Thesis} \times \text{Market Context Adjustment} \times \text{Risk Adjustment}$, separating expected return from risk and context. |
| 2026-09-21 | Priority Research Protocol for V0.4 | Enforce strict sequence: Phase A (Fundamentals-only multi-horizon), Phase B (Leave-one-group-out analysis), Phase C (Multi-horizon decay), Phase D (Sector/Beta neutral), Phase E (Nifty 500 PIT), Phase F (Bootstrap statistical significance). |
