# Sebastian Frey - Portfolio Website

Personal portfolio website for **Sebastian Frey**, Applied ML Engineer & Data Scientist.

**Live:** [itssebastianfrey.com](https://itssebastianfrey.com)

## Tech Stack

- **Framework:** [Astro](https://astro.build/) v5.12
- **Styling:** [Tailwind CSS](https://tailwindcss.com/) v4.1
- **Font:** IBM Plex Mono
- **Deployment:** GitHub Pages

## Project Structure

```
├── public/
│   ├── favicon.svg
│   ├── images/projects/         # Project screenshots & visualizations
│   └── sounds/                  # Chess game sound effects
├── src/
│   ├── components/
│   │   ├── Header.astro         # Fixed nav with scroll-triggered glassmorphism
│   │   ├── Hero.astro           # Animated intro section
│   │   ├── About.astro          # Bio + skill badges
│   │   ├── Projects.astro       # Project cards grid
│   │   ├── Experience.astro     # Work timeline
│   │   ├── Education.astro      # Academic background
│   │   └── Footer.astro         # Links + social icons
│   ├── layouts/
│   │   └── MainLayout.astro     # Base HTML template
│   ├── pages/
│   │   ├── index.astro          # Homepage
│   │   └── projects/
│   │       ├── biasbreaker.astro
│   │       ├── eternal-chess.astro
│   │       ├── latent-discovery.astro
│   │       └── sentinel-ltv.astro
│   ├── styles/
│   │   └── global.css           # Tailwind imports + base styles
│   └── config.ts                # All site content (projects, experience, etc.)
├── server/                      # Eternal Chess WebSocket server (deployed separately)
│   ├── main.py                  # FastAPI + WebSocket + python-chess
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── astro.config.mjs
├── package.json
└── tsconfig.json
```

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuration

All site content is centralized in [`src/config.ts`](src/config.ts):
- Personal info & social links
- About section text & skills
- Project listings (7 projects)
- Work experience (3 positions)
- Education (2 degrees)

To update content, edit `config.ts` — no need to touch individual components.

## Featured Projects

| Project | Description |
|---------|-------------|
| **LLM-Augmented GNN Forecasting** | Spatiotemporal CPC auction forecasting using LLM-derived semantic graphs (Master's Thesis) |
| **4youcast** | Real-time personalized news-to-podcast generation pipeline |
| **Clustering Comparison** | Manifold learning with K-Means, GMM, HDBSCAN on 28D financial fraud data |
| **Real-Estate Valuation API** | ML model covering 1.8M+ records for Austrian market pricing (proprietary) |
| **BiasBreaker** | LLM-powered news bias neutralization across ideologically opposed sources |
| **Eternal Chess** | Real-time multiplayer chess via WebSocket with round-robin queue, move animations, and persistent state |
| **SentinelLTV** | End-to-end XGBoost churn prediction with GridSearch optimization |

## License

MIT License - see [LICENSE.md](LICENSE.md)
