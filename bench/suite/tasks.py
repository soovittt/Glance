"""The task suite — 150 natural-language tasks across real, complex apps.

Every task tells the agent to leave a **checkable artifact** (a Desktop file, a Note, or
a Reminders list) so `verify()` scores correctness without a human — the verifiable
reward for the loop. Tasks span writing, spreadsheets, slides, web research, maps,
media, code editors, and system apps. Deliberately no bare Calculator tasks.

Grow or prune freely; `runner`/`report`/`loop` scale with whatever `TASKS` contains.
`SMOKE` is a tiny subset for a quick end-to-end check.
"""
# ruff: noqa: E501 — this is a data file; one-line task prompts read better than wrapped.

from __future__ import annotations

from functools import partial

from . import verifiers as v
from .model import Task


def _file(tid: str, diff: str, prompt: str, name: str, contains: str | None = None) -> Task:
    return Task(tid, diff, prompt, partial(v.desktop_file, name, contains),
                partial(v.rm_desktop_file, name))


def _note(tid: str, diff: str, prompt: str, title: str, min_chars: int = 8) -> Task:
    return Task(tid, diff, prompt, partial(v.note_exists, title, min_chars),
                partial(v.delete_note, title))


def _rem(tid: str, diff: str, prompt: str, name: str, n: int) -> Task:
    return Task(tid, diff, prompt, partial(v.reminder_list, name, n))


TASKS: list[Task] = [
    # ---------------- TextEdit / writing ----------------
    _file("text_01", "easy", "In TextEdit write 'Hello from Glance' and save it as hello.txt on the Desktop.", "hello.txt", "Hello from Glance"),
    _file("text_02", "easy", "Write a 4-line poem about mountains in TextEdit and save it as poem.txt on the Desktop.", "poem.txt"),
    _file("text_03", "medium", "Write a 3-line haiku about the ocean and save it as ocean.txt on the Desktop.", "ocean.txt"),
    _file("text_04", "medium", "In TextEdit write a 6-sentence story about a robot, replace every 'robot' with 'android', and save as story.txt on the Desktop.", "story.txt", "android"),
    _file("text_05", "medium", "Write a short cover letter for a software job and save it as letter.txt on the Desktop.", "letter.txt", "Dear"),
    _file("text_06", "medium", "List the 12 months of the year, one per line, in TextEdit and save as months.txt on the Desktop.", "months.txt", "December"),
    _file("text_07", "hard", "Write a 5-item numbered packing list for a beach trip and save it as packing.txt on the Desktop.", "packing.txt"),
    _file("text_08", "hard", "In TextEdit write two short paragraphs — one about coffee, one about tea — and save as drinks.txt on the Desktop.", "drinks.txt", "tea"),
    _file("text_09", "medium", "Write a simple recipe for pancakes with ingredients and steps, and save as pancakes.txt on the Desktop.", "pancakes.txt", "flour"),
    _file("text_10", "hard", "Write a 6-line outline for a talk titled 'Efficient Computer Use' and save as talk.txt on the Desktop.", "talk.txt", "Efficient Computer Use"),
    _file("text_11", "easy", "Write today's date and the words 'daily log' into log.txt on the Desktop.", "log.txt", "daily log"),
    _file("text_12", "medium", "Write the first 10 Fibonacci numbers separated by commas into fib.txt on the Desktop.", "fib.txt", "34"),

    # ---------------- Notes ----------------
    _note("notes_01", "easy", "Make a Note titled 'Groceries' listing milk, eggs and bread.", "Groceries", 10),
    _note("notes_02", "easy", "Create a Note titled 'Books to read' with 5 book titles.", "Books to read", 15),
    _note("notes_03", "medium", "Create a Note 'Standup' with a checklist of 3 agenda items.", "Standup", 10),
    _note("notes_04", "medium", "Make a Note titled 'Movies' with your 5 favourite films as a bulleted list.", "Movies", 15),
    _note("notes_05", "medium", "In Notes create 'Workout' with 4 exercises and the reps for each.", "Workout", 15),
    _note("notes_06", "hard", "Create a Note 'Trip Plan' with three sections: Flights, Hotel, Activities, each with one line.", "Trip Plan", 20),
    _note("notes_07", "easy", "Make a Note 'Ideas' with 3 app ideas.", "Ideas", 10),
    _note("notes_08", "medium", "Create a Note 'Passwords Hint' listing 3 (fake) service names and a hint for each — no real passwords.", "Passwords Hint", 15),
    _note("notes_09", "medium", "Make a Note titled 'Quotes' with two inspirational quotes.", "Quotes", 15),
    _note("notes_10", "hard", "Create a Note 'Weekly Menu' with a dinner for each day Mon–Fri.", "Weekly Menu", 25),
    _note("notes_11", "easy", "Create a Note 'Call List' with 3 people to call.", "Call List", 8),
    _note("notes_12", "medium", "Make a Note 'Chores' with a checklist of 5 household chores.", "Chores", 15),
    _note("notes_13", "hard", "Create a Note 'Reading Summary' with a 3-sentence summary of any book you know.", "Reading Summary", 30),
    _note("notes_14", "medium", "Make a Note 'Gift Ideas' with a gift idea for mom, dad and a friend.", "Gift Ideas", 15),

    # ---------------- Reminders ----------------
    _rem("rem_01", "easy", "In Reminders make a list 'Trip' with 4 items: passport, tickets, charger, sunscreen.", "Trip", 4),
    _rem("rem_02", "easy", "Create a Reminders list 'Groceries' with 6 items.", "Groceries", 6),
    _rem("rem_03", "medium", "Make a Reminders list 'Work' with 5 tasks for the week.", "Work", 5),
    _rem("rem_04", "medium", "Create a Reminders list 'Errands' with 4 errands.", "Errands", 4),
    _rem("rem_05", "hard", "Make a Reminders list 'Project Launch' with 7 launch tasks.", "Project Launch", 7),
    _rem("rem_06", "easy", "Create a Reminders list 'Weekend' with 3 things to do this weekend.", "Weekend", 3),
    _rem("rem_07", "medium", "Make a Reminders list 'Health' with 5 healthy habits.", "Health", 5),
    _rem("rem_08", "hard", "Create a Reminders list 'Move' with 8 tasks for moving apartments.", "Move", 8),
    _rem("rem_09", "medium", "Make a Reminders list 'Reading' with 4 books to read.", "Reading", 4),
    _rem("rem_10", "medium", "Create a Reminders list 'Garden' with 5 gardening tasks.", "Garden", 5),

    # ---------------- Pages (export to Desktop) ----------------
    _file("pages_01", "medium", "In Pages write a one-paragraph welcome letter and export it as welcome.pdf to the Desktop.", "welcome.pdf"),
    _file("pages_02", "hard", "In Pages write a simple one-page resume with your name and 3 skills, and export it as resume.pdf to the Desktop.", "resume.pdf"),
    _file("pages_03", "medium", "In Pages write a short thank-you note and export it as thanks.pdf to the Desktop.", "thanks.pdf"),
    _file("pages_04", "hard", "In Pages write a 2-paragraph blog post about productivity and export it as blog.pdf to the Desktop.", "blog.pdf"),
    _file("pages_05", "medium", "In Pages create a flyer with a title 'Garage Sale' and a date, and export it as flyer.pdf to the Desktop.", "flyer.pdf"),
    _file("pages_06", "hard", "In Pages write a formal complaint letter about a late delivery and export it as complaint.pdf to the Desktop.", "complaint.pdf"),
    _file("pages_07", "medium", "In Pages write a short meeting agenda with 4 items and export it as agenda.pdf to the Desktop.", "agenda.pdf"),
    _file("pages_08", "hard", "In Pages write a one-page essay outline about climate and export it as essay.pdf to the Desktop.", "essay.pdf"),
    _file("pages_09", "medium", "In Pages write a birthday invitation and export it as invite.pdf to the Desktop.", "invite.pdf"),
    _file("pages_10", "hard", "In Pages draft a short product description for a coffee mug and export it as product.pdf to the Desktop.", "product.pdf"),

    # ---------------- Numbers (export to Desktop) ----------------
    _file("num_01", "medium", "In Numbers make a table of 3 expenses with amounts, total them, and export as expenses.csv to the Desktop.", "expenses.csv"),
    _file("num_02", "hard", "In Numbers build a weekly schedule (Mon–Fri rows, one activity each) and export as schedule.csv to the Desktop.", "schedule.csv"),
    _file("num_03", "medium", "In Numbers list 5 products and prices and export as prices.csv to the Desktop.", "prices.csv"),
    _file("num_04", "hard", "In Numbers make a simple budget (rent, food, transit, misc) with a total and export as budget.csv to the Desktop.", "budget.csv"),
    _file("num_05", "medium", "In Numbers list the numbers 1 to 10 in a column with their squares beside them, export as squares.csv to the Desktop.", "squares.csv"),
    _file("num_06", "hard", "In Numbers create a 3-person contact table (name, email, phone) and export as contacts.csv to the Desktop.", "contacts.csv"),
    _file("num_07", "medium", "In Numbers make a grade sheet with 4 subjects and scores, and export as grades.csv to the Desktop.", "grades.csv"),
    _file("num_08", "hard", "In Numbers build a 7-day step-count log and export as steps.csv to the Desktop.", "steps.csv"),
    _file("num_09", "medium", "In Numbers list 5 cities and their (approx) populations and export as cities.csv to the Desktop.", "cities.csv"),
    _file("num_10", "hard", "In Numbers make an inventory of 6 items with quantities and export as inventory.csv to the Desktop.", "inventory.csv"),

    # ---------------- Keynote (export to Desktop) ----------------
    _file("key_01", "hard", "In Keynote make a 2-slide deck titled 'My Trip' and export it as trip.pdf to the Desktop.", "trip.pdf"),
    _file("key_02", "hard", "In Keynote create a title slide 'Quarterly Update' and export as update.pdf to the Desktop.", "update.pdf"),
    _file("key_03", "hard", "In Keynote make a 3-slide intro deck about a coffee shop and export as coffee.pdf to the Desktop.", "coffee.pdf"),
    _file("key_04", "hard", "In Keynote create a single slide with a big quote and export as quote.pdf to the Desktop.", "quote.pdf"),
    _file("key_05", "hard", "In Keynote build a 2-slide 'About Me' deck and export as aboutme.pdf to the Desktop.", "aboutme.pdf"),
    _file("key_06", "hard", "In Keynote make a 2-slide product pitch and export as pitch.pdf to the Desktop.", "pitch.pdf"),

    # ---------------- Web research (Chrome / Safari) -> record ----------------
    _note("web_01", "medium", "Look up the population of Japan and record it in a Note titled 'Japan'.", "Japan", 5),
    _note("web_02", "medium", "Find Ada Lovelace's birth and death years, work out her age, and record it in a Note titled 'Ada'.", "Ada", 5),
    _note("web_03", "hard", "Look up the three tallest mountains and list each with its height in a Note titled 'Mountains'.", "Mountains", 20),
    _note("web_04", "hard", "Find when the first iPhone was released and its original price and record both in a Note titled 'iPhone'.", "iPhone", 10),
    _file("web_05", "hard", "Find the current time in Tokyo and save 'Tokyo time: <time>' to tokyo.txt on the Desktop.", "tokyo.txt", "Tokyo"),
    _note("web_06", "medium", "Look up the capital of Australia and record it in a Note titled 'Capital'.", "Capital", 5),
    _note("web_07", "hard", "Find the top 3 highest-grossing films of all time and list them in a Note titled 'Films'.", "Films", 15),
    _note("web_08", "medium", "Look up the speed of light in km/s and record it in a Note titled 'Physics'.", "Physics", 5),
    _note("web_09", "hard", "Find the current USD to EUR rate and record what $500 is in euros in a Note titled 'FX'.", "FX", 5),
    _note("web_10", "medium", "Look up who wrote 'Pride and Prejudice' and record it in a Note titled 'Author'.", "Author", 5),
    _note("web_11", "hard", "Find the boiling point of water in °C and °F and record both in a Note titled 'Boiling'.", "Boiling", 8),
    _note("web_12", "medium", "Look up the largest planet in the solar system and record it in a Note titled 'Planet'.", "Planet", 5),
    _note("web_13", "hard", "Find the year the Berlin Wall fell and 2 sentences about it in a Note titled 'History'.", "History", 20),
    _note("web_14", "medium", "Look up the chemical symbol for gold and record it in a Note titled 'Gold'.", "Gold", 2),
    _note("web_15", "hard", "Find the 3 primary colors and 3 secondary colors and list them in a Note titled 'Colors'.", "Colors", 15),
    _note("web_16", "medium", "Look up the tallest building in the world and its height in a Note titled 'Building'.", "Building", 5),
    _note("web_17", "hard", "Find 3 programming languages and one use-case each in a Note titled 'Languages'.", "Languages", 20),
    _note("web_18", "medium", "Look up the freezing point of water and record it in a Note titled 'Freezing'.", "Freezing", 3),
    _note("web_19", "hard", "Find the current price of Bitcoin and record it with today's date in a Note titled 'BTC'.", "BTC", 5),
    _note("web_20", "medium", "Look up the author of 'The Odyssey' and record it in a Note titled 'Odyssey'.", "Odyssey", 4),
    _note("web_21", "hard", "Find 3 countries in South America and their capitals in a Note titled 'SouthAmerica'.", "SouthAmerica", 20),
    _note("web_22", "medium", "Look up how many continents there are and name them in a Note titled 'Continents'.", "Continents", 20),
    _note("web_23", "hard", "Find the distance from the Earth to the Moon and record it in a Note titled 'Moon'.", "Moon", 5),
    _note("web_24", "medium", "Look up the national animal of China and record it in a Note titled 'Animal'.", "Animal", 4),

    # ---------------- Maps -> record ----------------
    _note("maps_01", "medium", "In Maps find the driving distance from San Francisco to Los Angeles and record it in a Note titled 'Drive'.", "Drive", 3),
    _note("maps_02", "hard", "In Maps find a coffee shop near Times Square, New York and record its name in a Note titled 'Coffee'.", "Coffee", 3),
    _note("maps_03", "medium", "In Maps look up the distance from London to Paris and record it in a Note titled 'Eurotrip'.", "Eurotrip", 3),
    _note("maps_04", "hard", "In Maps find directions from the Golden Gate Bridge to Fisherman's Wharf and record the time in a Note titled 'SF'.", "SF", 3),
    _note("maps_05", "medium", "In Maps find the address of the Empire State Building and record it in a Note titled 'ESB'.", "ESB", 5),
    _note("maps_06", "hard", "In Maps look up a gas station near Stanford University and record its name in a Note titled 'Gas'.", "Gas", 3),

    # ---------------- Calendar / Contacts / Dictionary ----------------
    _note("cal_01", "medium", "In Calendar create an all-day event 'Focus day' next Friday, then record the date in a Note titled 'Focus'.", "Focus", 4),
    _note("cal_02", "hard", "In Calendar make an event 'Dentist' for next Monday at 10am, then record it in a Note titled 'Dentist'.", "Dentist", 4),
    _note("cal_03", "medium", "In Calendar tell me what weekday the 15th of next month is and record it in a Note titled 'Weekday'.", "Weekday", 3),
    _note("cal_04", "hard", "In Calendar create 'Gym' events for Mon, Wed, Fri next week and record them in a Note titled 'Gym'.", "Gym", 5),
    _note("con_01", "medium", "In Contacts (read only, don't edit) count how many contacts have a phone number and record it in a Note titled 'Contacts'.", "Contacts", 3),
    _note("con_02", "hard", "In Contacts (read only) find the first contact alphabetically and record their name in a Note titled 'FirstContact'.", "FirstContact", 3),
    _file("dict_01", "medium", "In Dictionary look up the word 'ephemeral' and save its definition to word1.txt on the Desktop.", "word1.txt", "ephemeral"),
    _file("dict_02", "medium", "In Dictionary look up 'serendipity' and save its definition to word2.txt on the Desktop.", "word2.txt", "serendipity"),
    _file("dict_03", "hard", "Look up 'quixotic' and 'laconic' and save both definitions to words.txt on the Desktop.", "words.txt", "laconic"),
    _note("dict_04", "medium", "In Dictionary find a synonym for 'happy' and record it in a Note titled 'Synonym'.", "Synonym", 3),
    _note("dict_05", "hard", "Look up the etymology of the word 'computer' and record a 1-sentence summary in a Note titled 'Etymology'.", "Etymology", 15),

    # ---------------- Preview / Freeform / Stickies ----------------
    _note("prev_01", "hard", "In Preview open a sample image (or a screenshot), read its pixel dimensions, and record them in a Note titled 'Image'.", "Image", 3),
    _file("prev_02", "hard", "Take a screenshot of the desktop and save it as shot.png on the Desktop.", "shot.png"),
    _note("free_01", "hard", "In Freeform create a board with a title 'Brainstorm' and 3 sticky ideas, then record the 3 ideas in a Note titled 'Brainstorm'.", "Brainstorm", 15),
    _note("free_02", "hard", "In Freeform make a simple mind map with a center topic and 3 branches, then list them in a Note titled 'MindMap'.", "MindMap", 15),
    _note("stick_01", "easy", "In Stickies add a sticky that says 'Call the dentist'.", "Call the dentist", 5),
    _note("stick_02", "medium", "In Stickies create a note with a 3-item to-do list, then copy it into a Note titled 'StickyTodo'.", "StickyTodo", 10),
    _note("stick_03", "easy", "In Stickies add a sticky with today's top priority, then record it in a Note titled 'Priority'.", "Priority", 5),

    # ---------------- Music / Weather / Stocks -> record ----------------
    _note("music_01", "hard", "In Music create a playlist called 'Focus' and record that you made it in a Note titled 'Playlist'.", "Playlist", 5),
    _note("music_02", "medium", "In Music search for a song by The Beatles and record its title in a Note titled 'Song'.", "Song", 3),
    _note("music_03", "hard", "In Music find an album by Taylor Swift and record its name and year in a Note titled 'Album'.", "Album", 5),
    _note("weather_01", "medium", "In the Weather app find today's high for New York and record it in a Note titled 'NYC'.", "NYC", 3),
    _note("weather_02", "medium", "In Weather find the current temperature in London and record it in a Note titled 'London'.", "London", 3),
    _note("weather_03", "hard", "In Weather compare today's high in San Francisco vs Miami and record both in a Note titled 'Compare'.", "Compare", 5),
    _note("weather_04", "medium", "In Weather find the chance of rain tomorrow where you are and record it in a Note titled 'Rain'.", "Rain", 3),
    _note("stock_01", "medium", "In Stocks look up Apple's current price and record it in a Note titled 'AAPL'.", "AAPL", 3),
    _note("stock_02", "medium", "In Stocks find Tesla's price and record it in a Note titled 'TSLA'.", "TSLA", 3),
    _note("stock_03", "hard", "In Stocks compare Apple and Microsoft prices and record both in a Note titled 'Compare2'.", "Compare2", 5),
    _note("stock_04", "medium", "In Stocks look up the price of the S&P 500 index and record it in a Note titled 'SP500'.", "SP500", 3),
    _note("stock_05", "hard", "In Stocks find Amazon's price and its day change and record both in a Note titled 'AMZN'.", "AMZN", 5),

    # ---------------- System Settings -> record ----------------
    _file("sys_01", "easy", "Find this Mac's macOS version and save it to sysinfo.txt on the Desktop.", "sysinfo.txt", "macOS"),
    _note("sys_02", "medium", "In System Settings find this Mac's computer name and record it in a Note titled 'MacName'.", "MacName", 3),
    _note("sys_03", "medium", "In System Settings find how much storage is free and record it in a Note titled 'Storage'.", "Storage", 3),
    _note("sys_04", "hard", "In System Settings find the current Wi-Fi network name and record it in a Note titled 'WiFi'.", "WiFi", 3),
    _note("sys_05", "medium", "In System Settings find the current battery percentage and record it in a Note titled 'Battery'.", "Battery", 2),
    _note("sys_06", "hard", "In System Settings find the display resolution and record it in a Note titled 'Display'.", "Display", 3),

    # ---------------- Code editors (Sublime Text / Cursor / TextEdit) ----------------
    _file("code_01", "medium", "In a text editor write a Python function that adds two numbers and save it as add.py on the Desktop.", "add.py", "def"),
    _file("code_02", "medium", "Write a bash script that prints 'hello' and save it as hi.sh on the Desktop.", "hi.sh", "echo"),
    _file("code_03", "hard", "Write a Python function that returns the factorial of n and save it as factorial.py on the Desktop.", "factorial.py", "factorial"),
    _file("code_04", "medium", "Write a JSON object with name, age and city and save it as data.json on the Desktop.", "data.json", "city"),
    _file("code_05", "hard", "Write an HTML page with a heading 'Glance' and a paragraph and save it as page.html on the Desktop.", "page.html", "<h1"),
    _file("code_06", "medium", "Write a CSS rule that makes text blue and save it as style.css on the Desktop.", "style.css", "blue"),
    _file("code_07", "hard", "Write a Python list comprehension that squares 1..5 and save it as squares.py on the Desktop.", "squares.py", "for"),
    _file("code_08", "medium", "Write a Markdown file with a title and 3 bullet points and save it as readme.md on the Desktop.", "readme.md", "-"),
    _file("code_09", "hard", "Write a SQL statement that selects all rows from a table 'users' and save it as query.sql on the Desktop.", "query.sql", "SELECT"),
    _file("code_10", "medium", "Write a Python 'Hello, World!' program and save it as hello.py on the Desktop.", "hello.py", "print"),

    # ---------------- Books / Font Book / Shortcuts ----------------
    _note("book_01", "hard", "In Books open the store or library, pick any book, and record its title and author in a Note titled 'Book'.", "Book", 5),
    _note("book_02", "medium", "In Books find a free classic (e.g. by Jane Austen) and record its title in a Note titled 'Classic'.", "Classic", 5),
    _note("font_01", "medium", "In Font Book find a font whose name starts with 'A' and record it in a Note titled 'Font'.", "Font", 3),
    _note("font_02", "hard", "In Font Book count roughly how many fonts are installed (a ballpark) and record it in a Note titled 'FontCount'.", "FontCount", 2),
    _note("short_01", "hard", "Open Shortcuts, pick any built-in shortcut, and record its name in a Note titled 'Shortcut'.", "Shortcut", 3),
    _note("short_02", "medium", "In Shortcuts find a shortcut related to text and record its name in a Note titled 'TextShortcut'.", "TextShortcut", 3),

    # ---------------- extra coverage (bring the suite to 150) ----------------
    _file("text_13", "easy", "In TextEdit write the numbers 1 through 20 separated by spaces and save as count.txt on the Desktop.", "count.txt", "20"),
    _note("notes_15", "easy", "Make a Note titled 'Today' with 3 things you want to get done today.", "Today", 10),
    _note("con_03", "medium", "In Contacts (read only) find how many contacts have an email address and record it in a Note titled 'Emails'.", "Emails", 2),
    _note("prev_03", "hard", "In Preview open any image and use the info panel to record its file size in a Note titled 'FileSize'.", "FileSize", 3),
    _note("book_03", "medium", "In Books browse the store's top charts and record the #1 book's title in a Note titled 'TopBook'.", "TopBook", 4),
    _note("free_03", "hard", "In Freeform create a board with 4 connected boxes forming a simple flowchart, then describe it in a Note titled 'Flowchart'.", "Flowchart", 15),
]

# A quick end-to-end sanity subset.
SMOKE: list[Task] = [t for t in TASKS if t.id in {"text_01", "notes_01", "rem_01", "web_01", "code_10"}]
