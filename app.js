// AI Code Manager Studio Pro - Fixed JavaScript

let currentSessionId = null;
let currentPlan = null;
let currentStep = 1;
let generatedFiles = [];

// Initialize
document.addEventListener("DOMContentLoaded", function() {
    console.log("App initialized");
});

// Step 1: Analyze Project
async function analyzeProject() {
    const description = document.getElementById("projectDescription").value.trim();

    if (!description) {
        alert("Please describe your project first!");
        return;
    }

    document.getElementById("analyzeLoading").classList.remove("hidden");

    try {
        const formData = new FormData();
        formData.append("message", description);

        const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to analyze");
        }

        const data = await response.json();
        currentSessionId = data.session_id;
        currentPlan = data.plan;

        displayPlan(data.plan);
        updateStep(2);

    } catch (error) {
        alert("Error: " + error.message);
    } finally {
        document.getElementById("analyzeLoading").classList.add("hidden");
    }
}

// Display Plan
function displayPlan(plan) {
    let html = "<div style='margin: 15px 0;'>";
    html += "<strong>Project Type:</strong> " + plan.project_type + "<br>";
    html += "<strong>Description:</strong> " + plan.description + "<br>";
    html += "<strong>Total Files:</strong> " + plan.total_files + "<br>";
    html += "<strong>Estimated Time:</strong> " + (plan.estimated_time || "2-3 minutes");
    html += "</div>";

    html += "<h3 style='margin-top: 20px;'>Files to Create:</h3>";

    plan.files.forEach(function(file) {
        html += "<div class='plan-file'>";
        html += "<div class='file-icon'>file</div>";
        html += "<div><strong>" + file.name + "</strong>";
        html += "<div style='color: #888; font-size: 14px;'>" + (file.description || "") + "</div></div>";
        html += "<span style='margin-left: auto; color: #667eea;'>" + (file.language || "text") + "</span>";
        html += "</div>";
    });

    document.getElementById("planContent").innerHTML = html;
    document.getElementById("section-describe").classList.add("hidden");
    document.getElementById("section-plan").classList.remove("hidden");
}

// Step 2: Generate Code
async function confirmAndGenerate() {
    document.getElementById("section-plan").classList.add("hidden");
    document.getElementById("section-progress").classList.remove("hidden");
    updateStep(3);

    const formData = new FormData();
    formData.append("session_id", currentSessionId);

    try {
        const response = await fetch("/api/generate-code", {
            method: "POST",
            body: formData
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const data = JSON.parse(line.slice(6));
                    handleProgress(data);
                }
            }
        }

    } catch (error) {
        alert("Error generating code: " + error.message);
    }
}

// Handle Progress
function handleProgress(data) {
    if (data.type === "progress") {
        updateProgress(data.percentage, "Generating " + data.filename + "...");
        addFileProgress(data.filename, "generating");
    } else if (data.type === "file_complete") {
        updateProgress(data.percentage, data.filename + " completed!");
        updateFileProgress(data.filename, "completed");
    } else if (data.type === "complete") {
        updateProgress(100, "All files generated!");

        setTimeout(function() {
            document.getElementById("section-progress").classList.add("hidden");
            document.getElementById("section-push").classList.remove("hidden");
            document.getElementById("completionMessage").innerHTML = 
                "All " + data.files.length + " files generated successfully! Now give a name and push to GitHub.";
            updateStep(4);
        }, 1000);
    }
}

// Update Progress Bar
function updateProgress(percentage, text) {
    document.getElementById("progressFill").style.width = percentage + "%";
    document.getElementById("progressText").textContent = text;
}

// Add File Progress
function addFileProgress(filename, status) {
    const div = document.getElementById("fileProgressList");
    div.innerHTML += "<div class='file-progress-item " + status + "' id='file-" + filename + "'>" +
        (status === "generating" ? "<div class='spinner'></div>" : "OK") +
        "<span>" + filename + "</span></div>";
}

// Update File Progress
function updateFileProgress(filename, status) {
    const element = document.getElementById("file-" + filename);
    if (element) {
        element.className = "file-progress-item completed";
        const spinner = element.querySelector(".spinner");
        if (spinner) spinner.remove();
        element.innerHTML = "OK <span>" + filename + " - Done!</span>";
    }
}

// Step 3: Push to GitHub
async function pushToGitHub() {
    const repoName = document.getElementById("repoName").value.trim();
    if (!repoName) {
        alert("Please enter a repository name!");
        return;
    }

    const formData = new FormData();
    formData.append("session_id", currentSessionId);
    formData.append("repo_name", repoName);

    document.getElementById("pushStatus").innerHTML = 
        "<div style='text-align: center;'><div class='spinner' style='margin: 0 auto;'></div><p>Pushing to GitHub...</p></div>";

    try {
        const response = await fetch("/api/push-to-github", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById("pushStatus").innerHTML = 
                "<div class='alert alert-success'>Successfully pushed to GitHub!<br>" +
                "<a href='" + data.repo_url + "' target='_blank' style='color: #38ef7d;'>" + data.repo_url + "</a></div>";
        } else {
            throw new Error(data.detail || "Push failed");
        }

    } catch (error) {
        document.getElementById("pushStatus").innerHTML = 
            "<div class='alert alert-error'>Error: " + error.message + "</div>";
    }
}

// Update Step Indicator
function updateStep(stepNumber) {
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById("step" + i);
        if (i <= stepNumber) {
            step.classList.add("active");
        } else {
            step.classList.remove("active");
        }
    }
}

// Reset App
function resetApp() {
    currentSessionId = null;
    currentPlan = null;
    document.getElementById("projectDescription").value = "";
    document.getElementById("repoName").value = "";
    document.getElementById("fileProgressList").innerHTML = "";
    document.getElementById("progressFill").style.width = "0%";
    document.getElementById("pushStatus").innerHTML = "";

    document.getElementById("section-describe").classList.remove("hidden");
    document.getElementById("section-plan").classList.add("hidden");
    document.getElementById("section-progress").classList.add("hidden");
    document.getElementById("section-push").classList.add("hidden");

    updateStep(1);
}

// Templates
function useTemplate(type) {
    const templates = {
        api: "Build a RESTful API with FastAPI...",
        webapp: "Create a full-stack web application...",
        bot: "Build a Telegram bot...",
        scraper: "Create a web scraper...",
        dashboard: "Build an admin dashboard...",
        cli: "Create a command-line tool..."
    };

    const textarea = document.getElementById("projectDescription");
    if (textarea && templates[type]) {
        textarea.value = templates[type];
        textarea.focus();
    }
}

console.log("AI Code Manager Studio Pro Ready!");