#!/usr/bin/env python3
"""Meal logger — log meals, see daily totals vs target, weekly adherence."""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB = Path("/home/server/data/schedule.db")

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def conn():
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    return c


def today_date():
    return datetime.now().strftime("%Y-%m-%d")


def get_target(date_str):
    """Return target row for date_str, or None."""
    c = conn()
    row = c.execute("SELECT * FROM daily_targets WHERE date=?", (date_str,)).fetchone()
    c.close()
    return dict(row) if row else None


def upsert_target(date_str, calories=None, protein_g=None, carbs_g=None, fat_g=None, weight_kg=None, notes=None):
    """Set/replace target for date_str."""
    c = conn()
    # build update values, skipping None
    updates = {}
    if calories is not None: updates["calories"] = calories
    if protein_g is not None: updates["protein_g"] = protein_g
    if carbs_g is not None: updates["carbs_g"] = carbs_g
    if fat_g is not None: updates["fat_g"] = fat_g
    if weight_kg is not None: updates["weight_kg"] = weight_kg
    if notes is not None: updates["notes"] = notes

    existing = c.execute("SELECT id FROM daily_targets WHERE date=?", (date_str,)).fetchone()
    if existing:
        if updates:
            sets = ", ".join(f"{k}=?" for k in updates)
            vals = list(updates.values()) + [existing["id"]]
            c.execute(f"UPDATE daily_targets SET {sets} WHERE id=?", vals)
    else:
        cols = ["date"] + list(updates.keys())
        placeholders = ",".join(["?"] * len(cols))
        vals = [date_str] + list(updates.values())
        c.execute(f"INSERT INTO daily_targets ({','.join(cols)}) VALUES ({placeholders})", vals)
    c.commit()
    c.close()
    return get_target(date_str)


def log_meal(date_str, meal_type, description, calories, protein_g=None, carbs_g=None, fat_g=None, source="manual"):
    """Insert a meal row. Returns the row."""
    if meal_type not in MEAL_TYPES:
        raise ValueError(f"meal_type must be one of {MEAL_TYPES}, got '{meal_type}'")
    c = conn()
    c.execute("""
        INSERT INTO meals (date, meal_type, description, calories, protein_g, carbs_g, fat_g, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (date_str, meal_type, description, calories, protein_g, carbs_g, fat_g, source))
    meal_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return meal_id


def get_day_totals(date_str):
    """Sum cals/P/C/F for a date. Returns dict."""
    c = conn()
    row = c.execute("""
        SELECT
            COALESCE(SUM(calories), 0) AS calories,
            COALESCE(SUM(protein_g), 0) AS protein_g,
            COALESCE(SUM(carbs_g), 0) AS carbs_g,
            COALESCE(SUM(fat_g), 0) AS fat_g,
            COUNT(*) AS meal_count
        FROM meals WHERE date=?
    """, (date_str,)).fetchone()
    c.close()
    return dict(row)


def get_day_meals(date_str):
    """Return all meals for date, oldest first."""
    c = conn()
    rows = c.execute("""
        SELECT id, meal_type, description, calories, protein_g, carbs_g, fat_g, source, created_at
        FROM meals WHERE date=? ORDER BY created_at
    """, (date_str,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def show_today():
    date_str = today_date()
    target = get_target(date_str)
    totals = get_day_totals(date_str)
    meals = get_day_meals(date_str)

    print(f"🍽 {date_str}")
    if not meals:
        print("  no meals logged yet")
    for m in meals:
        macros = []
        if m["protein_g"] is not None: macros.append(f"P{m['protein_g']:.0f}")
        if m["carbs_g"] is not None: macros.append(f"C{m['carbs_g']:.0f}")
        if m["fat_g"] is not None: macros.append(f"F{m['fat_g']:.0f}")
        macro_str = " ".join(macros)
        desc = (m["description"] or "")[:40]
        print(f"  {m['meal_type']:<10} {m['calories']:>5.0f}cal  {macro_str:<15} {desc}")

    print()
    if totals["meal_count"] > 0:
        print(f"  total: {totals['calories']:.0f}cal  P{totals['protein_g']:.0f} C{totals['carbs_g']:.0f} F{totals['fat_g']:.0f}  ({totals['meal_count']} meals)")

    if target and target.get("calories"):
        remaining = target["calories"] - totals["calories"]
        cals_str = f"{target['calories']:.0f}"
        if remaining > 0:
            print(f"  target: {cals_str} → {remaining:.0f} cals left")
        elif remaining < 0:
            print(f"  target: {cals_str} → {-remaining:.0f} cals OVER")
        else:
            print(f"  target: {cals_str} → on the money 🎯")
        if target.get("protein_g"):
            p_left = target["protein_g"] - totals["protein_g"]
            print(f"  protein target: {target['protein_g']:.0f}g → {p_left:.0f}g left" if p_left > 0 else f"  protein target: {target['protein_g']:.0f}g → hit")
    else:
        print(f"  no target set for today — `meal_log.py target 2300 150` to set")


def set_target_from_args(args):
    """Parse `meal_log.py target <cals> [protein] [carbs] [fat] [weight] [notes]`"""
    date_str = today_date()
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
    upsert_target(date_str, calories, protein_g, carbs_g, fat_g, weight_kg, notes)
    t = get_target(date_str)
    print(f"🎯 target set for {date_str}:")
    if t.get("calories"): print(f"  calories: {t['calories']:.0f}")
    if t.get("protein_g"): print(f"  protein:  {t['protein_g']:.0f}g")
    if t.get("carbs_g"): print(f"  carbs:    {t['carbs_g']:.0f}g")
    if t.get("fat_g"): print(f"  fat:      {t['fat_g']:.0f}g")
    if t.get("weight_kg"): print(f"  weight:   {t['weight_kg']:.1f}kg")
    if t.get("notes"): print(f"  notes:    {t['notes']}")


def show_week():
    """Last 7 days totals + adherence."""
    today = today_date()
    c = conn()
    rows = c.execute("""
        SELECT
            m.date,
            SUM(m.calories) AS cals,
            SUM(m.protein_g) AS protein,
            COUNT(*) AS meals
        FROM meals m
        WHERE m.date >= date(?, '-7 days')
        GROUP BY m.date
        ORDER BY m.date
    """, (today,)).fetchall()
    c.close()

    if not rows:
        print("no meals logged in last 7 days")
        return

    print(f"📊 last 7 days:\n")
    for r in rows:
        target = get_target(r["date"])
        adherence = ""
        if target and target.get("calories") and r["cals"]:
            # within 10% of target = good
            diff_pct = abs(r["cals"] - target["calories"]) / target["calories"] * 100
            if diff_pct <= 5:
                adherence = "🎯 on target"
            elif diff_pct <= 10:
                adherence = f"~{diff_pct:.0f}% off"
            else:
                side = "over" if r["cals"] > target["calories"] else "under"
                adherence = f"{side} {diff_pct:.0f}%"
        cals_str = f"{r['cals']:.0f}" if r["cals"] else "—"
        p_str = f"P{r['protein']:.0f}" if r["protein"] else "—"
        target_str = f"/{target['calories']:.0f}" if target and target.get("calories") else ""
        print(f"  {r['date']}  {cals_str}{target_str}  {p_str}  {r['meals']} meals  {adherence}")


def cmd_log(args):
    """meal_log.py log <meal_type> <calories> [protein_g] [carbs_g] [fat_g] [description...]"""
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

    # eat optional numeric args first (P, C, F); stop at first non-numeric
    macros = [None, None, None]  # [protein, carbs, fat]
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
        meal_id = log_meal(today_date(), meal_type, description, calories, protein_g, carbs_g, fat_g)
    except ValueError as e:
        print(f"❌ {e}")
        return

    macros = []
    if protein_g is not None: macros.append(f"P{protein_g:.0f}")
    if carbs_g is not None: macros.append(f"C{carbs_g:.0f}")
    if fat_g is not None: macros.append(f"F{fat_g:.0f}")
    macro_str = " ".join(macros) if macros else ""
    desc_str = f" — {description}" if description else ""
    print(f"✅ logged {meal_type} ({calories:.0f}cal {macro_str}){desc_str}")

    # show running total
    totals = get_day_totals(today_date())
    target = get_target(today_date())
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
        print("""meal_log.py [command]
  (none) | today  — show today's meals + totals vs target
  log <type> <cals> [P] [C] [F] [description]
                     — log a meal (type: breakfast/lunch/dinner/snack)
  target <cals> [P] [C] [F] [weight_kg] [notes]
                     — set today's target
  week               — last 7 days adherence summary""")
    else:
        print(f"unknown: {sys.argv[1]}")
        print("use 'help'")