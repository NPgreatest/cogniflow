# Contributing

## Working agreement

We optimize for a listenable end-to-end demo, not maximum infrastructure. Product decisions live in issues; code decisions live in pull requests. Raise uncertainty early with a short spike and a concrete artifact.

## Issue template

```md
## Outcome
What can the listener do when this is complete?

## Acceptance criteria
- [ ] Observable behavior
- [ ] Failure/empty state
- [ ] Demo evidence (screenshot, audio, or test)

## Out of scope
Explicitly excluded work
```

## Workflow

1. Pick or create an issue and assign one owner.
2. Create `feat/<issue>-short-name`, `fix/<issue>-short-name`, or `spike/<issue>-short-name` from `main`.
3. Open a draft PR once the data contract or user flow is visible.
4. Before review, add test notes and screenshots or an audio sample.
5. The other engineer reviews. Resolve blocking comments, then squash merge.

## Definition of done

- Acceptance criteria are met on the happy path and one failure/empty state.
- No secrets, licensed full text, or personal profile data are committed.
- Source attribution survives ingestion through script output.
- UI changes work on phone and desktop widths.
- Audio changes include a short sample and record voice/provider/settings.
- README or contracts are updated when behavior changes.

## Suggested first issues

1. `feat: define story and episode schemas`
2. `spike: produce one five-minute episode from fixed stories`
3. `feat: ingest and normalize Hacker News stories`
4. `feat: expose episode-generation job status`
5. `feat: connect prototype flow to generation endpoint`
6. `feat: capture already-known and go-deeper feedback`
