# The Poster Room: A Design Fiction

## Act I: The Blackboard Opens

The fluorescent lights hum overhead as **Maya Chen** opens her laptop at 9:47 AM. She's a post-doc at the Computational Media department, and today is the day she tests the new system. Her research partner **Dr. Samuel Okonkwo** stands by the whiteboard, marker in hand.

"So," Samuel says, "we dump the movie data into the folder, and then... what?"

Maya drags a folder labeled "blade_runner_2049" onto her desktop. Inside: a JSON file with metadata, three still frames from the film, and a text file with the cast list. She runs a command.

```bash
./poster_room --input ./blade_runner_2049 --output ./posters/br2049_v1
```

The terminal springs to life:

```
[09:48:12] Blackboard initialized at ./posters/br2049_v1/blackboard/
[09:48:12] Seeded with 4 items (heat: HOT)
[09:48:12] Activating nerds...
```

---

## Act II: The Nerds Wake Up

**Tyler** is the first to stir. He's the *Title Nerd*—obsessed with text, especially titles. He doesn't care about images, colors, or composition. He just loves breaking text apart, finding the rhythm in words.

Tyler scans the blackboard. There's a JSON file called `metadata.json` with a field `"title": "Blade Runner 2049"`. His heart races. Heat level: HOT. This is fresh data, just dumped. He *has* to work on it.

He queries the blackboard: "Give me anything with a 'title' field."

The blackboard responds with the metadata. Tyler grins and gets to work:

```python
def process(self, inputs):
    title = inputs['title']
    # Split into primary and secondary chunks
    words = title.split()
    mid = len(words) // 2
    return {
        'primary_title': ' '.join(words[:mid]),
        'secondary_title': ' '.join(words[mid:]),
        'full_title': title,
        'type': 'title_decomposition'
    }
```

Tyler writes his result back to the blackboard: `title_decomposition_001.json`. He marks it HOT. Fresh meat for the other nerds.

---

## Act III: The Color Maven Arrives

**Zahra** doesn't wake up until she senses images. She's the *Dominant Color Analyzer*, and she's been sleeping through Tyler's text-only excitement. But now there's a new item on the blackboard: `still_frame_01.png`. It's marked HOT—fresh from the initial seed.

Zahra wakes up and queries: "Give me any image files."

Three images return. She picks `still_frame_01.png` (randomly—though she has a slight bias toward items with higher heat). She opens it, runs her analysis:

```python
def process(self, inputs):
    image = Image.open(inputs['image_path'])
    # Extract dominant colors using k-means clustering
    colors = self.extract_palette(image, k=5)
    return {
        'key_color': colors[0],
        'accent_color': colors[1],
        'palette': colors,
        'source_image': inputs['image_path'],
        'type': 'color_analysis'
    }
```

She writes `color_analysis_001.json` to the blackboard. Key color: `#1a1a2e` (deep space blue). Accent: `#e94560` (neon coral). She marks it HOT.

---

## Act IV: Competition for Attention

The blackboard now has:

1. `metadata.json` (HOT → cooling to MEDIUM after being read twice)
2. `still_frame_01.png` (HOT → cooling)
3. `still_frame_02.png` (HOT)
4. `still_frame_03.png` (HOT)
5. `title_decomposition_001.json` (HOT)
6. `color_analysis_001.json` (HOT)

**Jin** wakes up. He's the *Typography Nerd*, and he loves combining text with colors. He queries: "Give me any title_decomposition items AND any color_analysis items."

The blackboard finds both. Jin gets to work, creating a text rendering specification:

```json
{
  "type": "typography_spec",
  "primary_title": "Blade Runner",
  "secondary_title": "2049",
  "key_color": "#1a1a2e",
  "accent_color": "#e94560",
  "suggested_typeface": "Eurostile Extended",
  "suggested_placement": "lower_third_center"
}
```

Meanwhile, **Alex** has been watching. They're the *Template Selector*, and they need both images AND typography specs to do their job. But the heat system is working against them—all those items are still HOT from Jin and Zahra's work. Alex's priority is lower.

Alex goes back to sleep, waiting for their moment.

---

## Act V: The Cooldown Cycle

Time passes. The heat system cools all items by 10% every iteration.

After 5 iterations:
- `metadata.json` is now COLD (hasn't been touched recently)
- `title_decomposition_001.json` is MEDIUM
- `color_analysis_001.json` is MEDIUM
- `typography_spec_001.json` (Jin's output) is HOT

**Alex** wakes up again. The typography spec is cooling, and Alex's internal heat has been rising—they've been waiting. Alex queries: "Give me any image files AND any typography_spec items."

Alex finds `still_frame_01.png` (now MEDIUM) and `typography_spec_001.json` (MEDIUM). Good enough. Alex selects a poster template that accommodates both a hero image and centered lower-third typography.

```json
{
  "type": "template_selection",
  "template_id": "hero_with_lower_text_v2",
  "hero_image": "still_frame_01.png",
  "typography_spec": "typography_spec_001.json",
  "layout_blocks": [
    {"type": "image", "region": "full_background"},
    {"type": "text", "region": "lower_third_center"}
  ]
}
```

---

## Act VI: The Critics Arrive

Now the blackboard is getting crowded. **Priya** wakes up—she's a *Critique Nerd* specializing in genre coherence. She sees the template selection and the color analysis. She frowns.

"That color palette," she mutters, "it's too warm for a neo-noir sci-fi film."

Priya doesn't create new items. She creates *critique* items:

```json
{
  "type": "critique",
  "target": "color_analysis_001.json",
  "issue": "genre_mismatch",
  "severity": "medium",
  "suggestion": "Consider cooler tones or higher contrast for neo-noir aesthetic"
}
```

This critique is marked HOT. Now **Zahra** (the Color Maven) sees it. She feels the heat—someone is critiquing her work! She queries for her own color_analysis items that have associated critiques.

Zahra decides to re-run her analysis with different parameters, this time emphasizing cooler tones. She creates `color_analysis_002.json` with a revised palette: `#0f0f1e` and `#ff2a6d`.

---

## Act VII: Completion Detection

**Dr. Okonkwo** has been watching the terminal. The system has been running for 12 minutes. Hundreds of items now litter the blackboard. But how does it know when to stop?

**Quinn** is the *Completion Nerd*. They don't create artifacts—they just read everything and decide: "Is this done?"

Quinn queries the blackboard: "Give me all items of type 'template_selection' and any 'rendered_poster' items."

There's a template selection from Alex. There's a rendered poster from **Jordan** (the *Compositor Nerd*) that used that template. Quinn runs their checks:

1. ✓ Title present? Yes, from `title_decomposition_001.json`
2. ✓ Hero image present? Yes, `still_frame_01.png`
3. ✓ Color scheme applied? Yes, from `color_analysis_002.json`
4. ✓ Typography rendered? Yes, from `typography_spec_001.json`
5. ✓ No blocking critiques? Yes, all critiques have been addressed or are marked resolved

Quinn writes one final item:

```json
{
  "type": "completion_decree",
  "final_output": "rendered_poster_003.png",
  "rationale": "All required elements present; composition complete; no blocking issues",
  "timestamp": "09:58:47"
}
```

The terminal displays:

```
[09:58:47] COMPLETION DECREE issued by Quinn
[09:58:47] Final output: rendered_poster_003.png
[09:58:47] Halting...
```

---

## Act VIII: The Morning After

Maya opens `rendered_poster_003.png`. It's not perfect—the tagline is missing, and the actor credits are in the wrong order. But it's a start.

"Look," she points to Samuel, "Quinn declared completion, but we never told the system what 'complete' actually means. We need more nerds that care about credits, about billing order, about MPAA ratings."

Samuel nods. "And see here? The heat system let Zahra dominate early because she found those fresh images. But Alex had to wait too long. We need to tune the thermal dynamics."

They spend the afternoon adding new nerds:

- **Riley**: The *Billing Order Nerd* (obsessed with actor hierarchy)
- **Sam**: The *MPAA Compliance Nerd* (checks for rating boxes)
- **Taylor**: The *Tagline Generator* (creates those snappy one-liners)
- **Casey**: The *Contrast Checker* (ensures text readability against backgrounds)

Each nerd has their specialty. Each has their biases. Each brings their heat to the blackboard.

---

## Reflection: What We Learned

From watching Maya and Samuel's system run, several design principles emerged:

**1. Nerds are specialists with blinders**
Tyler only sees titles. Zahra only sees images. They don't coordinate—they just react to what's hot. This emergent coordination is the system's strength.

**2. Heat is social attention**
When Priya critiqued Zahra's colors, Zahra felt compelled to respond. The heat system mimics social pressure: fresh work gets attention, old work fades, but critiques can reheat dormant items.

**3. Completion is arbitrary**
Quinn declared completion based on a checklist that was hardcoded. But "complete" is a design decision. Different Quinn nerds (or different thresholds) would produce different "done" states.

**4. The blackboard is a conversation**
Items aren't just data—they're utterances. `color_analysis_002.json` isn't just a palette; it's Zahra saying "I heard your critique, Priya, and here's my revision."

---

## Technical Requirements Revealed

To implement this system, we need:

### Core Infrastructure
- **Blackboard**: A filesystem-based JSON store with metadata (heat levels, timestamps, types)
- **Heat Manager**: Decay functions, reheat triggers, thermal mass calculations
- **Scheduler**: Boltzmann distribution selection from nerds based on their current "heat bias"
- **Schema Registry**: Input/output type definitions so nerds can query compatibly

### Nerd Implementation Pattern
```python
class Nerd:
    name: str
    input_schema: Dict[str, Type]
    output_schema: Dict[str, Type]
    heat_bias: float  # How much this nerd's internal heat rises when waiting
    
    def can_activate(self, blackboard) -> bool:
        # Check if compatible inputs exist
        pass
    
    def select_inputs(self, blackboard) -> Dict:
        # Heat-weighted selection from compatible items
        pass
    
    def process(self, inputs) -> Dict:
        # The actual work
        pass
```

### Required Programmatic Tools
```
Image Analysis: Pillow, scikit-image, colorthief
Image Processing: opencv-python, numpy
Typography: reportlab, fonttools
Face Detection: dlib (for checking face readability)
Composition: PIL for layer compositing
Data: json, pydantic (for schemas), watchdog (for filesystem events)
```

### Meta-Nerds (Control)
- **Heat Modulator**: Can artificially heat or cool items (simulating designer intervention)
- **Conflict Resolver**: When two nerds write conflicting items, this nerd picks or merges
- **Completion Detector**: Configurable criteria for "done"

---

## Open Questions

1. **Should nerds have memory?** Tyler processed that title already—should he remember and not re-process unless it changes?

2. **How do we prevent starvation?** Alex (Template Selector) had to wait a long time because they need multiple inputs. Should there be a "hunger" mechanism that boosts priority over time?

3. **Can nerds form coalitions?** What if Zahra and Jin could agree to work together on a specific poster iteration, excluding other nerds temporarily?

4. **Where does the movie data come from?** In this fiction, Maya dumped it. But could we have a *Research Nerd* that queries IMDb or TMDb APIs?

5. **What about failure?** In this run, everything worked. But what if Zahra's color analysis crashes? Do we need a *Error Recovery Nerd*?

---

*End of Design Fiction*

*The Poster Room v0.1 - A thought experiment in emergent, heat-driven generative systems.*
