#!/usr/bin/env python3
# /// script
# dependencies = [
#   "Pillow>=10.0.0",
#   "colorthief>=0.2.1",
#   "numpy>=1.24.0",
# ]
# ///

"""
The Poster Room: A Linear Implementation of the Nerds Architecture

This is a hardcoded, linear version of the blackboard system for generating
movie posters. It demonstrates the concept without the complexity of a heat-based
scheduler.

To run: uv run --script poster_room.py -- --movie ./blade_runner_2049
"""

import json
import os
import sys
import argparse
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Image processing imports
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np


def ensure_dir(path: Path):
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class BlackboardItem:
    """An item on the blackboard with metadata."""
    item_id: str
    item_type: str
    data: Dict[str, Any]
    source_nerd: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "data": self.data,
            "source_nerd": self.source_nerd,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "BlackboardItem":
        return cls(
            item_id=d["item_id"],
            item_type=d["item_type"],
            data=d["data"],
            source_nerd=d["source_nerd"],
            timestamp=datetime.fromisoformat(d["timestamp"])
        )


class MarkdownLogger:
    """Logs nerd activities in human-readable markdown format."""
    
    def __init__(self, output_dir: Path):
        self.log_file = output_dir / "nerd_log.md"
        self.session_start = datetime.now()
        self.activations: List[Dict] = []
        
    def start_session(self, movie_title: str):
        """Initialize the log file with session header."""
        with open(self.log_file, 'w') as f:
            f.write(f"# The Poster Room - Nerd Activity Log\n\n")
            f.write(f"**Session Started:** {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Movie:** {movie_title}\n\n")
            f.write("---\n\n")
    
    def log_activation(self, nerd_name: str, inputs: Dict[str, BlackboardItem], 
                       output: Optional[BlackboardItem], notes: Optional[List[str]] = None):
        """Log a nerd's activation."""
        activation = {
            'timestamp': datetime.now(),
            'nerd': nerd_name,
            'inputs': {k: {'id': v.item_id, 'type': v.item_type} for k, v in inputs.items()},
            'output': {'id': output.item_id, 'type': output.item_type} if output else None,
            'notes': notes or []
        }
        self.activations.append(activation)
        
        # Append to log file immediately
        with open(self.log_file, 'a') as f:
            f.write(f"## {nerd_name}\n\n")
            f.write(f"**Time:** {activation['timestamp'].strftime('%H:%M:%S')}\n\n")
            
            if inputs:
                f.write("**Inputs:**\n")
                for input_name, input_info in activation['inputs'].items():
                    f.write(f"- `{input_name}`: {input_info['id']} ({input_info['type']})\n")
                f.write("\n")
            
            if output:
                f.write(f"**Output:** {output.item_id} ({output.item_type})\n\n")
                # Show a snippet of the data
                f.write("**Data Summary:**\n")
                data_summary = self._summarize_data(output.data)
                f.write(f"```json\n{data_summary}\n```\n\n")
            else:
                f.write("**Output:** (none - nerd could not activate)\n\n")
            
            if notes:
                f.write("**Notes:**\n")
                for note in notes:
                    f.write(f"- {note}\n")
                f.write("\n")
            
            f.write("---\n\n")
    
    def _summarize_data(self, data: Dict, max_lines: int = 10) -> str:
        """Create a summarized JSON representation."""
        import json
        # Truncate long lists
        summary = {}
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 5:
                summary[k] = v[:5] + [f"... ({len(v) - 5} more items)"]
            elif isinstance(v, dict):
                summary[k] = self._summarize_data(v, max_lines=3)
            else:
                summary[k] = v
        
        json_str = json.dumps(summary, indent=2)
        lines = json_str.split('\n')
        if len(lines) > max_lines:
            lines = lines[:max_lines] + ['  ... (truncated)']
        return '\n'.join(lines)
    
    def finalize(self, completed: bool, total_items: int):
        """Write session summary."""
        duration = (datetime.now() - self.session_start).total_seconds()
        
        with open(self.log_file, 'a') as f:
            f.write(f"# Session Summary\n\n")
            f.write(f"**Status:** {'✓ Completed' if completed else '✗ Incomplete'}\n\n")
            f.write(f"**Duration:** {duration:.2f} seconds\n\n")
            f.write(f"**Nerds Activated:** {len(self.activations)}\n\n")
            f.write(f"**Items on Blackboard:** {total_items}\n\n")
            f.write("**Activation Sequence:**\n\n")
            for i, act in enumerate(self.activations, 1):
                output_str = f" → {act['output']['type']}" if act['output'] else " (no output)"
                f.write(f"{i}. **{act['nerd']}**{output_str}\n")
            f.write("\n")


class Blackboard:
    """The shared workspace where nerds read and write."""
    
    def __init__(self, directory: Path, clear_on_start: bool = True):
        self.directory = directory
        self.items: Dict[str, BlackboardItem] = {}
        self.counter = 0
        
        # Clear existing items if requested
        if clear_on_start and directory.exists():
            import shutil
            shutil.rmtree(directory)
        
        ensure_dir(directory)
        # Don't load existing - start fresh
    
    def query(self, item_type: Optional[str] = None, 
              source_nerd: Optional[str] = None) -> List[BlackboardItem]:
        """Query items by type or source."""
        results = []
        for item in self.items.values():
            if item_type and item.item_type != item_type:
                continue
            if source_nerd and item.source_nerd != source_nerd:
                continue
            results.append(item)
        return results
    
    def write(self, item_type: str, data: Dict, source_nerd: str) -> BlackboardItem:
        """Write a new item to the blackboard."""
        self.counter += 1
        item_id = f"item_{self.counter:04d}"
        item = BlackboardItem(
            item_id=item_id,
            item_type=item_type,
            data=data,
            source_nerd=source_nerd
        )
        self.items[item_id] = item
        
        # Write to disk
        file_path = self.directory / f"{item_id}.json"
        with open(file_path, 'w') as f:
            json.dump(item.to_dict(), f, indent=2)
        
        print(f"  [Blackboard] {source_nerd} wrote {item_id} ({item_type})")
        return item


class Nerd:
    """Base class for all nerds."""
    
    def __init__(self, name: str):
        self.name = name
        self.input_schema: Dict[str, str] = {}
        self.output_type: str = ""
    
    def can_activate(self, blackboard: Blackboard) -> bool:
        """Check if this nerd can run given current blackboard state."""
        # Check if all required inputs are available
        for input_name, input_type in self.input_schema.items():
            items = blackboard.query(item_type=input_type)
            if not items:
                return False
        return True
    
    def select_inputs(self, blackboard: Blackboard) -> Dict[str, BlackboardItem]:
        """Select inputs from blackboard."""
        inputs = {}
        for input_name, input_type in self.input_schema.items():
            items = blackboard.query(item_type=input_type)
            if items:
                # Simple random selection for now
                inputs[input_name] = random.choice(items)
        return inputs
    
    def process(self, inputs: Dict[str, BlackboardItem]) -> Dict:
        """Override this in subclasses."""
        raise NotImplementedError
    
    def run(self, blackboard: Blackboard, logger: Optional[MarkdownLogger] = None) -> Optional[BlackboardItem]:
        """Execute this nerd if possible."""
        if not self.can_activate(blackboard):
            if logger:
                logger.log_activation(self.name, {}, None, ["Could not activate - missing required inputs"])
            return None
        
        print(f"\n[{self.name}] Activating...")
        inputs = self.select_inputs(blackboard)
        
        # Show what inputs were selected
        for name, item in inputs.items():
            print(f"  Input '{name}': {item.item_id} ({item.item_type})")
        
        result = self.process(inputs)
        
        # Log the activation
        notes = []
        if result and 'message' in result:
            notes.append(result['message'])
        
        if result:
            item = blackboard.write(self.output_type, result, self.name)
            if logger:
                logger.log_activation(self.name, inputs, item, notes)
            return item
        else:
            if logger:
                logger.log_activation(self.name, inputs, None, notes)
            return None


# =============================================================================
# SPECIFIC NERD IMPLEMENTATIONS
# =============================================================================

class ResearchNerd(Nerd):
    """Morgan: Fetches movie metadata from local database."""
    
    def __init__(self, data_dir: Path):
        super().__init__("ResearchNerd")
        self.data_dir = data_dir
        self.input_schema = {"movie_query": "movie_query"}
        self.output_type = "movie_metadata"
    
    def process(self, inputs):
        query = inputs['movie_query'].data
        movie_title = query.get('title', 'Blade Runner 2049')
        
        # Try to load from local metadata file
        metadata_file = self.data_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
            print(f"  [ResearchNerd] Found metadata for '{metadata.get('title')}'")
            return metadata
        
        # Fallback to basic generation
        print(f"  [ResearchNerd] No local metadata found, using defaults")
        return {
            "title": movie_title,
            "tagline": "There's still a page left",
            "genre": "Science Fiction",
            "year": 2017,
            "director": "Denis Villeneuve",
            "main_actors": ["Ryan Gosling", "Harrison Ford", "Ana de Armas"]
        }


class ImageFetcherNerd(Nerd):
    """Sam: Finds and loads movie stills from disk."""
    
    def __init__(self, data_dir: Path):
        super().__init__("ImageFetcherNerd")
        self.data_dir = data_dir
        self.input_schema = {"metadata": "movie_metadata"}
        self.output_type = "movie_still"
    
    def process(self, inputs):
        metadata = inputs['metadata'].data
        movie_title = metadata.get('title', 'unknown')
        
        found_images = []
        
        # Search for images in stills/ subdirectory
        stills_dir = self.data_dir / "stills"
        if stills_dir.exists():
            for img_file in stills_dir.glob("*.png"):
                found_images.append({
                    "path": str(img_file),
                    "filename": img_file.name,
                    "source": "local_stills_folder"
                })
            for img_file in stills_dir.glob("*.jpg"):
                found_images.append({
                    "path": str(img_file),
                    "filename": img_file.name,
                    "source": "local_stills_folder"
                })
        
        # Also check root directory
        for img_file in self.data_dir.glob("*.png"):
            if img_file.name not in [i['filename'] for i in found_images]:
                found_images.append({
                    "path": str(img_file),
                    "filename": img_file.name,
                    "source": "local_root_folder"
                })
        for img_file in self.data_dir.glob("*.jpg"):
            if img_file.name not in [i['filename'] for i in found_images]:
                found_images.append({
                    "path": str(img_file),
                    "filename": img_file.name,
                    "source": "local_root_folder"
                })
        
        print(f"  [ImageFetcherNerd] Found {len(found_images)} stills for '{movie_title}'")
        
        # Return first image found (in real version, could return multiple)
        if found_images:
            return found_images[0]
        else:
            # Generate a placeholder
            print(f"  [ImageFetcherNerd] No images found, creating placeholder")
            return {
                "path": None,
                "filename": "placeholder.png",
                "source": "generated",
                "placeholder": True
            }


class TitleNerd(Nerd):
    """Tyler: Obsessed with breaking titles into chunks."""
    
    def __init__(self):
        super().__init__("TitleNerd")
        self.input_schema = {"metadata": "movie_metadata"}
        self.output_type = "title_decomposition"
    
    def process(self, inputs):
        metadata = inputs['metadata'].data
        title = metadata.get('title', '')
        
        words = title.split()
        mid = len(words) // 2
        
        return {
            'primary_title': ' '.join(words[:mid]),
            'secondary_title': ' '.join(words[mid:]),
            'full_title': title,
            'word_count': len(words)
        }


class ColorAnalyzerNerd(Nerd):
    """Zahra: Extracts dominant colors from images, with guidance from ColorPaletteNerd."""
    
    def __init__(self):
        super().__init__("ColorAnalyzerNerd")
        self.input_schema = {
            "image": "movie_still",
            "color_ref": "color_reference"
        }
        self.output_type = "color_analysis"
    
    def process(self, inputs):
        image_data = inputs['image'].data
        color_ref = inputs['color_ref'].data
        image_path = image_data.get('path')
        
        # Use color reference if available, otherwise extract from image
        if color_ref.get('reference_source') == 'color_reference.json':
            # ColorPaletteNerd already loaded official palette
            colors = color_ref.get('full_palette', ['#1a1a2e', '#e94560', '#0f3460'])
            method = 'from_official_palette_reference'
            print(f"  [ColorAnalyzerNerd] Using official palette ({len(colors)} colors)")
        else:
            # Extract from image (simulated)
            colors = ['#1a1a2e', '#e94560', '#0f3460', '#16c79a', '#f4f4f4']
            method = 'simulated_kmeans'
            print(f"  [ColorAnalyzerNerd] Extracted from image (simulated)")
        
        return {
            'key_color': colors[0],
            'accent_color': colors[1],
            'palette': colors,
            'source_image': image_path,
            'analysis_method': method,
            'reference_used': color_ref.get('palette_name', 'none')
        }


class TypefaceArchivistNerd(Nerd):
    """Jordan: Consults the typeface database and recommends fonts."""
    
    def __init__(self, data_dir: Path):
        super().__init__("TypefaceArchivistNerd")
        self.data_dir = data_dir
        self.input_schema = {"metadata": "movie_metadata"}
        self.output_type = "typeface_recommendation"
    
    def process(self, inputs):
        metadata = inputs['metadata'].data
        genre = metadata.get('genre', 'general')
        sub_genre = metadata.get('sub_genre', '')
        
        # Load typeface database
        db_file = self.data_dir / "typeface_database.json"
        typeface_data = None
        if db_file.exists():
            with open(db_file) as f:
                typeface_data = json.load(f)
            print(f"  [TypefaceArchivistNerd] Consulted typeface database ({len(typeface_data.get('typefaces', []))} fonts)")
        
        # Select appropriate typeface based on genre
        if typeface_data and 'typefaces' in typeface_data:
            # Look for sci-fi suitable fonts
            for font in typeface_data['typefaces']:
                if genre == "Science Fiction" and font.get('style') == "futuristic":
                    print(f"  [TypefaceArchivistNerd] Selected '{font['name']}' for sci-fi genre")
                    return {
                        'primary_typeface': font['name'],
                        'category': font['category'],
                        'mood': font['mood'],
                        'recommended_for': font.get('recommended_for', []),
                        'source': 'typeface_database'
                    }
        
        # Default fallback
        return {
            'primary_typeface': 'Eurostile Extended',
            'category': 'geometric-sans',
            'mood': 'sci-fi, corporate, technological',
            'recommended_for': ['main-title', 'character-names'],
            'source': 'fallback'
        }


class TemplateArchivistNerd(Nerd):
    """Taylor: Retrieves appropriate poster templates from the library."""
    
    def __init__(self, data_dir: Path):
        super().__init__("TemplateArchivistNerd")
        self.data_dir = data_dir
        self.input_schema = {"metadata": "movie_metadata"}
        self.output_type = "template_library_query"
    
    def process(self, inputs):
        metadata = inputs['metadata'].data
        genre = metadata.get('genre', 'general')
        
        # Load template library
        lib_file = self.data_dir / "template_library.json"
        templates = []
        if lib_file.exists():
            with open(lib_file) as f:
                lib_data = json.load(f)
                templates = lib_data.get('templates', [])
            print(f"  [TemplateArchivistNerd] Accessed template library ({len(templates)} templates)")
        
        # Find suitable templates for genre
        suitable = []
        if templates:
            for template in templates:
                if genre in template.get('suitable_for', []):
                    suitable.append(template)
        
        # Return the first suitable template or a default
        if suitable:
            selected = suitable[0]
            print(f"  [TemplateArchivistNerd] Selected template '{selected['id']}' for {genre}")
            return {
                'available_templates': len(templates),
                'suitable_for_genre': len(suitable),
                'selected_template': selected['id'],
                'template_data': selected,
                'source': 'template_library'
            }
        else:
            # Default template
            return {
                'available_templates': len(templates),
                'suitable_for_genre': 0,
                'selected_template': 'hero_with_lower_text_v1',
                'template_data': {
                    'id': 'hero_with_lower_text_v1',
                    'canvas_size': [1200, 1800],
                    'blocks': []
                },
                'source': 'fallback'
            }


class ColorPaletteNerd(Nerd):
    """Casey: Loads color references and palettes for the movie."""
    
    def __init__(self, data_dir: Path):
        super().__init__("ColorPaletteNerd")
        self.data_dir = data_dir
        self.input_schema = {"metadata": "movie_metadata"}
        self.output_type = "color_reference"
    
    def process(self, inputs):
        metadata = inputs['metadata'].data
        movie_title = metadata.get('title', '')
        
        # Load color reference
        color_file = self.data_dir / "color_reference.json"
        color_data = None
        if color_file.exists():
            with open(color_file) as f:
                color_data = json.load(f)
            palettes = list(color_data.get('color_palettes', {}).keys())
            print(f"  [ColorPaletteNerd] Loaded color reference ({len(palettes)} palettes)")
        
        # Use official movie palette if available
        if color_data and 'color_palettes' in color_data:
            official = color_data['color_palettes'].get('official_movie_palette')
            if official:
                colors = official.get('colors', [])
                return {
                    'reference_source': 'color_reference.json',
                    'palette_name': official.get('name', 'Unknown'),
                    'key_color': colors[0]['hex'] if colors else '#1a1a2e',
                    'accent_color': colors[1]['hex'] if len(colors) > 1 else '#e94560',
                    'full_palette': [c['hex'] for c in colors],
                    'color_count': len(colors)
                }
        
        # Fallback to basic extraction from image later
        return {
            'reference_source': 'will_extract_from_image',
            'key_color': '#1a1a2e',
            'accent_color': '#e94560',
            'note': 'ColorPaletteNerd loaded reference, awaiting image analysis'
        }


class TypographyNerd(Nerd):
    """Jin: Combines titles with colors and typefaces to create typography specs."""
    
    def __init__(self):
        super().__init__("TypographyNerd")
        self.input_schema = {
            "title": "title_decomposition",
            "colors": "color_analysis",
            "typeface": "typeface_recommendation"
        }
        self.output_type = "typography_spec"
    
    def process(self, inputs):
        title_data = inputs['title'].data
        color_data = inputs['colors'].data
        typeface_data = inputs['typeface'].data
        
        return {
            'primary_title': title_data['primary_title'],
            'secondary_title': title_data['secondary_title'],
            'key_color': color_data['key_color'],
            'accent_color': color_data['accent_color'],
            'suggested_typeface': typeface_data.get('primary_typeface', 'Eurostile Extended'),
            'typeface_mood': typeface_data.get('mood', 'neutral'),
            'suggested_placement': 'lower_third_center',
            'font_size_primary': 72,
            'font_size_secondary': 36
        }


class TemplateSelectorNerd(Nerd):
    """Alex: Selects layout templates based on available assets."""
    
    def __init__(self):
        super().__init__("TemplateSelectorNerd")
        self.input_schema = {
            "image": "movie_still",
            "typography": "typography_spec"
        }
        self.output_type = "template_selection"
    
    def process(self, inputs):
        image_data = inputs['image'].data
        typography_data = inputs['typography'].data
        
        return {
            'template_id': 'hero_with_lower_text_v2',
            'hero_image': image_data.get('path'),
            'typography_spec': typography_data,
            'layout_blocks': [
                {'type': 'image', 'region': 'full_background'},
                {'type': 'text', 'region': 'lower_third_center'}
            ],
            'canvas_size': [1200, 1800]  # width, height
        }


class CritiqueNerd(Nerd):
    """Priya: Evaluates items and writes critiques (does NOT fix them)."""
    
    def __init__(self):
        super().__init__("CritiqueNerd")
        self.input_schema = {"item": "color_analysis"}
        self.output_type = "critique"
    
    def process(self, inputs):
        color_data = inputs['item'].data
        
        # Check if colors are too warm for sci-fi
        key_color = color_data.get('key_color', '')
        
        # Simple heuristic: if key color has too much red/green, it's too warm
        critiques = []
        
        # Simulate genre check
        if '#e94560' in color_data.get('palette', []):
            critiques.append({
                'issue': 'genre_mismatch',
                'severity': 'medium',
                'message': 'Accent color too warm for neo-noir sci-fi aesthetic',
                'suggestion': 'Consider cooler tones or higher contrast'
            })
        
        return {
            'target_item': inputs['item'].item_id,
            'target_type': inputs['item'].item_type,
            'critiques': critiques,
            'overall_assessment': 'needs_revision' if critiques else 'acceptable'
        }


class ColorReviserNerd(Nerd):
    """Zahra's colleague: Fixes color issues based on critiques (NOT the same as CritiqueNerd)."""
    
    def __init__(self):
        super().__init__("ColorReviserNerd")
        self.input_schema = {
            "critique": "critique",
            "original": "color_analysis"
        }
        self.output_type = "color_analysis"  # Produces revised color analysis
    
    def process(self, inputs):
        critique_data = inputs['critique'].data
        original_data = inputs['original'].data
        
        # Check if there are actionable critiques
        critiques = critique_data.get('critiques', [])
        
        if not critiques:
            # No issues, just pass through with a note
            return {
                **original_data,
                'revision_note': 'No changes needed',
                'revision_number': 1
            }
        
        # Revise the palette based on critiques
        # For genre_mismatch with sci-fi, shift to cooler tones
        revised_palette = ['#0f0f1e', '#ff2a6d', '#16213e', '#0f3460', '#e94560']
        
        return {
            'key_color': revised_palette[0],
            'accent_color': revised_palette[1],
            'palette': revised_palette,
            'source_image': original_data.get('source_image'),
            'analysis_method': 'revised_kmeans',
            'revision_note': f'Revised based on critique: {critiques[0]["issue"]}',
            'revision_number': 2
        }


class CompositorNerd(Nerd):
    """Jordan: Renders the final poster image from template and assets."""
    
    def __init__(self):
        super().__init__("CompositorNerd")
        self.input_schema = {"template": "template_selection"}
        self.output_type = "rendered_poster"
    
    def process(self, inputs):
        template_data = inputs['template'].data
        
        # Get canvas size
        canvas_size = template_data.get('canvas_size', [1200, 1800])
        width, height = canvas_size
        
        # Create base canvas
        poster = Image.new('RGB', (width, height), '#1a1a2e')
        draw = ImageDraw.Draw(poster)
        
        # Get typography spec
        typography = template_data.get('typography_spec', {})
        
        # Draw primary title
        primary_title = typography.get('primary_title', 'TITLE')
        key_color = typography.get('key_color', '#ffffff')
        
        # Use default font (in real version, would load specific typeface)
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw title
        draw.text((width//2, height - 200), primary_title, fill=key_color, 
                  font=font_large, anchor="mm")
        
        # Draw secondary title
        secondary_title = typography.get('secondary_title', '')
        if secondary_title:
            accent_color = typography.get('accent_color', '#e94560')
            draw.text((width//2, height - 120), secondary_title, fill=accent_color,
                      font=font_small, anchor="mm")
        
        # Add some visual interest - simulated hero image area
        # In real version, would composite actual image
        hero_box = (100, 100, width-100, height-300)
        draw.rectangle(hero_box, fill='#0f0f1e', outline='#16213e', width=2)
        
        # Add placeholder text for hero image
        draw.text((width//2, height//2 - 100), "[HERO IMAGE]", 
                  fill='#333333', font=font_small, anchor="mm")
        
        # Store the image reference separately (not JSON serializable)
        self._last_rendered_image = poster
        
        return {
            'canvas_size': canvas_size,
            'template_used': template_data.get('template_id'),
            'elements_rendered': ['title', 'typography', 'placeholder_image']
        }


class CompletionNerd(Nerd):
    """Quinn: Decides when the poster is complete."""
    
    def __init__(self):
        super().__init__("CompletionNerd")
        self.input_schema = {"poster": "rendered_poster"}
        self.output_type = "completion_decree"
    
    def process(self, inputs):
        poster_data = inputs['poster'].data
        
        # Check if poster has required elements
        elements = poster_data.get('elements_rendered', [])
        
        required = ['title', 'typography']
        has_all = all(req in elements for req in required)
        
        return {
            'is_complete': has_all,
            'final_output': 'rendered_poster' if has_all else None,
            'missing_elements': [req for req in required if req not in elements],
            'rationale': f"Poster has {len(elements)} elements rendered" if has_all else "Missing required elements"
        }


# =============================================================================
# THE POSTER ROOM - Main System
# =============================================================================

class PosterRoom:
    """The main orchestration system."""
    
    def __init__(self, output_dir: Path, movie_data_dir: Optional[Path] = None):
        self.output_dir = output_dir
        self.movie_data_dir = movie_data_dir
        self.blackboard = Blackboard(output_dir / "blackboard")
        self.nerds: List[Nerd] = []
        self.iteration = 0
        self.logger = MarkdownLogger(output_dir)
        
        # Register all nerds - data fetching nerds need movie_data_dir
        if movie_data_dir is not None:
            self.register_nerd(ResearchNerd(movie_data_dir))
            self.register_nerd(ImageFetcherNerd(movie_data_dir))
            self.register_nerd(TypefaceArchivistNerd(movie_data_dir))
            self.register_nerd(TemplateArchivistNerd(movie_data_dir))
            self.register_nerd(ColorPaletteNerd(movie_data_dir))
        
        # These nerds don't need external data
        self.register_nerd(TitleNerd())
        self.register_nerd(ColorAnalyzerNerd())
        self.register_nerd(TypographyNerd())
        self.register_nerd(TemplateSelectorNerd())
        self.register_nerd(CritiqueNerd())
        self.register_nerd(ColorReviserNerd())
        self.register_nerd(CompositorNerd())
        self.register_nerd(CompletionNerd())
    
    def register_nerd(self, nerd: Nerd):
        """Add a nerd to the system."""
        self.nerds.append(nerd)
        print(f"[System] Registered nerd: {nerd.name}")
    
    def seed_blackboard(self, movie_title: str = "Blade Runner 2049"):
        """Seed blackboard with just a query - nerds will fetch the rest."""
        # Initialize logger session
        self.logger.start_session(movie_title)
        
        print(f"\n{'='*60}")
        print(f"SEEDING BLACKBOARD with query: '{movie_title}'")
        print(f"{'='*60}\n")
        
        # Just write a query - nerds will go fetch everything else
        self.blackboard.write("movie_query", {
            "title": movie_title,
            "timestamp": datetime.now().isoformat()
        }, "System")
        
        print(f"[System] Seeded 1 query item. Nerds will fetch the rest.\n")
    
    def run_linear_pipeline(self):
        """Run nerds in a hardcoded sequence."""
        print(f"\n{'='*60}")
        print(f"RUNNING LINEAR PIPELINE")
        print(f"{'='*60}\n")
        
        # Define the sequence - DATA FETCHING phase first
        sequence = [
            # Phase 1: Data Fetching (nerds go get resources)
            "ResearchNerd",           # Fetches metadata
            "ImageFetcherNerd",       # Loads still images  
            "TypefaceArchivistNerd",  # Consults typeface DB
            "TemplateArchivistNerd",  # Loads templates
            "ColorPaletteNerd",       # Loads color references
            
            # Phase 2: Analysis & Processing
            "TitleNerd",              # Decomposes title
            "ColorAnalyzerNerd",      # Analyzes image colors
            "TypographyNerd",         # Creates typography spec
            "TemplateSelectorNerd",   # Selects layout
            
            # Phase 3: Critique & Revision
            "CritiqueNerd",           # Critiques colors
            "ColorReviserNerd",       # Fixes based on critique
            
            # Phase 4: Production
            "CompositorNerd",         # Renders poster
            "CompletionNerd"          # Decides if done
        ]
        
        for nerd_name in sequence:
            nerd = next((n for n in self.nerds if n.name == nerd_name), None)
            if not nerd:
                print(f"[Warning] Nerd {nerd_name} not found")
                continue
            
            result = nerd.run(self.blackboard, self.logger)
            
            if nerd_name == "CompletionNerd" and result:
                completion_data = result.data
                if completion_data.get('is_complete'):
                    print(f"\n{'='*60}")
                    print(f"✓ POSTER COMPLETE!")
                    print(f"{'='*60}")
                    print(f"Output: {completion_data.get('final_output')}")
                    print(f"Rationale: {completion_data.get('rationale')}")
                    # Finalize logger session
                    self.logger.finalize(True, len(self.blackboard.items))
                    return True
        
        # Pipeline didn't complete
        self.logger.finalize(False, len(self.blackboard.items))
        return False
    
    def save_final_poster(self):
        """Save the final rendered poster."""
        # Find the CompositorNerd to get the last rendered image
        compositor = next((n for n in self.nerds if n.name == "CompositorNerd"), None)
        
        if compositor and hasattr(compositor, '_last_rendered_image'):
            output_path = self.output_dir / "final_poster.png"
            compositor._last_rendered_image.save(output_path)
            print(f"\n[Output] Final poster saved to: {output_path}")
        else:
            print("[Error] No rendered poster found")


def create_sample_movie_data(movie_dir: Path):
    """Create sample movie data for testing."""
    ensure_dir(movie_dir)
    
    # Create metadata
    metadata = {
        "title": "Blade Runner 2049",
        "tagline": "There's still a page left",
        "genre": "Science Fiction",
        "year": 2017,
        "director": "Denis Villeneuve",
        "main_actors": ["Ryan Gosling", "Harrison Ford", "Ana de Armas"]
    }
    
    with open(movie_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Create a sample still frame (just a colored rectangle for now)
    img = Image.new('RGB', (1920, 1080), '#1a1a2e')
    draw = ImageDraw.Draw(img)
    # Add some visual interest
    draw.rectangle([100, 100, 500, 400], fill='#0f3460')
    draw.rectangle([1400, 600, 1820, 980], fill='#e94560')
    
    img.save(movie_dir / "still_frame_01.png")
    
    print(f"[Setup] Created sample movie data in {movie_dir}")


def main():
    parser = argparse.ArgumentParser(description='The Poster Room - Nerds Architecture Demo')
    parser.add_argument('--movie', type=str, help='Path to movie data directory')
    parser.add_argument('--output', type=str, default='./output', help='Output directory')
    parser.add_argument('--create-sample', action='store_true', help='Create sample movie data')
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_movie_data(Path("./sample_movie"))
        print("\nSample movie data created. Run again with:")
        print("  uv run --script poster_room.py -- --movie ./sample_movie")
        return
    
    if not args.movie:
        print("Error: --movie required (or use --create-sample)")
        parser.print_help()
        sys.exit(1)
    
    movie_dir = Path(args.movie)
    output_dir = Path(args.output)
    
    if not movie_dir.exists():
        print(f"Error: Movie directory not found: {movie_dir}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"THE POSTER ROOM")
    print(f"Nerds Architecture - Linear Pipeline Demo")
    print(f"{'='*60}\n")
    
    # Initialize the system with movie data directory
    room = PosterRoom(output_dir, movie_dir)
    
    # Seed with just a movie title - nerds will fetch everything else
    room.seed_blackboard("Blade Runner 2049")
    
    # Run the pipeline
    completed = room.run_linear_pipeline()
    
    if completed:
        room.save_final_poster()
        print(f"\n{'='*60}")
        print(f"SUCCESS!")
        print(f"{'='*60}")
        print(f"Check the output directory: {output_dir}")
    else:
        print(f"\n{'='*60}")
        print(f"Pipeline did not complete")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
