"""The task suite — natural prompts, each with a programmatic end-state check.

Every task tells the agent to leave a checkable artifact (a Desktop file, a Note, a
Reminders list) so `verify()` can score correctness without a human. Prompts stay in
plain user language. Grow this list toward 100-200; the loop scales with it.
"""

from __future__ import annotations

from functools import partial

from . import verifiers as v
from .model import Task

TASKS: list[Task] = [
    # -- easy: single app, checkable artifact --
    Task("calc_mul", "easy",
         "Work out 48 × 12 in Calculator and save just the result to calc.txt on the Desktop.",
         partial(v.desktop_file, "calc.txt", "576"), partial(v.rm_desktop_file, "calc.txt")),
    Task("text_hello", "easy",
         "In TextEdit write 'Hello from Glance' and save it as hello.txt on the Desktop.",
         partial(v.desktop_file, "hello.txt", "Hello from Glance"),
         partial(v.rm_desktop_file, "hello.txt")),
    Task("calc_tip", "easy",
         "Work out a 15% tip on $86.40 and save the result to tip.txt on the Desktop.",
         partial(v.desktop_file, "tip.txt", "12.96"), partial(v.rm_desktop_file, "tip.txt")),
    Task("note_groceries", "easy",
         "Make a Note titled 'Groceries' listing milk, eggs and bread.",
         partial(v.note_exists, "Groceries", 10), partial(v.delete_note, "Groceries")),
    Task("sysinfo", "easy",
         "Find this Mac's macOS version and save it to sysinfo.txt on the Desktop.",
         partial(v.desktop_file, "sysinfo.txt", "macOS"), partial(v.rm_desktop_file, "sysinfo.txt")),

    # -- medium: multi-step or extract-and-record --
    Task("text_haiku", "medium",
         "Write a 3-line haiku about the ocean and save it as ocean.txt on the Desktop.",
         partial(v.desktop_file, "ocean.txt"), partial(v.rm_desktop_file, "ocean.txt")),
    Task("calc_sum", "medium",
         "Add 12, 45, 8, 99 and 23 and save the total to sum.txt on the Desktop.",
         partial(v.desktop_file, "sum.txt", "187"), partial(v.rm_desktop_file, "sum.txt")),
    Task("calc_budget", "medium",
         "Add a budget of rent 1800, food 600, transit 120 and misc 250, and save the "
         "total to budget.txt on the Desktop.",
         partial(v.desktop_file, "budget.txt", "2770"), partial(v.rm_desktop_file, "budget.txt")),
    Task("text_replace", "medium",
         "Write a 6-sentence story about a robot, replace every 'robot' with 'android', "
         "and save it as story.txt on the Desktop.",
         partial(v.desktop_file, "story.txt", "android"), partial(v.rm_desktop_file, "story.txt")),
    Task("note_system", "medium",
         "Find this Mac's computer name and macOS version and put both in a Note titled 'System'.",
         partial(v.note_exists, "System", 5), partial(v.delete_note, "System")),

    # -- hard: multi-app / longer / research-and-record --
    Task("reminders_trip", "hard",
         "In Reminders make a list called 'Trip' with 4 items: passport, tickets, "
         "charger, sunscreen.",
         partial(v.reminder_list, "Trip", 4)),
    Task("talk_outline", "hard",
         "Write an outline for a talk titled 'Efficient Computer Use' with 5 bullet "
         "points and save it as talk.txt on the Desktop.",
         partial(v.desktop_file, "talk.txt", "Efficient Computer Use"),
         partial(v.rm_desktop_file, "talk.txt")),
    Task("note_fx", "hard",
         "Look up the USD to EUR rate and record what $500 is in euros in a Note titled 'FX'.",
         partial(v.note_exists, "FX", 5), partial(v.delete_note, "FX")),
    Task("tokyo_time", "hard",
         "Find the current time in Tokyo and save 'Tokyo time: <time>' to tokyo.txt on the Desktop.",
         partial(v.desktop_file, "tokyo.txt", "Tokyo"), partial(v.rm_desktop_file, "tokyo.txt")),
    Task("note_iphone", "hard",
         "Look up when the first iPhone was released and its original price and record "
         "both in a Note titled 'iPhone'.",
         partial(v.note_exists, "iPhone", 5), partial(v.delete_note, "iPhone")),
]
