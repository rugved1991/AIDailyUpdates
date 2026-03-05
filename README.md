# 🧠 AI Upskill Digest Agent

A multi-agent [Strands](https://github.com/awslabs/strands-agents) pipeline that fetches, ranks, and writes a daily AI upskilling digest from **Hacker News**, **Simon Willison's blog**, **Hugging Face Blog**, **Sebastian Raschka's newsletter**, and **YouTube channels** — saved as a clean markdown file.

**Focus:** Tutorials, tools, research, model updates, and top AI news that help you learn and build with AI — not funding news or company drama.

**Cost:** ~$0.002–0.004 per run (~$1.50/year running daily) + YouTube Data API (free tier, ~6 quota units/day)

---

## 📁 Project Structure

```
AIDailyUpdates/
├── agent.py                  # Main orchestrator — run this
├── tools/
│   ├── rss_fetcher.py        # Fetches RSS from technical AI blogs
│   ├── hn_fetcher.py         # Fetches Hacker News via Algolia API
│   ├── yt_fetcher.py         # Fetches YouTube videos + transcripts
│   ├── article_fetcher.py    # Fetches full article text for richer summaries
│   ├── save_digest.py        # Writes markdown digest to digests/
│   └── email_digest.py       # Converts digest to styled HTML and emails it
├── prompts/
│   ├── ranker.txt            # Prompt for filtering + ranking agent
│   └── writer.txt            # Prompt for digest writer agent
├── digests/                  # Output — created automatically on first run
├── .env.example              # Copy to .env and fill in your API keys
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/rugved1991/AIDailyUpdates.git
cd AIDailyUpdates
pip install -r requirements.txt
```

### 2. Configure API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required for YouTube video fetching (free)
YOUTUBE_API_KEY=your_youtube_api_key_here

# Required for Anthropic API (Option B below)
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Get a YouTube Data API key (free):**
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → Create project
2. Enable **YouTube Data API v3**
3. Credentials → Create API Key → copy it into `.env`

> If `YOUTUBE_API_KEY` is not set, the YouTube fetcher is silently skipped and the digest runs on RSS + HN only.

### 3. Configure your AI model provider

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

Add your key to `.env`:
```env
ANTHROPIC_API_KEY=your_key
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

### 4. Set up email delivery (optional)

The digest is automatically emailed as a styled HTML newsletter after each run.

Add these three lines to your `.env`:

```env
EMAIL_TO=you@example.com
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

> **Gmail users:** you must use an [App Password](https://myaccount.google.com/apppasswords), not your account password.
> App Passwords require 2-Step Verification to be enabled on your Google account.

If any of these are missing, the email step is silently skipped and the digest is still saved locally.

### 5. Run it

```bash
python agent.py
```

Your digest will be saved to `digests/digest-YYYY-MM-DD.md` and emailed if configured.

---

## ⏰ Schedule It (Run Daily Automatically)

### macOS / Linux — cron

```bash
crontab -e
# Add this line to run every morning at 9am:
0 9 * * * cd /path/to/AIDailyUpdates && python agent.py >> /path/to/AIDailyUpdates/run.log 2>&1
```

### Windows — Task Scheduler (PowerShell)

```powershell
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "agent.py" `
    -WorkingDirectory "C:\Users\sadis\Documents\Workspace\AIDailyUpdates"
$trigger = New-ScheduledTaskTrigger -Daily -At "9:00AM"
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "AIDailyDigest"
```

Or manually via the UI:
1. Open **Task Scheduler** → Create Basic Task
2. Trigger: **Daily** at **9:00 AM**
3. Action: **Start a program**
   - Program: `python`
   - Arguments: `agent.py`
   - Start in: `C:\Users\sadis\Documents\Workspace\AIDailyUpdates`

### AWS Lambda + EventBridge (serverless)

Package the project into a Lambda function and trigger with EventBridge:
```
cron(0 9 * * ? *)
```

---

## 🏗️ How It Works

```
Orchestrator (agent.py)
│
├── Step 1: Fetch
│   ├── fetch_rss_stories()      → Simon Willison, Hugging Face Blog, Sebastian Raschka
│   ├── fetch_hn_ai_stories()    → Hacker News Algolia API (last 7 days, >10 points)
│   └── fetch_youtube_stories()  → Yannic Kilcher, AI Explained, Two Minute Papers, AI Daily Brief
│
├── Step 2: Rank (Nova Micro — cheapest model)
│   └── Filters, deduplicates, scores, enforces source diversity
│       Returns top 10 upskilling + top 5 news stories
│
├── Step 2.5: Enrich
│   └── Fetches full article/transcript text for each ranked story
│
└── Step 3: Write (Nova Lite — slightly smarter)
    └── Writes 5-section markdown digest + saves to digests/
```

**Why two different models?**
- Ranking is a classification task → cheapest model is sufficient
- Writing needs better language quality → one tier up
- This cuts cost by ~40% vs using one model for everything

**Sources chosen for quality:**
- **Simon Willison** — hands-on LLM tool breakdowns and agentic patterns, posted daily
- **Hugging Face Blog** — tutorials, model cards, deployment guides
- **Sebastian Raschka** — research paper explanations, ML architecture deep dives
- **Hacker News** — community-vetted recent AI projects and discussions
- **Yannic Kilcher** — paper walkthroughs and model deep dives
- **AI Explained** — weekly AI tool demos and tutorials
- **Two Minute Papers** — research summaries with practical context
- **AI Daily Brief** — daily AI news recap and trend analysis

---

## 📄 Sample Output

```markdown
# 🧠 AI Upskill Digest — March 03, 2026

> What to learn and build with AI today.

---

## 📚 Tutorials & Guides

### [Train AI models with Unsloth and Hugging Face Jobs for FREE](https://huggingface.co/blog/unsloth-jobs)
*Source: Hugging Face Blog*
Demonstrates how to use Unsloth for free model training with Hugging Face Jobs,
offering faster training and lower VRAM usage.
**Takeaway:** Use Unsloth + Hugging Face Jobs for cost-effective fine-tuning without
paying for GPU compute.

---

## 🛠️ Tools & SDKs

### [Show HN: CodeLeash — framework for quality agent development](https://codeleash.dev/)
*Source: Hacker News*
A framework that enforces code quality standards during AI agent development,
separating orchestration from quality control.
**Takeaway:** Use CodeLeash to build agents that produce consistently structured,
reviewable code outputs.

---

## 🔬 Research Worth Reading

### [Understanding and Implementing Qwen3 From Scratch](https://magazine.sebastianraschka.com/p/qwen3-from-scratch)
*Source: Sebastian Raschka*
In-depth implementation walkthrough of the Qwen3 architecture, covering its
grouped-query attention and tokenizer design.
**Takeaway:** Use this as a reference implementation when studying or adapting
open-weight LLM architectures.

---

## 🚀 Model Updates

### [Deploying Open Source VLMs on Jetson](https://huggingface.co/blog/nvidia/cosmos-on-jetson)
*Source: Hugging Face Blog*
Step-by-step guide to deploying Cosmos Reason 2B with vLLM on Jetson AGX
for edge AI applications.
**Takeaway:** Follow this recipe to run vision-language models on-device
without cloud inference costs.

---

## 📰 Top AI News

### [The Month AI Woke Up](https://www.youtube.com/watch?v=-FJ7HiPBkCM)
*Source: AI Daily Brief*
Covers the rapid acceleration in agentic AI capabilities across major labs
in February 2026 and what shifted in the market.
**Takeaway:** Agentic AI frameworks (LangGraph, CrewAI, Strands) are now the focus of major lab investment — worth prioritizing over raw model benchmarks when deciding what to learn next.
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

**Add more YouTube channels** — edit `tools/yt_fetcher.py`:
```python
YOUTUBE_CHANNELS = {
    "Yannic Kilcher":    "@YannicKilcher",
    "AI Explained":      "@aiexplained",
    "Two Minute Papers": "@TwoMinutePapers",
    "AI Daily Brief":    "@AIDailyBrief",
    "Your Channel":      "@YourChannelHandle",  # add here
}
```
Find a channel's handle by visiting it on YouTube — it's the `@name` in the URL.

**Change topic focus** — edit `prompts/ranker.txt` to adjust scoring priorities.

**Change digest style** — edit `prompts/writer.txt` to change tone, sections, or format.

**Disable email delivery** — remove or comment out the `send_digest_email` call at the bottom of `run_digest()` in `agent.py`.

---

## 💰 Cost Reference

| Model / API | Per run | Per month (daily) |
|-------------|---------|-------------------|
| Nova Micro (ranker) | ~$0.0005 | ~$0.015 |
| Nova Lite (writer) | ~$0.002 | ~$0.06 |
| **Total LLM** | **~$0.003** | **~$0.09** |
| Anthropic Haiku (alternative) | ~$0.004 | ~$0.12 |
| Ollama local | $0.00 | $0.00 |
| YouTube Data API | $0.00 | $0.00 (free tier: 10k units/day, uses ~8) |

---

## 🔒 Security

- XML feeds parsed with `defusedxml` to prevent XXE injection
- Article URLs validated against private IP ranges before fetching (SSRF protection)
- No credentials stored in code — all via `.env` file or environment variables
- `.env` is gitignored and never committed
