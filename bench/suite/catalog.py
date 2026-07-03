"""A ~1000-task catalog spanning the machine's real apps.

Hand-writing 1000 task literals would be an unmaintainable wall, so this is a generator:
compact per-app banks + parametric families (cities, tickers, words, research topics)
that expand to ~1000 distinct, realistic tasks. Each task is verifiable where possible
(file export / Notes / Reminders) and `manual` where the result lives inside the app —
an After Effects comp, a Premiere edit, a played video — which no script can check.

    from bench.suite.catalog import build
    TASKS = build()                      # list[Task], ~1000

    python -m bench.suite.catalog        # prints the per-app + verifier breakdown
    python -m bench.suite.catalog --dump # also writes results/catalog.md (human-readable)

Run a slice with the existing harness by pointing it at build() (see runner). Creative
tasks are benign: they create throwaway projects and export to the Desktop; nothing is
sent, purchased, or deleted.
"""
# ruff: noqa: E501 — a data file; one-line task prompts read better than wrapped.

from __future__ import annotations

from functools import partial

from . import verifiers as v
from .model import Task

# --------------------------------------------------------------------------- constructors
_ids: dict[str, int] = {}


def _id(app: str) -> str:
    _ids[app] = _ids.get(app, 0) + 1
    return f"{app}_{_ids[app]:03d}"


def F(app: str, diff: str, prompt: str, name: str, contains: str | None = None) -> Task:
    return Task(_id(app), diff, prompt, partial(v.desktop_file, name, contains), partial(v.rm_desktop_file, name))


def N(app: str, diff: str, prompt: str, title: str, min_chars: int = 8) -> Task:
    return Task(_id(app), diff, prompt, partial(v.note_exists, title, min_chars), partial(v.delete_note, title))


def R(app: str, diff: str, prompt: str, listname: str, n: int) -> Task:
    return Task(_id(app), diff, prompt, partial(v.reminder_list, listname, n))


def M(app: str, diff: str, prompt: str, check: str) -> Task:
    """A task whose result lives inside the app — verified by hand (excluded from the auto rate)."""
    return Task(_id(app), diff, prompt, partial(v.manual, f"check by hand: {check}"))


# --------------------------------------------------------------------------- parametric data
CITIES = ["New York", "London", "Tokyo", "Paris", "Sydney", "Mumbai", "Berlin", "Toronto",
          "Dubai", "Singapore", "Cairo", "Rio de Janeiro", "Moscow", "Seoul", "Mexico City",
          "Los Angeles", "Chicago", "Miami", "Istanbul", "Bangkok", "Madrid", "Rome",
          "Amsterdam", "Vienna", "Stockholm", "Oslo", "Lisbon", "Athens", "Dublin",
          "Prague", "Warsaw", "Helsinki"]
TICKERS = [("AAPL", "Apple"), ("MSFT", "Microsoft"), ("TSLA", "Tesla"), ("AMZN", "Amazon"),
           ("GOOGL", "Alphabet"), ("NVDA", "Nvidia"), ("META", "Meta"), ("NFLX", "Netflix"),
           ("AMD", "AMD"), ("INTC", "Intel"), ("DIS", "Disney"), ("BA", "Boeing"),
           ("JPM", "JPMorgan"), ("V", "Visa"), ("WMT", "Walmart"), ("KO", "Coca-Cola"),
           ("PEP", "PepsiCo"), ("ORCL", "Oracle"), ("CRM", "Salesforce"), ("UBER", "Uber")]
WORDS = ["ephemeral", "serendipity", "quixotic", "laconic", "ubiquitous", "petrichor",
         "sonder", "ineffable", "mellifluous", "eloquent", "resilient", "paradigm",
         "catalyst", "nuance", "ostensible", "pragmatic", "esoteric", "verbose",
         "cogent", "salient", "gregarious", "ephemera", "juxtapose", "quintessential",
         "surreptitious", "ephemeralize", "obfuscate", "perfunctory", "sanguine",
         "taciturn", "vociferous", "wistful", "zealous", "ambivalent", "brevity",
         "candor", "diligent", "empathy", "fortitude", "gratitude"]
TOPICS = ["the speed of light", "the population of Brazil", "who painted the Mona Lisa",
          "the tallest mountain in Africa", "when the Eiffel Tower was built",
          "the largest ocean on Earth", "the inventor of the telephone",
          "the boiling point of water", "the capital of Canada", "the longest river in the world",
          "the first person on the Moon", "the chemical symbol for iron",
          "the author of Hamlet", "the freezing point of mercury", "the fastest land animal",
          "the number of bones in the human body", "the currency of Japan",
          "the year World War II ended", "the smallest planet", "the national bird of the USA",
          "the deepest lake in the world", "the largest desert", "the hardest natural mineral",
          "the human body's largest organ", "the distance to the Sun",
          "the population of Nigeria", "who wrote Pride and Prejudice", "the capital of Australia",
          "the highest waterfall in the world", "when the Great Wall of China was built",
          "the largest mammal", "the inventor of the light bulb", "the melting point of gold",
          "the capital of Egypt", "the widest river in the world", "the first woman in space",
          "the atomic number of oxygen", "the composer of the Ninth Symphony",
          "the number of countries in Africa", "the speed of sound",
          "the largest island in the world", "who discovered penicillin",
          "the capital of Argentina", "the tallest animal", "the year the internet was invented",
          "the largest planet's number of moons", "the national flower of Japan",
          "the length of the Amazon river", "the oldest university in the world",
          "the deepest point in the ocean"]
ARTISTS = ["The Beatles", "Taylor Swift", "Miles Davis", "Queen", "Beyoncé", "Bob Dylan",
           "Daft Punk", "Kendrick Lamar", "Adele", "Radiohead", "Coldplay", "Drake",
           "Pink Floyd", "Nina Simone", "David Bowie", "Frank Ocean", "Fleetwood Mac",
           "The Weeknd", "Stevie Wonder", "Billie Eilish", "Led Zeppelin", "Amy Winehouse",
           "Prince", "Johnny Cash"]
PLACES = [("San Francisco", "Los Angeles"), ("London", "Paris"), ("New York", "Boston"),
          ("Seattle", "Portland"), ("Chicago", "Detroit"), ("Austin", "Houston"),
          ("Denver", "Salt Lake City"), ("Miami", "Orlando"), ("Toronto", "Montreal"),
          ("Berlin", "Munich"), ("Madrid", "Barcelona"), ("Rome", "Florence"),
          ("Tokyo", "Osaka"), ("Sydney", "Melbourne"), ("Dublin", "Belfast"),
          ("Amsterdam", "Rotterdam"), ("Vancouver", "Calgary"), ("Phoenix", "Las Vegas"),
          ("Atlanta", "Nashville"), ("San Diego", "Sacramento")]
# effect / operation banks for the creative apps — each expands to a distinct task
AE_EFFECTS = ["Gaussian Blur", "Glow", "Drop Shadow", "Fast Box Blur", "Tint", "Curves",
              "Levels", "Fractal Noise", "Turbulent Displace", "Motion Tile", "Roughen Edges",
              "Radial Blur", "Sharpen", "Hue/Saturation", "Brightness & Contrast", "CC Vignette"]
PR_EFFECTS = ["Gaussian Blur", "Lumetri Color", "Warp Stabilizer", "Crop", "Tint",
              "Directional Blur", "Ultra Key", "Brightness & Contrast", "Black & White"]
PR_TRANSITIONS = ["Cross Dissolve", "Dip to Black", "Dip to White", "Push", "Slide",
                  "Film Dissolve", "Wipe", "Cross Zoom"]
PHOTO_FILTERS = ["Vivid", "Dramatic", "Mono", "Silvertone", "Noir", "Vivid Warm",
                 "Dramatic Cool", "Vivid Cool", "Dramatic Warm"]
POPULAR_APPS = ["Slack", "Spotify", "Notion", "Zoom", "Trello", "Figma", "Discord",
                "Telegram", "VLC", "1Password", "Todoist", "Evernote", "Dropbox", "Bear",
                "Fantastical", "Things", "Craft", "Raycast", "Obsidian", "WhatsApp"]
SITES = [("apple.com", "Apple"), ("wikipedia.org", "Wikipedia"), ("github.com", "GitHub"),
         ("nytimes.com", "NYT"), ("bbc.com", "BBC"), ("stackoverflow.com", "SO"),
         ("reddit.com", "Reddit"), ("amazon.com", "Amazon"), ("python.org", "Python"),
         ("openai.com", "OpenAI"), ("news.ycombinator.com", "HackerNews"),
         ("nasa.gov", "NASA"), ("weather.gov", "WeatherGov"), ("archive.org", "Archive")]


# --------------------------------------------------------------------------- creative / video
def after_effects() -> list[Task]:
    a = "ae"
    base = [
        F(a, "hard", "In After Effects create a new composition (1920x1080, 5s), add a solid background, and export a frame as ae_frame.png to the Desktop.", "ae_frame.png"),
        F(a, "hard", "In After Effects make a 3-second comp with a text layer reading 'GLANCE' and render it to ae_title.mov on the Desktop.", "ae_title.mov"),
        M(a, "hard", "In After Effects add a Gaussian Blur effect to a text layer and keyframe its blurriness from 0 to 20 over 2 seconds.", "text layer has an animated Gaussian Blur"),
        M(a, "hard", "In After Effects create a shape layer with a circle and animate its position from left to right across the comp.", "circle animates left to right"),
        M(a, "hard", "In After Effects apply a Glow effect to a text layer and increase the glow threshold.", "text layer has a Glow effect"),
        M(a, "medium", "In After Effects import an image and scale it to fit the composition frame.", "image scaled to frame"),
        M(a, "hard", "In After Effects parent a null object to a text layer and rotate the null.", "text layer parented to a rotating null"),
        M(a, "hard", "In After Effects add a wiggle expression to the position of a layer.", "layer position has a wiggle expression"),
        M(a, "medium", "In After Effects change the composition background color to dark blue.", "comp background is dark blue"),
        M(a, "hard", "In After Effects precompose two layers into a single nested comp.", "two layers precomposed"),
        F(a, "hard", "In After Effects create a 2-second fade-in on a text layer and render to ae_fade.mov on the Desktop.", "ae_fade.mov"),
        M(a, "hard", "In After Effects add a Drop Shadow to a shape layer and offset it.", "shape has an offset drop shadow"),
        M(a, "medium", "In After Effects trim a layer's in-point to start 1 second into the comp.", "layer starts at 1s"),
        M(a, "hard", "In After Effects enable motion blur on an animated layer and turn on the comp motion-blur switch.", "motion blur enabled"),
        M(a, "hard", "In After Effects use the Ellipse tool to draw a mask on a solid and feather it.", "feathered elliptical mask"),
    ]
    base += [M(a, "hard", f"In After Effects apply the {fx} effect to a layer and adjust one of its parameters.", f"{fx} effect applied") for fx in AE_EFFECTS]
    base += [M(a, "hard", f"In After Effects keyframe the {prop} of a layer over 2 seconds.", f"{prop} keyframed")
             for prop in ["Opacity", "Scale", "Rotation", "Position", "Anchor Point"]]
    return base


def premiere() -> list[Task]:
    p = "pr"
    base = [
        F(p, "hard", "In Premiere Pro create a new project and sequence, add a color matte clip, and export the sequence to pr_out.mp4 on the Desktop.", "pr_out.mp4"),
        M(p, "hard", "In Premiere Pro import a video clip and add it to the timeline.", "clip on the timeline"),
        M(p, "hard", "In Premiere Pro make a razor cut on a timeline clip and delete the second half.", "clip cut and trimmed"),
        M(p, "hard", "In Premiere Pro add a Cross Dissolve transition between two clips.", "cross dissolve between clips"),
        M(p, "medium", "In Premiere Pro add a title with the text 'My Video' to the timeline.", "title clip added"),
        M(p, "hard", "In Premiere Pro apply the Lumetri Color effect to a clip and raise the exposure.", "Lumetri exposure raised"),
        M(p, "hard", "In Premiere Pro add a keyframed opacity fade-out at the end of a clip.", "opacity fades out"),
        M(p, "medium", "In Premiere Pro mute the audio on a timeline clip.", "clip audio muted"),
        M(p, "hard", "In Premiere Pro speed up a clip to 200% using Speed/Duration.", "clip at 200% speed"),
        M(p, "hard", "In Premiere Pro add a background music track and lower its volume by 6 dB.", "music track at -6dB"),
        F(p, "hard", "In Premiere Pro export a 5-second sequence as pr_clip.mov to the Desktop.", "pr_clip.mov"),
        M(p, "medium", "In Premiere Pro rename a timeline clip in the project panel.", "clip renamed"),
        M(p, "hard", "In Premiere Pro nest two clips into a single nested sequence.", "clips nested"),
        M(p, "hard", "In Premiere Pro add the Gaussian Blur video effect to a clip.", "clip has Gaussian Blur"),
    ]
    base += [M(p, "hard", f"In Premiere Pro apply the {fx} effect to a timeline clip.", f"{fx} applied") for fx in PR_EFFECTS]
    base += [M(p, "hard", f"In Premiere Pro add a {tr} transition between two clips.", f"{tr} added") for tr in PR_TRANSITIONS]
    return base


def media_encoder() -> list[Task]:
    a = "me"
    return [
        F(a, "hard", "In Adobe Media Encoder add a video file to the queue, set the format to H.264, and encode it to me_out.mp4 on the Desktop.", "me_out.mp4"),
        M(a, "hard", "In Media Encoder create a preset for 1080p H.264 at 10 Mbps.", "1080p H.264 preset exists"),
        M(a, "medium", "In Media Encoder add a watch folder.", "watch folder added"),
        F(a, "hard", "In Media Encoder transcode a clip to a GIF and save as me_out.gif on the Desktop.", "me_out.gif"),
        M(a, "medium", "In Media Encoder change an item's output format to QuickTime.", "output set to QuickTime"),
        M(a, "hard", "In Media Encoder set the output frame rate to 24 fps for a queued item.", "output at 24fps"),
    ]


def capcut() -> list[Task]:
    a = "capcut"
    return [
        F(a, "hard", "In CapCut create a project, add a text clip 'Hello', and export it as capcut_out.mp4 to the Desktop.", "capcut_out.mp4"),
        M(a, "medium", "In CapCut add a video to the timeline and split it in the middle.", "clip split"),
        M(a, "hard", "In CapCut apply a filter to a clip and adjust its intensity.", "filter applied"),
        M(a, "medium", "In CapCut add a sticker to the canvas.", "sticker added"),
        M(a, "hard", "In CapCut add captions to a clip and change the font.", "captions added"),
        M(a, "medium", "In CapCut add a fade-in transition to the first clip.", "fade-in added"),
        M(a, "hard", "In CapCut add background music and trim it to the video length.", "music trimmed to length"),
        F(a, "hard", "In CapCut export a 720p vertical video as capcut_vert.mp4 on the Desktop.", "capcut_vert.mp4"),
    ]


def screen_studio() -> list[Task]:
    a = "screenstudio"
    return [
        F(a, "hard", "In Screen Studio record a 3-second screen clip and export it as ss_rec.mp4 to the Desktop.", "ss_rec.mp4"),
        M(a, "medium", "In Screen Studio change the recording's background to a gradient.", "gradient background"),
        M(a, "hard", "In Screen Studio add an auto-zoom to a click in a recording.", "auto-zoom on click"),
        M(a, "medium", "In Screen Studio adjust the cursor size in a recording.", "cursor size changed"),
        M(a, "hard", "In Screen Studio add rounded corners and a shadow to the recording frame.", "rounded corners + shadow"),
        M(a, "medium", "In Screen Studio set the export resolution to 1080p.", "export at 1080p"),
    ]


def imovie() -> list[Task]:
    a = "imovie"
    return [
        F(a, "hard", "In iMovie create a project, add a title card 'My Trip', and export it as imovie_out.mp4 to the Desktop.", "imovie_out.mp4"),
        M(a, "medium", "In iMovie add a clip to the timeline and trim its start.", "clip trimmed"),
        M(a, "hard", "In iMovie apply the 'Ken Burns' effect to a photo.", "Ken Burns applied"),
        M(a, "medium", "In iMovie add a cross-dissolve transition between two clips.", "transition added"),
        M(a, "hard", "In iMovie add background music from the built-in library.", "music added"),
        M(a, "medium", "In iMovie apply a black-and-white filter to a clip.", "B&W filter"),
        M(a, "hard", "In iMovie add a slow-motion effect to a clip.", "slow-motion applied"),
        F(a, "medium", "In iMovie export the current project as imovie_final.mov to the Desktop.", "imovie_final.mov"),
    ]


def garageband() -> list[Task]:
    a = "garageband"
    return [
        F(a, "hard", "In GarageBand create a project, record 4 bars of a software instrument, and export it as gb_song.m4a to the Desktop.", "gb_song.m4a"),
        M(a, "medium", "In GarageBand add a drummer track.", "drummer track added"),
        M(a, "hard", "In GarageBand add a software instrument track and play a few notes with the musical typing keyboard.", "notes recorded"),
        M(a, "medium", "In GarageBand change the project tempo to 120 BPM.", "tempo 120"),
        M(a, "hard", "In GarageBand add an Apple Loop to the timeline.", "loop added"),
        M(a, "medium", "In GarageBand add reverb to a track.", "reverb added"),
        M(a, "hard", "In GarageBand duplicate a region and move it 4 bars later.", "region duplicated"),
        F(a, "medium", "In GarageBand export the current song as gb_export.mp3 to the Desktop.", "gb_export.mp3"),
    ]


def photos() -> list[Task]:
    a = "photos"
    return [
        M(a, "medium", "In Photos open any image and apply the 'Vivid' filter.", "Vivid filter applied"),
        M(a, "medium", "In Photos crop a photo to a square.", "photo cropped square"),
        M(a, "hard", "In Photos create a new album called 'Glance Test'.", "album 'Glance Test' exists"),
        F(a, "medium", "In Photos export any photo as photos_out.jpg to the Desktop.", "photos_out.jpg"),
        M(a, "medium", "In Photos rotate a photo 90 degrees.", "photo rotated"),
        M(a, "hard", "In Photos adjust the brightness and contrast of a photo.", "brightness/contrast adjusted"),
        M(a, "medium", "In Photos mark a photo as a Favorite.", "photo favorited"),
        M(a, "hard", "In Photos use auto-enhance on a photo.", "auto-enhance applied"),
    ] + [M(a, "medium", f"In Photos apply the '{f}' filter to any photo.", f"{f} filter applied") for f in PHOTO_FILTERS]


def preview() -> list[Task]:
    a = "preview"
    return [
        F(a, "medium", "Take a screenshot of the desktop and save it as preview_shot.png on the Desktop.", "preview_shot.png"),
        M(a, "medium", "In Preview open an image and use Markup to draw a red rectangle.", "red rectangle drawn"),
        F(a, "hard", "In Preview open an image, rotate it, and export it as preview_rot.png to the Desktop.", "preview_rot.png"),
        M(a, "medium", "In Preview add a text annotation to an image.", "text annotation added"),
        F(a, "hard", "In Preview open an image and export it as a PDF named preview_doc.pdf on the Desktop.", "preview_doc.pdf"),
        M(a, "medium", "In Preview use the crop tool on an image.", "image cropped"),
        N(a, "medium", "In Preview open any image, read its dimensions from the Inspector, and record them in a Note titled 'ImageDims'.", "ImageDims", 3),
        M(a, "hard", "In Preview highlight text in a PDF.", "PDF text highlighted"),
    ]


def quicktime() -> list[Task]:
    a = "quicktime"
    return [
        F(a, "hard", "In QuickTime Player record a 3-second screen recording and save it as qt_rec.mov on the Desktop.", "qt_rec.mov"),
        M(a, "medium", "In QuickTime Player open a video and trim the first 2 seconds.", "video trimmed"),
        M(a, "medium", "In QuickTime Player play a video and set it to loop.", "loop enabled"),
        F(a, "hard", "In QuickTime Player make an audio recording of 2 seconds and save as qt_audio.m4a on the Desktop.", "qt_audio.m4a"),
        M(a, "medium", "In QuickTime Player split a clip into two.", "clip split"),
    ]


# --------------------------------------------------------------------------- docs / iWork / text
def pages() -> list[Task]:
    a = "pages"
    prompts = [
        ("welcome letter", "welcome.pdf"), ("a one-page resume with 3 skills", "resume.pdf"),
        ("a thank-you note", "thanks.pdf"), ("a 2-paragraph blog post about focus", "blog.pdf"),
        ("a flyer titled 'Garage Sale' with a date", "flyer.pdf"), ("a formal complaint letter", "complaint.pdf"),
        ("a meeting agenda with 4 items", "agenda.pdf"), ("a one-page essay outline about climate", "essay.pdf"),
        ("a birthday invitation", "invite.pdf"), ("a product description for a coffee mug", "product.pdf"),
        ("a cover letter for a designer role", "cover.pdf"), ("a packing checklist", "checklist.pdf"),
        ("a short newsletter with two sections", "newsletter.pdf"), ("a recipe card for pancakes", "recipe.pdf"),
        ("a business memo about a deadline", "memo.pdf"), ("a poster for a concert", "poster.pdf"),
        ("a two-column brochure about a park", "brochure.pdf"), ("a formal apology letter", "apology.pdf"),
        ("a bio paragraph for a website", "bio.pdf"), ("a certificate of achievement", "certificate.pdf"),
    ]
    tasks = [F(a, "medium", f"In Pages write {desc} and export it as {name} to the Desktop.", name) for desc, name in prompts]
    tasks += [
        M(a, "medium", "In Pages insert a 3x3 table and fill the first row with headers.", "3x3 table with headers"),
        M(a, "hard", "In Pages add a bulleted list and change the bullet style.", "bulleted list with custom bullets"),
        M(a, "medium", "In Pages change the document font to Helvetica and the size to 14.", "font Helvetica 14"),
        M(a, "hard", "In Pages insert a shape and align it to the center of the page.", "centered shape"),
        M(a, "medium", "In Pages add a header with the page title.", "header added"),
    ]
    return tasks


def numbers() -> list[Task]:
    a = "num"
    prompts = [
        ("3 expenses with amounts, total them", "expenses.csv"), ("a Mon-Fri schedule, one activity each", "schedule.csv"),
        ("5 products and prices", "prices.csv"), ("a budget (rent, food, transit, misc) with a total", "budget.csv"),
        ("1 to 10 with their squares", "squares.csv"), ("3 contacts (name, email, phone)", "contacts.csv"),
        ("a grade sheet with 4 subjects and scores", "grades.csv"), ("a 7-day step-count log", "steps.csv"),
        ("5 cities and their populations", "cities.csv"), ("a 6-item inventory with quantities", "inventory.csv"),
        ("monthly rainfall for 6 months", "rainfall.csv"), ("a savings plan for 12 months", "savings.csv"),
        ("5 employees and salaries", "salaries.csv"), ("a workout log for a week", "workout.csv"),
        ("temperatures for 7 days", "temps.csv"), ("a book list with authors and ratings", "books.csv"),
        ("a to-do list with priorities", "todo.csv"), ("sales for 4 quarters", "sales.csv"),
        ("a mileage log for 5 trips", "mileage.csv"), ("a recipe's ingredients with quantities", "ingredients.csv"),
    ]
    tasks = [F(a, "medium", f"In Numbers build a table of {desc} and export it as {name} to the Desktop.", name) for desc, name in prompts]
    tasks += [
        M(a, "hard", "In Numbers add a SUM formula that totals a column of numbers.", "SUM total cell"),
        M(a, "hard", "In Numbers create a bar chart from a small table.", "bar chart created"),
        M(a, "medium", "In Numbers format a column as currency.", "column formatted as currency"),
        M(a, "hard", "In Numbers add an AVERAGE formula for a row of scores.", "AVERAGE cell"),
        M(a, "medium", "In Numbers freeze the header row of a table.", "header row frozen"),
    ]
    return tasks


def keynote() -> list[Task]:
    a = "key"
    prompts = [
        ("a 2-slide deck titled 'My Trip'", "trip.pdf"), ("a title slide 'Quarterly Update'", "update.pdf"),
        ("a 3-slide intro about a coffee shop", "coffee.pdf"), ("a single slide with a big quote", "quote.pdf"),
        ("a 2-slide 'About Me' deck", "aboutme.pdf"), ("a 2-slide product pitch", "pitch.pdf"),
        ("a 3-slide roadmap", "roadmap.pdf"), ("a welcome slide for a workshop", "workshop.pdf"),
        ("a 2-slide comparison of two options", "compare.pdf"), ("a closing 'Thank You' slide", "thankyou.pdf"),
    ]
    tasks = [F(a, "hard", f"In Keynote make {desc} and export it as {name} to the Desktop.", name) for desc, name in prompts]
    tasks += [
        M(a, "medium", "In Keynote apply a theme to a new presentation.", "theme applied"),
        M(a, "hard", "In Keynote add a slide transition (Dissolve) between two slides.", "dissolve transition"),
        M(a, "medium", "In Keynote insert a bulleted list on a slide.", "bulleted list on slide"),
        M(a, "hard", "In Keynote add a build animation to a text box.", "build animation added"),
        M(a, "medium", "In Keynote change the slide background color.", "background color changed"),
    ]
    return tasks


def textedit() -> list[Task]:
    a = "text"
    prompts = [
        ("'Hello from Glance'", "hello.txt", "Hello from Glance"), ("a 4-line poem about mountains", "poem.txt", None),
        ("a 3-line haiku about the ocean", "ocean.txt", None), ("a 6-sentence story about a robot", "story.txt", None),
        ("a cover letter that starts with 'Dear'", "letter.txt", "Dear"), ("the 12 months, one per line", "months.txt", "December"),
        ("a 5-item packing list", "packing.txt", None), ("two short paragraphs on coffee and tea", "drinks.txt", "tea"),
        ("a pancakes recipe with ingredients", "pancakes.txt", "flour"), ("today's date and 'daily log'", "log.txt", "daily log"),
        ("the first 10 Fibonacci numbers, comma-separated", "fib.txt", "34"), ("a shopping list of 8 items", "shopping.txt", None),
        ("a short bio in 3 sentences", "bio.txt", None), ("the numbers 1 to 20 space-separated", "count.txt", "20"),
        ("a limerick", "limerick.txt", None), ("a list of 5 movie titles", "movies.txt", None),
        ("a motivational quote and its author", "quote.txt", None), ("a paragraph about your favorite city", "city.txt", None),
        ("a 4-item numbered to-do list", "tasks.txt", None), ("the alphabet backwards", "alpha.txt", "ZYX"),
        ("a gratitude list of 5 things", "gratitude.txt", None), ("the days of the week", "days.txt", "Sunday"),
        ("a 3-line thank-you message", "ty.txt", None), ("a list of 6 countries", "countries.txt", None),
        ("your top 5 goals for the year", "goals.txt", None), ("a short apology note", "sorry.txt", None),
        ("the numbers 1 to 10 and their doubles", "doubles.txt", "20"), ("a 4-line rhyming poem", "rhyme.txt", None),
        ("a packing list for a ski trip", "ski.txt", None), ("three fun facts about space", "space.txt", None),
        ("a to-do list for tomorrow", "tomorrow.txt", None), ("a list of 5 programming languages", "langs.txt", None),
    ]
    return [F(a, "easy" if i < 6 else "medium", f"In TextEdit write {desc} and save it as {name} on the Desktop.", name, contains)
            for i, (desc, name, contains) in enumerate(prompts)]


# --------------------------------------------------------------------------- code editors
def _code_tasks(app: str, editor: str) -> list[Task]:
    specs = [
        ("a Python function that adds two numbers", "add.py", "def"),
        ("a bash script that prints hello", "hi.sh", "echo"),
        ("a Python factorial function", "factorial.py", "factorial"),
        ("a JSON object with name, age and city", "data.json", "city"),
        ("an HTML page with an <h1> heading 'Glance'", "page.html", "<h1"),
        ("a CSS rule making text blue", "style.css", "blue"),
        ("a Python list comprehension squaring 1..5", "squares.py", "for"),
        ("a Markdown file with a title and 3 bullets", "readme.md", "-"),
        ("a SQL SELECT of all rows from 'users'", "query.sql", "SELECT"),
        ("a Python 'Hello, World!' program", "hello.py", "print"),
        ("a JavaScript function that reverses a string", "rev.js", "function"),
        ("a YAML config with three keys", "config.yaml", ":"),
        ("a Python class 'Dog' with a bark method", "dog.py", "class"),
        ("a TypeScript interface for a User", "user.ts", "interface"),
        ("a Go function that returns the max of two ints", "max.go", "func"),
        ("a Rust function that prints hello", "hello.rs", "fn"),
        ("a C program with a main that returns 0", "main.c", "int main"),
        ("a Java class HelloWorld with a main method", "Hello.java", "class"),
        ("a shell script that loops 1 to 5", "loop.sh", "for"),
        ("a Python dict with 3 key-value pairs", "map.py", "{"),
        ("a regex that matches an email in a text file", "regex.txt", "@"),
        ("a Dockerfile that starts from python:3.12", "Dockerfile.txt", "FROM"),
    ]
    return [F(app, "medium", f"In {editor} write {desc} and save it as {app}_{name} on the Desktop.", f"{app}_{name}", contains)
            for desc, name, contains in specs]


def cursor() -> list[Task]:
    return _code_tasks("cursor", "Cursor")


def sublime() -> list[Task]:
    return _code_tasks("sublime", "Sublime Text")


def xcode() -> list[Task]:
    a = "xcode"
    return [
        M(a, "hard", "In Xcode create a new Swift command-line project.", "new Swift project created"),
        M(a, "hard", "In Xcode add a Swift file printing 'Hello' and build it.", "project builds"),
        M(a, "medium", "In Xcode open the SwiftUI preview canvas.", "preview canvas open"),
        M(a, "hard", "In Xcode add a button to a SwiftUI view.", "button added"),
        M(a, "medium", "In Xcode change the app's display name in settings.", "display name changed"),
        M(a, "hard", "In Xcode set a breakpoint and run the app.", "breakpoint hit"),
        M(a, "medium", "In Xcode open the device simulator.", "simulator open"),
        M(a, "hard", "In Xcode add a unit test and run it.", "test runs"),
    ]


def android_studio() -> list[Task]:
    a = "androidstudio"
    return [
        M(a, "hard", "In Android Studio create a new Empty Activity project.", "new project created"),
        M(a, "hard", "In Android Studio add a Button to the layout XML.", "button in layout"),
        M(a, "medium", "In Android Studio open the AVD Manager.", "AVD manager open"),
        M(a, "hard", "In Android Studio change the app label in strings.xml.", "app label changed"),
        M(a, "medium", "In Android Studio open the Logcat panel.", "logcat open"),
        M(a, "hard", "In Android Studio sync the Gradle project.", "gradle synced"),
    ]


def tableplus() -> list[Task]:
    a = "tableplus"
    return [
        M(a, "hard", "In TablePlus create a new SQLite database connection.", "SQLite connection created"),
        M(a, "hard", "In TablePlus create a table 'users' with id and name columns.", "users table created"),
        M(a, "medium", "In TablePlus insert a row into a table.", "row inserted"),
        M(a, "hard", "In TablePlus run a SELECT query and view the results.", "query results shown"),
        F(a, "hard", "In TablePlus export a table's rows to tableplus_out.csv on the Desktop.", "tableplus_out.csv"),
        M(a, "medium", "In TablePlus add a new column to an existing table.", "column added"),
    ]


def postman() -> list[Task]:
    a = "postman"
    return [
        M(a, "medium", "In Postman create a GET request to https://api.github.com and send it.", "GET request sent, 200 response"),
        M(a, "hard", "In Postman create a new collection called 'Glance'.", "collection 'Glance' exists"),
        M(a, "hard", "In Postman add a query parameter to a request.", "query param added"),
        M(a, "medium", "In Postman add a header to a request.", "header added"),
        M(a, "hard", "In Postman save a request to a collection.", "request saved"),
        M(a, "hard", "In Postman create a POST request with a JSON body.", "POST with JSON body"),
    ]


def docker() -> list[Task]:
    a = "docker"
    return [
        M(a, "medium", "In Docker Desktop open the Containers tab.", "containers tab open"),
        M(a, "hard", "In Docker Desktop pull the 'hello-world' image.", "hello-world image pulled"),
        M(a, "hard", "In Docker Desktop run the 'hello-world' container.", "container ran"),
        M(a, "medium", "In Docker Desktop open the Images tab and read the image list.", "images listed"),
        M(a, "medium", "In Docker Desktop check the Docker engine status.", "engine status shown"),
    ]


def github_desktop() -> list[Task]:
    a = "ghd"
    return [
        M(a, "medium", "In GitHub Desktop open the current repository's history.", "history shown"),
        M(a, "hard", "In GitHub Desktop create a new branch called 'glance-test'.", "branch created"),
        M(a, "medium", "In GitHub Desktop view the changes tab.", "changes tab open"),
        M(a, "hard", "In GitHub Desktop stage a change and write a commit message (do not push).", "commit message written"),
        M(a, "medium", "In GitHub Desktop switch between two branches.", "branch switched"),
    ]


def terminal() -> list[Task]:
    a = "terminal"
    return [
        F(a, "medium", "Open Terminal and run a command that writes 'hello' into term_out.txt on the Desktop.", "term_out.txt", "hello"),
        F(a, "medium", "In Terminal use `date` to write the current date into term_date.txt on the Desktop.", "term_date.txt", None),
        M(a, "medium", "In Terminal run `ls` in the home directory and read the output.", "ls output shown"),
        F(a, "hard", "In Terminal create a folder 'glance_dir' on the Desktop and a file inside it named marker.txt.", "glance_dir/marker.txt", None),
        M(a, "medium", "In Terminal run `pwd` and confirm the working directory.", "pwd shown"),
        M(a, "hard", "In Terminal run `echo $PATH` and read it.", "PATH shown"),
        M(a, "medium", "In Terminal run `whoami`.", "username shown"),
    ]


def anaconda() -> list[Task]:
    a = "anaconda"
    return [
        M(a, "medium", "In Anaconda Navigator open the Environments tab.", "environments tab open"),
        M(a, "hard", "In Anaconda Navigator launch Jupyter Notebook.", "Jupyter launched"),
        M(a, "medium", "In Anaconda Navigator view the list of installed packages in the base environment.", "packages listed"),
    ]


# --------------------------------------------------------------------------- browsers / research
def _research(app: str, label: str) -> list[Task]:
    tasks = [N(app, "medium", f"In {label} look up {topic} and record the answer in a Note titled '{app.title()}Fact{i:02d}'.", f"{app.title()}Fact{i:02d}", 4)
             for i, topic in enumerate(TOPICS, 1)]
    return tasks


def safari() -> list[Task]:
    a = "safari"
    nav = [
        M(a, "easy", "In Safari open example.com and read the page heading.", "example.com heading read"),
        M(a, "medium", "In Safari open a new tab and go to apple.com.", "apple.com open"),
        M(a, "medium", "In Safari bookmark the current page.", "page bookmarked"),
        M(a, "hard", "In Safari open two tabs and switch between them.", "two tabs, switched"),
        M(a, "medium", "In Safari use Find on Page to find a word.", "find on page used"),
        M(a, "medium", "In Safari open the Reader view on an article.", "reader view open"),
        M(a, "hard", "In Safari open a private browsing window.", "private window open"),
        M(a, "medium", "In Safari zoom the page in twice.", "page zoomed"),
        N(a, "hard", "In Safari go to Wikipedia, search for the Moon, and record its diameter in a Note titled 'MoonDiameter'.", "MoonDiameter", 3),
        F(a, "hard", "In Safari open example.com and save the page's link text to safari_links.txt on the Desktop.", "safari_links.txt", None),
    ]
    return _research(a, "Safari") + nav


def chrome() -> list[Task]:
    a = "chrome"
    nav = [
        M(a, "easy", "In Google Chrome open example.com and read the heading.", "example.com read"),
        M(a, "medium", "In Chrome open a new tab and search for 'weather today'.", "search done"),
        M(a, "medium", "In Chrome bookmark the current page.", "page bookmarked"),
        M(a, "hard", "In Chrome open DevTools and view the Console tab.", "console open"),
        M(a, "medium", "In Chrome open an incognito window.", "incognito open"),
        M(a, "hard", "In Chrome open three tabs and close the middle one.", "middle tab closed"),
        M(a, "medium", "In Chrome zoom out the page once.", "zoomed out"),
        M(a, "hard", "In Chrome use the address bar to do a calculation (e.g. 25*4).", "calc result shown"),
        N(a, "hard", "In Chrome search for the current world population and record it in a Note titled 'WorldPop'.", "WorldPop", 4),
        F(a, "medium", "In Chrome go to example.com and save the page title to chrome_title.txt on the Desktop.", "chrome_title.txt", None),
    ]
    return _research(a, "Google Chrome") + nav


# --------------------------------------------------------------------------- native productivity
def notes() -> list[Task]:
    a = "notes"
    specs = [
        ("'Groceries' listing milk, eggs and bread", "Groceries", 10),
        ("'Books to read' with 5 titles", "Books to read", 15),
        ("'Standup' with a checklist of 3 items", "Standup", 10),
        ("'Movies' with 5 favourite films", "Movies", 15),
        ("'Workout' with 4 exercises and reps", "Workout", 15),
        ("'Trip Plan' with Flights, Hotel, Activities sections", "Trip Plan", 20),
        ("'Ideas' with 3 app ideas", "Ideas", 10),
        ("'Quotes' with two quotes", "Quotes", 15),
        ("'Weekly Menu' with a dinner for Mon-Fri", "Weekly Menu", 25),
        ("'Call List' with 3 people", "Call List", 8),
        ("'Chores' with a 5-item checklist", "Chores", 15),
        ("'Gift Ideas' for mom, dad and a friend", "Gift Ideas", 15),
        ("'Today' with 3 things to do", "Today", 10),
        ("'Wishlist' with 4 items", "Wishlist", 10),
        ("'Habits' with 5 daily habits", "Habits", 15),
        ("'Recipes' with two dish names", "Recipes", 12),
        ("'Passwords Hint' with 3 fake service hints (no real passwords)", "Passwords Hint", 15),
        ("'Goals' with 3 goals for the month", "Goals", 12),
        ("'Packing' with a 6-item list", "Packing", 12),
        ("'Meeting' with a 4-item agenda checklist", "Meeting", 12),
        ("'Bucket List' with 5 things to do someday", "Bucket List", 15),
        ("'Restaurants' with 4 places to try", "Restaurants", 12),
        ("'Podcasts' with 3 shows to listen to", "Podcasts", 10),
        ("'Home Projects' with 4 tasks", "Home Projects", 12),
        ("'Study Plan' with 5 topics", "Study Plan", 15),
        ("'Contacts to Add' with 3 names", "Contacts to Add", 10),
        ("'Budget Notes' with 3 spending categories", "Budget Notes", 12),
        ("'Travel Wishlist' with 5 destinations", "Travel Wishlist", 15),
        ("'Skills to Learn' with 4 skills", "Skills to Learn", 12),
        ("'Weekend Plans' with 3 activities", "Weekend Plans", 10),
        ("'Books Finished' with 4 titles", "Books Finished", 12),
        ("'Recipe Ideas' with 3 dishes", "Recipe Ideas", 10),
        ("'Fitness Goals' with 4 goals", "Fitness Goals", 12),
        ("'Project Notes' with 3 next steps", "Project Notes", 12),
        ("'Journal' with a 3-sentence entry for today", "Journal", 25),
        ("'Reflection' with 3 things you're grateful for", "Reflection", 15),
        ("'Questions' with 3 questions to research", "Questions", 12),
        ("'Reminders Backup' with 4 to-dos", "Reminders Backup", 12),
        ("'Notes to Self' with 3 short notes", "Notes to Self", 10),
    ]
    return [N(a, "easy" if m <= 10 else "medium", f"In Notes create a note titled {desc}.", title, m) for desc, title, m in specs]


def reminders() -> list[Task]:
    a = "rem"
    specs = [("Trip", 4, "passport, tickets, charger, sunscreen"), ("Groceries", 6, "6 grocery items"),
             ("Work", 5, "5 work tasks"), ("Errands", 4, "4 errands"), ("Project Launch", 7, "7 launch tasks"),
             ("Weekend", 3, "3 weekend plans"), ("Health", 5, "5 healthy habits"), ("Move", 8, "8 moving tasks"),
             ("Reading", 4, "4 books"), ("Garden", 5, "5 gardening tasks"), ("Party", 6, "6 party prep items"),
             ("Study", 5, "5 study topics"), ("Bills", 4, "4 bills to pay"), ("Repairs", 3, "3 home repairs"),
             ("Shopping", 7, "7 shopping items"), ("Packing", 6, "6 packing items"),
             ("Chores", 5, "5 chores"), ("Deadlines", 4, "4 deadlines"),
             ("Calls", 3, "3 calls to make"), ("Meds", 3, "3 medications"),
             ("Cleaning", 6, "6 cleaning tasks"), ("Interview Prep", 5, "5 prep items"),
             ("Car", 4, "4 car maintenance items"), ("Pets", 3, "3 pet care tasks"),
             ("Birthday", 5, "5 birthday party tasks")]
    return [R(a, "medium", f"In Reminders make a list '{name}' with {n} items ({what}).", name, n) for name, n, what in specs]


def calendar() -> list[Task]:
    a = "cal"
    return [
        N(a, "medium", "In Calendar create an all-day event 'Focus day' next Friday, then record the date in a Note titled 'Focus'.", "Focus", 4),
        N(a, "hard", "In Calendar make an event 'Dentist' for next Monday at 10am and record it in a Note titled 'Dentist'.", "Dentist", 4),
        N(a, "medium", "In Calendar tell me the weekday of the 15th of next month and record it in a Note titled 'Weekday'.", "Weekday", 3),
        N(a, "hard", "In Calendar create 'Gym' events for Mon/Wed/Fri next week and record them in a Note titled 'Gym'.", "Gym", 5),
        M(a, "medium", "In Calendar switch to Week view.", "week view"),
        M(a, "hard", "In Calendar create a new calendar named 'Glance'.", "calendar 'Glance' created"),
        M(a, "medium", "In Calendar go to today.", "today shown"),
        M(a, "hard", "In Calendar add a 30-minute event tomorrow at noon.", "noon event tomorrow"),
        M(a, "medium", "In Calendar delete a test event you created.", "event deleted"),
        M(a, "hard", "In Calendar set an alert on an event 15 minutes before.", "15-min alert set"),
    ] + [N(a, "hard", f"In Calendar create an event '{occ}' next week, then record its date in a Note titled 'Ev{i:02d}'.", f"Ev{i:02d}", 4)
         for i, occ in enumerate(["Birthday party", "Doctor appointment", "Team meeting", "Lunch with a friend",
                                  "Gym session", "Project deadline", "Movie night", "Call with family",
                                  "Study session", "Haircut", "Car service", "Coffee catch-up",
                                  "Book club", "Yoga class", "Standup"], 1)]


def contacts() -> list[Task]:
    a = "con"
    return [
        N(a, "medium", "In Contacts (read only) count how many contacts have a phone number and record it in a Note titled 'PhoneCount'.", "PhoneCount", 2),
        N(a, "hard", "In Contacts (read only) find the first contact alphabetically and record their name in a Note titled 'FirstContact'.", "FirstContact", 3),
        N(a, "medium", "In Contacts (read only) count contacts with an email and record it in a Note titled 'EmailCount'.", "EmailCount", 2),
        M(a, "medium", "In Contacts create a new contact 'Glance Test' with a fake phone number.", "contact created"),
        M(a, "hard", "In Contacts add a note to a contact.", "note added to contact"),
        M(a, "medium", "In Contacts search for a contact by name.", "search done"),
    ]


def maps() -> list[Task]:
    a = "maps"
    tasks = [N(a, "medium", f"In Maps find the driving distance from {x} to {y} and record it in a Note titled 'Drive{i:02d}'.", f"Drive{i:02d}", 3)
             for i, (x, y) in enumerate(PLACES, 1)]
    tasks += [
        N(a, "medium", "In Maps find the address of the Empire State Building and record it in a Note titled 'ESB'.", "ESB", 5),
        N(a, "hard", "In Maps find a coffee shop near Times Square and record its name in a Note titled 'Coffee'.", "Coffee", 3),
        M(a, "medium", "In Maps search for the Golden Gate Bridge and drop a pin.", "pin dropped"),
        M(a, "hard", "In Maps get walking directions between two nearby places.", "walking directions shown"),
        M(a, "medium", "In Maps switch to satellite view.", "satellite view"),
    ]
    tasks += [N(a, "medium", f"In Maps find a coffee shop in {c} and record its name in a Note titled 'Cafe{i:02d}'.", f"Cafe{i:02d}", 3)
              for i, c in enumerate(CITIES, 1)]
    return tasks


def weather() -> list[Task]:
    a = "weather"
    tasks = [N(a, "medium", f"In the Weather app find today's high for {c} and record it in a Note titled 'Wx{i:02d}'.", f"Wx{i:02d}", 3)
             for i, c in enumerate(CITIES, 1)]
    tasks += [N(a, "medium", f"In the Weather app find the chance of rain tomorrow in {c} and record it in a Note titled 'Rain{i:02d}'.", f"Rain{i:02d}", 3)
              for i, c in enumerate(CITIES, 1)]
    return tasks


def stocks() -> list[Task]:
    a = "stock"
    tasks = [N(a, "medium", f"In Stocks look up {name} ({tk}) and record its current price in a Note titled 'Stk{i:02d}'.", f"Stk{i:02d}", 3)
             for i, (tk, name) in enumerate(TICKERS, 1)]
    tasks += [N(a, "medium", f"In Stocks find {name}'s day change (up or down) and record it in a Note titled 'Chg{i:02d}'.", f"Chg{i:02d}", 3)
              for i, (tk, name) in enumerate(TICKERS, 1)]
    return tasks


def dictionary() -> list[Task]:
    a = "dict"
    tasks = [F(a, "medium", f"In Dictionary look up '{w}' and save its definition to dict_{w}.txt on the Desktop.", f"dict_{w}.txt", w)
             for w in WORDS]
    tasks += [N(a, "medium", f"In Dictionary find a synonym for '{w}' and record it in a Note titled 'Syn_{w}'.", f"Syn_{w}", 3)
              for w in WORDS]
    return tasks


def music() -> list[Task]:
    a = "music"
    tasks = [N(a, "medium", f"In Music search for {artist} and record one of their song titles in a Note titled 'Song{i:02d}'.", f"Song{i:02d}", 3)
             for i, artist in enumerate(ARTISTS, 1)]
    tasks += [N(a, "medium", f"In Music find an album by {artist} and record its name in a Note titled 'Album{i:02d}'.", f"Album{i:02d}", 3)
              for i, artist in enumerate(ARTISTS, 1)]
    tasks += [
        M(a, "hard", "In Music create a playlist called 'Focus'.", "playlist 'Focus' created"),
        M(a, "medium", "In Music play a song and pause it.", "played and paused"),
        M(a, "hard", "In Music add a song to a playlist.", "song added to playlist"),
        M(a, "medium", "In Music search the catalog for a genre.", "genre searched"),
    ]
    return tasks


def books() -> list[Task]:
    a = "books"
    return [
        N(a, "medium", "In Books browse the store top charts and record the #1 book's title in a Note titled 'TopBook'.", "TopBook", 4),
        N(a, "medium", "In Books find a free classic by Jane Austen and record its title in a Note titled 'Classic'.", "Classic", 5),
        M(a, "medium", "In Books open a sample and read the first page.", "sample opened"),
        M(a, "hard", "In Books add a book to your Want to Read list.", "book added to list"),
        M(a, "medium", "In Books change the reading theme to Night.", "night theme"),
    ]


def stickies() -> list[Task]:
    a = "stick"
    return [
        M(a, "easy", "In Stickies add a sticky that says 'Call the dentist'.", "sticky created"),
        N(a, "medium", "In Stickies create a 3-item to-do sticky, then copy it into a Note titled 'StickyTodo'.", "StickyTodo", 10),
        M(a, "easy", "In Stickies change a sticky's color to yellow.", "sticky color changed"),
        M(a, "medium", "In Stickies make a sticky with today's top priority.", "priority sticky"),
        M(a, "medium", "In Stickies make the font of a sticky bold.", "bold font"),
    ]


def freeform() -> list[Task]:
    a = "free"
    return [
        N(a, "hard", "In Freeform create a board 'Brainstorm' with 3 sticky ideas, then list them in a Note titled 'Brainstorm'.", "Brainstorm", 15),
        N(a, "hard", "In Freeform make a mind map with a center topic and 3 branches, then list them in a Note titled 'MindMap'.", "MindMap", 15),
        M(a, "medium", "In Freeform add a text box and a shape to a board.", "text + shape added"),
        M(a, "hard", "In Freeform connect two shapes with a line.", "shapes connected"),
        M(a, "medium", "In Freeform add a sticky note to a board.", "sticky added"),
    ]


def shortcuts() -> list[Task]:
    a = "short"
    return [
        N(a, "hard", "Open Shortcuts, pick any built-in shortcut, and record its name in a Note titled 'Shortcut'.", "Shortcut", 3),
        M(a, "hard", "In Shortcuts create a simple shortcut that shows an alert.", "shortcut created"),
        M(a, "medium", "In Shortcuts run a built-in shortcut.", "shortcut ran"),
        M(a, "hard", "In Shortcuts add an action to an existing shortcut.", "action added"),
    ]


def automator() -> list[Task]:
    a = "automator"
    return [
        M(a, "hard", "In Automator create a new Quick Action workflow.", "quick action created"),
        M(a, "hard", "In Automator add a 'Get Specified Finder Items' action.", "action added"),
        M(a, "medium", "In Automator save a workflow.", "workflow saved"),
    ]


def calculator() -> list[Task]:
    a = "calc"
    exprs = [("(145+67)*3-89", "phone-style"), ("15% tip on 86.40", "tip"), ("72F to C", "convert"),
             ("sqrt of 144", "sci"), ("2^10", "power"), ("1800+600+120+250 total", "sum"),
             ("average of 12,45,8,99,23", "avg"), ("18% of 250", "percent")]
    tasks = [N(a, "easy", f"In Calculator compute {e} and record the result in a Note titled 'Calc{i:02d}'.", f"Calc{i:02d}", 1)
             for i, (e, _) in enumerate(exprs, 1)]
    tasks += [
        M(a, "easy", "Open Calculator and switch to Scientific mode.", "scientific mode"),
        M(a, "medium", "In Calculator use the paper tape / history.", "history shown"),
    ]
    return tasks


def clock() -> list[Task]:
    a = "clock"
    return [
        N(a, "medium", "In Clock find the current time in Tokyo (World Clock) and record it in a Note titled 'TokyoTime'.", "TokyoTime", 3),
        M(a, "medium", "In Clock add a world clock for London.", "London clock added"),
        M(a, "hard", "In Clock set a 5-minute timer (do not start a long one).", "timer set"),
        M(a, "medium", "In Clock create an alarm for 7am (disabled).", "alarm created"),
        M(a, "medium", "In Clock use the stopwatch and reset it.", "stopwatch reset"),
    ] + [N(a, "medium", f"In Clock (World Clock) find the current time in {c} and record it in a Note titled 'Clk{i:02d}'.", f"Clk{i:02d}", 3)
         for i, c in enumerate(CITIES[:12], 1)]


def system_settings() -> list[Task]:
    a = "sys"
    return [
        F(a, "easy", "Find this Mac's macOS version and save it to sysinfo.txt on the Desktop.", "sysinfo.txt", "macOS"),
        N(a, "medium", "In System Settings find this Mac's computer name and record it in a Note titled 'MacName'.", "MacName", 3),
        N(a, "medium", "In System Settings find how much storage is free and record it in a Note titled 'Storage'.", "Storage", 3),
        N(a, "hard", "In System Settings find the current Wi-Fi network name and record it in a Note titled 'WiFi'.", "WiFi", 3),
        N(a, "medium", "In System Settings find the battery percentage and record it in a Note titled 'Battery'.", "Battery", 2),
        N(a, "hard", "In System Settings find the display resolution and record it in a Note titled 'Display'.", "Display", 3),
        M(a, "medium", "In System Settings toggle Dark Mode on.", "dark mode on"),
        M(a, "medium", "In System Settings open the Bluetooth panel.", "bluetooth panel"),
        M(a, "hard", "In System Settings change the desktop wallpaper.", "wallpaper changed"),
        M(a, "medium", "In System Settings open the Sound panel and read the output device.", "output device read"),
    ]


def mail() -> list[Task]:
    a = "mail"
    return [
        M(a, "hard", "In Mail compose a DRAFT to test@example.com with subject 'Hello' and a one-line body — do NOT send it.", "draft composed, not sent"),
        M(a, "medium", "In Mail open the inbox and read the newest subject line.", "newest subject read"),
        M(a, "hard", "In Mail create a draft with a subject and save it — do NOT send.", "draft saved"),
        M(a, "medium", "In Mail mark an email as read.", "email marked read"),
        M(a, "medium", "In Mail search the mailbox for a keyword.", "search done"),
    ]


def misc_apps() -> list[Task]:
    return [
        M("messages", "medium", "In Messages open a conversation and type a draft message — do NOT send it.", "draft typed, not sent"),
        M("messages", "medium", "In Messages read the most recent message preview in the list.", "preview read"),
        M("facetime", "easy", "Open FaceTime and read your account email shown in the app.", "account email read"),
        M("photobooth", "medium", "In Photo Booth take a photo with the built-in camera.", "photo taken"),
        M("photobooth", "hard", "In Photo Booth take a photo with a distortion effect.", "effect photo taken"),
        M("podcasts", "medium", "In Podcasts search for a show and open it.", "show opened"),
        N("podcasts", "hard", "In Podcasts find a top technology podcast and record its name in a Note titled 'Podcast'.", "Podcast", 3),
        M("news", "medium", "In News open the Top Stories and read a headline.", "headline read"),
        N("news", "hard", "In News find a top headline and record it in a Note titled 'Headline'.", "Headline", 5),
        M("home", "easy", "Open the Home app and read whether any accessories are set up.", "accessories state read"),
        M("passwords", "medium", "Open Passwords and read how many logins are stored (do NOT reveal any password).", "count read"),
        M("fontbook", "medium", "In Font Book find a font whose name starts with 'A' and record nothing sensitive.", "font found"),
        N("fontbook", "hard", "In Font Book find a font starting with 'H' and record its name in a Note titled 'Font'.", "Font", 3),
        M("chess", "easy", "Open Chess and make the opening move e2 to e4.", "opening move made"),
        M("imagecapture", "medium", "Open Image Capture and read whether a device is connected.", "device state read"),
        M("primevideo", "easy", "Open Prime Video and read the featured title on the home screen.", "featured title read"),
        M("tv", "easy", "Open the TV app and read a featured item.", "featured item read"),
        M("appstore", "medium", "In the App Store search for 'Slack' and read its rating.", "rating read"),
        N("appstore", "hard", "In the App Store find the top free app and record its name in a Note titled 'TopApp'.", "TopApp", 3),
        M("siri", "easy", "Open Siri settings and read whether 'Listen for Siri' is enabled.", "siri setting read"),
        M("timemachine", "medium", "Open Time Machine settings and read the backup status.", "backup status read"),
    ]


WIKI = ["Albert Einstein", "the Moon", "Mount Everest", "the Pacific Ocean", "the Roman Empire",
        "photosynthesis", "the Great Barrier Reef", "Leonardo da Vinci", "the Amazon rainforest",
        "the Eiffel Tower", "DNA", "the Milky Way", "World War I", "the Sahara", "Isaac Newton",
        "the Nile", "quantum mechanics", "the Colosseum", "Marie Curie", "the Berlin Wall"]


def app_store() -> list[Task]:
    a = "appstore"
    tasks = [N(a, "medium", f"In the App Store search for {app} and record its star rating in a Note titled 'Rate{i:02d}'.", f"Rate{i:02d}", 2)
             for i, app in enumerate(POPULAR_APPS, 1)]
    tasks += [N(a, "medium", f"In the App Store find whether {app} is free or paid and record it in a Note titled 'Cost{i:02d}'.", f"Cost{i:02d}", 3)
              for i, app in enumerate(POPULAR_APPS, 1)]
    return tasks


def web_nav() -> list[Task]:
    tasks: list[Task] = []
    for url, label in SITES:
        tasks.append(M("safari", "easy", f"In Safari navigate to {url} and confirm the {label} page loaded.", f"{label} loaded in Safari"))
        tasks.append(M("chrome", "easy", f"In Google Chrome navigate to {url} and confirm the {label} page loaded.", f"{label} loaded in Chrome"))
    return tasks


def wiki_lookup() -> list[Task]:
    a = "wiki"
    return [N(a, "medium", f"In Safari look up {e} on Wikipedia and record one key fact in a Note titled 'Wiki{i:02d}'.", f"Wiki{i:02d}", 5)
            for i, e in enumerate(WIKI, 1)]


# --------------------------------------------------------------------------- assembly
_GENERATORS = [
    after_effects, premiere, media_encoder, capcut, screen_studio, imovie, garageband,
    photos, preview, quicktime,
    pages, numbers, keynote, textedit,
    cursor, sublime, xcode, android_studio, tableplus, postman, docker, github_desktop,
    terminal, anaconda,
    safari, chrome,
    notes, reminders, calendar, contacts, maps, weather, stocks, dictionary, music, books,
    stickies, freeform, shortcuts, automator, calculator, clock, system_settings, mail,
    misc_apps, app_store, web_nav, wiki_lookup,
]


def build() -> list[Task]:
    """Assemble the full catalog (~1000 tasks) with unique ids."""
    _ids.clear()
    tasks: list[Task] = []
    for gen in _GENERATORS:
        tasks.extend(gen())
    return tasks


def _breakdown(tasks: list[Task]) -> dict:
    from collections import Counter
    apps = Counter(t.id.rsplit("_", 1)[0] for t in tasks)
    verifiers = Counter(t.verify.func.__name__ for t in tasks)
    diffs = Counter(t.difficulty for t in tasks)
    return {"total": len(tasks), "apps": dict(apps), "verifiers": dict(verifiers), "difficulty": dict(diffs)}


def main() -> None:
    import json
    import sys
    tasks = build()
    b = _breakdown(tasks)
    print(f"=== catalog: {b['total']} tasks across {len(b['apps'])} apps ===")
    print("difficulty:", b["difficulty"])
    print("verifiers :", b["verifiers"], " (manual = result lives inside the app)")
    print("per app   :")
    for app, n in sorted(b["apps"].items(), key=lambda kv: -kv[1]):
        print(f"  {app:16} {n}")
    if "--dump" in sys.argv:
        from pathlib import Path
        out = Path(__file__).parent / "results"
        out.mkdir(parents=True, exist_ok=True)
        md = ["# Glance task catalog\n", f"{b['total']} tasks across {len(b['apps'])} apps.\n"]
        cur = None
        for t in tasks:
            app = t.id.rsplit("_", 1)[0]
            if app != cur:
                md.append(f"\n## {app}\n")
                cur = app
            md.append(f"- `{t.id}` [{t.difficulty}] {t.prompt}")
        (out / "catalog.md").write_text("\n".join(md))
        (out / "catalog.json").write_text(json.dumps(
            [{"id": t.id, "difficulty": t.difficulty, "prompt": t.prompt} for t in tasks], indent=2))
        print(f"\ndumped -> {out/'catalog.md'} and {out/'catalog.json'}")


if __name__ == "__main__":
    main()
