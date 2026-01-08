# Inspiration Repositories Review Instructions

Save this file as: `docs/inspiration_repos.md`

## General Review Instructions
- Read README.md first for overall architecture and setup.
- Focus on high-level concepts, patterns, and approaches—do not copy code.
- Prioritize local/offline/privacy features that align with Applicant's local-first, no-auto-submission design.
- Note ideas for extraction, scoring, generation, review UI, sanitization, and exports.
- Test locally where feasible (many use Ollama—pull a small model like llama3.2 for quick runs).
- Record useful patterns in a separate notes file (e.g., docs/inspiration_notes.md).

## Repositories to Review

1. **srbhr/Resume-Matcher**  
   https://github.com/srbhr/Resume-Matcher  
   **Check for**:  
   - Robust PDF/DOC resume parsing and structured JSON output (inspiration for extract_profile.py)  
   - Weighted keyword + optional semantic scoring patterns (match_score.py, vectorizer.py)  
   - Cover letter generation prompts and templates (generate_app.py, prompts/)  
   - Dashboard visualizations and score breakdowns (web/ UI enhancements)

2. **stanleyume/coverlettermaker**  
   https://github.com/stanleyume/coverlettermaker  
   **Check for**:  
   - Fully local cover letter generation with Ollama (prompt engineering for generate_app.py)  
   - Simple resume upload and caching patterns  
   - Minimalist web UI structure (Tailwind inspiration for web/)

3. **olyaiy/resume-lm**  
   https://github.com/olyaiy/resume-lm  
   **Check for**:  
   - Resume tailoring logic and template system (exporter.py, prompts/)  
   - JD input handling and alignment checks

4. **eristavi/CV-Matcher**  
   https://github.com/eristavi/CV-Matcher  
   **Check for**:  
   - Offline vector embeddings and cosine similarity scoring (vectorizer.py alternatives)  
   - Batch PDF processing and golden output handling (testing ideas)

5. **sliday/resume-job-matcher**  
   https://github.com/sliday/resume-job-matcher  
   **Check for**:  
   - Weighted scoring with quality checks and red-flag detection (match_score.py enhancements)  
   - Prompt-based personalized response generation

6. **mahiikshith/LLM_RESUME_PARSER**  
   https://github.com/mahiikshith/LLM_RESUME_PARSER  
   **Check for**:  
   - LLM-based resume parsing to structured JSON as fallback to regex (extract_profile.py)  
   - Prompt design for reliable JSON output

7. **resume-llm/resume-ai**  
   https://github.com/resume-llm/resume-ai  
   **Check for**:  
   - Schema-driven resume generation and Markdown → DOCX/PDF pipeline (exporter.py)  
   - Local LLM integration patterns

8. **dadicharan/resume-analyzer**  
   https://github.com/dadicharan/resume-analyzer  
   **Check for**:  
   - Resume extraction utilities and categorization logic  
   - Customizable prompt handling in Streamlit context
