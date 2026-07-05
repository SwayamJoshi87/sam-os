#!/usr/bin/env python3
"""Meal logger — CLI wrapper around samos.meals."""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos import meals


def show_today():
    d = meals.today_date()
    target = meals.get_target(d)
    totals = meals.get_day_totals(d)
    logged = meals.get_day_meals(d)

    print(f"🍽 {d}")
    if not logged:
        print("  no meals logged yet")
    for m in logged:
        macros = []
        if m["protein_g"] is not None:
            macros.append(f"P{m['protein_g']:.0f}")
        if m["carbs_g"] is not None:
            macros.append(f"C{m['carbs_g']:.0f}")
        if m["fat_g"] is not None:
            macros.append(f"F{m['fat_g']:.0f}")
        macro_str = " ".join(macros)
        desc = (m["description"] or "")[:40]
        print(f"  {m['meal_type']:<10} {m['calories']:>5.0f}cal  {macro_str:<15} {desc}")

    print()
    if totals["meal_count"] > 0:
        print(
            f"  total: {totals['calories']:.0f}cal  "
            f"P{totals['protein_g']:.0f} C{totals['carbs_g']:.0f} F{totals['fat_g']:.0f}  "
            f"({totals['meal_count']} meals)"
        )

    if target and target.get("calories"):
        remaining = target["calories"] - totals["calories"]
        if remaining > 0:
            print(f"  target: {target['calories']:.0f} → {remaining:.0f} cals left")
        elif remaining < 0:
            print(f"  target: {target['calories']:.0f} → {-remaining:.0f} cals OVER")
        else:
            print(f"  target: {target['calories']:.0f} → on the money 🎯")
        if target.get("protein_g"):
            p_left = target["protein_g"] - totals["protein_g"]
            print(
                f"  protein target: {target['protein_g']:.0f}g → {p_left:.0f}g left"
                if p_left > 0
                else f"  protein target: {target['protein_g']:.0f}g → hit"
            )
    else:
        print("  no target set for today — `meal_log.py target 2300 150` to set")


def set_target_from_args(args):
    d = meals.today_date()
    if not args:
        print("usage: target <cals> [protein_g] [carbs_g] [fat_g] [weight_kg] [notes...]")
        return
    try:
        calories = float(args[0])
        protein_g = float(args[1]) if len(args) > 1 else None
        carbs_g = float(args[2]) if len(args) > 2 else None
        fat_g = float(args[3]) if len(args) > 3 else None
        weight_kg = float(args[4]) if len(args) > 4 else None
        notes = " ".join(args[5:]) if len(args) > 5 else None
    except ValueError as e:
        print(f"bad number: {e}")
        return
    t = meals.set_target(d, calories, protein_g, carbs_g, fat_g, weight_kg, notes)
    t = t["target"]
    print(f"🎯 target set for {d}:")
    if t.get("calories"):
        print(f"  calories: {t['calories']:.0f}")
    if t.get("protein_g"):
        print(f"  protein:  {t['protein_g']:.0f}g")
    if t.get("carbs_g"):
        print(f"  carbs:    {t['carbs_g']:.0f}g")
    if t.get("fat_g"):
        print(f"  fat:      {t['fat_g']:.0f}g")
    if t.get("weight_kg"):
        print(f"  weight:   {t['weight_kg']:.1f}kg")
    if t.get("notes"):
        print(f"  notes:    {t['notes']}")


def show_week():
    rows = meals.week_meals()
    if not rows:
        print("no meals logged in last 7 days")
        return
    print("📊 last 7 days:\n")
    for r in rows:
        target = meals.get_target(r["date"])
        adherence = ""
        if target and target.get("calories") and r["calories"]:
            diff_pct = abs(r["calories"] - target["calories"]) / target["calories"] * 100
            if diff_pct <= 5:
                adherence = "🎯 on target"
            elif diff_pct <= 10:
                adherence = f"~{diff_pct:.0f}% off"
            else:
                side = "over" if r["calories"] > target["calories"] else "under"
                adherence = f"{side} {diff_pct:.0f}%"
        target_str = f"/{target['calories']:.0f}" if target and target.get("calories") else ""
        print(
            f"  {r['date']}  {r['calories']:.0f}{target_str}  "
            f"P{r['protein_g']:.0f}  {r['meal_count']} meals  {adherence}"
        )


def cmd_log(args):
    if len(args) < 2:
        print("usage: log <meal_type> <calories> [protein_g] [carbs_g] [fat_g] [description...]")
        print("  meal_type: breakfast | lunch | dinner | snack")
        return
    meal_type = args[0].lower()
    try:
        calories = float(args[1])
    except ValueError:
        print(f"calories must be a number, got '{args[1]}'")
        return

    macros = [None, None, None]
    desc_start = None
    for i in range(2, min(5, len(args))):
        try:
            macros[i - 2] = float(args[i])
        except ValueError:
            desc_start = i
            break
    if desc_start is None:
        desc_start = min(len(args), 5)

    protein_g, carbs_g, fat_g = macros
    description = " ".join(args[desc_start:]) if desc_start < len(args) else None

    try:
        result = meals.log_meal(
            meals.today_date(), meal_type, calories, description, protein_g, carbs_g, fat_g
        )
    except ValueError as e:
        print(f"❌ {e}")
        return

    macro_parts = []
    if protein_g is not None:
        macro_parts.append(f"P{protein_g:.0f}")
    if carbs_g is not None:
        macro_parts.append(f"C{carbs_g:.0f}")
    if fat_g is not None:
        macro_parts.append(f"F{fat_g:.0f}")
    macro_str = " ".join(macro_parts) if macro_parts else ""
    desc_str = f" — {description}" if description else ""
    print(f"✅ logged {meal_type} ({calories:.0f}cal {macro_str}){desc_str}")

    totals = result["today_total"]
    target = result["target"]
    print(f"   today: {totals['calories']:.0f}cal", end="")
    if target and target.get("calories"):
        remaining = target["calories"] - totals["calories"]
        if remaining > 0:
            print(f" / {target['calories']:.0f} → {remaining:.0f} left")
        elif remaining < 0:
            print(f" / {target['calories']:.0f} → {-remaining:.0f} OVER")
        else:
            print(f" / {target['calories']:.0f} → on the money 🎯")
    else:
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "today":
        show_today()
    elif sys.argv[1] == "log":
        cmd_log(sys.argv[2:])
    elif sys.argv[1] == "target":
        set_target_from_args(sys.argv[2:])
    elif sys.argv[1] == "week":
        show_week()
    elif sys.argv[1] == "help":
        print(
            """meal_log.py [command]
  (none) | today  — show today's meals + totals vs target
  log <type> <cals> [P] [C] [F] [description]
                     — log a meal (type: breakfast/lunch/dinner/snack)
  target <cals> [P] [C] [F] [weight_kg] [notes]
                     — set today's target
  week               — last 7 days adherence summary"""
        )
    else:
        print(f"unknown: {sys.argv[1]}")
        print("use 'help'")
