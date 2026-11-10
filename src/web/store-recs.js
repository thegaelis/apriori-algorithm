/* Shared recommendation ranking: confidence first, then lift/support/count. */
window.StoreRecs = (() => {
  function compute(cartSet, data, max = 4) {
    const recs = [];
    const byCode = new Map();

    const push = (code, tier, extra) => {
      if (cartSet.has(code) || !data.catalog[code]) return;
      const rule = extra.rule || null;
      const confidence = rule ? rule.confidence : 0;
      const lift = rule ? rule.lift : 0;
      const support = rule ? rule.support : (extra.support || 0);
      const count = rule ? rule.count : (extra.count || 0);

      if (byCode.has(code)) {
        const existing = byCode.get(code);
        existing.ruleCount += 1;
        const better = confidence > existing.confidence
          || (confidence === existing.confidence && lift > existing.lift)
          || (confidence === existing.confidence && lift === existing.lift && support > existing.support);
        if (better) {
          existing.tier = tier;
          existing.confidence = confidence;
          existing.lift = lift;
          existing.support = support;
          existing.count = count;
          existing.rule = rule;
        }
        return;
      }

      byCode.set(code, {
        code, tier, confidence, lift, support, count,
        rule, ruleCount: 1,
      });
      recs.push(byCode.get(code));
    };

    let fired = 0;
    if (cartSet.size) {
      for (const rule of data.rules) {
        if (rule.antecedent.every(code => cartSet.has(code))) {
          const targets = rule.consequent.filter(code => !cartSet.has(code));
          if (targets.length) fired += 1;
          targets.forEach(code => push(code, 1, { rule }));
        }
      }
    }

    if (!recs.length) {
      const l1 = (data.frequent_itemsets && data.frequent_itemsets.L1) || [];
      for (const entry of l1) {
        if (recs.length >= max) break;
        push(entry.items[0], 4, { support: entry.support, count: entry.count });
      }
    }

    recs.sort((a, b) =>
      a.tier - b.tier
      || b.confidence - a.confidence
      || b.lift - a.lift
      || b.support - a.support
      || b.count - a.count
    );
    return { recs: recs.slice(0, max), fired };
  }

  return { compute };
})();
