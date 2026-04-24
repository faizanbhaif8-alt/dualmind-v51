import os
import uuid
import json
import traceback
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import engine, get_db, Base, ChatSession, Message, Project
from handlers.chat import analyze_project_plan, generate_file_code, extract_code_from_response
from handlers.github import push_to_github
from middleware import setup_middleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ LIFESPAN ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🚀 Starting AI Code Manager Studio Pro...")
    print("=" * 60)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database ready")
    except Exception as e:
        print(f"❌ Database error: {e}")

    print(f"🌐 App running on port {settings.PORT}")
    print("=" * 60)
    yield
    await engine.dispose()


# ============ FASTAPI APP ============
app = FastAPI(
    title="AI Code Manager Studio Pro",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware
setup_middleware(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    print(f"⚠️  Static files: {e}")

templates = Jinja2Templates(directory="templates")


# ============ ERROR HANDLER ============
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("=" * 60)
    print("🔥 ERROR!")
    print(f"Path: {request.url.path}")
    print(traceback.format_exc())
    print("=" * 60)

    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )


# ============ FAVICON ============
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


# ============ HEALTH CHECK ============
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0"
    }


# ============ MAIN PAGE ============
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Code Manager Studio Pro</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
    <link rel="stylesheet" href="/static/style.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0d0d2b 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }

        .header {
            text-align: center;
            padding: 40px 30px;
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 36px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .header p { color: #888; font-size: 16px; }

        .steps {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .step {
            text-align: center;
            flex: 1;
            opacity: 0.4;
            transition: all 0.3s;
            cursor: pointer;
        }
        .step.active { opacity: 1; }
        .step.completed { opacity: 0.8; }
        .step-num {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-weight: bold;
            font-size: 18px;
        }
        .step.active .step-num {
            box-shadow: 0 0 20px rgba(102,126,234,0.5);
        }
        .step-label { font-size: 14px; font-weight: bold; }
        .step-sub { font-size: 11px; color: #888; }

        .card {
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            padding: 30px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .card:hover { border-color: rgba(102,126,234,0.3); }
        .card h2 { margin-bottom: 5px; font-size: 22px; }
        .card > p { color: #888; margin-bottom: 20px; font-size: 14px; }

        textarea, input[type="text"] {
            width: 100%;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            color: white;
            font-size: 16px;
            font-family: inherit;
            resize: vertical;
            transition: all 0.3s;
        }
        textarea:focus, input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102,126,234,0.15);
        }
        textarea { min-height: 120px; }

        .btn {
            padding: 12px 28px;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        .btn-primary:hover { box-shadow: 0 10px 30px rgba(102,126,234,0.4); }

        .btn-success {
            background: linear-gradient(135deg, #11998e, #38ef7d);
            color: white;
        }
        .btn-success:hover { box-shadow: 0 10px 30px rgba(56,239,125,0.4); }

        .btn-github {
            background: linear-gradient(135deg, #24292e, #444);
            color: white;
        }
        .btn-github:hover { box-shadow: 0 10px 30px rgba(0,0,0,0.4); }

        .btn-outline {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
        }
        .btn-outline:hover { border-color: #667eea; }

        .input-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
        }
        .char-count { color: #888; font-size: 13px; }

        .progress-bar {
            width: 100%;
            height: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 10px;
            width: 0%;
            transition: width 0.5s ease;
        }
        .progress-text {
            text-align: center;
            color: #888;
            margin-bottom: 20px;
        }

        .file-item {
            display: flex;
            align-items: center;
            padding: 12px 15px;
            margin: 8px 0;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            gap: 12px;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .file-item.completed {
            background: rgba(56,239,125,0.08);
            border-left: 3px solid #38ef7d;
        }
        .file-item.generating {
            background: rgba(255,193,7,0.08);
            border-left: 3px solid #ffc107;
        }
        .file-item.error {
            background: rgba(235,51,73,0.08);
            border-left: 3px solid #eb3349;
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.2);
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            flex-shrink: 0;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .plan-file {
            display: flex;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.08);
            gap: 15px;
        }
        .plan-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        .plan-info { flex: 1; }
        .plan-name { font-weight: 600; }
        .plan-desc { font-size: 13px; color: #888; }
        .plan-lang {
            padding: 4px 12px;
            background: rgba(102,126,234,0.15);
            border-radius: 15px;
            font-size: 12px;
            color: #667eea;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 12px;
            margin: 15px 0;
        }
        .alert-success {
            background: rgba(56,239,125,0.1);
            border: 1px solid #38ef7d;
            color: #38ef7d;
        }
        .alert-error {
            background: rgba(235,51,73,0.1);
            border: 1px solid #eb3349;
            color: #eb3349;
        }

        .hidden { display: none !important; }
        .action-buttons { display: flex; gap: 10px; margin-top: 20px; }

        .loading-overlay {
            text-align: center;
            padding: 30px;
        }
        .loading-overlay .spinner { margin: 0 auto 15px; width: 40px; height: 40px; }

        .repo-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .repo-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">

        <!-- Header -->
        <div class="header">
            <h1>🚀 AI Code Manager Studio Pro</h1>
            <p>AI-Powered Code Generation with Live Progress Tracking</p>
        </div>

        <!-- Steps -->
        <div class="steps">
            <div class="step active" id="step1">
                <div class="step-num">1</div>
                <div class="step-label">Describe</div>
                <div class="step-sub">Tell AI your idea</div>
            </div>
            <div class="step" id="step2">
                <div class="step-num">2</div>
                <div class="step-label">Review Plan</div>
                <div class="step-sub">AI creates structure</div>
            </div>
            <div class="step" id="step3">
                <div class="step-num">3</div>
                <div class="step-label">Generate</div>
                <div class="step-sub">Live code creation</div>
            </div>
            <div class="step" id="step4">
                <div class="step-num">4</div>
                <div class="step-label">Deploy</div>
                <div class="step-sub">Push to GitHub</div>
            </div>
        </div>

        <!-- Section 1: Describe -->
        <div class="card" id="section1">
            <h2>💡 Describe Your Project</h2>
            <p>Tell AI what you want to build. Be specific for better results.</p>
            <textarea id="projectDescription" placeholder="Example: Build a REST API for a todo app with user authentication, database models, and CRUD operations..." oninput="updateCharCount()"></textarea>
            <div class="input-row">
                <span class="char-count" id="charCount">0 characters</span>
                <button class="btn btn-primary" onclick="analyzeProject()">
                    🔍 Analyze & Create Plan
                </button>
            </div>
            <div class="loading-overlay hidden" id="analyzeLoading">
                <div class="spinner"></div>
                <p>AI is analyzing your project...</p>
            </div>
        </div>

        <!-- Section 2: Plan -->
        <div class="card hidden" id="section2">
            <h2>📋 Project Plan</h2>
            <p>Review the file structure AI created for your project</p>
            <div id="planContent"></div>
            <div class="action-buttons">
                <button class="btn btn-success" onclick="confirmAndGenerate()">✅ Confirm & Generate Code</button>
                <button class="btn btn-outline" onclick="resetApp()">↩️ Start Over</button>
            </div>
        </div>

        <!-- Section 3: Progress -->
        <div class="card hidden" id="section3">
            <h2>⚡ Live Code Generation</h2>
            <p>Watch as AI creates each file in real-time</p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p class="progress-text" id="progressText">0% Complete</p>
            <div id="fileProgressList"></div>
        </div>

        <!-- Section 4: Push -->
        <div class="card hidden" id="section4">
            <h2>📤 Deploy to GitHub</h2>
            <p>Name your project and push all generated code</p>
            <div class="alert alert-success" id="completionMessage"></div>
            <input type="text" id="repoName" placeholder="Enter repository name (e.g., my-awesome-project)" style="margin: 15px 0;">
            <button class="btn btn-github" onclick="pushToGitHub()" id="pushButton">🚀 Push to GitHub</button>
            <div id="pushStatus" style="margin-top: 15px;"></div>
        </div>

    </div>

    <script>
        // Global Variables
        let currentSessionId = null;
        let currentPlan = null;

        // Char counter
        function updateCharCount() {
            const count = document.getElementById('projectDescription').value.length;
            document.getElementById('charCount').textContent = count + ' character' + (count !== 1 ? 's' : '');
        }

        // Update steps
        function updateStep(stepNum) {
            for (let i = 1; i <= 4; i++) {
                const step = document.getElementById('step' + i);
                step.classList.remove('active', 'completed');
                if (i < stepNum) step.classList.add('completed');
                if (i === stepNum) step.classList.add('active');
            }
        }

        // Show section
        function showSection(num) {
            for (let i = 1; i <= 4; i++) {
                document.getElementById('section' + i).classList.add('hidden');
            }
            document.getElementById('section' + num).classList.remove('hidden');
            document.getElementById('section' + num).scrollIntoView({ behavior: 'smooth' });
        }

        // Step 1: Analyze Project
        async function analyzeProject() {
            const description = document.getElementById('projectDescription').value.trim();
            if (!description) {
                alert('Please describe your project first!');
                return;
            }

            document.getElementById('analyzeLoading').classList.remove('hidden');

            try {
                const formData = new FormData();
                formData.append('message', description);

                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to analyze');
                }

                const data = await response.json();
                currentSessionId = data.session_id;
                currentPlan = data.plan;

                // Display plan
                displayPlan(data.plan);
                updateStep(2);
                showSection(2);

            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                document.getElementById('analyzeLoading').classList.add('hidden');
            }
        }

        // Display Plan
        function displayPlan(plan) {
            let html = '';

            // Summary
            html += '<div style="background: rgba(102,126,234,0.08); border: 1px solid rgba(102,126,234,0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px;">';
            html += '<div style="display: flex; justify-content: space-between; padding: 8px 0;"><span>📌 Type:</span><strong>' + (plan.project_type || 'Project') + '</strong></div>';
            html += '<div style="display: flex; justify-content: space-between; padding: 8px 0;"><span>📁 Files:</span><strong>' + (plan.total_files || plan.files.length) + '</strong></div>';
            html += '<div style="display: flex; justify-content: space-between; padding: 8px 0;"><span>⏱️ Est. Time:</span><strong>' + (plan.estimated_time || '2-3 min') + '</strong></div>';
            html += '</div>';

            // Files
            html += '<h3 style="margin-bottom: 15px;">📂 Files to Create:</h3>';

            plan.files.forEach(function(file) {
                html += '<div class="plan-file">';
                html += '<div class="plan-icon">📄</div>';
                html += '<div class="plan-info">';
                html += '<div class="plan-name">' + file.name + '</div>';
                html += '<div class="plan-desc">' + (file.description || 'No description') + '</div>';
                html += '</div>';
                html += '<span class="plan-lang">' + (file.language || 'code') + '</span>';
                html += '</div>';
            });

            document.getElementById('planContent').innerHTML = html;
        }

        // Step 2: Generate Code
        async function confirmAndGenerate() {
            showSection(3);
            updateStep(3);

            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('progressText').textContent = 'Starting...';
            document.getElementById('fileProgressList').innerHTML = '';

            const formData = new FormData();
            formData.append('session_id', currentSessionId);

            try {
                const response = await fetch('/api/generate-code', {
                    method: 'POST',
                    body: formData
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                handleProgress(data);
                            } catch (e) {}
                        }
                    }
                }

            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Handle progress events
        function handleProgress(data) {
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const fileList = document.getElementById('fileProgressList');

            if (data.type === 'progress') {
                progressFill.style.width = data.percentage + '%';
                progressText.textContent = 'Generating ' + data.filename + '... (' + data.current + '/' + data.total + ')';

                fileList.innerHTML += '<div class="file-item generating" id="file-' + data.filename + '">' +
                    '<div class="spinner"></div>' +
                    '<span>' + data.filename + '</span>' +
                    '<span style="margin-left: auto; font-size: 12px; color: #888;">Generating...</span>' +
                '</div>';
            }
            else if (data.type === 'file_complete') {
                progressFill.style.width = data.percentage + '%';
                progressText.textContent = data.filename + ' completed!';

                const fileEl = document.getElementById('file-' + data.filename);
                if (fileEl) {
                    fileEl.className = 'file-item completed';
                    fileEl.innerHTML = '<span>✅</span><span>' + data.filename + '</span>' +
                        '<span style="margin-left: auto; font-size: 12px; color: #38ef7d;">Done</span>';
                }
            }
            else if (data.type === 'complete') {
                progressFill.style.width = '100%';
                progressText.textContent = 'All files generated! ✅';

                setTimeout(function() {
                    showSection(4);
                    updateStep(4);
                    document.getElementById('completionMessage').innerHTML =
                        '✅ <strong>Success!</strong> All ' + data.files.length + ' files generated. Now name your project and push to GitHub.';
                }, 1000);
            }
            else if (data.type === 'error') {
                const fileEl = document.getElementById('file-' + data.filename);
                if (fileEl) {
                    fileEl.className = 'file-item error';
                    fileEl.innerHTML = '<span>❌</span><span>' + data.filename + '</span>' +
                        '<span style="margin-left: auto; font-size: 12px; color: #eb3349;">Failed</span>';
                }
            }
        }

        // Step 3: Push to GitHub
        async function pushToGitHub() {
            const repoName = document.getElementById('repoName').value.trim();
            if (!repoName) {
                alert('Please enter a repository name!');
                return;
            }

            const pushBtn = document.getElementById('pushButton');
            pushBtn.disabled = true;
            pushBtn.textContent = '⏳ Pushing...';

            document.getElementById('pushStatus').innerHTML =
                '<div style="text-align: center; padding: 20px;"><div class="spinner" style="margin: 0 auto;"></div><p style="margin-top: 10px;">Pushing to GitHub...</p></div>';

            try {
                const formData = new FormData();
                formData.append('session_id', currentSessionId);
                formData.append('repo_name', repoName);

                const response = await fetch('/api/push-to-github', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    document.getElementById('pushStatus').innerHTML =
                        '<div class="alert alert-success">' +
                        '<strong>✅ Successfully pushed to GitHub!</strong><br><br>' +
                        '🔗 <a href="' + data.repo_url + '" target="_blank" class="repo-link">' + data.repo_url + '</a>' +
                        '</div>';
                    pushBtn.textContent = '✅ Done!';
                    pushBtn.className = 'btn btn-success';
                } else {
                    throw new Error(data.detail || 'Push failed');
                }

            } catch (error) {
                document.getElementById('pushStatus').innerHTML =
                    '<div class="alert alert-error">❌ Error: ' + error.message + '</div>';
                pushBtn.disabled = false;
                pushBtn.textContent = '🔄 Retry Push';
            }
        }

        // Reset
        function resetApp() {
            currentSessionId = null;
            currentPlan = null;
            document.getElementById('projectDescription').value = '';
            document.getElementById('repoName').value = '';
            document.getElementById('fileProgressList').innerHTML = '';
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('pushStatus').innerHTML = '';
            document.getElementById('planContent').innerHTML = '';
            document.getElementById('completionMessage').innerHTML = '';
            document.getElementById('charCount').textContent = '0 characters';

            const pushBtn = document.getElementById('pushButton');
            pushBtn.disabled = false;
            pushBtn.textContent = '🚀 Push to GitHub';
            pushBtn.className = 'btn btn-github';

            showSection(1);
            updateStep(1);
        }

        // Initialize
        updateCharCount();
        console.log('🚀 AI Code Manager Studio Pro Ready!');
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# ============ API: ANALYZE PROJECT ============
@app.post("/api/analyze")
async def analyze_project(
    message: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"📝 Analyzing: {message[:50]}...")

        plan = await analyze_project_plan(message)

        session = ChatSession(
            id=str(uuid.uuid4()),
            name=message[:50],
            status="planning"
        )
        db.add(session)

        user_msg = Message(
            session_id=session.id,
            role="user",
            content=message
        )
        db.add(user_msg)

        plan_text = f"📋 Project Plan\n\nType: {plan.get('project_type', 'N/A')}\nFiles: {plan.get('total_files', 0)}\n"
        for f in plan.get('files', []):
            plan_text += f"\n• {f['name']} - {f.get('description', '')}"

        plan_msg = Message(
            session_id=session.id,
            role="assistant",
            content=plan_text,
            files_plan=plan
        )
        db.add(plan_msg)
        await db.commit()

        logger.info(f"✅ Plan created: {session.id}")
        return {"session_id": session.id, "plan": plan}

    except Exception as e:
        logger.error(f"❌ Analyze error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ API: GENERATE CODE ============
@app.post("/api/generate-code")
async def generate_code_stream(
    session_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"⚡ Generating code for: {session_id}")

    result = await db.execute(
        select(Message).where(
            Message.session_id == session_id,
            Message.files_plan.isnot(None)
        )
    )
    plan_msg = result.scalar_one_or_none()

    if not plan_msg:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = plan_msg.files_plan
    files = plan.get('files', [])

    session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if session:
        session.status = "generating"
        await db.commit()

    async def event_generator():
        generated_files = {}

        for i, file_info in enumerate(files):
            filename = file_info['name']
            percentage = int((i / len(files)) * 100)

            yield f"data: {json.dumps({'type': 'progress', 'filename': filename, 'percentage': percentage, 'current': i+1, 'total': len(files)})}\n\n"

            try:
                code = await generate_file_code(
                    filename,
                    file_info.get('description', ''),
                    plan.get('description', '')
                )
                clean_code = extract_code_from_response(code)
                generated_files[filename] = clean_code

                yield f"data: {json.dumps({'type': 'file_complete', 'filename': filename, 'percentage': int(((i+1)/len(files))*100)})}\n\n"

            except Exception as e:
                logger.error(f"Error generating {filename}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'filename': filename, 'error': str(e)})}\n\n"

        all_code = "\n\n".join([f"# === {name} ===\n{code}" for name, code in generated_files.items()])

        code_msg = Message(
            session_id=session_id,
            role="assistant",
            content=f"✅ Generated {len(generated_files)} files",
            code=all_code
        )
        db.add(code_msg)

        project = Project(
            session_id=session_id,
            name=session.name if session else "Project",
            files=generated_files
        )
        db.add(project)

        if session:
            session.status = "completed"
        await db.commit()

        yield f"data: {json.dumps({'type': 'complete', 'files': list(generated_files.keys()), 'project_id': project.id})}\n\n"

        logger.info(f"✅ Code generation complete: {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============ API: PUSH TO GITHUB ============
@app.post("/api/push-to-github")
async def push_project_to_github(
    session_id: str = Form(...),
    repo_name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"📤 Pushing to GitHub: {repo_name}")

    if not settings.GITHUB_TOKEN or "your_token" in settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GitHub token not configured")

    result = await db.execute(select(Project).where(Project.session_id == session_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.files:
        raise HTTPException(status_code=400, detail="No files to push")

    try:
        repo_url = await push_to_github(repo_name, project.files, settings.GITHUB_TOKEN)

        project.name = repo_name
        project.repo_url = repo_url
        project.pushed = "yes"

        session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        session = session_result.scalar_one_or_none()
        if session:
            session.status = "pushed"

        await db.commit()

        logger.info(f"✅ Pushed: {repo_url}")
        return {"success": True, "repo_url": repo_url, "message": f"Pushed to {repo_url}"}

    except Exception as e:
        logger.error(f"❌ Push error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ API: GET SESSION STATUS ============
@app.get("/api/session/{session_id}")
async def get_session_status(session_id: str, db: AsyncSession = Depends(get_db)):
    session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    project_result = await db.execute(select(Project).where(Project.session_id == session_id))
    project = project_result.scalar_one_or_none()

    return {
        "session_id": session.id,
        "name": session.name,
        "status": session.status,
        "project": {
            "id": project.id if project else None,
            "name": project.name if project else None,
            "files": list(project.files.keys()) if project and project.files else [],
            "pushed": project.pushed if project else "no",
            "repo_url": project.repo_url if project else None
        } if project else None
    }


# ============ RUN ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=False)