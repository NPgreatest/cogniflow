# Signal — AI Personal Podcast MVP

Signal turns the news and knowledge a person cares about into a short, personalized audio briefing. The first release is a focused, two-engineer experiment: can a listener describe their context, choose a few trusted inputs, and receive a coherent episode that feels more useful than opening five feeds?

## Product vision

Build an AI audio companion that learns a listener's interests and knowledge boundary, finds the most valuable new information, and turns it into an understandable podcast for moments when looking at a screen is inconvenient. The long-term product is not another podcast directory; it is a personal knowledge layer that decides what is worth hearing now.

## Core user pain

- Useful information is scattered across publications, feeds, and topics.
- Choosing, reading, deduplicating, and contextualizing stories takes more time than listening.
- Generic podcasts repeat what listeners already know and rarely match the time or depth available.
- Existing feeds optimize for clicks and recency, not a person's knowledge gaps.

## MVP flow

1. **Set a profile:** age range, region, interests, and knowledge level.
2. **Choose inputs:** mix sources and topics such as The New York Times, financial news, Hacker News, startups, AI, OpenAI, China–US model progress, and major-company updates.
3. **Curate today:** review a mock feed and add several stories to a listening queue.
4. **Generate:** click **Generate Podcast**. The system retrieves, filters, deduplicates, orders, and writes a personalized episode.
5. **Listen:** click **Start Listening** in the resulting player and review the episode summary and chapter list.

The included browser demo uses mock data and simulated generation. It makes no network requests and requires no paid API.

## Non-goals for the first sprint

- A production news crawler, licensing system, or publisher partnership
- Real-time coverage or comprehensive source support
- A native mobile app, social feed, or creator marketplace
- Perfect voice cloning, multi-speaker production, or studio-quality mastering
- A durable personalization model, payments, accounts, or cross-device sync
- Autonomous publishing without source attribution and human-visible review

## 1–2 week sprint scope

### Week 1 — prove the loop

- Agree on one target user: a busy, tech-curious Bay Area professional.
- Ship profile, source/topic selection, mock daily feed, queue, generation state, and player states.
- Define the content-orchestration contract: selected items in; cited script, chapters, and audio segments out.
- Build one happy-path server endpoint with cached sample articles and one TTS voice.
- Conduct 3–5 short usability sessions focused on whether the generated outline feels worth listening to.

### Week 2 — one real vertical

- Connect one legally accessible source type (for example Hacker News API plus publisher links/snippets).
- Add deduplication, relevance ranking, source attribution, and graceful failure states.
- Generate a 5–10 minute episode from selected items; cache the script and audio artifact.
- Add lightweight feedback: already knew this, go deeper, less like this.
- Demo end-to-end and decide whether retention intent justifies another sprint.

**Sprint success signal:** at least 3 of 5 target users generate an episode, listen past the midpoint, and say they would use another briefing within a week.

## Suggested stack

| Layer | MVP choice | Why |
| --- | --- | --- |
| Web | Next.js + TypeScript + Tailwind CSS | Fast UI iteration and a simple path to server routes |
| API | Next.js route handlers initially; FastAPI only if audio work needs Python | Avoid a premature second service |
| Storage | SQLite/Drizzle locally, Postgres/Supabase when deployed | Simple local setup with an easy upgrade path |
| Ingestion | Hacker News API/RSS and cached fixtures | Low-friction, inspectable inputs |
| Orchestration | Structured LLM output validated with Zod | Predictable episode outline, citations, and chapters |
| Audio | Provider-neutral TTS adapter + local/mock provider | Swap voices/providers without changing orchestration |
| Jobs/files | In-process job for demo; object storage and a queue later | Keep the first vertical small |
| Quality | Vitest + Playwright smoke test | Protect core flow without heavy test infrastructure |

Keep model and TTS providers behind interfaces. Never commit API keys; use `.env.local` based on `.env.example` when real services are introduced.

## Repository structure

```text
.
├── index.html          # Dependency-free interactive overview prototype
├── styles.css          # Visual system and responsive layout
├── app.js              # Mock state, feed, generation, and player behavior
├── README.md           # Product, sprint, architecture, and collaboration guide
├── CONTRIBUTING.md     # Branch, issue, review, and definition-of-done rules
└── .gitignore
```

When implementation begins, evolve toward `apps/web`, `packages/orchestration`, `packages/audio`, and `packages/shared` only after those boundaries become real.

## Two-person ownership

### Founder / you

- Product direction and weekly scope decisions
- TTS evaluation, audio segmentation, stitching, and playback quality
- Content orchestration: retrieval policy, ranking, deduplication, episode structure, prompting, and evaluation
- User interviews and the definition of “worth listening to”

### Collaborating engineer

- Frontend/backend integration and product-state plumbing
- Source/feed ingestion, normalization, caching, and attribution
- Job/status APIs, persistence, error handling, and deployment path
- Integration tests and operational reliability

Use ownership to create clear decision rights, not silos. Each person reviews the other's changes; shared contracts (story, episode, chapter, audio job) are agreed on before implementation.

## Work together now, or solo first?

**Recommendation: build the first clickable and one generated sample yourself for 2–3 focused days, then start the two-person sprint.** The included prototype is the clickable portion, so the next solo proof is a single compelling 5–10 minute sample created from fixed inputs. This prevents two engineers from parallelizing an unclear product loop. Bring in the collaborator immediately after that sample if they can commit at least 6–8 hours in the same week and independently own ingestion/integration.

Work together from day one only if both of you have already listened to the same sample output, agree on the target user and success signal, and can set two non-overlapping workstreams. Stay solo for the full first week if schedules are uncertain, the partner mainly wants to brainstorm, or the episode format is still changing daily. The gating question is not engineering capacity; it is whether the audio result is promising enough to integrate.

## Issues and pull requests

- Create one issue per user-visible outcome, sized to half a day or less when possible.
- Prefix titles with `feat:`, `fix:`, `spike:`, `docs:`, or `chore:` and include acceptance criteria.
- Branch from `main` using `feat/<issue>-short-name` or `fix/<issue>-short-name`.
- Keep PRs small, link the issue, add screenshots/audio samples, list tests, and name follow-ups explicitly.
- Require one approval and passing checks before merge; prefer squash merge.
- Never push directly to `main` once the collaborator joins. Use draft PRs early for contract changes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the working agreement and issue template.

## Milestones

| Milestone | Exit criteria |
| --- | --- |
| M0 — Product contract | Target user, sample episode, schema, and success signal agreed |
| M1 — Clickable loop | Profile → selection → queue → generation → player works with mocks |
| M2 — First real episode | One real source produces a cited, playable 5–10 minute briefing |
| M3 — Feedback loop | Users can signal known/deeper/less; 3–5 sessions completed |
| M4 — Continue/pivot decision | Listening behavior and interviews support or reject another sprint |

## Run the demo

Open `index.html` directly in a modern browser. No install or build step is required. For stricter browser settings, serve the folder with any static file server.

## Privacy and content notes

The repository should remain private while the product direction and provider experiments are early. Store the minimum profile data, make personalization editable, retain source links, and validate publisher/API terms before using full article text. AI-generated scripts should clearly distinguish sourced facts from commentary.
