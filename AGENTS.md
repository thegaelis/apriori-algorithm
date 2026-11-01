# Project Guidelines & Domain Rules (Apriori Algorithm Web Application)

## 1. Dataset Selection & Explainability Rules
- **Human-Interpretable B2C Items**: Always use retail datasets where items and co-occurrence rules are immediately intuitive to a general audience (e.g., **Groceries POS dataset** by Hahsler et al., 2006 — `whole milk`, `rolls/buns`, `sausage`, `root vegetables`, `berries`, `whipped/sour cream`).
- **Keep Canonical English Item Names**: Preserve original English item names from the academic dataset so rules match published literature, while grouping items into clear supermarket aisles/categories.
- **Vietnamese Display Names, Canonical Data Keys**: The storefront may display Vietnamese names from `src/data/products.csv`, but rule text, metrics, tooltips, and all JSON/API fields MUST keep the canonical English item keys so rules match the literature.
- **Avoid Same-Variant B2B Noise**: Do not highlight trivial variant-to-variant rules (such as same item in two colors) as hero examples. Prioritize complementary cross-item rules with clear culinary or usage synergy and high Lift (`lift >= 2.0`).

## 2. Algorithm-Centric Statistics (`/dataset`)
- **Strict Alignment with Apriori Metrics**: Every chart and table on `/dataset` must directly explain what the user sees on the storefront (`/shop`) using Apriori metrics (`count`, `support`, `confidence`, `lift`):
  1. **Bestsellers ($L_1$)**: Rank top items by transaction `count` and `support = count / N` to explain why they are featured.
  2. **Frequent Combos ($L_2, L_3$)**: Show top pairs and triplets by co-occurrence `count` and `support` to explain bundle formation.
  3. **Recommendation Mechanics ($A \Rightarrow B$)**: Explain why buying $A$ recommends $B$ using `confidence = support(A ∪ B) / support(A)` and `lift = confidence / support(B)`, accompanied by a concise preprocessing funnel.
- **No Unrelated Accounting Charts**: Avoid cluttering `/stats` with non-algorithmic dimensions (e.g., revenue by country, day-of-week histograms, or customer ID null-rate charts).

## 3. Minimalist UI Design
- **Green Brand Palette**: Use a warm light background (`#f5f7f6` / `#ffffff`), ink `#1b2420`, and brand green `#0f8a4b`; promo orange `#e8572a` is reserved for savings, discount, and bestseller badges. Typography: Be Vietnam Pro. Avoid other decorative badge colors.
- **Concise Card Copy**: Each recommendation card in `/shop` should display at most:
  1. Product name & price
  2. Concise trigger rule (`{A} → {B}`)
  3. Single-line muted metrics (`Support · Confidence · Lift`)
