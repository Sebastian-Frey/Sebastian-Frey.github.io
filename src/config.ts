export const siteConfig = {
  name: "Sebastian Frey",
  title: "Applied ML Engineer / Data Scientist",
  description: "Portfolio website of Sebastian Frey",
  accentColor: "#1d4ed8",
  social: {
    emailEncoded: "c2MuZnJleUBhb2wuZGU=",
    linkedin: "https://www.linkedin.com/in/sebastian--frey",
    github: "https://www.github.com/Sebastian-Frey",
  },
  aboutMe:
    "I work at the intersection of machine learning, LLMs, and real-world business problems, with a strong focus on applied modeling, forecasting, and production-ready systems. My background combines deep technical work with business-critical use cases. As a Data Scientist, I design and implement advanced ML models end to end — from raw, large-scale data pipelines to evaluation, validation, and deployment — while keeping a clear view on how models are actually used for decision-making.",
  skills: [
    "Python (Advanced)", 
    "PyTorch & JAX", 
    "Graph Neural Networks (GNNs)", 
    "NVIDIA H100/A100/T4 Orchestration", 
    "CUDA Optimization", 
    "Spark & Polars", 
    "GCP", 
    "SQL"
  ],
  projectCategories: [
    {
      name: "NLP & Research",
      projects: [
        {
          name: "Wiki Pulse",
          description:
            "Real-time unsupervised topic discovery on Wikipedia's live edit stream. Embeds articles with Sentence-BERT, clusters with HDBSCAN, and visualizes the evolving topic landscape via UMAP on a live WebSocket dashboard.",
          link: "projects/wiki-pulse",
          skills: ["HDBSCAN", "UMAP", "Sentence-BERT", "DuckDB", "Supabase", "FastAPI", "WebSocket", "Docker", "c-TF-IDF"],
        },
        {
          name: "LLM-Augmented GNN Forecasting (Master's Thesis)",
          description:
            "Developed a novel spatiotemporal framework using LLM-derived semantic graphs to predict Cost-Per-Click (CPC) auctions. Proved that explicit relational structures improve medium-to-long-term robustness over foundation models.",
          link: "https://arxiv.org/abs/2603.13059",
          skills: ["PyTorch", "GNNs", "LLMs", "Sentence-BERT", "DuckDB"],
        },
        {
          name: "4youcast: Personalized Generative Audio",
          description:
            "Architected a 'zero-caching' real-time pipeline for personalized news-to-podcast generation. Orchestrated complex LLM workflows and Google Cloud TTS synthesis for high-fidelity unique audio output.",
          link: "https://4youcast.com",
          skills: ["Python", "PostgreSQL", "GCP", "GitHub Actions", "React"],
        },
        {
          name: "BiasBreaker",
          description:
            "Leveraged LLMs to create source-aware unbiased news articles from idiologically oposed sources (Fox vs. CNN). Works independet of language and topic to create a news dashboard of unbiased information",
          link: "projects/biasbreaker",
          skills: ["OpenAI-API", "LLMs", "Streamlit", "Dashboards"],
        },
      ],
    },
    {
      name: "Production ML",
      projects: [
        {
          name: "Nationwide Real-Estate Valuation API",
          description:
            "Designed and deployed a model covering 1.8M+ records with 300+ features, providing base price estimations for 80% of the Austrian market via a real-time production API.",
          link: "#proprietary",
          skills: ["Time Series", "R", "Ensemble Models", "Data Quality Monitoring", "API-Hosting"],
        },
        {
          name: "Clustering Comparison",
          description:
            "Comparative manifold learning pipeline applying K-Means, GMM, and HDBSCAN to a 28-dimensional financial dataset projected into 3D latent space via UMAP to isolate fraudulent transaction topologies.",
          link: "projects/latent-discovery",
          skills: ["UMAP", "HDBSCAN", "GMM", "K-Means", "Scikit-Learn"],
        },
        {
          name: "SentinelLTV",
          description:
            "An end-to-end ML pipeline for high-throughput churn prediction. Features automated preprocessing, GridSearch hyperparameter optimization for XGBoost, and production-grade validation strategies to forecast customer lifetime value (LTV).",
          link: "projects/sentinel-ltv",
          skills: ["XGBoost", "Scikit-Learn", "Hyperparameter-Tuning", "ML-Ops"],
        },
      ],
    },
    {
      name: "Systems & Real-Time",
      projects: [
        {
          name: "Eternal Chess",
          description:
            "A real-time multiplayer chess game powered by WebSockets. Server validates moves with python-chess and broadcasts to all players instantly. Features a round-robin queue system, move animations, and persistent game state.",
          link: "projects/eternal-chess",
          skills: ["chess.js", "WebSocket", "python-chess", "FastAPI", "Real-Time"],
        },
      ],
    },
  ],
  projects: [
    {
      name: "LLM-Augmented GNN Forecasting (Master's Thesis)",
      description:
        "Developed a novel spatiotemporal framework using LLM-derived semantic graphs to predict Cost-Per-Click (CPC) auctions.Proved that explicit relational structures improve medium-to-long-term robustness over foundation models.",
      link: "https://arxiv.org/abs/2603.13059", // Replace with your GitHub link or PDF path
      skills: ["PyTorch", "GNNs", "LLMs", "Sentence-BERT", "DuckDB"],
    },
    {
      name: "4youcast: Personalized Generative Audio",
      description:
        "Architected a 'zero-caching' real-time pipeline for personalized news-to-podcast generation. Orchestrated complex LLM workflows and Google Cloud TTS synthesis for high-fidelity unique audio output.",
      link: "https://4youcast.com",
      skills: ["Python", "PostgreSQL", "GCP", "GitHub Actions", "React"],
    },
    {
      name: "Clustering Comparison",
      description:
        "Comparative manifold learning pipeline applying K-Means, GMM, and HDBSCAN to a 28-dimensional financial dataset projected into 3D latent space via UMAP to isolate fraudulent transaction topologies.",
      link: "projects/latent-discovery",
      skills: ["UMAP", "HDBSCAN", "GMM", "K-Means", "Scikit-Learn"],
    },
    {
      name: "Nationwide Real-Estate Valuation API",
      description:
        "Designed and deployed a model covering 1.8M+ records with 300+ features, providing base price estimations for 80% of the Austrian market via a real-time production API.",
      link: "#proprietary",
      skills: ["Time Series", "R", "Ensemble Models", "Data Quality Monitoring","API-Hosting"],
    },
    {
      name: "BiasBreaker",
      description:
        "Leveraged LLMs to create source-aware unbiased news articles from idiologically oposed sources (Fox vs. CNN). Works independet of language and topic to create a news dashboard of unbiased information",
      link: "projects/biasbreaker", 
      skills: ["OpenAI-API", "LLMs", "Streamlit", "Dashboards"],
    },
    {
      name: "Eternal Chess",
      description:
        "A real-time multiplayer chess game powered by WebSockets. Server validates moves with python-chess and broadcasts to all players instantly. Features a round-robin queue system, move animations, and persistent game state.",
      link: "projects/eternal-chess",
      skills: ["chess.js", "WebSocket", "python-chess", "FastAPI", "Real-Time"],
    },
    {
      name: "Wiki Pulse",
      description:
        "Real-time unsupervised topic discovery on Wikipedia's live edit stream. Embeds articles with Sentence-BERT, clusters with HDBSCAN, and visualizes the evolving topic landscape via UMAP on a live WebSocket dashboard.",
      link: "projects/wiki-pulse",
      skills: ["HDBSCAN", "UMAP", "Sentence-BERT", "DuckDB", "Supabase", "FastAPI", "WebSocket", "Docker", "c-TF-IDF"],
    },
    {
      name: "SentinelLTV",
      description:
        "An end-to-end ML pipeline for high-throughput churn prediction. Features automated preprocessing, GridSearch hyperparameter optimization for XGBoost, and production-grade validation strategies to forecast customer lifetime value (LTV).",
      link: "projects/sentinel-ltv",
      skills: ["XGBoost", "Scikit-Learn", "Hyperparameter-Tuning", "ML-Ops"],
    }
  ],
  experience: [
    {
      company: "IMMOunited",
      title: "Data Scientist / Product Owner",
      dateRange: "Nov 2023 - Present",
      bullets: [
        "Engineered nationwide real-estate price prediction tools utilizing mixed models and time series.",
        "Managed 1.8M records and 400 features to power internal and external client pricing tools.",
        "Served as the technical interface between business stakeholders and engineering for production ML systems.",
      ],
    },
    {
      company: "4youcast",
      title: "Co-Founder & Lead Engineer",
      dateRange: "Jan 2025 - Present",
      bullets: [
        "Building a personalized news-to-podcast platform using AI-powered assistant pipelines.",
        "Implemented robust API orchestration and rate-limit handling for LLM-based workflows.",
        "Developed a zero-caching architecture to handle unique, user-specific audio generation.",
      ],
    },
    {
      company: "KPMG Austria",
      title: "Risk Consultant (Financial Services)",
      dateRange: "Jul 2021 - Jun 2023",
      bullets: [
        "Validated risk models for national and commercial banks with assets up to €120bn.",
        "Developed the first Sanction Risk Assessment Tool for the Austrian market prior to the 2022 crisis.",
        "Led 2-4 person workstreams delivering analytics-driven reporting and stress testing.",
      ],
    },
  ],
  education: [
    {
      school: "Nova School of Business and Economics",
      degree: "Master in Business Analytics",
      dateRange: "Aug 2024 - Jan 2026",
      achievements: [
        "Nova SBE Merit Scholarship recipient.",
        "Master's Thesis: LLM-augmented time series forecasting at scale using GNNs.",
      ],
    },
    {
      school: "Vienna University of Business and Economics",
      degree: "BSc Business & Economics (Data Science Major)",
      dateRange: "2020 - 2023",
      achievements: [
        "Merit Scholarship recipient.",
        "Thesis focused on predicting residential rent through data science models.",
      ],
    },
  ],
};
