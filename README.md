# Apriori Market Basket Analysis - Interactive Training Guide

A dedicated, self-hosted educational web simulator that teaches how the Apriori algorithm works step by step on grocery baskets.

Zero external dependencies: 100% pure Python standard library (`http.server`), runs instantly on any machine with Python 3.8+!

## Key Features

- **Step-by-Step Training Guide (Pedagogical Mode)**:
  - Designed for learners who have never seen Apriori before.
  - Interactive stepper with **First**, **Previous**, **Next**, **Jump to End**, and clickable step timeline bubbles.
  - Explains the exact reasoning and math at each step:
    1. **Problem Setup**: Total baskets $N$, items, threshold requirements ($minsup$, $minconf$).
    2. **Scan & Filter $C_1 \to L_1$**: Support counting for 1-itemsets, pass/fail decisions.
    3. **Join & Prune to $C_2$**: Generating pairs, explaining why no pruning is needed yet.
    4. **Scan & Filter $C_2 \to L_2$**: Computing 2-item support with exact basket matches.
    5. **Join & Apriori Pruning to $C_3$**: Demonstrating the core Apriori downward-closure property (pruning candidate triplets if any 2-item subset is missing from $L_2$ before scanning data).
    6. **Higher levels ($C_k \to L_k$)**: Iterating until no more candidates can be generated.
    7. **Association Rule Generation ($A \to B$)**: Computing Support, Confidence, and Lift with step-by-step formulas.
    8. **Summary & Retail Strategy**: Cross-selling bundles, product placement, and recommendations.
- **Full Process Dashboard**:
  - Immediate view of all mined frequent itemsets and association rules.
- **Interactive Controls**:
  - Sample presets (Classic Supermarket, Breakfast Store, Dinner & Pasta).
  - Live editable basket input.
  - Minimum support ($minsup$) and confidence ($minconf$) sliders.

## How to Run

Zero package installations needed! Simply run:

```bash
python app.py
```

Or using Makefile:

```bash
make run
```

Then open your browser to:
- `http://localhost:8000` (or `http://127.0.0.1:8000`)

To run unit tests:

```bash
python -m unittest discover -s tests
# or
make test
```

milk, bread, butter
bread, diaper, beer, eggs
milk, diaper, bread, cola
```

## HuggingFace Spaces

This repo is ready for a Gradio Space:

- Keep `app.py` at the repository root.
- Keep `requirements.txt` at the repository root.
- Deploy the repository as a Python Gradio Space.
