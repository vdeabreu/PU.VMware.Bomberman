# Kickoff slide deck

`kickoff.md` is the ~19-slide deck you'll project at the start of the day. Written in **Marp-compatible markdown**: each `---` is a slide break, with a YAML frontmatter controlling theme and style.

## Rendering options

### Option A — Marp (recommended)

Install the [Marp CLI](https://github.com/marp-team/marp-cli) once:

```bash
npm install -g @marp-team/marp-cli
```

Then:

```bash
# Live-reload preview on your laptop
marp --preview slides/kickoff.md

# Export to PDF for projection
marp --pdf slides/kickoff.md -o slides/kickoff.pdf

# Export to PowerPoint if your offsite runs on PowerPoint
marp --pptx slides/kickoff.md -o slides/kickoff.pptx

# Export to HTML (self-contained, present in any browser)
marp --html slides/kickoff.md -o slides/kickoff.html
```

### Option B — Marp for VS Code

Install the "Marp for VS Code" extension, open `kickoff.md`, hit the preview button.

### Option C — Copy/paste into Google Slides / Keynote

The `---` breaks and image paths make that straightforward. Each slide is short enough to fit one Google Slide without editing.

## Editing

- Each slide's boundary is a `---` on its own line.
- Image paths are **relative to the repo root** (`../assets/...` from `slides/`). If your render target doesn't like that, run Marp from the repo root or copy the images into `slides/`.
- Marp-specific syntax: `![w:900](...)` sets image width in px. `<!-- Slide N -->` comments are for the author; they don't render.
- Edit style at the top of `kickoff.md` — the `style:` YAML block applies to every slide.

## Tips for presenting

- Skip slide 13 (Node stub) if your room is all-Python, or vice versa.
- Slide 15 (scrimmage) is the one where you announce the **reference AI URL** — write it on a whiteboard too, nobody will copy it fast enough.
- Slide 18 (rules recap) is the one you leave up during coding time.
