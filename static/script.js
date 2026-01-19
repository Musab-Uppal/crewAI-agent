// static/script.js - Complete updated version
document.addEventListener("DOMContentLoaded", function () {
  const topicInput = document.getElementById("topicInput");
  const generateBtn = document.getElementById("generateBtn");
  const resultsContainer = document.getElementById("resultsContainer");
  const loadingModal = document.getElementById("loadingModal");
  const apiInfoModal = document.getElementById("apiInfoModal");
  const topicChips = document.querySelectorAll(".topic-chip");

  let currentStep = 0;
  let stepInterval;

  // Handle example topic chips
  topicChips.forEach((chip) => {
    chip.addEventListener("click", function () {
      topicInput.value = this.textContent;
      topicInput.focus();
    });
  });

  // Handle Enter key in input
  topicInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter" && !generateBtn.disabled) {
      e.preventDefault();
      generateHeadline();
    }
  });

  // Handle generate button click
  generateBtn.addEventListener("click", function (e) {
    e.preventDefault();
    generateHeadline();
  });

  async function generateHeadline() {
    const topic = topicInput.value.trim();

    if (!topic) {
      showError("Please enter a topic");
      topicInput.focus();
      return;
    }

    // Disable button and show loading
    generateBtn.disabled = true;
    generateBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i><span>Generating...</span>';

    // Show loading modal
    showLoadingModal();

    try {
      console.log("Sending request for topic:", topic);

      const response = await fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ topic: topic }),
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Response data:", data);

      // Simulate agent steps
      simulateAgentSteps(() => {
        hideLoadingModal();
        displayResult(data, topic);
      });
    } catch (error) {
      console.error("Error:", error);
      hideLoadingModal();
      showError(`Error: ${error.message}. Check console for details.`);
    } finally {
      generateBtn.disabled = false;
      generateBtn.innerHTML =
        '<i class="fas fa-bolt"></i><span>Generate Headline</span>';
    }
  }

  // ============================================================================
  // CRON JOB FUNCTIONS
  // ============================================================================

  async function checkCronStatus() {
    try {
      const response = await fetch("/api/cron/status");
      const data = await response.json();

      document.getElementById("cronStatus").innerHTML =
        `<span style="color: #10b981;">✓ Active</span>`;
      document.getElementById("nextRun").textContent =
        data.schedule?.in_words || "9:00 AM UTC";

      // Update the results panel with status
      updateCronStatusPanel(data);
    } catch (error) {
      document.getElementById("cronStatus").innerHTML =
        `<span style="color: #ef4444;">✗ Error</span>`;
      console.error("Cron status check failed:", error);
    }
  }

  async function triggerAutomation() {
    const topic = prompt("Enter a topic (or leave empty for daily topic):", "");

    const generateBtn = document.getElementById("generateBtn");
    const originalText = generateBtn.innerHTML;

    generateBtn.disabled = true;
    generateBtn.innerHTML =
      '<i class="fas fa-robot fa-spin"></i><span>Running Automation...</span>';

    try {
      const response = await fetch("/api/automation/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic || undefined }),
      });

      const result = await response.json();

      if (result.success) {
        // Display the result
        displayResult(result.result, result.topic);

        // Show success message
        showNotification("Automation completed successfully!", "success");
      } else {
        showNotification(`Error: ${result.error}`, "error");
      }
    } catch (error) {
      showNotification(
        `Failed to trigger automation: ${error.message}`,
        "error",
      );
    } finally {
      generateBtn.disabled = false;
      generateBtn.innerHTML = originalText;
    }
  }

  function updateCronStatusPanel(statusData) {
    // Create or update a status panel in results
    const statusHTML = `
            <div class="cron-status-panel">
                <h4><i class="fas fa-robot"></i> Automation Status</h4>
                <div class="status-grid">
                    <div class="status-item">
                        <div class="status-label">Schedule</div>
                        <div class="status-value">${statusData.schedule.human_readable}</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Next Run</div>
                        <div class="status-value">${statusData.schedule.in_words}</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Total Runs</div>
                        <div class="status-value">${statusData.statistics.total_executions}</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Success Rate</div>
                        <div class="status-value">
                            ${
                              statusData.statistics.total_executions > 0
                                ? Math.round(
                                    (statusData.statistics.successful /
                                      statusData.statistics.total_executions) *
                                      100,
                                  )
                                : 0
                            }%
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Insert at top of results
    const resultsContainer = document.getElementById("resultsContainer");
    if (resultsContainer) {
      const existingStatus =
        resultsContainer.querySelector(".cron-status-panel");
      if (existingStatus) {
        existingStatus.innerHTML = statusHTML;
      } else {
        resultsContainer.insertAdjacentHTML("afterbegin", statusHTML);
      }
    }
  }

  // ============================================================================
  // UI HELPER FUNCTIONS
  // ============================================================================

  function showLoadingModal() {
    loadingModal.style.display = "block";
    startStepAnimation();
  }

  function hideLoadingModal() {
    loadingModal.style.display = "none";
    if (stepInterval) {
      clearInterval(stepInterval);
    }
    currentStep = 0;
    updateAgentSteps();
  }

  function startStepAnimation() {
    const steps = document.querySelectorAll(".agent-step");
    steps.forEach((step) => step.classList.remove("active"));

    currentStep = 0;
    updateAgentSteps();

    stepInterval = setInterval(() => {
      currentStep = (currentStep + 1) % 5; // 0-4 steps
      updateAgentSteps();
    }, 1500);
  }

  function updateAgentSteps() {
    const steps = document.querySelectorAll(".agent-step");
    steps.forEach((step, index) => {
      if (index < currentStep) {
        step.classList.add("active");
      } else {
        step.classList.remove("active");
      }
    });
  }

  function simulateAgentSteps(callback) {
    setTimeout(callback, 5000); // Simulate processing time
  }

  function displayResult(data, topic) {
    console.log("Displaying result:", data);

    const resultHTML = data.success
      ? createSuccessHTML(data, topic)
      : createErrorHTML(data);

    resultsContainer.innerHTML = resultHTML;

    // Smooth scroll to results
    setTimeout(() => {
      resultsContainer.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 100);
  }

  function createSuccessHTML(data, topic) {
    const now = new Date();
    const date = now.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });

    const time = now.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    // Clean headline
    let headline = data.headline || "No headline generated";
    headline = headline.replace(/^HEADLINE:\s*/i, "").trim();

    // Format key points
    let keyPointsHTML = "";
    if (data.key_points && data.key_points.length > 0) {
      keyPointsHTML = `
                <div class="key-points-card">
                    <div class="key-points-header">
                        <i class="fas fa-key"></i>
                        <h4>Key Information</h4>
                    </div>
                    <div class="key-points-list">
                        ${data.key_points
                          .map(
                            (point) => `
                            <div class="key-point-item">
                                <i class="fas fa-chevron-right"></i>
                                <span>${point}</span>
                            </div>
                        `,
                          )
                          .join("")}
                    </div>
                </div>
            `;
    }

    // Slack status
    const slackSuccess =
      data.slack_status === "Sent" ||
      data.slack_status?.toLowerCase().includes("success");

    return `
            <div class="headline-result">
                <!-- Header -->
                <div class="result-header">
                    <div class="topic-display">
                        <i class="fas fa-bullseye"></i>
                        <h3>${topic}</h3>
                    </div>
                    <div class="status-badges">
                        <span class="status-badge status-success">
                            <i class="fas fa-check-circle"></i> Generated
                        </span>
                        <span class="status-badge ${slackSuccess ? "status-success" : "status-info"}">
                            <i class="fab fa-slack"></i> ${slackSuccess ? "Sent to Slack" : "Slack Pending"}
                        </span>
                        <span class="status-badge status-info">
                            <i class="fas fa-save"></i> Saved to Sheets
                        </span>
                    </div>
                </div>
                
                <!-- Headline Display -->
                <div class="headline-display-section">
                    <div class="headline-wrapper">
                        <i class="fas fa-quote-left quote-icon left"></i>
                        <h2 class="headline-text">${headline}</h2>
                        <i class="fas fa-quote-right quote-icon right"></i>
                    </div>
                    
                    ${keyPointsHTML}
                    
                    <div class="metadata-grid">
                        <div class="metadata-item">
                            <i class="far fa-calendar"></i>
                            <div class="metadata-content">
                                <div class="metadata-label">Date</div>
                                <div class="metadata-value">${date}</div>
                            </div>
                        </div>
                        
                        <div class="metadata-item">
                            <i class="far fa-clock"></i>
                            <div class="metadata-content">
                                <div class="metadata-label">Time</div>
                                <div class="metadata-value">${time}</div>
                            </div>
                        </div>
                        
                        <div class="metadata-item">
                            <i class="fas fa-hashtag"></i>
                            <div class="metadata-content">
                                <div class="metadata-label">Words</div>
                                <div class="metadata-value">${headline.split(" ").length}</div>
                            </div>
                        </div>
                        
                        <div class="metadata-item">
                            <i class="fas fa-robot"></i>
                            <div class="metadata-content">
                                <div class="metadata-label">Agents Used</div>
                                <div class="metadata-value">${data.agents_used ? data.agents_used.join(", ") : "2"}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="action-section">
                    <a href="https://docs.google.com/spreadsheets/d/${data.spreadsheet_link || "1Ol0Fi9OE-DX78E_187x3BGggQm2LeRTbawmJm3tgF5o"}" 
                       target="_blank" 
                       class="action-button primary">
                        <i class="fab fa-google-drive"></i>
                        <span>View in Google Sheets</span>
                        <i class="fas fa-external-link-alt external-icon"></i>
                    </a>
                    
                    <button onclick="copyToClipboard('${headline.replace(/'/g, "\\'")}')" 
                            class="action-button secondary">
                        <i class="far fa-copy"></i>
                        <span>Copy Headline</span>
                    </button>
                    
                    <button onclick="shareResult('${headline.replace(/'/g, "\\'")}', '${topic}')" 
                            class="action-button tertiary">
                        <i class="fas fa-share-alt"></i>
                        <span>Share Result</span>
                    </button>
                </div>
                
                <!-- System Status -->
                <div class="system-status-section">
                    <h4><i class="fas fa-server"></i> System Status</h4>
                    <div class="status-grid">
                        <div class="system-status-item">
                            <i class="fas fa-search"></i>
                            <div>
                                <div class="system-status-label">Research Agent</div>
                                <div class="system-status-value success">Complete</div>
                            </div>
                        </div>
                        
                        <div class="system-status-item">
                            <i class="fab fa-slack ${slackSuccess ? "success" : "warning"}"></i>
                            <div>
                                <div class="system-status-label">Slack Integration</div>
                                <div class="system-status-value ${slackSuccess ? "success" : "warning"}">
                                    ${slackSuccess ? "Message Sent" : "Check Configuration"}
                                </div>
                            </div>
                        </div>
                        
                        <div class="system-status-item">
                            <i class="fab fa-google"></i>
                            <div>
                                <div class="system-status-label">Google Sheets</div>
                                <div class="system-status-value success">Data Saved</div>
                            </div>
                        </div>
                        
                        <div class="system-status-item">
                            <i class="fas fa-database"></i>
                            <div>
                                <div class="system-status-label">API Connection</div>
                                <div class="system-status-value success">Active</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
  }

  function createErrorHTML(data) {
    const errorMessage =
      data.error || "Unknown error occurred. Please check your API keys.";

    return `
            <div class="headline-result">
                <div class="result-header">
                    <div class="topic-display">
                        <i class="fas fa-exclamation-triangle"></i>
                        <h3>Generation Failed</h3>
                    </div>
                    <span class="status-badge status-error">
                        <i class="fas fa-times-circle"></i>
                        Error Occurred
                    </span>
                </div>
                
                <div class="headline-display-section">
                    <div style="text-align: center; padding: 2rem;">
                        <i class="fas fa-exclamation-circle" style="font-size: 3rem; color: var(--error); margin-bottom: 1rem;"></i>
                        <h3 style="color: var(--error); margin-bottom: 1rem;">Error Generating Headline</h3>
                        <p style="color: var(--text-secondary);">${errorMessage}</p>
                    </div>
                </div>
                
                <div class="system-status-section">
                    <h4><i class="fas fa-wrench"></i> Troubleshooting Tips</h4>
                    <div class="key-points-list">
                        <div class="key-point-item">
                            <i class="fas fa-check-circle"></i>
                            <span>Check that all API keys are properly set in your environment variables</span>
                        </div>
                        <div class="key-point-item">
                            <i class="fas fa-check-circle"></i>
                            <span>Ensure the Google Sheet is shared with your service account</span>
                        </div>
                        <div class="key-point-item">
                            <i class="fas fa-check-circle"></i>
                            <span>Verify internet connectivity and API rate limits</span>
                        </div>
                        <div class="key-point-item">
                            <i class="fas fa-check-circle"></i>
                            <span>Try a different topic or check the console for detailed errors</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
  }

  function showError(message) {
    const errorHTML = `
            <div class="headline-result">
                <div class="headline-display-section" style="text-align: center; padding: 2rem;">
                    <p style="color: var(--error); font-size: 1rem;">
                        <i class="fas fa-exclamation-circle" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                        ${message}
                    </p>
                </div>
            </div>
        `;
    resultsContainer.innerHTML = errorHTML;
  }

  function showNotification(message, type = "info") {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
            <i class="fas fa-${type === "success" ? "check-circle" : "exclamation-circle"}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">&times;</button>
        `;

    // Add to page
    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }

  // ============================================================================
  // GLOBAL FUNCTIONS
  // ============================================================================

  // Copy to clipboard function
  window.copyToClipboard = function (text) {
    navigator.clipboard
      .writeText(text)
      .then(function () {
        // Show success message
        const originalBtn = event.target.closest("button");
        const originalHTML = originalBtn.innerHTML;

        originalBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        originalBtn.style.background = "rgba(16, 185, 129, 0.2)";
        originalBtn.style.color = "var(--success)";

        setTimeout(() => {
          originalBtn.innerHTML = originalHTML;
          originalBtn.style.background = "";
          originalBtn.style.color = "";
        }, 2000);
      })
      .catch(function (err) {
        alert("Failed to copy: " + err);
      });
  };

  // Share result function
  window.shareResult = function (headline, topic) {
    const shareText = `Check out this AI-generated headline about ${topic}: "${headline}"\n\nGenerated by AI Headline Generator`;

    if (navigator.share) {
      navigator.share({
        title: `AI Headline: ${topic}`,
        text: shareText,
        url: window.location.href,
      });
    } else {
      copyToClipboard(shareText);
      showNotification(
        "Headline copied to clipboard! Share it anywhere.",
        "success",
      );
    }
  };

  // Modal functions
  window.showApiInfo = function () {
    apiInfoModal.style.display = "block";
  };

  window.showCredits = function () {
    alert(
      "Built with:\n• CrewAI Framework\n• Google Gemini AI\n• Groq AI\n• Serper API\n• Slack API\n• Google Sheets API\n\nDaily Automation via Vercel Cron Jobs",
    );
  };

  window.closeModal = function () {
    apiInfoModal.style.display = "none";
  };

  window.testConnection = async function () {
    try {
      const response = await fetch("/api/health");
      const data = await response.json();
      alert(
        `✅ Connection successful!\n\nStatus: ${data.status}\nVersion: ${data.version}\nTime: ${new Date(data.timestamp).toLocaleTimeString()}`,
      );
    } catch (error) {
      alert(`❌ Connection failed: ${error.message}`);
    }
  };

  // Close modals when clicking outside
  window.onclick = function (event) {
    if (event.target === loadingModal || event.target === apiInfoModal) {
      event.target.style.display = "none";
    }
  };

  // Add click listener to close button on API info modal
  document.querySelector(".close-btn")?.addEventListener("click", function () {
    apiInfoModal.style.display = "none";
  });

  // Initialize empty state
  if (resultsContainer) {
    resultsContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-headline"></i>
                <h3>No Headlines Yet</h3>
                <p>Enter a topic above to generate your first headline!</p>
                <p class="hint">💡 Try clicking "Run Now" in the automation panel for a daily topic.</p>
            </div>
        `;
  }

  // Make functions available globally
  window.generateHeadline = generateHeadline;
  window.triggerAutomation = triggerAutomation;
  window.checkCronStatus = checkCronStatus;

  // Check cron status when page loads
  setTimeout(checkCronStatus, 1000);

  // Debug info
  console.log("AI Headline Generator script loaded successfully");
  console.log(
    "Generate button element:",
    document.getElementById("generateBtn"),
  );
  console.log("Topic input element:", document.getElementById("topicInput"));
});
