// Render one story (lead or section item).
//
// Expects ``story`` to carry the schema produced by orchestrate._story_dict:
//   headline, deck, body, category, pull_quote (string|none),
//   sources: list of {title, url, domain, type, published_at, channel_name}
// where each source is the authoritative DB row, not LLM-fabricated.

#let _format-date(iso) = {
  if iso == none or iso == "" { return "" }
  // ISO timestamps look like 2026-05-09T14:30:00+00:00 — slice the date out.
  iso.slice(0, 10)
}

#let _source-line(src) = {
  let kind = src.at("type", default: "rss")
  let glyph = if kind == "youtube" { "▸" } else { "▸" }
  let label = if kind == "youtube" { "Video" } else { "Artikel" }
  let channel = src.at("channel_name", default: src.at("domain", default: ""))
  let date = _format-date(src.at("published_at", default: none))
  let title = src.at("title", default: "")
  let url = src.at("url", default: "")

  text(size: 0.85em)[
    #glyph #label · #emph[#channel]#if date != "" [ · #date]#if title != "" [ · #link(url)[#title]]
  ]
  linebreak()
}

#let story-block(story, profile) = {
  heading(level: 2)[#story.at("headline", default: "")]

  let deck = story.at("deck", default: "")
  if deck != "" {
    text(style: "italic")[#deck]
    v(0.4em)
  }

  text()[#story.at("body", default: "")]

  let pq = story.at("pull_quote", default: none)
  if pq != none and pq != "" {
    v(0.6em)
    text(weight: "bold", style: "italic", size: 1.05em)[„#pq"]
  }

  let sources = story.at("sources", default: ())
  if sources.len() > 0 {
    v(0.6em)
    line(length: 30%, stroke: 0.5pt + luma(180))
    v(0.2em)
    text(size: 0.85em, fill: luma(80))[Quellen:]
    linebreak()
    for src in sources {
      _source-line(src)
    }
  }

  v(1.2em)
}
