# Project Guidelines & Domain Rules (Apriori Algorithm Web Application)

## 1. Dataset Selection & Explainability Rules
- **Human-Interpretable B2C Items**: Always use retail datasets where items and co-occurrence rules are immediately intuitive to a general audience (e.g., **Groceries POS dataset** by Hahsler et al., 2006 — `whole milk`, `rolls/buns`, `sausage`, `root vegetables`, `berries`, `whipped/sour cream`).
- **Keep Canonical English Item Names**: Preserve original English item names from the academic dataset so rules match published literature, while grouping items into clear supermarket aisles/categories.
- **Avoid Same-Variant B2B Noise**: Do not highlight trivial variant-to-variant rules (such as same item in two colors) as hero examples. Prioritize complementary cross-item rules with clear culinary or usage synergy and high Lift (`lift >= 2.0`).

## 2. Algorithm-Centric Statistics (`/stats`)
- **Strict Alignment with Apriori Metrics**: Every chart and table on `/stats` must directly explain what the user sees on the storefront (`/shop`) using Apriori metrics (`count`, `support`, `confidence`, `lift`):
  1. **Bestsellers ($L_1$)**: Rank top items by transaction `count` and `support = count / N` to explain why they are featured.
  2. **Frequent Combos ($L_2, L_3$)**: Show top pairs and triplets by co-occurrence `count` and `support` to explain bundle formation.
  3. **Recommendation Mechanics ($A \Rightarrow B$)**: Explain why buying $A$ recommends $B$ using `confidence = support(A ∪ B) / support(A)` and `lift = confidence / support(B)`, accompanied by a concise preprocessing funnel.
- **No Unrelated Accounting Charts**: Avoid cluttering `/stats` with non-algorithmic dimensions (e.g., revenue by country, day-of-week histograms, or customer ID null-rate charts).

## 3. Minimalist UI Design
- **Single-Accent Palette**: Use a clean light background (`#ffffff` / `#f8fafc`), high-contrast slate typography (`#0f172a`), and a single primary accent color (`#4f46e5`). Avoid multi-colored badges on product and recommendation cards.
- **Concise Card Copy**: Each recommendation card in `/shop` should display at most:
  1. Product name & price
  2. Concise trigger rule (`{A} → {B}`)
  3. Single-line muted metrics (`Support · Confidence · Lift`)
