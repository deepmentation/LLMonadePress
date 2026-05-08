// JSON payloads are written to sibling files by lemonade.render.typst_runner.
#let edition = json("edition.json")
#let profile = json("profile.json")

#set page(
  width: profile.page.width_mm * 1mm,
  height: profile.page.height_mm * 1mm,
  margin: (
    top: profile.page.margin_top_mm * 1mm,
    bottom: profile.page.margin_bottom_mm * 1mm,
    inside: profile.page.margin_inner_mm * 1mm,
    outside: profile.page.margin_outer_mm * 1mm,
  ),
)

#set text(
  font: profile.typography.body_family,
  size: profile.typography.body_size_pt * 1pt,
  lang: edition.at("language", default: "en"),
)

#import "components/cover.typ": cover-page
#import "components/story.typ": story-block
#import "components/colophon.typ": colophon-page

#cover-page(edition, profile)

#let lead = edition.at("lead_story", default: none)
#if lead != none {
  story-block(lead, profile)
}

#for section in edition.at("sections", default: ()) {
  let stories = section.at("stories", default: ())
  if stories.len() > 0 {
    heading(level: 1)[#section.at("name", default: "")]
    for story in stories {
      story-block(story, profile)
    }
  }
}

#colophon-page(edition, profile)
