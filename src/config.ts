export const siteConfig = {
  name: "Sebastian Frey",
  title: "Applied ML Engineer / Data Scientist",
  description: "Portfolio website of Sebastian Frey",
  accentColor: "#1d4ed8",
  social: {
    email: "sc.frey@aol.de",
    linkedin: "linkedin.com/in/sebastian-frey",
    github: "github.com/Sebastian-Frey",
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
  projects: [
    {
      name: "LLM-Augmented GNN Forecasting (Master's Thesis)",
      description:
        "Developed a novel spatiotemporal framework using LLM-derived semantic graphs to predict Cost-Per-Click (CPC) auctions. [cite_start]Proved that explicit relational structures improve medium-to-long-term robustness over foundation models[cite: 15, 18, 89].",
      link: "#", // Replace with your GitHub link or PDF path
      skills: ["PyTorch", "GNNs", "LLMs", "Sentence-BERT", "DuckDB"],
    },
    {
      name: "4youcast: Personalized Generative Audio",
      description:
        "Architected a 'zero-caching' real-time pipeline for personalized news-to-podcast generation. [cite_start]Orchestrated complex LLM workflows and Google Cloud TTS synthesis for high-fidelity unique audio output[cite: 23, 26, 29].",
      link: "https://4youcast.com",
      skills: ["Python", "PostgreSQL", "GCP", "GitHub Actions", "React"],
    },
    {
      name: "Nationwide Real-Estate Valuation API",
      description:
        [cite_start]"Designed and deployed a model covering 1.8M+ records with 300+ features, providing base price estimations for 80% of the Austrian market via a real-time production API[cite: 38, 39, 41].",
      link: "#",
      skills: ["Time Series", "R-Shiny", "Mixed Models", "Data Quality Monitoring"],
    },
  ],
  experience: [
    {
      company: "4youcast",
      title: "Co-Founder & Lead Engineer",
      dateRange: "Jan 2025 - Present",
      bullets: [
        [cite_start]"Building a personalized news-to-podcast platform using AI-powered assistant pipelines[cite: 69, 71].",
        [cite_start]"Implemented robust API orchestration and rate-limit handling for LLM-based workflows[cite: 71].",
        [cite_start]"Developed a zero-caching architecture to handle unique, user-specific audio generation[cite: 26].",
      ],
    },
    {
      company: "IMMOunited",
      title: "Data Scientist / Product Owner",
      dateRange: "Nov 2023 - Present",
      bullets: [
        [cite_start]"Engineered nationwide real-estate price prediction tools utilizing mixed models and time series[cite: 74, 76].",
        [cite_start]"Managed 1.8M records and 400 features to power internal and external client pricing tools[cite: 77].",
        [cite_start]"Served as the technical interface between business stakeholders and engineering for production ML systems[cite: 78].",
      ],
    },
    {
      company: "KPMG Austria",
      title: "Risk Consultant (Financial Services)",
      dateRange: "Jul 2021 - Jun 2023",
      bullets: [
        [cite_start]"Validated risk models for national and commercial banks with assets up to €120bn[cite: 49, 83].",
        [cite_start]"Developed the first Sanction Risk Assessment Tool for the Austrian market prior to the 2022 crisis[cite: 47].",
        [cite_start]"Led 2-4 person workstreams delivering analytics-driven reporting and stress testing[cite: 84, 85].",
      ],
    },
  ],
  education: [
    {
      school: "Nova School of Business and Economics",
      degree: "Master in Business Analytics",
      dateRange: "Aug 2024 - Jan 2026",
      achievements: [
        [cite_start]"Nova SBE Merit Scholarship recipient[cite: 90].",
        [cite_start]"Master's Thesis: LLM-augmented time series forecasting at scale using GNNs[cite: 89].",
      ],
    },
    {
      school: "Vienna University of Business and Economics",
      degree: "BSc Business & Economics (Data Science Major)",
      dateRange: "2020 - 2023",
      achievements: [
        [cite_start]"Merit Scholarship recipient[cite: 92].",
        [cite_start]"Thesis focused on predicting residential rent through data science models[cite: 92].",
      ],
    },
  ],
};
  ],
};
