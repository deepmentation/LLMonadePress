#let cover-page(edition, profile) = {
  set align(center + horizon)

  text(
    font: profile.typography.heading_family,
    size: profile.typography.heading_h1_pt * 1pt,
    weight: "bold",
  )[LLMonadePress]

  v(1em)

  text(size: 14pt)[
    #edition.at("edition_date", default: "")
  ]

  v(2em)

  let lead = edition.at("lead_story", default: none)
  if lead != none {
    text(
      font: profile.typography.heading_family,
      size: profile.typography.heading_h2_pt * 1pt,
      weight: "bold",
    )[#lead.at("headline", default: "")]

    v(0.5em)

    let deck = lead.at("deck", default: "")
    if deck != "" {
      text(style: "italic")[#deck]
    }
  }

  pagebreak()
}
