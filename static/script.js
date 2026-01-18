document.addEventListener("DOMContentLoaded", function () {
  const topicInput = document.getElementById("topicInput");
  const generateBtn = document.getElementById("generateBtn");
  const resultsContainer = document.getElementById("resultsContainer");
  const loadingModal = document.getElementById("loadingModal");
  const apiInfoModal = document.getElementById("apiInfoModal");
  const topicChips = document.querySelectorAll(".topic-chip");

  let currentStep = 0;
  let stepInterval;

  // Handle example topic chips - FIXED
  topicChips.forEach((chip) => {
    chip.addEventListener("click", function () {
      topicInput.value = this.textContent;
      topicInput.focus();
    });
  });

  // Handle Enter key in input
  topicInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter" && !generateBtn.disabled) {
      generateHeadline();
    }
  });

  // Handle generate button click - FIXED
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
      currentStep = (currentStep + 1) % 4; // 0-3 steps (0 for reset)
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
    });

    // Clean and format the headline
    let headlineText = data.headline || "No headline generated";
    headlineText = headlineText.replace(/^"|"$/g, "");
    headlineText = headlineText.replace(/\\n/g, "<br>");

    // Extract just the main headline if it's in a verbose format
    // This handles CrewAI's sometimes verbose output
    const cleanHeadline = headlineText.split("\n")[0];
    const details = headlineText.split("\n").slice(1).join("<br>");

    return `
        <div class="headline-result">
            <div class="headline-topic">
                <i class="fas fa-tag"></i>
                <h3>Topic: ${topic}</h3>
                <span class="status-badge status-success">
                    <i class="fas fa-check-circle"></i>
                    Successfully Generated
                </span>
            </div>
            
            <div class="headline-content">
                <div class="headline-text">${cleanHeadline}</div>
                
                ${
                  details
                    ? `
                <div class="headline-details">
                    <p><strong>Details:</strong></p>
                    <p>${details}</p>
                </div>
                `
                    : ""
                }
                
                <div class="result-meta">
                    <span><i class="far fa-calendar"></i> ${date}</span>
                    <span><i class="far fa-clock"></i> ${time}</span>
                    <span><i class="fas fa-save"></i> Saved to Google Sheets</span>
                    <span><i class="fab fa-slack"></i> Sent to Slack</span>
                </div>
            </div>
            
            <div class="result-actions">
                <a href="https://docs.google.com/spreadsheets/d/1Ol0Fi9OE-DX78E_187x3BGggQm2LeRTbawmJm3tgF5o/edit" 
                   target="_blank" 
                   class="sheet-link">
                    <i class="fab fa-google-drive"></i> View in Google Sheets
                </a>
                
                <button class="copy-btn" onclick="copyToClipboard('${cleanHeadline.replace(/'/g, "\\'")}')">
                    <i class="far fa-copy"></i> Copy Headline
                </button>
            </div>
            
            <p class="info-note">
                <i class="fas fa-info-circle"></i> 
                This headline was generated by AI, saved to Google Sheets, and shared on Slack.
            </p>
        </div>
    `;
  }

  function createErrorHTML(data) {
    const errorMessage =
      data.error || "Unknown error occurred. Please check your API keys.";

    return `
            <div class="headline-result">
                <div class="headline-topic">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Generation Failed</h3>
                    <span class="status-badge status-error">
                        <i class="fas fa-times-circle"></i>
                        Error Occurred
                    </span>
                </div>
                <div class="headline-content">
                    <p style="color: var(--error); font-size: 0.9rem; padding: 1rem;">
                        ${errorMessage}
                    </p>
                </div>
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 1rem;">
                    <i class="fas fa-lightbulb"></i> Tips:
                    <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
                        <li>Check that all API keys are properly set in your environment variables</li>
                        <li>Ensure the Google Sheet is shared with your service account</li>
                        <li>Verify internet connectivity</li>
                        <li>Try a different topic</li>
                    </ul>
                </p>
            </div>
        `;
  }

  function showError(message) {
    const errorHTML = `
            <div class="headline-result">
                <div class="headline-content" style="text-align: center; padding: 2rem;">
                    <p style="color: var(--error); font-size: 1rem;">
                        <i class="fas fa-exclamation-circle" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                        ${message}
                    </p>
                </div>
            </div>
        `;
    resultsContainer.innerHTML = errorHTML;
  }

  // Debug: Check if button event listener is attached
  console.log("Generate button:", generateBtn);
  console.log("Button event listeners:", generateBtn.onclick);

  // Modal functions
  window.showApiInfo = function () {
    apiInfoModal.style.display = "block";
  };

  window.showCredits = function () {
    alert(
      'Built with:\n• CrewAI Framework\n• Google Gemini AI\n• Groq AI\n• Serper API\n• Google Sheets API\n\nClick "API Info" for required API keys.',
    );
  };

  window.closeModal = function () {
    apiInfoModal.style.display = "none";
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
            </div>
        `;
  }

  // Make generateHeadline function available globally for testing
  window.generateHeadline = generateHeadline;
});
