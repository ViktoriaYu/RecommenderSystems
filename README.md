# Book Recommender System (BRS)

We conducted an initial evaluation of baseline recommendation algorithms to establish performance benchmarks. The results demonstrate significant improvements from simple heuristics to advanced collaborative filtering.

| Algorithm | nDCG@10 | MAP@10 |
|-----------|---------|---------|
| Random    | 0.0096 ± 0.0037 | 0.0006 ± 0.0003 |
| Popular   | 0.2366 ± 0.0132 | 0.0264 ± 0.0022 |
| ALS(SVD)  | **0.6286 ± 0.0126** | **0.1754 ± 0.0067** |

### Key Insights:
- **ALS (SVD) outperforms Popular by 2.7×** in nDCG@10, demonstrating the power of collaborative filtering
- **65× improvement over random baseline** shows meaningful signal in the data
- Low standard deviations (± values) indicate stable and reproducible results
- Results provide a strong foundation for hybrid system development

### Evaluation Details:
- **Dataset**: Goodbooks-10k (6M ratings, 10K books, 53K users)
- **Data Split**: 80% for training and 20% for testing (simple random split)
- **Validation**: Hold-out split with bootstrap sampling (n=20)
- **Metrics**: 
  - **nDCG@10**: Normalized Discounted Cumulative Gain (ranking quality)
  - **MAP@10**: Mean Average Precision (relevance accuracy)

These results establish a solid baseline for comparing our hybrid recommendation approach in upcoming iterations.
