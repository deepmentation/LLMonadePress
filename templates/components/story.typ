#let story-block(story, profile) = {
  heading(
    level: 2,
  )[#story.at("headline", default: "")]

  if "deck" in story {
    text(style: "italic")[#story.deck]
    v(0.5em)
  }

  text()[#story.at("body", default: "")]

  v(0.5em)

  if "sources" in story {
    text(size: 0.85em, fill: luma(100))[
      Quellen: #story.sources.map(s => s.at("domain", default: s.at("url", default: ""))).join(", ")
    ]
  }

  v(1.5em)
}
