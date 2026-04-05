const refs = {
  button: document.getElementById("generateButton"),
  copyButton: document.getElementById("copyButton"),
  copyToast: document.getElementById("copyToast"),
  status: document.getElementById("status"),
  modelChoice: document.getElementById("modelChoice"),
  apiTitle: document.getElementById("apiTitle"),
  apiVersion: document.getElementById("apiVersion"),
  content: document.getElementById("content"),
  yamlOutput: document.getElementById("yamlOutput"),
  docsOutput: document.getElementById("docsOutput"),
  validationOutput: document.getElementById("validationOutput"),
  preprocessingOutput: document.getElementById("preprocessingOutput"),
  elementsOutput: document.getElementById("elementsOutput"),
  badgeRow: document.getElementById("badgeRow"),
};

function setStatus(message) {
  // Update the status line shown under the form.
  refs.status.textContent = message;
}

function getActiveOutputElement() {
  // Return the currently visible output panel element.
  const activePanel = document.querySelector(".tab-panel.active pre");
  return activePanel;
}

let copyToastTimer;

async function copyActiveOutput() {
  // Copy the currently visible output text and show a short confirmation toast.
  const activeOutput = getActiveOutputElement();
  const text = activeOutput ? activeOutput.textContent : "";

  if (!text) {
    setStatus("Nothing to copy yet.");
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    refs.copyToast.classList.add("visible");
    window.clearTimeout(copyToastTimer);
    copyToastTimer = window.setTimeout(() => {
      refs.copyToast.classList.remove("visible");
    }, 1600);
  } catch (error) {
    setStatus(`Copy failed: ${error.message}`);
  }
}

function renderBadges(result) {
  // Render summary badges for validation and extraction status.
  refs.badgeRow.innerHTML = "";
  const badges = [
    { label: result.validation.valid ? "Schema valid" : "Schema invalid", warn: !result.validation.valid },
    { label: result.llm_used ? "LLM extraction used" : "Fallback heuristics used", warn: !result.llm_used },
    { label: `${result.validation.semantic_warnings.length} semantic warnings`, warn: result.validation.semantic_warnings.length > 0 },
  ];

  badges.forEach((badge) => {
    const span = document.createElement("span");
    span.className = `badge${badge.warn ? " warn" : ""}`;
    span.textContent = badge.label;
    refs.badgeRow.appendChild(span);
  });
}

async function generate() {
  // Send the form input to the backend and populate all result panels.
  const payload = {
    input_type: "auto",
    model_choice: refs.modelChoice ? refs.modelChoice.value : "gpt_default",
    api_title: refs.apiTitle ? refs.apiTitle.value : "Generated API",
    api_version: refs.apiVersion ? refs.apiVersion.value : "1.0.0",
    content: refs.content ? refs.content.value : "",
  };

  setStatus("Generating specification...");
  refs.button.disabled = true;

  try {
    const response = await fetch("/api/v1/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Request failed with status ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    refs.yamlOutput.textContent = result.openapi_yaml;
    refs.docsOutput.textContent = result.documentation_markdown;
    refs.validationOutput.textContent = JSON.stringify(result.validation, null, 2);
    refs.preprocessingOutput.textContent = JSON.stringify(result.preprocessing, null, 2);
    refs.elementsOutput.textContent = JSON.stringify(result.extracted_elements, null, 2);
    renderBadges(result);

    const fallbackNote = result.llm_error ? ` LLM error: ${result.llm_error}` : "";
    setStatus(`Finished.${fallbackNote}`);
  } catch (error) {
    setStatus(`Generation failed: ${error.message}`);
  } finally {
    refs.button.disabled = false;
  }
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    // Switch the visible results panel when a tab is clicked.
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.target).classList.add("active");
  });
});

if (refs.button) {
  refs.button.addEventListener("click", generate);
}

if (refs.copyButton) {
  refs.copyButton.addEventListener("click", copyActiveOutput);
}
