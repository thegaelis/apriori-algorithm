/* Shared Apriori recommendation ranking used by the shop and cart pages. */
window.StoreRecs = (() => {
  function compute(cartSet, data, max = 4) {
    const recs = [];
    const byCode = new Map();
    const push = (code, tier, score, extra) => {
      if (cartSet.has(code) || !data.catalog[code]) return;
      if (byCode.has(code)) {
        const existing = byCode.get(code);
        existing.ruleCount = (existing.ruleCount || 1) + 1;
        if (tier < existing.tier || (tier === existing.tier && score > existing.score)) {
          existing.tier = tier;
          existing.score = score;
          if (extra && extra.rule) existing.rule = extra.rule;
        }
        return;
      }
      byCode.set(code, Object.assign({ code, tier, score, ruleCount: 1 }, extra));
      recs.push(byCode.get(code));
    };

    let fired = 0;
    if (cartSet.size) {
      for (const rule of data.rules) {
        if (rule.antecedent.every(code => cartSet.has(code))) {
          const targets = rule.consequent.filter(code => !cartSet.has(code));
          if (targets.length) fired += 1;
          // Prioritize matching more items in the current cart (antecedent length),
          // combined with high conditional probability (confidence) and correlation (lift).
          const antMatchScore = rule.antecedent.length * 50;
          const confScore = (rule.confidence || 0) * 20;
          const liftScore = (rule.lift || 1) * 3;
          const score = antMatchScore + confScore + liftScore;
          targets.forEach(code => push(code, 1, score, { rule }));
        }
      }
    } else {
      const l1 = (data.frequent_itemsets && data.frequent_itemsets.L1) || [];
      for (const entry of l1) {
        if (recs.length >= max) break;
        push(entry.items[0], 4, entry.support, { support: entry.support, count: entry.count });
      }
    }

    recs.sort((a, b) => a.tier - b.tier || b.score - a.score);
    return { recs: recs.slice(0, max), fired };
  }

  return { compute };
})();
