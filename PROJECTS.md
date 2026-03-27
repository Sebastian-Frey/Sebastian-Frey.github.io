# Project Descriptions

Detailed descriptions of all projects featured on the portfolio.

---

## 1. LLM-Augmented GNN Forecasting (Master's Thesis)

**Category:** Research / Deep Learning
**Status:** Published on arXiv
**Link:** [arxiv.org/abs/2603.13059](https://arxiv.org/abs/2603.13059)
**Tech:** PyTorch, GNNs, LLMs, Sentence-BERT, DuckDB

A novel spatiotemporal forecasting framework developed as a Master's Thesis at Nova School of Business and Economics. The system uses LLM-derived semantic graphs to predict Cost-Per-Click (CPC) auction prices. The core contribution demonstrates that explicit relational structures (semantic similarity graphs built from LLM embeddings) improve medium-to-long-term forecasting robustness compared to foundation model baselines. The pipeline processes auction data through Sentence-BERT for semantic feature extraction, constructs dynamic graphs, and applies Graph Neural Networks for temporal prediction.

---

## 2. 4youcast: Personalized Generative Audio

**Category:** Product / Startup
**Status:** Live
**Link:** [4youcast.com](https://4youcast.com)
**Tech:** Python, PostgreSQL, GCP, GitHub Actions, React

A real-time personalized news-to-podcast generation platform, co-founded and built from scratch. The architecture follows a "zero-caching" design, meaning every audio output is uniquely generated per user request rather than served from pre-rendered content. The system orchestrates complex LLM workflows for content curation and summarization, then synthesizes high-fidelity audio through Google Cloud Text-to-Speech. Infrastructure runs on GCP with CI/CD through GitHub Actions and a React frontend.

---

## 3. Clustering Comparison (Latent Discovery)

**Category:** Data Science / Unsupervised Learning
**Status:** Complete (detail page on portfolio)
**Route:** `/projects/latent-discovery`
**Tech:** UMAP, HDBSCAN, GMM, K-Means, Scikit-Learn

A comparative manifold learning pipeline applied to financial fraud detection. Takes a 28-dimensional financial transaction dataset and projects it into 3D latent space using UMAP for visualization. Three clustering algorithms are compared:

- **K-Means:** Baseline partitioning method - fast but assumes spherical clusters
- **GMM (Gaussian Mixture Models):** Probabilistic soft clustering - captures elliptical structures
- **HDBSCAN:** Density-based hierarchical method - identifies noise points and irregular cluster shapes

The project includes 3D UMAP visualizations, density heatmaps, feature importance analysis, and performance metrics comparing silhouette scores and cluster quality. The detail page features animated GIFs of the latent space exploration and interactive visualizations.

**Key Images:** 8 figures including 3D UMAP projections per algorithm, density heatmaps, feature heatmaps, HDBSCAN noise analysis, and animated latent space journey.

---

## 4. Nationwide Real-Estate Valuation API

**Category:** Production ML / Industry
**Status:** Proprietary (IMMOunited GmbH)
**Tech:** Time Series, R, Ensemble Models, Data Quality Monitoring, API-Hosting

A production machine learning system that provides real-time property price estimations for the Austrian real estate market. The model covers 1.8M+ records with 300+ engineered features, serving base price predictions for approximately 80% of the Austrian market through a production REST API. Built during tenure as Data Scientist / Product Owner at IMMOunited. The system includes automated data quality monitoring and validation pipelines to maintain prediction reliability at scale.

*This project is proprietary and details are limited due to confidentiality.*

---

## 5. BiasBreaker

**Category:** NLP / LLM Application
**Status:** Complete (detail page on portfolio)
**Route:** `/projects/biasbreaker`
**Tech:** OpenAI API (GPT-4o), BeautifulSoup4, Streamlit

An LLM-powered tool that creates source-aware, unbiased news articles by combining content from ideologically opposed sources (e.g., Fox News vs. CNN). The pipeline:

1. **Input:** User provides URLs from opposing news sources
2. **Processing:** BeautifulSoup4 scrapes article content; GPT-4o analyzes bias patterns and synthesizes a neutral version
3. **Output:** A balanced article that preserves factual content while removing ideological framing

Works independently of language and topic. Built with Streamlit for a dashboard interface. The detail page features a 3-step slideshow walkthrough demonstrating the input-processing-output flow.

**Key Images:** 4 screenshots showing input, loading, output, and data persistence views.

---

## 6. Eternal Chess

**Category:** Systems / Real-Time / Creative Engineering
**Status:** Live (detail page on portfolio)
**Route:** `/projects/eternal-chess`
**Tech:** chess.js, python-chess, FastAPI, WebSocket, Docker, Vanilla JS

A real-time multiplayer chess game powered by WebSockets. One shared board for the world — the game persists even when everyone leaves. Server validates every move with python-chess and broadcasts state to all connected clients instantly.

**How it works:**

1. **User Move** — Player clicks a piece or types SAN notation on the cyberpunk-styled board
2. **WebSocket Send** — The frontend sends the move over a persistent WebSocket connection
3. **Server Validate** — FastAPI server validates the move with python-chess, rejecting illegal moves
4. **Broadcast** — Valid moves are broadcast to all connected clients in real time
5. **Board Refresh** — All viewers see the move with a sliding piece animation and sound effect

**Features:**
- **Round-robin queue** — When 3+ people are online, each person makes one move then goes to the back of the line. Server enforces turn order and notifies players when it's their turn.
- **Move animations & sounds** — Pieces slide smoothly between squares. Distinct sounds for moves, captures, and check.
- **Check/game-over notifications** — Visual banners for check and game-over states. Vote-to-restart system with majority threshold.
- **Persistent state** — Game state synced to GitHub as source of truth. Server resumes from last position on restart.

**Design:** Cyberpunk aesthetic with slate-950 backgrounds, electric blue neon accents, glitch effect title, live telemetry dashboard showing server status, FEN, move history, and PGN. Metrics ribbon displays total moves, WebSocket latency, and connected viewers.

---

## 7. SentinelLTV

**Category:** ML Engineering / MLOps
**Status:** Complete (detail page on portfolio)
**Route:** `/projects/sentinel-ltv`
**Tech:** XGBoost, Scikit-Learn, Hyperparameter Tuning, ML-Ops

An end-to-end machine learning pipeline for high-throughput customer churn prediction and lifetime value (LTV) forecasting. The system features:

- **Automated Preprocessing:** Data cleaning, feature engineering, and transformation pipelines
- **Model Training:** XGBoost classifier with GridSearch hyperparameter optimization
- **Validation:** Production-grade cross-validation strategies with learning curve analysis
- **Evaluation:** Confusion matrices, feature importance rankings, CV score distributions

The detail page showcases performance metrics, hyperparameter tuning results, and multiple visualization charts including confusion matrices, cross-validation scores, feature importance plots, learning curves, and churn distribution donuts.

**Key Images:** 5 charts covering confusion matrix, CV scores, churn donut, feature importance, and learning curves.
