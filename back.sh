source venv/bin/activate

for period in \
  "2025-09-01 2026-02-28" \
  "2025-03-01 2025-08-31" \
  "2024-09-01 2025-02-28" \
  "2024-03-01 2024-08-31" \
  "2023-09-01 2024-02-29" \
  "2023-03-01 2023-08-31" \
  "2022-09-01 2023-02-28" \
  "2022-03-01 2022-08-31"
do
  start=$(echo $period | cut -d' ' -f1)
  end=$(echo $period | cut -d' ' -f2)
  echo ""
  echo ">>> $start ~ $end"
  python run_backtest.py --start $start --end $end 2>&1 | grep -E "(RESULT|기간|총 거래|승률|수익률|낙폭|보유|주당|잔고|===)"
done
