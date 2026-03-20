#!/usr/bin/env python3
"""Awesome Miner - Recursive resource scanner"""
import json, re, os, sys, time, subprocess
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("/root/clawd/awesome-miner/data")
AWESOME_DIR = Path("/root/clawd/awesome")
STATUS_FILE = DATA_DIR / "status.json"
RESOURCES_FILE = DATA_DIR / "resources.json"
LOG_FILE = DATA_DIR / "scan.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {"phase":"scanning","total_links":699,"scanned":0,"relevant":0,
            "immediate":0,"longterm":0,"categories":{}}

def save_status(s):
    s["last_update"] = datetime.now().isoformat()
    STATUS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))

def load_resources():
    if RESOURCES_FILE.exists():
        return json.loads(RESOURCES_FILE.read_text())
    return {"immediate":[], "longterm":[], "archive":[]}

def save_resources(r):
    RESOURCES_FILE.write_text(json.dumps(r, ensure_ascii=False, indent=2))

# Keywords that indicate value for an AI agent
IMMEDIATE_KEYWORDS = [
    'llm', 'gpt', 'chatgpt', 'openai', 'anthropic', 'claude', 'gemini',
    'langchain', 'llamaindex', 'rag', 'vector', 'embedding', 'chromadb',
    'agent', 'autonomous', 'autogen', 'crewai', 'multi-agent',
    'prompt', 'prompt-engineering', 'few-shot', 'chain-of-thought',
    'fine-tune', 'lora', 'qlora', 'sft', 'rlhf',
    'ollama', 'vllm', 'text-generation', 'llama', 'mistral',
    'self-hosted', 'homelab', 'docker-compose',
    'github-actions', 'cicd', 'deploy', 'automation',
    'api-wrapper', 'sdk', 'openai-api',
    'memory', 'knowledge-graph', 'neo4j', 'context',
    'web-scraping', 'crawler', 'playwright', 'selenium',
    'tts', 'stt', 'whisper', 'speech',
    'image-generation', 'stable-diffusion', 'dall-e', 'midjourney',
    'cursor', 'copilot', 'code-generation', 'codex',
]

LONGTERM_KEYWORDS = [
    'scalability', 'distributed', 'consensus', 'raft', 'paxos',
    'observability', 'prometheus', 'grafana', 'monitoring',
    'security', 'penetration', 'vulnerability', 'zero-trust',
    'startup', 'saas', 'business-model', 'monetization',
    'newsletter', 'content-marketing', 'growth', 'seo',
    'design-system', 'ui-ux', 'tailwind', 'react', 'nextjs',
    'database', 'postgresql', 'redis', 'elasticsearch',
    'graphql', 'grpc', 'websocket', 'microservice',
    'rust', 'wasm', 'performance', 'optimization',
    'machine-learning', 'pytorch', 'tensorflow', 'jupyter',
    'data-pipeline', 'airflow', 'spark', 'kafka',
    'linux', 'bash', 'zsh', 'tmux', 'neovim',
    'git', 'github', 'code-review', 'testing', 'tdd',
]

def score_resource(name, desc, url):
    """Score a resource link and categorize it."""
    text = f"{name} {desc}".lower()
    url_lower = url.lower()
    
    imm_score = 0
    long_score = 0
    imm_hits = []
    long_hits = []
    
    for kw in IMMEDIATE_KEYWORDS:
        if kw in text or kw in url_lower:
            imm_score += 2
            imm_hits.append(kw)
    
    for kw in LONGTERM_KEYWORDS:
        if kw in text or kw in url_lower:
            long_score += 1
            long_hits.append(kw)
    
    if imm_score >= 4:
        return "immediate", imm_score, imm_hits[:5]
    elif long_score >= 3 or imm_score >= 2:
        return "longterm", max(long_score, imm_score), (long_hits + imm_hits)[:5]
    return "archive", 0, []

def parse_awesome_readme(content):
    """Parse an awesome list README into structured resources."""
    resources = []
    current_section = ""
    
    for line in content.split('\n'):
        # Section headers
        h_match = re.match(r'^#{1,3}\s+(.+)$', line)
        if h_match:
            current_section = h_match.group(1).strip()
            continue
        
        # Links: - [Name](URL) - Description
        link_match = re.match(r'^[\s-]*\[([^\]]+)\]\(([^)]+)\)(?:\s*[-–—]\s*(.+))?', line)
        if link_match:
            name = link_match.group(1).strip()
            url = link_match.group(2).strip()
            desc = link_match.group(3).strip() if link_match.group(3) else ""
            
            # Skip non-github or non-project links
            if not url.startswith('http'):
                continue
            if any(x in url for x in ['#', 'mailto:', 'javascript:']):
                continue
                
            resources.append({
                "name": name,
                "url": url,
                "desc": desc[:200] if desc else "",
                "section": current_section
            })
    
    return resources

def fetch_readme(repo_url):
    """Fetch README content from a GitHub repo."""
    # Extract owner/repo
    match = re.match(r'https://github\.com/([^/]+/[^/]+)', repo_url)
    if not match:
        return None
    
    repo_path = match.group(1)
    readme_url = f"https://raw.githubusercontent.com/{repo_path}/main/README.md"
    
    try:
        result = subprocess.run(
            ['curl', '-sL', '--max-time', '15', readme_url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return result.stdout
        
        # Try master branch
        readme_url = f"https://raw.githubusercontent.com/{repo_path}/master/README.md"
        result = subprocess.run(
            ['curl', '-sL', '--max-time', '15', readme_url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return result.stdout
    except Exception as e:
        log(f"  ❌ Fetch error: {e}")
    
    return None

# Load filtered links
links_file = DATA_DIR / "filtered_links.json"
if not links_file.exists():
    log("❌ No filtered_links.json found")
    sys.exit(1)

links = json.loads(links_file.read_text())
status = load_status()
resources = load_resources()

log(f"🔍 Starting recursive scan of {len(links)} awesome lists")
log(f"=" * 60)

seen_urls = set()
total_new = 0

for i, link in enumerate(links):
    name = link['name']
    url = link['url']
    
    log(f"\n📖 [{i+1}/{len(links)}] Scanning: {name}")
    log(f"   URL: {url}")
    
    content = fetch_readme(url)
    if not content:
        log(f"  ⚠️ SKIP: Could not fetch README")
        status["scanned"] = i + 1
        save_status(status)
        continue
    
    log(f"   📄 README: {len(content)} chars")
    
    parsed = parse_awesome_readme(content)
    log(f"   🔗 Found {len(parsed)} resource links")
    
    new_count = 0
    for res in parsed:
        if res['url'] in seen_urls:
            continue
        seen_urls.add(res['url'])
        
        category, score, keywords = score_resource(res['name'], res['desc'], res['url'])
        
        if category != "archive" and score > 0:
            entry = {
                "name": res['name'],
                "url": res['url'],
                "desc": res['desc'],
                "source_list": name,
                "source_section": res['section'],
                "tags": keywords,
                "score": score,
                "added": datetime.now().isoformat()
            }
            
            if category == "immediate":
                resources["immediate"].append(entry)
                status["immediate"] = len(resources["immediate"])
            else:
                resources["longterm"].append(entry)
                status["longterm"] = len(resources["longterm"])
            
            new_count += 1
            total_new += 1
    
    log(f"   ✅ New relevant: {new_count} (total: {total_new})")
    
    # Update status after each list
    status["scanned"] = i + 1
    status["relevant"] = len(resources["immediate"]) + len(resources["longterm"])
    status["phase_detail"] = f"Scanning {name}... Found {total_new} resources"
    
    # Category breakdown
    cats = {}
    for r in resources["immediate"] + resources["longterm"]:
        src = r.get("source_list", "unknown")
        if src not in cats:
            cats[src] = {"count": 0, "desc": ""}
        cats[src]["count"] += 1
    status["categories"] = cats
    
    save_status(status)
    save_resources(resources)
    
    # Rate limit
    time.sleep(0.5)

# Sort by score
resources["immediate"].sort(key=lambda x: x.get("score", 0), reverse=True)
resources["longterm"].sort(key=lambda x: x.get("score", 0), reverse=True)

status["phase"] = "done"
status["phase_detail"] = f"Complete! {len(resources['immediate'])} immediate + {len(resources['longterm'])} long-term resources"
save_status(status)
save_resources(resources)

log(f"\n{'='*60}")
log(f"🏁 SCAN COMPLETE")
log(f"   Immediate action: {len(resources['immediate'])} resources")
log(f"   Long-term maintain: {len(resources['longterm'])} resources")
log(f"   Total unique scanned: {len(seen_urls)}")
