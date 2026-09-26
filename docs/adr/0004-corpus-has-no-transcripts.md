# The Corpus has no transcripts

A Video's text is its title, description, Chapters (parsed from the description), tags and topic categories, never its transcript. YouTube offers no ToS-compliant way to get transcripts of other people's Videos: `captions.download` needs edit rights, `youtube-transcript-api` calls undocumented endpoints that the ToS and Developer Policies forbid, and downloading audio to transcribe it ourselves is equally unauthorised. We chose to stay within the terms, consistent with reading the derived-metrics rule strictly (ADR 0003), and accept that retrieval runs on short metadata and that the Content Optimiser cannot compare a Draft's opening with comparable Videos.

## Considered Options

- **`youtube-transcript-api` at low volume from a home IP.** Rejected: knowingly breaks the ToS daily, can stop working at any time, and YouTube blocks some IPs.
- **Transcripts of the user's own Videos only, via OAuth.** Rejected for the MVP: extra setup, and only the user's Videos would carry rich text, skewing comparisons against everyone else's.

## Consequences

- A Draft's optional script is summarised by the LLM into Chapters so it can be compared with Corpus Videos' Chapters, and used to infer the Draft's Audience. There are no suggestions about the script's wording, because no Evidence can back them.
- Keyword search carries more weight in hybrid retrieval than it would over transcripts.
