# 🧠 AI Upskill Digest Agent

A multi-agent [Strands](https://github.com/awslabs/strands-agents) pipeline that fetches, ranks, and writes a daily AI upskilling digest from **Hacker News**, **Simon Willison's blog**, **Hugging Face Blog**, and **Sebastian Raschka's newsletter** — saved as a clean markdown file.

**Focus:** Tutorials, tools, research, and model updates that help you learn and build with AI — not funding news or company drama.

**Cost:** ~$0.002–0.004 per run (~$1.50/year running daily)

---

## 📁 Project Structure

```
AIDailyUpdates/
├── agent.py                  # Main orchestrator — run this
├── tools/
│   ├── rss_fetcher.py        # Fetches RSS from technical AI blogs
│   ├── hn_fetcher.py         # Fetches Hacker News via Algolia API
│   ├── article_fetcher.py    # Fetches full article text for richer summaries
│   └── save_digest.py        # Writes markdown digest to digests/
├── prompts/
│   ├── ranker.txt            # Prompt for filtering + ranking agent
│   └── writer.txt            # Prompt for digest writer agent
├── digests/                  # Output — created automatically on first run
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/AIDailyUpdates.git
cd AIDailyUpdates
pip install -r requirements.txt
```

### 2. Configure your model provider

**Option A — Amazon Bedrock (default)**

**macOS / Linux:**
```bash
aws configure
# or set manually:
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

**Windows (Command Prompt):**
```cmd
aws configure
:: or set manually:
set AWS_ACCESS_KEY_ID=your_key
set AWS_SECRET_ACCESS_KEY=your_secret
set AWS_DEFAULT_REGION=us-east-1
```

**Windows (PowerShell):**
```powershell
aws configure
# or set manually:
$env:AWS_ACCESS_KEY_ID = "your_key"
$env:AWS_SECRET_ACCESS_KEY = "your_secret"
$env:AWS_DEFAULT_REGION = "us-east-1"
```

Make sure you have model access enabled in the AWS Bedrock console for:
- `amazon.nova-micro-v1:0`
- `amazon.nova-lite-v1:0`

---

**Option B — Anthropic API**

In `agent.py`, uncomment these lines:
```python
# RANKER_MODEL_ID = "claude-haiku-4-5-20251001"
# WRITER_MODEL_ID = "claude-haiku-4-5-20251001"
```

Then set your API key:

**macOS / Linux:**
```bash
export ANTHROPIC_API_KEY=your_key
```

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=your_key
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "your_key"
```

Get your key at [console.anthropic.com](https://console.anthropic.com) → API Keys.

---

**Option C — Ollama (free, runs locally)**

```bash
ollama pull llama3.2
```

Then in `agent.py`, replace `BedrockModel` with:
```python
from strands.models.ollama import OllamaModel
model = OllamaModel(host="http://localhost:11434", model_id="llama3.2")
```

### 3. Run it

```bash
python agent.py
```

Your digest will be saved to `digests/digest-YYYY-MM-DD.md`.

---

## ⏰ Schedule It (Run Daily Automatically)

### macOS / Linux — cron

```bash
crontab -e
# Add this line to run every morning at 7am:
0 7 * * * cd /path/to/AIDailyUpdates && python agent.py >> /path/to/AIDailyUpdates/run.log 2>&1
```

### Windows — Task Scheduler

1. Open **Task Scheduler** → Create Basic Task
2. Set trigger: **Daily** at your preferred time
3. Set action: **Start a program**
   - Program: `python`
   - Arguments: `agent.py`
   - Start in: `C:\path\to\AIDailyUpdates`
4. Click Finish

Or use PowerShell to create the task:
```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "agent.py" -WorkingDirectory "C:\path\to\AIDailyUpdates"
$trigger = New-ScheduledTaskTrigger -Daily -At "7:00AM"
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "AIDailyDigest"
```

### AWS Lambda + EventBridge (serverless)

Package the project into a Lambda function and trigger with EventBridge:
```
cron(0 7 * * ? *)
```

---

## 🏗️ How It Works

```
Orchestrator (agent.py)
│
├── Step 1: Fetch
│   ├── fetch_rss_stories()    → Simon Willison, Hugging Face Blog, Sebastian Raschka
│   └── fetch_hn_ai_stories()  → Hacker News Algolia API (last 7 days, >10 points)
│
├── Step 2: Rank (Nova Micro — cheapest model)
│   └── Filters to upskilling content, deduplicates, scores, returns top 6
│
├── Step 2.5: Enrich
│   └── Fetches full article text for each ranked story (safe URL validation included)
│
└── Step 3: Write (Nova Lite — slightly smarter)
    └── Writes themed markdown digest with takeaways + saves to digests/
```

**Why two different models?**
- Ranking is a classification task → cheapest model is sufficient
- Writing needs better language quality → one tier up
- This cuts cost by ~40% vs using one model for everything

**Sources chosen for quality:**
- **Simon Willison** — code-heavy LLM tool breakdowns, posted daily
- **Hugging Face Blog** — tutorials, model cards, deployment guides
- **Sebastian Raschka** — research paper explanations, ML architecture deep dives
- **Hacker News** — community-vetted recent AI projects and discussions

---

## 📄 Sample Output

```markdown
# 🧠 AI Upskill Digest — March 03, 2026

> What to learn and build with AI today.

---

## 📚 Tutorials & Guides

### [PRX Part 3 — Training a Text-to-Image Model in 24h!](https://huggingface.co/blog/Photoroom/prx-part3)
*Source: Hugging Face Blog*
Covers how Photoroom trained a production-quality diffusion model using perceptual
losses and token routing within a strict 24-hour compute budget.
**Takeaway:** Use their training recipe as a template for fine-tuning image models
on a tight budget.

---

## 🔬 Research Worth Reading

### [Understanding the 4 Main Approaches to LLM Evaluation](https://magazine.sebastianraschka.com/p/llm-evaluation-4-approaches)
*Source: Sebastian Raschka*
Breaks down multiple-choice benchmarks, verifier-based evaluation, leaderboards,
and LLM-as-judge — explaining when each is appropriate.
**Takeaway:** Use LLM-as-judge for open-ended outputs, verifiers for math/code,
benchmarks only for rough capability comparisons.
```

---

## 🔧 Customization

**Add more RSS sources** — edit `tools/rss_fetcher.py`:
```python
RSS_SOURCES = {
    "Simon Willison":    "https://simonwillison.net/atom/everything/",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "Sebastian Raschka": "https://magazine.sebastianraschka.com/feed",
    "Your New Source":   "https://example.com/feed.xml",   # add here
}
```

**Change topic focus** — edit `prompts/ranker.txt` to adjust scoring priorities.

**Change digest style** — edit `prompts/writer.txt` to change tone, sections, or format.

**Add email delivery** — after the writer saves the digest, read it and send via Gmail MCP or SMTP.

---

## 💰 Cost Reference

| Model | Per run | Per month (daily) |
|-------|---------|-------------------|
| Nova Micro (ranker) | ~$0.0005 | ~$0.015 |
| Nova Lite (writer) | ~$0.002 | ~$0.06 |
| **Total** | **~$0.003** | **~$0.09** |
| Anthropic Haiku | ~$0.004 | ~$0.12 |
| Ollama local | $0.00 | $0.00 |

---

## 🔒 Security

- XML feeds parsed with `defusedxml` to prevent XXE injection
- Article URLs validated against private IP ranges before fetching (SSRF protection)
- No credentials stored in code — all via environment variables
