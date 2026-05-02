const enrollmentState = {
  samples: [],
  fullName: "",
  email: "",
  passphrase: "",
};

function normalizeText(text) {
  return (text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function setStatus(el, message) {
  if (el) {
    el.textContent = message;
  }
}

async function recordSample(button, statusEl, canvas) {
  button.disabled = true;
  button.classList.add("record-ring");
  setStatus(statusEl, "Listening...");
  const blob = await Recorder.recordWav({
    durationMs: 6000,
    minDurationMs: 2000,
    silenceDurationMs: 1200,
    silenceThreshold: 0.01,
    canvas,
  });
  button.classList.remove("record-ring");
  button.disabled = false;
  setStatus(statusEl, "Recorded. Ready to upload.");
  return blob;
}

function setupRegister() {
  const stepOne = document.getElementById("step-one");
  const stepTwo = document.getElementById("step-two");
  const startBtn = document.getElementById("start-enrollment");
  const recordBtn = document.getElementById("record-sample");
  const submitBtn = document.getElementById("submit-enrollment");
  const statusEl = document.getElementById("record-status");
  const progressEl = document.getElementById("sample-progress");
  const passphrasePreview = document.getElementById("passphrase-preview");
  const canvas = document.getElementById("waveform");

  if (!startBtn) {
    return;
  }

  startBtn.addEventListener("click", () => {
    const fullName = document.getElementById("full-name").value.trim();
    const email = document.getElementById("email").value.trim();
    const passphrase = document.getElementById("passphrase").value.trim();
    if (!fullName || !email || !passphrase) {
      setStatus(statusEl, "Please enter your full name, email, and key sentence.");
      return;
    }
    enrollmentState.fullName = fullName;
    enrollmentState.email = email;
    enrollmentState.passphrase = passphrase;
    stepOne.classList.add("hidden");
    stepTwo.classList.remove("hidden");
    if (passphrasePreview) {
      passphrasePreview.textContent = `Key sentence: \"${passphrase}\"`;
    }
    setStatus(statusEl, "Record sample 1 and say the exact key sentence.");
  });

  recordBtn.addEventListener("click", async () => {
    const blob = await recordSample(recordBtn, statusEl, canvas);
    enrollmentState.samples.push(blob);
    progressEl.textContent = `${enrollmentState.samples.length} / 5 samples captured`;

    if (enrollmentState.samples.length >= 5) {
      submitBtn.classList.remove("hidden");
      recordBtn.classList.add("hidden");
      setStatus(statusEl, "All samples captured. Submit to enroll.");
    } else {
      setStatus(
        statusEl,
        `Sample captured. Next: sample ${enrollmentState.samples.length + 1} with the same exact sentence.`
      );
    }
  });

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    setStatus(statusEl, "Uploading voiceprints...");
    const formData = new FormData();
    formData.append("full_name", enrollmentState.fullName);
    formData.append("email", enrollmentState.email);
    formData.append("passphrase", enrollmentState.passphrase);
    enrollmentState.samples.forEach((blob, index) => {
      formData.append("samples", blob, `sample_${index + 1}.wav`);
    });

    const response = await fetch("/api/register", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await parseJsonSafe(response);
      setStatus(statusEl, error.error || "Enrollment failed.");
      submitBtn.disabled = false;
      return;
    }

    setStatus(statusEl, "Enrollment complete. Redirecting to login...");
    setTimeout(() => (window.location.href = "/login"), 1200);
  });
}

function setupLogin() {
  const micBtn = document.getElementById("login-mic");
  if (!micBtn) {
    return;
  }
  const challengeEl = document.getElementById("challenge-code");
  const statusEl = document.getElementById("login-status");
  const debugEl = document.getElementById("login-debug");
  const canvas = document.getElementById("login-waveform");
  if (challengeEl) {
    challengeEl.textContent = "Say your key sentence";
  }

  micBtn.addEventListener("click", async () => {
    const blob = await recordSample(micBtn, statusEl, canvas);
    setStatus(statusEl, "Processing...");

    const formData = new FormData();
    formData.append("sample", blob, "login.wav");

    const response = await fetch("/api/login", {
      method: "POST",
      body: formData,
    });

    const data = await parseJsonSafe(response);

    if (!response.ok) {
      setStatus(statusEl, data.error || "Login failed.");
      const heardText = normalizeText(data.heard || "");
      const scoreText =
        typeof data.score === "number" ? `Similarity: ${data.score.toFixed(3)}` : "";
      const transcriptText = heardText ? `Heard: \"${heardText}\"` : "Heard: (not recognized)";
      if (debugEl) {
        debugEl.textContent = `${transcriptText}${scoreText ? ` | ${scoreText}` : ""}`;
      }
      return;
    }

    if (debugEl) {
      debugEl.textContent = "";
    }
    setStatus(statusEl, `Welcome back, ${data.full_name}! Redirecting...`);
    setTimeout(() => (window.location.href = "/dashboard"), 1200);
  });
}

setupRegister();
setupLogin();
