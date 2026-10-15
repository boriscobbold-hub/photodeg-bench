# Eligibility criteria (v1.0)

A paper is **included** only if all of E1–E6 hold. Screening records the first criterion a paper fails as its exclusion code, so the flow diagram can count reasons. Criteria were set before screening began and were not changed during it; any later change is a new version.

| Code | Criterion | Excluded when |
|---|---|---|
| E1 | **Primary experimental study** | review, perspective, tutorial, computational-only, patent, erratum |
| E2 | **A synthetic (or semi-synthetic) organic polymer is the substrate being deconstructed**: commodity plastics, poly(meth)acrylates, polyesters, polyamides, polyurethanes, polyethers, PVC, designed degradable polymers | the polymer is only a support, membrane, binder or fabric for a photocatalyst; the substrate is a dye, drug or other small molecule; the substrate is a biopolymer (lignin, cellulose, polysaccharide, protein, PHA, DNA) |
| E3 | **Light with a visible component drives the reaction**: emission at or above 380 nm (visible LEDs or lamps, white light, sunlight or solar simulator, Xe lamp without a UV cut-on restriction) | UV-only irradiation (all emission below 380 nm), or light not used |
| E4 | **The photochemical step is the deconstruction route** (photocatalytic, photoredox, photo-HAT, photo-oxidative, photo-triggered self-immolation; tandem processes count if the light step is required) | deconstruction is thermal, enzymatic, microbial or mechanochemical alone; light is used only for synthesis or curing |
| E5 | **A benchmark endpoint is reported quantitatively**: molar mass (M<sub>n</sub>, M<sub>w</sub> or M<sub>p</sub>) before **and** after irradiation, and/or a yield or amount of an identified product | only mass loss, CO<sub>2</sub> evolution, visual change, FTIR carbonyl index, or qualitative statements (v1.0 scope; see NEXT_STEPS) |
| E6 | **The endpoint values are accessible as text or table values** in an openly licensed full text available to the pipeline | full text not retrievable; values only in figures or in supplementary PDFs not processed in v1.0 |

E1–E4 are judged from title and abstract and, where the abstract is unclear, from the methods section. E5–E6 are judged from the full text. Papers without accessible full text that pass E1–E4 are excluded under E6 and counted separately, so the coverage loss is visible.

**Ambiguous** is recorded (and the paper excluded from v1.0, not guessed at) when E2–E4 cannot be settled from the accessible text.

## Who applied these criteria

Screening decisions in v1.0 were made by an AI system (Claude) reading titles, abstracts and full texts, following this document. Each decision records the criterion, a short rationale and the location of the evidence. See `docs/METHODS_AUTOMATED_CURATION.md`.
