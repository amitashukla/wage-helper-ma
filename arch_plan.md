# MA Wage Theft Chatbot — Target Architecture

> This is the intended end-state file structure for the monorepo. It is **not** created all at once.
> Each file and directory is created in the phase where it is first needed.
> Claude Code should treat this as a reference map, not a scaffolding instruction.
> The minimal initial structure (created in Phase 0) is noted separately at the bottom.

---

```
ma-wage-theft-chatbot/
│
├── README.md                                         # Phase 0
├── .env.example                                      # Phase 0
├── .gitignore                                        # Phase 0
│
├── frontend/                                         # Phase 0 (root only)
│   ├── package.json                                  # Phase 0
│   ├── vite.config.ts                                # Phase 0
│   ├── vercel.json                                   # Phase 5
│   └── src/
│       ├── App.tsx                                   # Phase 4
│       ├── main.tsx                                  # Phase 4
│       ├── types/
│       │   └── index.ts                              # Phase 4
│       ├── hooks/
│       │   └── useSession.ts                         # Phase 4
│       └── components/
│           ├── layout/
│           │   ├── ChatWindow.tsx                    # Phase 4
│           │   └── Sidebar.tsx                       # Phase 4
│           ├── chat/
│           │   ├── MessageBubble.tsx                 # Phase 4
│           │   ├── BotMessage.tsx                    # Phase 4
│           │   ├── TypingIndicator.tsx               # Phase 4
│           │   ├── VerdictBanner.tsx                 # Phase 4
│           │   ├── ViolationCategoryBadge.tsx        # Phase 4
│           │   ├── PriorComplaintsCallout.tsx        # Phase 4
│           │   └── CitationBlock.tsx                 # Phase 4
│           ├── input/
│           │   ├── InputBar.tsx                      # Phase 4
│           │   └── InputHints.tsx                    # Phase 4
│           ├── session/
│           │   └── SessionPill.tsx                   # Phase 4
│           └── sidebar/
│               └── SuggestedNextSteps.tsx            # Phase 4
│
├── backend/                                          # Phase 0 (root only)
│   ├── requirements.txt                              # Phase 0
│   ├── railway.json                                  # Phase 5
│   ├── main.py                                       # Phase 2
│   ├── prompts/
│   │   ├── system.txt                                # Phase 3
│   │   └── few_shot.txt                              # Phase 3
│   ├── routers/
│   │   ├── chat.py                                   # Phase 3
│   │   ├── statute.py                                # Phase 2
│   │   ├── violations.py                             # Phase 2
│   │   └── complaints.py                             # Phase 2
│   ├── services/
│   │   ├── rag.py                                    # Phase 3
│   │   ├── statute_search.py                         # Phase 2
│   │   ├── violation_mapper.py                       # Phase 2
│   │   ├── complaint_lookup.py                       # Phase 2
│   │   ├── citation_verifier.py                      # Phase 3
│   │   ├── input_guard.py                            # Phase 3
│   │   └── llm.py                                    # Phase 3
│   ├── db/
│   │   ├── connection.py                             # Phase 1
│   │   └── models.py                                 # Phase 1
│   └── session/
│       └── schema.py                                 # Phase 3
│
├── data/
│   ├── raw/                                          # Phase 0 (empty, gitignored)
│   │   ├── complaints.xlsx                           # user-supplied, not committed
│   │   └── civil_enforcement.xlsx                   # user-supplied, not committed
│   ├── publications/                                 # Phase 1
│   │   ├── manifest.json                             # Phase 1
│   │   └── {slug}.pdf  (×24)                        # Phase 1
│   ├── processed/                                    # Phase 1
│   │   ├── complaints.json                           # Phase 1
│   │   └── civil_enforcement.json                   # Phase 1
│   └── statutes/
│       └── chapter149_v{YYYYMMDD}.json              # Phase 1
│
├── embeddings/
│   └── statute_embeddings_v{YYYYMMDD}.npy           # Phase 1
│
└── scripts/
    ├── download_publications.py                      # Phase 1
    ├── scrape_statute.py                             # Phase 1
    ├── ingest_excel.py                               # Phase 1
    ├── embed_statutes.py                             # Phase 1
    └── validate_data.py                              # Phase 1
```

---

## Minimal initial structure (Phase 0 only)

This is all that exists after Step 0.3. Everything else is created incrementally:

```
ma-wage-theft-chatbot/
├── README.md
├── .env.example
├── .gitignore
├── frontend/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   └── requirements.txt
└── data/
    └── raw/             # empty directory, gitignored contents
```

---

## Component responsibility summary

| Component | Responsibility | Phase |
|---|---|---|
| `ChatWindow.tsx` | Outer container, message list, scroll-to-bottom | 4 |
| `Sidebar.tsx` | Right panel layout: next steps + clinic link | 4 |
| `MessageBubble.tsx` | Shell: avatar, bubble wrapper, user vs. bot routing | 4 |
| `BotMessage.tsx` | Composes bot response: verdict → prose → badges → callout → citation | 4 |
| `TypingIndicator.tsx` | Three-dot loading animation | 4 |
| `VerdictBanner.tsx` | Verdict bar with high/low/fallback confidence variants | 4 |
| `ViolationCategoryBadge.tsx` | Individual teal violation category pill | 4 |
| `PriorComplaintsCallout.tsx` | Amber employer complaint callout, conditionally rendered | 4 |
| `CitationBlock.tsx` | Collapsible statute citation with verbatim text | 4 |
| `InputBar.tsx` | Textarea, send button, static disclaimer text | 4 |
| `InputHints.tsx` | Rotating starter prompt chips, hidden after first message | 4 |
| `SessionPill.tsx` | "What I know" tag strip, hidden until first tag exists | 4 |
| `SuggestedNextSteps.tsx` | Dynamic next-step buttons inside sidebar | 4 |
