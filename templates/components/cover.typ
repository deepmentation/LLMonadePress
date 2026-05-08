#let cover-page(edition, profile) = {
  set align(center + horizon)

  text(
    font: profile.typography.heading_family,
    size: profile.typography.heading_h1_pt * 1pt,
    weight: "bold",
  )[Lemonade]

  v(1em)

  text(size: 14pt)[
    #edition.at("edition_date", default: "")
  ]

  v(2em)

  if "lead_story" in edition {
    text(
      font: profile.typography.heading_family,
      size: profile.typography.heading_h2_pt * 1pt,
      weight: "bold",
    )[#edition.lead_story.headline]

    v(0.5em)

    if "deck" in edition.lead_story {
      text(style: "italic")[#edition.lead_story.deck]
    }
  }

  pagebreak()
}
