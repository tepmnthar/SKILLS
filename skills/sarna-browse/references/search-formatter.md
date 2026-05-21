# Search Mode Output Formatter

Use this template when presenting search results in the conversation.

## Rules

- Links must be plain text, never markdown. Use `Title: https://...` in the Sources section.
- Preserve paragraph structure where possible, but the body is flexible in form and content.
- Do not translate unless the user explicitly requests it.
- The Introduction should summarize the entire output as a coherent narrative.
- The body may include subsections, bullet points, or large paragraphs as appropriate to the query.

## Template

```
# Sarna Search — {query}

## Introduction

{A concise narrative summary (2-6 paragraphs) that synthesizes the most relevant findings from the aggregate data and directly answers the user's question. Treat this like an academic paper abstract or introduction — it should stand alone.}

---

## Body

### {Subsection Title (optional)}

{Flexible content: paragraphs, lists, or analysis as needed.}

### {Another Subsection (optional)}

{More flexible content.}

---

## Sources

- {Page Title 1}: {full_url_1}
- {Page Title 2}: {full_url_2}
- {Page Title 3}: {full_url_3}
...
```

## Example

```
# Sarna Search — heavy lasers

## Introduction

Heavy Lasers are a Clan-exclusive weapon line developed by Clan Star Adder in 3059, available in Small (6 damage), Medium (10 damage), and Large (16 damage) variants. All share a common design philosophy: packing more punch into a compact package at the cost of increased heat generation, a subtle firing delay, and sensor interference that reduces accuracy.

Notable platforms include the Hellfire, which served as the testbed 'Mech for heavy laser technology and mounts a full array of them, and the Burrock, a fast heavy assault 'Mech carrying six heavy medium lasers alongside an Ultra AC/20. Over the decades, the weapon line evolved from an experimental Clan specialty into a mainstream assault weapon, though the original B-2000 command computer concept was largely abandoned.

---

## Body

### Technical Specifications

The Heavy Large Laser deals 16 damage for 18 heat, weighs 4 tons, and occupies 3 critical slots. The Heavy Medium Laser deals 10 damage for 7 heat at 1 ton and 2 slots. The Heavy Small Laser deals 6 damage for 3 heat at 0.5 tons and 1 slot. All variants suffer from sensor interference and reduced accuracy.

### Key BattleMechs

The Hellfire was developed by Clan Star Adder as a testbed for heavy laser technology. Using a resurrected Lupus OmniMech chassis, it mounts a heavy large laser, twin heavy medium lasers, and twin heavy small lasers. Seventeen double heat sinks are inadequate for the thermal load.

The Burrock, produced by Albion Armor Works Gamma in 3066, carries six Series 22a heavy medium lasers scattered throughout the 'Mech, supported by an Ultra AC/20. Its Modified 375 XL engine gives it a top speed of 86 km/h.

---

## Sources

- Heavy Large Laser: https://www.sarna.net/wiki/Heavy_Large_Laser
- Heavy Medium Lasers: https://www.sarna.net/wiki/Heavy_Medium_Lasers
- Heavy Small Laser: https://www.sarna.net/wiki/Heavy_Small_Laser
- Hellfire (BattleMech): https://www.sarna.net/wiki/Hellfire_(BattleMech)
- Burrock (BattleMech): https://www.sarna.net/wiki/Burrock_(BattleMech)
```
