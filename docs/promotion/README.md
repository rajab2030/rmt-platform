# Promotion record

This directory holds finished launch copy and a factual record of promotion
work. It does not change the platform's architecture or operating guarantees.

## Published assets

- Project homepage: https://rajab2030.github.io/rmt-platform/
- Technical article: https://rajab2030.github.io/rmt-platform/agent-action-audit-trail.html
- Source: https://github.com/rajab2030/rmt-platform
- Feedback: https://github.com/rajab2030/rmt-platform/discussions
- Launch announcement: https://github.com/rajab2030/rmt-platform/discussions/3
- Profile introduction: https://github.com/rajab2030/rajab2030
- Newcomer tasks: https://github.com/rajab2030/rmt-platform/issues/1 and
  https://github.com/rajab2030/rmt-platform/issues/2

[Finished social posts](social-posts.md) are available for a connected account.
Social publishing is not implied by these files being present in GitHub.

## Publication evidence — 2026-09-18

- Website and article source published in `f0df2c1`; pre-push gate passed 642
  tests. GitHub CI and the Pages build both completed successfully.
- Homepage, article, stylesheet, and preview image returned HTTP 200. GitHub
  Pages reports `built` with HTTPS enforced. The repository's homepage field
  points to the deployed site.
- Local Chromium checks passed at 1280px and 390px widths for both pages,
  without horizontal overflow. Local asset links and image alternatives were
  checked; the mobile screenshot was visually inspected.
- GitHub Discussions was enabled and announcement #3 published. The previously
  absent profile repository was created with the completed RMT introduction.
- The GitHub bio edit was denied because the current token lacks user-profile
  write scope. The bio remains unchanged; the profile README is live.
- Metricool was suggested for social publishing but no connection was confirmed.
  LinkedIn, Reddit, and other external social posts have not been submitted.
  Completed copy is in `social-posts.md`; no writing task remains for the owner.

## Baseline

GitHub API snapshot on 2026-09-18, before the website launch:

| Metric | Value |
| --- | ---: |
| Stars | 0 |
| Forks | 0 |
| Subscribers | 0 |
| Views in GitHub's current traffic window | 1 |
| Unique visitors in that window | 1 |
| Clones in that window | 109 |
| Unique cloners in that window | 42 |

Traffic counts may include automation and prior activity. Clones are not proof
of adoption, and this is not a measured result of the new promotion.

For a later comparison, read the same GitHub endpoints (`traffic/views`,
`traffic/clones`, and `traffic/popular/referrers`) and record the collection date.
Also count useful setup reports, successful trial reports, and contributions.
No recurring posting or analytics job is installed by this promotion work.

## Publishing boundaries

The demo recording is historical and uses automated approval inputs. The later
security remediation has separate test and deployment evidence. Public copy
must preserve that distinction, policy-dependent approval, and the supported
single-process boundary. Do not claim all actions need human approval or that
the system guarantees exactly-once execution.

The site is a static presentation of already-public repository content,
published from `master:/docs` with GitHub Pages. It contains no backend access,
credentials, tracking scripts, or user data collection.
