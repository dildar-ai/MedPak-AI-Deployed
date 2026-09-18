/**
 * Shared formatting helpers for medicine prices and packs.
 */

/**
 * Singular unit word derived from a pack description.
 *   "10 caps"   → "cap"
 *   "3×7"       → "unit"   (multiplier packs have no unit word)
 *   "120 ml"    → "ml"
 */
export const unitWord = (packDesc) => {
  const m = /(caps|tabs|sachets|vials|ampoules|pens|units|ml)\b/i.exec(packDesc || '');
  if (!m) return 'unit';
  const w = m[1].toLowerCase();
  if (w === 'ml') return 'ml';
  return w.endsWith('s') ? w.slice(0, -1) : w;
};
