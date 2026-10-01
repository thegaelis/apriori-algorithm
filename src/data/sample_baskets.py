from __future__ import annotations

DEFAULT_PRESET_NAME = "Classic grocery baskets"

PRESET_BASKETS = {
    "Classic grocery baskets": """milk, bread, butter
bread, diaper, beer, eggs
milk, diaper, bread, cola
bread, milk, diaper, beer
milk, bread, diaper, cola
eggs, flour, sugar
bread, butter, jam
milk, cereal, banana""",
    "Breakfast baskets": """bread, butter, jam
milk, cereal, banana
bread, eggs, milk
oatmeal, milk, banana
bread, peanut butter, jelly
coffee, milk, sugar""",
    "Dinner baskets": """rice, chicken, onion, garlic
rice, beans, tomato
pasta, tomato, cheese
bread, butter, soup
rice, chicken, broccoli
pasta, garlic, olive oil""",
}


# Presets used by the interactive UI.
UI_PRESETS = [{'id': 'han',
  'name': 'SGK Han et al. — Table 4.1 (9 giao dịch, I1…I5)',
  'src': 'Han, Pei & Tong (2022), Table 4.1, Example 4.3–4.4 — trùng slide 16–18 của nhóm.',
  'mode': 'count',
  'minsup': 2,
  'minconf': 70,
  'text': 'T100: I1, I2, I5\n'
          'T200: I2, I4\n'
          'T300: I2, I3\n'
          'T400: I1, I2, I4\n'
          'T500: I1, I3\n'
          'T600: I2, I3\n'
          'T700: I1, I3\n'
          'T800: I1, I2, I3, I5\n'
          'T900: I1, I2, I3'},
 {'id': 'abcd',
  'name': 'Lattice {a, b, c, d} — minh họa join/prune (slide 12–13)',
  'src': 'Dữ liệu dựng sao cho L₂ = {ab, ac, ad, bc, bd} và cd ∉ L₂, đúng như ví dụ prune trên '
         'slide 13.',
  'mode': 'count',
  'minsup': 2,
  'minconf': 60,
  'text': 'T1: a, b, c\nT2: a, b, d\nT3: a, c\nT4: b, d\nT5: a, d\nT6: b, c'},
 {'id': 'grocery',
  'name': 'Giỏ hàng siêu thị (10 giao dịch)',
  'src': 'Bộ giỏ hàng dựng để thấy đủ tình huống: L₁ và L₂ có loại, k = 3 có cặp không ghép và có '
         'prune, k = 4 sinh 3 ứng viên → prune còn 1 → quét thấy L₄ = ∅.',
  'mode': 'count',
  'minsup': 3,
  'minconf': 70,
  'text': 'T1: milk, bread, diaper, beer\n'
          'T2: bread, beer, eggs\n'
          'T3: milk, bread, eggs, butter\n'
          'T4: bread, diaper, beer\n'
          'T5: milk, bread, beer, eggs\n'
          'T6: milk, diaper, beer\n'
          'T7: bread, beer, eggs, cola\n'
          'T8: milk, bread, diaper\n'
          'T9: milk, eggs, butter\n'
          'T10: milk, bread, diaper, beer'},
 {'id': 'breakfast',
  'name': 'Bữa sáng (6 giao dịch)',
  'src': 'Preset "Breakfast baskets" trong sample_baskets.py.',
  'mode': 'count',
  'minsup': 2,
  'minconf': 60,
  'text': PRESET_BASKETS['Breakfast baskets']},
 {'id': 'dinner',
  'name': 'Bữa tối (6 giao dịch)',
  'src': 'Preset "Dinner baskets" trong sample_baskets.py.',
  'mode': 'count',
  'minsup': 2,
  'minconf': 60,
  'text': PRESET_BASKETS['Dinner baskets']},
 {'id': 'custom',
  'name': 'Tự nhập…',
  'src': 'Nhập giao dịch của bạn ở ô bên trái rồi bấm "Áp dụng dữ liệu".',
  'mode': 'count',
  'minsup': 2,
  'minconf': 60,
  'text': 'T1: A, B, C\nT2: A, C\nT3: A, D\nT4: B, E, F'}]

