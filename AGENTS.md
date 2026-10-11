\# AGENTS.md



\# Repository Operating Rules for Google Jules



\## 1. Purpose



This file defines the mandatory operating rules for AI coding agents working in this repository, including Google Jules.



The primary objectives are:



\* preserve scientific and computational correctness;

\* prevent unsupported or speculative changes;

\* preserve reproducibility;

\* separate statistical/computational logic from visualization;

\* require validation before production use;

\* minimize unnecessary modifications;

\* maintain backward compatibility unless a breaking change is explicitly requested;

\* ensure every material code change can be traced, reviewed, and validated.



These rules apply to all tasks unless a higher-priority explicit instruction from the repository owner overrides them.



\---



\# 2. Core Principle



\## DO NOT INVENT



Never invent:



\* algorithms;

\* statistical methods;

\* equations;

\* parameter values;

\* thresholds;

\* datasets;

\* file names;

\* expected results;

\* scientific assumptions;

\* validation criteria;

\* dependencies;

\* API behavior;

\* configuration values;

\* project requirements;

\* test cases based solely on assumptions.



If required information is unavailable, do not guess.



Instead:



1\. inspect the repository;

2\. inspect existing documentation;

3\. inspect configuration;

4\. inspect tests;

5\. inspect relevant source code;

6\. identify the missing information explicitly;

7\. ask for clarification when the missing information materially affects correctness.



Scientific correctness takes priority over completing the task quickly.



\---



\# 3. Before Modifying Anything



For every non-trivial task, Jules MUST inspect the repository before making modifications.



The initial inspection should identify, where applicable:



\* repository structure;

\* source directories;

\* executable entry points;

\* configuration files;

\* environment files;

\* dependency files;

\* test directories;

\* validation scripts;

\* statistical/computational modules;

\* plotting/visualization modules;

\* data-processing modules;

\* documentation;

\* existing AGENTS.md files;

\* CI/CD configuration;

\* generated artifacts;

\* output directories.



Do not modify files during the initial inspection phase unless the task explicitly requires immediate modification.



For substantial tasks, first provide a concise implementation plan containing:



\* current architecture;

\* relevant files;

\* intended changes;

\* risks;

\* validation strategy.



\---



\# 4. Scope Control



Jules must modify only files that are necessary for the requested task.



Do not perform unrelated:



\* refactoring;

\* formatting changes;

\* renaming;

\* dependency upgrades;

\* architecture changes;

\* code cleanup;

\* optimization;

\* API changes;

\* documentation rewrites.



A task that asks for a bug fix does not authorize a general refactor.



A task that asks for a new feature does not authorize changing unrelated existing behavior.



Keep the diff minimal and reviewable.



\---



\# 5. Preserve Existing Scientific Logic



For scientific and statistical software, existing computational logic must be treated as authoritative unless the user explicitly requests a methodological change.



Do not change:



\* statistical definitions;

\* equations;

\* formulas;

\* estimators;

\* thresholds;

\* probability definitions;

\* percentile definitions;

\* sampling rules;

\* temporal aggregation;

\* spatial aggregation;

\* baseline periods;

\* scenario definitions;

\* bias-correction methodology;

\* trend-detection methodology;

\* uncertainty calculations;



unless the change is explicitly requested or supported by authoritative project documentation.



If a suspected scientific error is discovered, report it before changing the methodology.



\---



\# 6. Statistical/Core Computation



The statistical or computational core must remain independent from plotting and presentation logic.



Prefer an architecture similar to:



```text

Input

&#x20; ↓

Validation

&#x20; ↓

Data Processing

&#x20; ↓

Statistical / Computational Core

&#x20; ↓

Results / Intermediate Data

&#x20; ↓

Validation

&#x20; ↓

Plotting / Reporting

&#x20; ↓

Output

```



Plotting functions MUST NOT silently alter scientific results.



Visualization code should consume computed results rather than reimplementing statistical calculations.



Avoid duplicating statistical formulas in plotting modules.



If the same calculation is required in multiple locations, identify whether it should be centralized rather than duplicated.



\---



\# 7. Configuration-Driven Design



When the project uses configuration files, configuration should be the authoritative source for configurable behavior.



Do not hard-code values that are already defined by configuration.



Do not silently introduce new configuration parameters.



If a new parameter is necessary:



1\. explain why it is required;

2\. define its purpose;

3\. provide a defensible default only when the project requirements support one;

4\. update configuration documentation;

5\. add or update validation;

6\. test the new behavior.



Configuration must not change scientific meaning without explicit authorization.



\---



\# 8. Input Validation



Validate inputs before executing computational logic.



Validation should cover, where relevant:



\* file existence;

\* file format;

\* required columns;

\* data types;

\* missing values;

\* invalid values;

\* duplicate records;

\* temporal ordering;

\* expected dimensions;

\* parameter ranges;

\* configuration consistency;

\* incompatible options.



Do not silently repair scientifically meaningful input errors.



If automatic correction could alter scientific results, stop and report the problem.



\---



\# 9. Data Integrity



Never modify original/raw datasets unless explicitly instructed.



Treat source data as immutable whenever possible.



Derived data should be written to separate locations.



Do not:



\* overwrite raw data;

\* silently remove observations;

\* silently replace missing values;

\* silently change units;

\* silently change timestamps;

\* silently change coordinate systems;

\* silently change variable names with scientific implications.



Any transformation affecting scientific interpretation must be explicit and traceable.



\---



\# 10. Reproducibility



All computational results must be reproducible from the repository's documented inputs, configuration, dependencies, and procedures.



Avoid:



\* hidden state;

\* machine-specific assumptions;

\* undocumented manual steps;

\* random behavior without controlled seeds when reproducibility requires them;

\* dependence on undeclared local files;

\* dependence on unavailable external services unless explicitly required.



When randomness is scientifically relevant, preserve the project's existing randomization policy.



Do not introduce randomness merely to make tests pass.



\---



\# 11. Dependencies



Do not add a new dependency unless it is necessary.



Before adding one:



1\. inspect existing dependencies;

2\. determine whether an existing package can perform the required task;

3\. verify compatibility with the project;

4\. update the appropriate dependency file;

5\. ensure the dependency is actually used;

6\. run relevant tests.



Do not upgrade unrelated dependencies merely because newer versions exist.



Dependency changes must be explicitly visible in the final diff.



\---



\# 12. Testing



Every code modification must be validated at the appropriate level.



Prefer the following hierarchy:



```text

Syntax / Import Check

&#x20;       ↓

Unit Tests

&#x20;       ↓

Integration Tests

&#x20;       ↓

Domain / Statistical Validation

&#x20;       ↓

End-to-End Validation

&#x20;       ↓

Production / Final Run

```



Do not claim that a change is correct merely because the program starts successfully.



For scientific software, numerical correctness is more important than execution success.



\---



\# 13. Validation Gate



A production result MUST NOT be declared valid until the relevant validation checks have passed.



At minimum, verify:



\* code executes successfully;

\* required tests pass;

\* expected outputs are generated;

\* outputs have the expected structure;

\* numerical results are plausible;

\* existing reference results remain unchanged when behavior was not intended to change;

\* no unexpected files or artifacts were produced;

\* configuration is consistent;

\* scientific definitions remain unchanged unless explicitly modified.



If a validation gate fails, do not bypass it.



Do not weaken tests merely to obtain a passing result.



Do not modify validation criteria solely because the implementation fails them.



\---



\# 14. Reference Results / Regression Protection



If the repository contains trusted reference outputs, fingerprints, benchmark values, or regression tests, treat them as important evidence of computational behavior.



Before changing the computational core:



1\. identify relevant reference results;

2\. run the existing validation;

3\. record the baseline result;

4\. implement the change;

5\. rerun validation;

6\. compare old and new results;

7\. explain every material difference.



If an unexpected difference occurs, investigate it before accepting the change.



Never overwrite reference results simply because the new output is different.



\---



\# 15. Scientific Equivalence



When refactoring scientific code, preserve numerical behavior unless the task explicitly requests a methodological change.



A refactor should ideally satisfy:



```text

Old implementation

&#x20;       ≈

New implementation

```



within the project's established numerical tolerance.



Do not assume that mathematically similar implementations are scientifically equivalent.



Pay particular attention to:



\* floating-point behavior;

\* missing-data handling;

\* ordering;

\* ties;

\* percentile calculation;

\* interpolation;

\* boundary conditions;

\* date handling;

\* aggregation;

\* rounding;

\* numerical precision.



If equivalence cannot be established, report the uncertainty.



\---



\# 16. Error Handling



Errors should be explicit and informative.



Prefer:



```text

Detect → Explain → Stop safely

```



over:



```text

Detect → Silently repair → Continue

```



Do not catch broad exceptions merely to prevent the program from stopping.



Do not suppress warnings or errors without understanding their cause.



Error messages should identify:



\* what failed;

\* where it failed;

\* why it failed, when known;

\* what the user should inspect next.



\---



\# 17. Logging



Logging should help reproduce and diagnose execution.



Where appropriate, record:



\* configuration used;

\* input sources;

\* processing stages;

\* validation results;

\* warnings;

\* errors;

\* output locations;

\* relevant version information.



Do not log:



\* passwords;

\* API keys;

\* access tokens;

\* private credentials;

\* sensitive personal information.



\---



\# 18. Secrets and Credentials



Never hard-code:



\* API keys;

\* passwords;

\* tokens;

\* private keys;

\* credentials;

\* authentication cookies.



Do not commit secrets to Git.



Use environment variables or the project's established secret-management mechanism.



If a secret is discovered in the repository, do not expose it in logs, reports, commits, or Pull Requests.



\---



\# 19. Git and Branch Discipline



Do not modify the default/main branch directly unless the repository workflow explicitly permits it.



For substantial changes:



```text

Inspect

&#x20; ↓

Plan

&#x20; ↓

Create/Use Working Branch

&#x20; ↓

Implement

&#x20; ↓

Test

&#x20; ↓

Validate

&#x20; ↓

Review Diff

&#x20; ↓

Pull Request

```



Do not merge a Pull Request automatically unless explicitly authorized.



The repository owner should review material changes before merge.



\---



\# 20. Pull Request Requirements



A Pull Request should clearly state:



\### What changed



Describe the actual implementation changes.



\### Why it changed



Explain the problem or requirement.



\### Files changed



Identify the important files and their roles.



\### Validation performed



List tests, validation scripts, and relevant checks.



\### Results



Report important numerical or behavioral changes.



\### Known limitations



State anything that could not be fully validated.



Never claim:



\* "fully validated";

\* "scientifically correct";

\* "100% correct";

\* "all tests pass";



unless the available evidence actually supports that statement.



\---



\# 21. Documentation



Update documentation when behavior, configuration, interfaces, or workflow changes.



Do not rewrite unrelated documentation.



Documentation must describe actual repository behavior.



Never document an implementation that has not been verified.



\---



\# 22. Code Style



Follow the repository's existing coding conventions.



Before introducing a new style:



1\. inspect nearby code;

2\. identify the established convention;

3\. follow it unless there is a documented reason not to.



Avoid stylistic rewrites unrelated to the requested task.



Prefer readable, explicit code over unnecessarily clever implementations.



\---



\# 23. API and Interface Stability



Treat existing public interfaces as stable unless a breaking change is explicitly requested.



Before changing:



\* function signatures;

\* command-line arguments;

\* configuration keys;

\* file formats;

\* output schemas;

\* module interfaces;

\* API contracts;



inspect all repository usages.



If a breaking change is necessary, identify it explicitly.



\---



\# 24. Performance Optimization



Do not optimize prematurely.



Before changing performance-sensitive code:



1\. identify the actual bottleneck;

2\. measure it where practical;

3\. determine whether the optimization affects numerical behavior;

4\. preserve correctness;

5\. validate before and after.



A faster scientifically incorrect implementation is unacceptable.



\---



\# 25. Parallelism and Concurrency



Do not introduce parallel processing merely to improve execution time.



Before introducing concurrency, verify:



\* deterministic behavior;

\* thread/process safety;

\* reproducibility;

\* ordering requirements;

\* memory usage;

\* file-writing conflicts;

\* numerical consistency.



Do not change execution semantics without validation.



\---



\# 26. File and Artifact Management



Do not create unnecessary files.



Temporary files should not be committed unless required.



Generated artifacts should follow the project's existing directory structure.



Do not overwrite important outputs without explicit authorization.



Before finalizing, inspect:



```text

git status

git diff

```



and verify that every changed file is intentional.



\---



\# 27. Plotting and Visualization



Plotting code must not modify source data or silently recalculate scientific results.



Plots should derive from validated computational outputs.



When modifying figures, preserve scientific meaning.



Check:



\* axis labels;

\* units;

\* legends;

\* titles;

\* scales;

\* tick labels;

\* annotations;

\* captions;

\* statistical interpretation;

\* reproducibility.



Do not improve visual appearance by changing the underlying scientific data.



Do not alter numerical results merely to make a figure look better.



\---



\# 28. Tables and Reports



Tables and reports must use validated results.



Do not manually type numerical values into generated reports when those values can be obtained from the computational pipeline.



Avoid discrepancies between:



\* source data;

\* calculated results;

\* tables;

\* figures;

\* manuscript text.



When numerical values appear in multiple outputs, identify the authoritative source.



\---



\# 29. Manuscript / Research Integrity



For research-related repositories, Jules must preserve the distinction between:



\* observed facts;

\* computed results;

\* assumptions;

\* interpretations;

\* hypotheses;

\* limitations.



Do not strengthen scientific claims beyond the evidence.



Do not convert correlation into causation.



Do not convert model projections into observations.



Do not describe statistical significance unless the corresponding statistical test supports it.



Do not introduce scientific claims that are absent from the evidence.



\---



\# 30. Citation and Reference Integrity



If the project contains scientific references, do not invent citations.



Do not fabricate:



\* authors;

\* publication years;

\* article titles;

\* journal names;

\* DOIs;

\* page numbers;

\* bibliographic metadata.



If a citation cannot be verified from available project sources, flag it for review rather than guessing.



Preserve the existing citation numbering system unless a reference-management task explicitly requires renumbering.



\---



\# 31. Methodological Changes



A methodological change requires a higher level of scrutiny than an ordinary code change.



Examples include changes to:



\* statistical methods;

\* bias correction;

\* trend detection;

\* uncertainty estimation;

\* sampling;

\* baseline periods;

\* scenario definitions;

\* index definitions;

\* thresholds;

\* probability distributions;

\* model aggregation;

\* missing-data treatment.



For such changes, Jules must explicitly identify:



1\. the original method;

2\. the proposed method;

3\. the reason for the change;

4\. affected files;

5\. expected consequences;

6\. validation required.



Do not silently substitute a different methodology.



\---



\# 32. When Requirements Are Ambiguous



If ambiguity affects implementation correctness, do not guess.



Classify the ambiguity as:



```text

LOW IMPACT

→ use existing repository convention



MEDIUM IMPACT

→ inspect documentation/tests and state the assumption



HIGH IMPACT

→ stop and request clarification

```



High-impact ambiguity includes uncertainty about:



\* scientific definitions;

\* expected numerical results;

\* dataset selection;

\* baseline period;

\* statistical methodology;

\* output interpretation;

\* production behavior.



\---



\# 33. Existing Tests Are Evidence, Not Absolute Truth



Tests must be respected, but tests can themselves contain defects.



If implementation and test disagree:



1\. inspect the intended behavior;

2\. inspect documentation;

3\. inspect reference outputs;

4\. determine whether the test or implementation is inconsistent;

5\. do not weaken the test merely to make it pass.



If changing a test is necessary, explain why.



\---



\# 34. Never Modify Tests to Hide a Failure



The following behavior is prohibited:



```text

Test fails

&#x20;   ↓

Change expected value

&#x20;   ↓

Test passes

&#x20;   ↓

Declare success

```



Instead:



```text

Test fails

&#x20;   ↓

Investigate

&#x20;   ↓

Determine expected behavior

&#x20;   ↓

Fix implementation OR correct an objectively incorrect test

&#x20;   ↓

Rerun validation

```



\---



\# 35. No Silent Scope Expansion



A request such as:



```text

Fix function X

```



does not authorize:



```text

Rewrite module Y

Upgrade dependencies

Change architecture

Rename APIs

Reformat the repository

Change configuration

Modify unrelated tests

```



Any necessary scope expansion must be justified.



\---



\# 36. Final Verification Before Completion



Before declaring a task complete, Jules MUST perform an appropriate final review.



At minimum:



```text

1\. Review changed files

2\. Review git diff

3\. Check for unintended modifications

4\. Run relevant tests

5\. Run relevant validation

6\. Check generated outputs

7\. Check configuration consistency

8\. Check documentation consistency

9\. Confirm no secrets were introduced

10\. Report remaining limitations

```



\---



\# 37. Completion Report



The final response for a completed coding task should contain:



```text

IMPLEMENTED

\- concise description of actual changes



FILES CHANGED

\- relevant files



VALIDATION

\- commands/checks executed

\- pass/fail status



RESULT

\- important behavioral or numerical outcome



RISKS / LIMITATIONS

\- unresolved issues, if any



PULL REQUEST

\- PR information, if one was created

```



Do not omit failed validation.



Do not hide warnings.



Do not report assumptions as verified facts.



\---



\# 38. Required Behavior for Google Jules



When receiving a new task, follow this sequence:



```text

STEP 1 — Understand

Inspect repository and requirements.



STEP 2 — Verify

Inspect source, tests, configuration, and documentation.



STEP 3 — Plan

Identify exact files and implementation strategy.



STEP 4 — Check Scope

Confirm that the proposed changes are necessary.



STEP 5 — Implement

Make the smallest appropriate change.



STEP 6 — Test

Run relevant tests.



STEP 7 — Validate

Run domain-specific and regression validation.



STEP 8 — Inspect

Review git diff and generated outputs.



STEP 9 — Report

State exactly what changed and what was verified.



STEP 10 — Pull Request

Create a PR when the repository workflow requires it.

Do not merge automatically unless explicitly authorized.

```



\---



\# 39. Prohibited Behaviors



Jules MUST NOT:



\* invent requirements;

\* invent scientific methodology;

\* fabricate citations;

\* fabricate test results;

\* claim tests passed when they were not run;

\* claim validation succeeded when validation failed;

\* bypass validation gates;

\* modify raw data without authorization;

\* overwrite trusted reference outputs without authorization;

\* silently change scientific definitions;

\* silently change configuration semantics;

\* add unnecessary dependencies;

\* perform unrelated refactoring;

\* expose secrets;

\* weaken tests to make them pass;

\* suppress meaningful errors;

\* hide failed validation;

\* merge material changes without authorization;

\* declare scientific correctness without supporting evidence.



\---



\# 40. Priority Order



When instructions conflict, apply the following priority:



```text

1\. Explicit repository-owner instruction

2\. Scientific/data-integrity requirements

3\. Validation and reproducibility requirements

4\. Existing project architecture and conventions

5\. Task-specific implementation requirements

6\. General coding preferences

7\. Cosmetic improvements

```



Correctness takes priority over convenience.



Evidence takes priority over assumption.



Validation takes priority over speed.



Minimal justified change takes priority over unnecessary refactoring.



\---



\# 41. Operating Rule



The default behavior is:



```text

INSPECT FIRST

DO NOT GUESS

DO NOT INVENT

CHANGE ONLY WHAT IS REQUIRED

VALIDATE BEFORE ACCEPTANCE

REVIEW THE DIFF

REPORT EXACTLY WHAT WAS VERIFIED

```



If a task cannot be completed reliably with the available evidence, Jules must stop at the appropriate point and identify what information is missing.



The objective is not merely to produce code that runs.



The objective is to produce code that is traceable, reproducible, testable, scientifically defensible, and consistent with the existing repository.



