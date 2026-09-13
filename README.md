# Cogniflow

**Cogniflow** is an AI-powered knowledge companion that turns the information a person cares about into a personalized daily audio briefing.

The product is designed for moments when people cannot or do not want to look at a screen—commuting, driving, walking, exercising, or doing chores. Instead of asking users to browse through endless feeds and podcasts, it learns their interests, context, and existing knowledge, then helps them continuously absorb useful new ideas.

## How it works

Users begin by setting a lightweight profile:

- Age range and region
- Interests and topics they want to follow
- Current knowledge level
- Preferred episode length

They can then combine topics and information sources such as:

- AI, startups, technology, markets, history, and science
- Hacker News, The New York Times, financial publications, and company blogs
- OpenAI news, major-company updates, and China–US model developments

Each day, the product presents a small set of relevant stories. The user selects what they want to understand and clicks **Generate Podcast**. AI filters repetition, connects related ideas, adds useful context, and organizes the selection into a coherent personal audio episode.

## MVP

The first MVP focuses on demonstrating the complete product experience:

1. Set a personal profile and knowledge level.
2. Select interests, tags, and preferred sources.
3. Browse a personalized daily feed.
4. Add several stories to an episode queue.
5. Generate a structured personal briefing.
6. Listen through a simple podcast player.
7. Review an episode summary and chapters.

The current demo uses mock stories and simulated generation. It does not call paid APIs or collect personal data.

## Demo

![Cogniflow interactive demo overview](assets/cogniflow-overview.jpg)

Open `index.html` directly in a modern browser. No installation or build step is required.

The repository currently contains:

```text
.
├── index.html   # Interactive overview demo
├── styles.css   # Responsive visual design
├── app.js       # Mock feed, generation, and player interactions
└── README.md    # Product and MVP overview
```

This prototype is intended to answer one question: **can AI turn a person's information interests into a daily audio experience that genuinely improves how they understand the world?**
