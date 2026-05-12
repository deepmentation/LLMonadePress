// Render one story (lead or section item).
//
// Expects ``story`` to carry the schema produced by orchestrate._story_dict:
//   headline, deck, body, category, pull_quote (string|none),
//   sources: list of {title, url, domain, type, published_at,
//                     channel_name, qr_filename (added by typst_runner)}
// Sources come from the authoritative DB rows, not LLM-fabricated. QR
// PNGs are generated alongside edition.json by typst_runner.

#let _format-date(iso) = {
  if iso == none or iso == "" { return "" }
  // ISO timestamps look like 2026-05-09T14:30:00+00:00 — slice the date out.
  iso.slice(0, 10)
}

#let _source-row(src) = {
  let kind = src.at("type", default: "rss")
  let label = if kind == "youtube" { "Video" } else { "Artikel" }
  let channel = src.at("channel_name", default: src.at("domain", default: ""))
  let date = _format-date(src.at("published_at", default: none))
  let title = src.at("title", default: "")
  let url = src.at("url", default: "")
  let qr = src.at("qr_filename", default: none)

  block(breakable: false, {
    grid(
      columns: (60%, 10%, 30%),
      column-gutter: 0pt,
      // ─── 60%: textual citation ─────────────────────────────────
      align(left + horizon, text(size: 0.85em)[
        #text(weight: "bold")[#label]#if channel != "" [ · #channel]
        #if date != "" [#linebreak()#text(fill: luma(110), size: 0.95em)[#date]]
        #if title != "" [#linebreak()#link(url)[#emph[#title]]]
      ]),
      // ─── 10%: visual gap ───────────────────────────────────────
      [],
      // ─── 30%: QR code (or URL text fallback if QR missing) ─────
      align(right + horizon,
        if qr != none {
          // image() paths are relative to the importing file by default;
          // prefix with / to resolve against the project root (the temp
          // dir set up by typst_runner) where QR PNGs live.
          image("/" + qr, width: 100%)
        } else {
          text(size: 0.7em, fill: luma(120))[#url]
        }
      ),
    )
  })
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
    // Wrap header + every source row in a single non-breakable block so
    // we never end up with the "QUELLEN" header alone at the bottom of
    // one page and the actual sources on the next. If it doesn't fit
    // below the body, the whole block jumps to the next page together.
    v(0.8em)
    block(breakable: false, {
      line(length: 100%, stroke: 0.5pt + luma(180))
      v(0.3em)
      text(size: 0.8em, fill: luma(80), weight: "bold")[QUELLEN]
      v(0.3em)
      for src in sources {
        _source-row(src)
        v(0.4em)
      }
    })
  }
}
