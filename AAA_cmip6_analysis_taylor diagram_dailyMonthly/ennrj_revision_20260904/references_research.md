# EnNRJ bibliography audit — frozen research record

Retrieval date: 2026-09-04 (Asia/Bangkok).

## Pre-registration (frozen before source retrieval)

Question: Which of the manuscript's 28 bibliography entries require bibliographic or citation-use corrections before EnNRJ resubmission?

H1: The supplied author/year/title/journal/volume/pages identify real publications. Prediction: official publisher or institutional records match the core fields. Falsifier: a primary record contradicts a field or no matching record can be located within bounded search.

H2: The cited works support the adjacent manuscript claims. Prediction: title/abstract or available full text relates directly to each cited proposition. Falsifier: cited work concerns another location/topic and cannot establish the stated local fact.

Methods: M1 (confirmatory) extract paragraph numbers and exact reference/citation wording; M2 (confirmatory) search primary publishers, DOI and official records for every entry; M3 (confirmatory) compare cited claims against primary abstracts or text; M4 (confirmatory) second-pass audit by parent against this evidence, then JSON parse validation.

Stopping rules: stop when all 28 are screened; unresolved fields are labeled unverified after one targeted search plus a plausible primary-source fallback. No fabricated metadata, no changes to manuscript, no communications to publishers/authors. Bibliographic research is not library/API documentation lookup; the skill's three-query API-documentation limit is not applicable.

Output ownership: references_verified.json and this file only. The parent performs the independent closeout pass. Until that pass, result is provisional.

## Evidence log (append-only)

E01 — Local source: inspection/manuscript.json, SHA-256 recorded by source as 55453767483ab1de05aafeed540c3c5a12b4c9301e12b3166b3cc6011f89b721. Initial full Get-Content was truncated; pivot to selecting only paragraph index/text to avoid XML noise. No source fields changed.

E02 — Ahmad: publisher-branded paper at https://pdfs.semanticscholar.org/b883/f72dd7cb8f4007c2df289c4bf4bbda2f7f13.pdf identifies five authors including TianFang Wang, volume 2015, article 431860, DOI 10.1155/2015/431860. Publisher landing fetch failed. No substantive metadata change; TF/T indexing uncertainty retained.

E03 — Arai: https://engj.org/index.php/ej/article/view/3546 identifies Shojun Arai, Kazuya Urayama, Taichi Tebakari, Boonlert Archvarahuprok; 2019;23(6):461-468; DOI 10.4186/ej.2019.23.6.461. Publication analyzes gridded Thailand rainfall.

E04 — Asfaw: https://www.sciencedirect.com/science/article/pii/S2212094717300932 confirms 2018;19:29-41 and DOI 10.1016/j.wace.2017.12.002. NII record https://cir.nii.ac.jp/crid/1361137044726430592 confirms four authors. Publisher abstract analyzes Ethiopian rainfall/temperature trends, not measured reservoir impacts.

E05 — Azam: https://www.mdpi.com/2073-4441/10/6/765 confirms all five authors and 2018;10(6):765. Abstract reports significant monthly changes without significant annual precipitation trends. Section 2.5.1 says original series is tested if lag-1 correlation is nonsignificant; otherwise the pre-whitened series is tested. Useful methodological/context comparison, not validation of local code.

E06 — Blain: official publisher PDF https://periodicos.uem.br/ojs/index.php/ActaSciAgron/article/download/18199/pdf_48/ header explicitly gives "v. 37, n. 1, p. 21-28, Jan.-Mar., 2015" and author Gabriel Constantino Blain. These contradict supplied initials/year/end page. Publisher landing page returned 403; PDF succeeded. Main contribution concerns nonlinear-trend effects on TFPW power.

E07 — Burn: https://www.sciencedirect.com/science/article/pii/S0022169401005145 identifies Donald H. Burn and Mohamed A. Hag Elnur, 255(1-4):107-122, 2002. https://pascal-francis.inist.fr/vibad/index.php?action=getRecordDetail&idt=13398400 explicitly indexes family name HAG ELNUR. Correction uses Hag Elnur MA and in-text Burn and Hag Elnur.

E08 — Deng: https://www.sciencedirect.com/science/article/abs/pii/S0169809525003801 confirms seven authors; Atmospheric Research 326, 108288, November 2025. Abstract concerns global monsoon rainfall seasonality 1960-2022. Does not establish an exhaustive gap in local Thai literature.

E09 — Dinpashoh: https://ascelibrary.org/doi/10.1061/%28ASCE%29HE.1943-5584.0000819 confirms five authors (including Hamid Zare Abianeh), 2014 print, volume 19 issue 3, pages 617-625. Online 2013 is not issue year. Author copy and official contents establish monthly/seasonal/annual persistence-aware trend topic.

E10 — Do: https://ph02.tci-thaijo.org/index.php/ennrj/article/view/258010 confirms Xuan Duc Do; OJS says published November 17, 2025 but links volume 24(1), Jan-Feb 2026. https://ph02.tci-thaijo.org/index.php/ennrj/issue/view/17412 confirms pages 98-114. Propose issue-year 2026. Abstract/reference list do not mention pre-whitening. PDF viewer click yielded an empty parsed page, so conditional-TFPW attribution remains unsupported, not conclusively disproved by full text.

E11 — Endo: https://www.jstage.jst.go.jp/article/sola/5/0/5_0_168/_article/-char/ja/ and publisher PDF https://www.jstage.jst.go.jp/article/sola/5/0/5_0_168/_pdf confirm authors, 2009 volume 5 pages 168-171, DOI 10.2151/sola.2009-043. Topic is daily precipitation extremes/wet days/dry spells, not the manuscript's annual lag-1 autocorrelation.

E12 — Fiaz: author-lab-hosted publisher PDF https://www.ahrl.re.kr/img_up/shop_pds/adm014m/contents/myboard/myboard3/127.impactsofclimatechangeonthesouthasian.pdf confirms Attiqa Fiaz, Ghani Rahman, Hyun-Han Kwon; Journal of Hydro-environment Research 59 (2025) 100654; DOI 10.1016/j.jher.2025.100654. South Asian review, not specific Thai/Southeast Asian evidence. DOI fetch failed; original paper is primary evidence despite host being author's lab.

E13 — Gilbert: official Wiley catalogue https://www.wiley.com/en-us/General%2B%26%2BIntroductory%2BCivil%2BEngineering%2B%26%2BConstruction/Waste%2BTreatment-c-CE41?pq=%7Crelevance%7Cseries%3A3054 lists first edition February 1987, Richard O. Gilbert. Wiley 1987 imprint corroborated by https://search.worldcat.org/title/Statistical-methods-for-environmental-pollution-monitoring/oclc/59107514 and UNSAM library MARC https://buscador.unsam.edu.ar/Record/3745/Details. Contrary official EPA entry https://hero.epa.gov/reference/51155/ and National Agricultural Library record via https://agris.fao.org/search/en/providers/122535/records/65ddd9894c5aef494fd6138b give Van Nostrand Reinhold (different ISBN). Preserve supplied Wiley; author should check consulted copy.

E14 — Hamed: https://www.sciencedirect.com/science/article/pii/S002216949700125X confirms Khaled H. Hamed and A. Ramachandra Rao; 1998;204(1-4):182-196; DOI 10.1016/S0022-1694(97)00125-X. Abstract supports variance effects of serial correlation.

E15 — Harmoko: https://ph02.tci-thaijo.org/index.php/ennrj/article/view/262255 confirms all five names; author-institution https://scholar.undip.ac.id/en/publications/decadal-rainfall-distribution-shift-in-northern-coastal-java-hist/ confirms 2026;24(4):482-495 and DOI 10.32526/ennrj/24/20250315. Supari mononym preserved, ignoring OJS duplicated name. Abstract location is northern Central Java; cannot substantiate local Prachuap geography.

E16 — IPCC: https://www.ipcc.ch/report/ar6/syr/resources/how-to-cite-this-report/ and official full volume https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_FullVolume.pdf identify full report subtitle, editors Core Writing Team/Hoesung Lee/José Romero, Geneva, 2023, DOI 10.59327/IPCC/AR6-9789291691647. Page-span inconsistency across official guidance is avoided by not specifying pages for full report.

E17 — Jiang: https://link.springer.com/article/10.1007/s00477-024-02872-3 lists Albert Jiang, Edward McBean, Peineng Zeng, Yi Wang; 2025 volume 39 pages 445-464, issue February 2025; online December 2024. Contradicts supplied Huang J and Wang Z. Abstract evaluates Ontario rainfall-event timing; in-text use is comparative only.

E18 — Kendall: official CEA library https://e-bib-fe.extra.cea.fr/Default/doc/SYRACUSE/158826/rank-correlation-methods-maurice-kendall?_lg=en-US and https://search.worldcat.org/title/Rank-correlation-methods/oclc/3827024 confirm Griffin, London, 1975, fourth edition second impression. No year correction needed.

E19 — Khalil: publisher university repository https://digital.car.chula.ac.th/aer/vol40/iss3/8/ and publisher PDF https://ph01.tci-thaijo.org/index.php/aer/article/download/110487/106283/938897 confirm authors; 2018;40(3):77-90. Topic is Mae Klong, not direct evidence for Prachuap physical causation.

E20 — Limsakul: official issue https://tshe.org/ea/ea_july2017.html and PDF https://tshe.org/ea/pdf/EA10%282%29_17.pdf confirm authors; journal name EnvironmentAsia; 2017;10(2):162-176. DOI 10.14456/ea.2017.31. Wintertime defined DJF; narrower than all seasonal-duration claims.

E21 — Mann: https://www.jstor.org/stable/1907187 retrieved title only; Econometric Society domain disallows retrieval. Original 1968 statistical research article at https://doi.org/10.1007/BF02911642 cites Mann HB 1945, Econometrica 13:245-259. Primary target's issue not exposed; supplied issue 3 retained as partially verified, not fabricated.

E22 — Palizdan: https://link.springer.com/article/10.1007/s00704-013-1026-6 confirms five authors; "Volume 117, pages 589–606, (2014)"; issue date August 2014, online 2013. Correct supplied year/volume/page span. Full author list includes Abdul Halim Ghazali. Issue 3-4 independently appears in indexed publisher paper metadata.

E23 — Pascale: https://link.springer.com/article/10.1007/s00382-014-2278-2 confirms five names Pascale, Lucarini, Feng, Porporato, Shabeh ul Hasson, and volume 44 pages 3281-3301 (2015). Reading repository https://centaur.reading.ac.uk/71502/1/PascaleRainfall2015.pdf gives Hasson S. u. Correction replaces wrong Guez with Porporato/Hasson; final S vs SU abbreviation remains named explicitly as indexing convention caveat.

E24 — Sen: publisher DOI https://doi.org/10.1080/01621459.1968.10480934 fetch failed. Official NII DOI record https://cir.nii.ac.jp/crid/1360292620718152576 confirms Pranab Kumar Sen, 1968, Journal of the American Statistical Association 63(324):1379-1389. Bibliography verified via official record, not full-text methodological validation.

E25 — Suo: https://www.nature.com/articles/s41598-025-18721-4 confirms all ten authors; 2025 volume 15, article 33152. Online September 26, 2025. Global precipitation concentration analysis supports broad comparison, not proof of present local findings. Publisher citation omits issue number.

E26 — Trenberth: official author institution https://impacts.ucar.edu/en/publications/the-changing-character-of-precipitation/ confirms Parsons DB and standard article pages 1205-1217 plus front-matter 1161. Later same-author AMS paper https://journals.ametsoc.org/abstract/journals/bams/99/2/bams-d-17-0107.1.xml confirms normal citation 84:1205-1217. Correct last page 1218 to 1217; no front-matter page appended.

E27 — WMO: https://wmo.int/wmo-climatological-normals and https://community.wmo.int/site/knowledge-hub/programmes-and-initiatives/climate-services/climate-data confirm WMO-No. 1203 (2017). Official technical note https://extranet.wmo.int/edistrib_exped/grp_prs/_en/2011_2022_Archives/2019/08791-2019-CLW-CLPA-DMA-CLIN8110_en.pdf describes 30-year standard normal periods. This does not establish a universal trend-test sample-size minimum.

E28 — Xie: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0319477 and printable original confirm all authors and 2025;20(3):e0319477. Article does discuss reservoir/agricultural applications in its introduction, so initial apparent mismatch is downgraded to indirect support. Its direct contribution is precipitation-product validation.

E29 — Yue: https://onlinelibrary.wiley.com/doi/abs/10.1002/hyp.1095 explicitly gives authors and volume 16 issue 9 pages 1807-1829, 2002. Correct supplied end page 1825. Abstract supports detrending before serial-correlation estimation and cautions that ordinary pre-whitening can remove trend.

E30 — Journal style: https://ph02.tci-thaijo.org/index.php/ennrj/author explicitly says author-date citations and alphabetic bibliography, despite generic Vancouver label elsewhere. Examples show full journal names, author initials without periods, abbreviated page ranges, and Article No. formatting. It requires matching cited/listed references both directions. All ten Suo and seven Deng authors retained because no maximum author rule is explicit in instructions. Some published examples elsewhere use six authors plus et al.; no need to truncate here.

## Experiments and deviations

M1 confirmatory — completed. PowerShell ConvertFrom-Json extraction succeeded (exit 0), returning exactly source paragraphs 144-171 plus relevant prose. Exact selection command: `$referenceAuditData = Get-Content -LiteralPath 'ennrj_revision_20260904/inspection/manuscript.json' -Raw | ConvertFrom-Json; $referenceAuditData.paragraphs | Where-Object { $_.p -ge 144 -and $_.p -le 171 } | Select-Object p,text | ConvertTo-Json -Depth 3`. Follow-up inspected Gilbert narrative citation at paragraph 66.

M2 confirmatory — completed with bounded unresolved items. All 28 screened against publisher, author-institution, original publication, or official library/DOI metadata. Mann primary archive partial; compound-name initials and Gilbert imprint unresolved as documented. Search-only third-party citation lists were used to discover DOIs, not as sole authority for substantive correction.

M3 confirmatory — completed with caveats. Seven meaningful citation-placement/interpretation warnings recorded in JSON. Full-text verification not claimed for every cited proposition. Initial Xie warning was too strong; primary full paper supports general management relevance, so it is explicitly reduced to weak/indirect support (E28). No source evidence deleted.

Exploratory E31 — Direct Crossref API URLs for Pascale/Burn/Ahmad/Mann/Sen could not be opened by the web service (non-retryable safe-open errors). No network bypass attempted. Continued with available official records. Several publisher HTML/DOI fetches failed; successful original PDFs and official records are identified above. These are retrieval gaps, not evidence the publications do not exist.

M4 confirmatory — JSON syntax validation to run next. Independent evidence closeout is delegated to parent, not self-certified. No subagents spawned by this worker.

## Provisional result

H1 partially confirmed: all 28 publications identified, but at least eight entries contain substantive author/year/page/journal-name issues. H2 partially confirmed: several citations have geographical/topic mismatch or infer more than their available evidence supports. Proposed bibliography is in references_verified.json. The parent should decide whether to relocate, replace, or remove weak citations, then enforce bibliography/in-text parity. Research status remains pending independent parent second pass.

E32 — Validation command (bundled Python, exit 0): `C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import json; from pathlib import Path; p=Path('ennrj_revision_20260904/references_verified.json'); d=json.loads(p.read_text(encoding='utf-8')); assert len(d['references'])==28; assert [r['source_paragraph'] for r in d['references']]==list(range(144,172)); assert all(r['corrected_reference'] and r['authoritative_url'] and r['verification_status'] for r in d['references']); print('PASS: JSON parses; 28 unique sequential source references; required fields populated')"`. Decisive output: `PASS: JSON parses; 28 unique sequential source references; required fields populated`. Validation is syntax/completeness only, not independent verification of source accuracy. M4 syntax component closed; parent source-evidence component pending.
