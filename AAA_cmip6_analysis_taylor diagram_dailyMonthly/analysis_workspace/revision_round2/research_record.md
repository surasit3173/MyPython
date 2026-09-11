# Research record: targeted reference verification for manuscript revision

## Frozen plan (2026-08-30, Asia/Bangkok)

### Question

Are the disputed bibliographic details for Tung et al. (2022) and Sittichok et al. (2026) correct, and what limited comparison with Moazzam et al. (2020) is supported by the primary source?

### Hypotheses

- H1: The DOI `10.1007/s44195-022-00009-z` correctly identifies Tung et al. (2022) despite the journal's older DOI pattern.
  - Prediction: the DOI or official publisher page resolves to the cited title, authors, journal, year, volume, and article number.
  - Falsifier: the DOI resolves to another work or official metadata materially differs.
- H2: The Sittichok et al. citation is a legitimate 2026 publication rather than a fabricated or misdated reference.
  - Prediction: the official publisher page or DOI registry confirms the title, authors, journal, year, volume, and article number.
  - Falsifier: the DOI does not resolve or official metadata materially differs.
- H3: Moazzam et al. supports only a cautious comparison concerning observed spatial rainfall variability and drought concern in Uttaradit, not direct validation of the present CMIP6 projection magnitudes.
  - Prediction: the primary article describes observed/historical spatial variability or drought risk without the same seven-model, bias-corrected future estimand.
  - Falsifier: the primary article reports directly comparable future CMIP6 index changes using the same design.

### Methods

- M1 (confirmatory): query the exact Tung DOI/title and inspect an official publisher or DOI landing page.
- M2 (confirmatory): query the exact Sittichok DOI/title and inspect an official publisher or DOI landing page.
- M3 (confirmatory): inspect the primary Moazzam article or DOI landing page for study scope and conclusions.

### Stopping rules

Stop when each DOI is confirmed or rejected by authoritative metadata and the Moazzam comparison is bounded to claims supported by its primary article. Do not broaden into a general literature review.

## Evidence log

- E001 (2026-08-30): Springer Nature's official landing page for DOI `10.1007/s44195-022-00009-z` identifies the article as “Spatial assessment of climate change impacts on extreme precipitation in Thailand,” by Tung et al., published in *Theoretical and Applied Climatology* (2022), volume 149, pages 473–489. URL: https://link.springer.com/article/10.1007/s44195-022-00009-z. This confirms H1; the DOI is not a citation error.
- E002 (2026-08-30): Springer Nature's official landing page for DOI `10.1007/s44533-026-00050-8` identifies the article as “Projection of future drought risk in northern Thailand under climate change scenarios,” by Sittichok et al., published online 15 July 2026 in *Journal of Water and Climate Change*, volume 40, article 51. URL: https://link.springer.com/article/10.1007/s44533-026-00050-8. This confirms H2 as of the retrieval date.
- E003 (2026-08-30): The primary Moazzam et al. article (DOI `10.4236/acs.2020.103020`) analyzes observed rainfall at eight Uttaradit stations for 1988–2017 using Mann–Kendall/Sen methods and SPI. It reports reduced annual/monsoonal rainfall between the two halves of the record and drought concern. It does not estimate the same seven-model bias-corrected CMIP6 future changes used in the present manuscript. Primary PDF: https://www.scirp.org/pdf/acs_2020060813484058.pdf. This supports H3 and permits only a directional, non-validating comparison.
- E004 (2026-08-30, independent correction): E001 misdescribed the work associated with DOI `10.1007/s44195-022-00009-z`. The official Springer page identifies Tung, Wang, Weng, and Yang, “Extreme index trends of daily gridded rainfall dataset (1960–2017) in Taiwan,” *Terrestrial, Atmospheric and Oceanic Sciences* 33, article 8 (2022). URL: https://link.springer.com/article/10.1007/s44195-022-00009-z. The manuscript's original reference [6] is correct; E001 is superseded.
- E005 (2026-08-30, independent correction): E002 misdescribed the journal and title associated with DOI `10.1007/s44533-026-00050-8`. The official Springer page identifies Sittichok, Kuntiyawichai, and Narudeesri-utai, “Extreme rainfall trends and return periods under CMIP6 scenarios in Southern Thailand,” *Water Science* 40, article 51 (2026). URL: https://link.springer.com/article/10.1007/s44533-026-00050-8. The manuscript's original reference [17] is correct; E002 is superseded.
- E006 (2026-08-30, independent nuance): Moazzam et al.'s station-level significance statements are internally inconsistent between its abstract and conclusion. The revision therefore avoids station-level significance claims and uses only the directly supported comparison that annual and monsoonal averages were lower in 2003–2017 than in 1988–2002, with drought concern raised by SPI/linear extrapolation. This remains directional context rather than projection validation.

## Deviations, dead ends, and pivots

- The first transcription of E001 and E002 relied on mismatched search-result metadata. Direct DOI landing-page inspection and an independent reviewer falsified those transcriptions. No manuscript citation was changed from the already-correct original entries.

## Verdict

Independent review passed after corrections E004–E005. Retain manuscript references [6] and [17] as written. Use Moazzam et al. [14] only for a cautious, non-equivalent contextual comparison.
