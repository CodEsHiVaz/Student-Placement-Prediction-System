// Client-side helpers: sidebar toggle + prediction AJAX call.

// Mobile sidebar toggle (open/close the off-canvas navigation).
document.addEventListener("DOMContentLoaded", function () {
  const menuBtn = document.getElementById("menuBtn");
  const backdrop = document.getElementById("sidebarBackdrop");
  const close = () => document.body.classList.remove("sidebar-open");

  if (menuBtn) {
    menuBtn.addEventListener("click", () =>
      document.body.classList.toggle("sidebar-open")
    );
  }
  if (backdrop) backdrop.addEventListener("click", close);
  // Close the drawer after tapping a nav link on mobile.
  document.querySelectorAll(".sidebar .nav-item").forEach((el) =>
    el.addEventListener("click", close)
  );
});

// Prediction form: validate then POST to /api/predict and render the result.
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("prediction-form");
  if (!form) return;

  const resultBox = document.getElementById("prediction-result");

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    if (!form.checkValidity()) {
      form.classList.add("was-validated");
      return;
    }

    // Build JSON payload from the form fields.
    const payload = {
      age: numVal("age"),
      gender: strVal("gender"),
      degree: strVal("degree"),
      branch: strVal("branch"),
      cgpa: numVal("cgpa"),
      internships: numVal("internships"),
      projects: numVal("projects"),
      coding_skills: numVal("coding_skills"),
      communication_skills: numVal("communication_skills"),
      aptitude_test_score: numVal("aptitude_test_score"),
      soft_skills_rating: numVal("soft_skills_rating"),
      certifications: numVal("certifications"),
      backlogs: numVal("backlogs"),
    };

    const submitBtn = form.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Predicting...";

    try {
      const resp = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();

      if (!resp.ok) {
        showError(data.error || "Prediction failed.");
      } else {
        showResult(data);
      }
    } catch (err) {
      showError("Could not reach the prediction service.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Predict Placement";
    }
  });

  function numVal(id) {
    const v = document.getElementById(id).value;
    return v === "" ? null : Number(v);
  }
  function strVal(id) {
    return document.getElementById(id).value;
  }

  function colorFor(category) {
    return { High: "success", Medium: "warning", Low: "danger" }[category] || "secondary";
  }

  function showResult(data) {
    const color = colorFor(data.category);
    const statusColor = data.predicted_status === "Placed" ? "success" : "danger";
    resultBox.innerHTML = `
      <div class="card shadow-sm border-${color}">
        <div class="card-body text-center">
          <h5 class="card-title text-muted">Placement Probability</h5>
          <div class="prob-display text-${color}">${data.probability_percentage}%</div>
          <span class="badge bg-${color} fs-6 mb-3">${data.category}</span>
          <p class="mb-0">Predicted Status:
            <span class="badge bg-${statusColor} fs-6">${data.predicted_status}</span>
          </p>
          <a href="/recommendations" class="btn btn-outline-primary mt-3">View Recommendations</a>
        </div>
      </div>`;
    resultBox.scrollIntoView({ behavior: "smooth" });
  }

  function showError(msg) {
    resultBox.innerHTML = `<div class="alert alert-danger">${msg}</div>`;
  }
});
