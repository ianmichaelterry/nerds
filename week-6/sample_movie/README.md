# Sample Movie Dataset for The Poster Room

This directory contains sample data for the Nerds Architecture demonstration, specifically for generating a Blade Runner 2049 movie poster.

## Directory Structure

```
sample_movie/
├── metadata.json              # Main movie metadata
├── stills_index.json          # Index of still images with metadata
├── typeface_database.json     # Typography options and recommendations
├── template_library.json      # Poster layout templates
├── color_reference.json       # Official color palettes
└── stills/                    # Actual image files
    ├── still_01.jpg          # Jared Leto as Niander Wallace (2048x1365)
    ├── still_02.jpg          # Ana de Armas as Joi (2048x854)
    ├── still_03.jpg          # Roy Batty tribute (640x924)
    └── still_04.jpg          # Timeline graphic (640x271)
```

## Data Sources

### Images
- **IMDB**: Official production stills (Stephen Vaughan photography)
- **Reddit r/bladerunner**: Community contributions and tributes

### Design References
- **Typography**: Based on Eurostile Extended (official movie font)
- **Color Palettes**: Extracted from movie production design
- **Templates**: Standard movie poster layouts adapted for sci-fi genre

## Metadata Fields

### Movie Metadata (`metadata.json`)
- Basic info: title, tagline, genre, year
- Cast: main actors with billing order and characters
- Crew: director, cinematographer, production designer
- Visual style keywords and color palette notes
- Thematic keywords

### Image Index (`stills_index.json`)
- File metadata: dimensions, format, source
- Visual analysis: dominant colors, lighting, mood
- Composition notes

### Typeface Database (`typeface_database.json`)
- Font metadata: category, style, mood
- Usage recommendations
- Genre-specific rules
- Pairing suggestions

### Template Library (`template_library.json`)
- Layout definitions with block coordinates
- Canvas specifications
- Complexity ratings
- Genre suitability

### Color Reference (`color_reference.json`)
- Official movie color palettes by scene/location
- Genre coherence rules
- Readability guidelines
- Extraction method parameters

## Usage

```bash
# Run the poster generation
uv run --script poster_room.py --movie ./sample_movie
```

## File Statistics

- **Total images**: 4 stills
- **Total size**: ~1 MB
- **Resolution range**: 640x271 to 2048x1365
- **JSON files**: 5 metadata/configuration files

## Notes

- Images are a mix of official production stills and community content
- Color palettes are approximations based on visual analysis
- Typeface database includes the actual font used in the movie (Eurostile Extended)
- Templates follow standard movie poster conventions (2:3 aspect ratio, 1200x1800px)
