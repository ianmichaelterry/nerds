# External Dependencies and API Keys

This document lists all external resources that NERDS accesses and where API keys/tokens should be stored.

## Token Files

All tokens should be stored as plain text files in `~/.tokens/`:

| Token | File | Purpose |
|-------|------|---------|
| Bayleaf API | `~/.tokens/bayleaf-api` | LLM-powered poster critique (OpenAI-compatible) |
| OMDb API | `~/.tokens/omdb-api` | Movie plot keywords |
| Noun Project | `~/.tokens/noun-project-api-key` and `~/.tokens/noun-project-api-secret` | Genre-relevant icons |

## External APIs

### Bayleaf (LLM Critique)
- **Endpoint:** `https://api.bayleaf.dev/v1`
- **Model:** `openai/gpt-4o-mini` (vision-enabled)
- **No token stored in file:** Uses OAuth Bearer token in `~/.tokens/bayleaf-api`

### Wikidata SPARQL
- **Endpoint:** `https://query.wikidata.org/sparql`
- **Access:** Public, no authentication required
- **User-Agent:** Required (see code for format)

### Wikimedia Commons API
- **Endpoint:** `https://commons.wikimedia.org/w/api.php`
- **Access:** Public, no authentication required

### OMDb API
- **Endpoint:** `http://www.omdbapi.com/`
- **Requires:** API key in `~/.tokens/omdb-api`
- **Used for:** Movie plot keywords

### Noun Project API
- **Endpoint:** `https://api.thenounproject.com/v2`
- **Requires:** OAuth1 credentials (key + secret)
- **Keys:** `~/.tokens/noun-project-api-key`, `~/.tokens/noun-project-api-secret`

## Running Without Tokens

The system will function without some tokens:
- **No Bayleaf:** Falls back to text-only critique (no vision)
- **No OMDb:** Uses genre-based keywords instead
- **No Noun Project:** Skips icon fetching

Note: Without the Bayleaf API key, the PosterCriticNerd cannot provide vision-based critiques.
