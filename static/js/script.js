// ---------- Tab switching ----------

const tabButtons = document.querySelectorAll(".tab-btn");
const panels = {
  submit: document.getElementById("submit-panel"),
  list: document.getElementById("list-panel"),
};

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabButtons.forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");

    Object.values(panels).forEach((p) => p.classList.remove("active"));
    panels[btn.dataset.tab].classList.add("active");

    if (btn.dataset.tab === "list") {
      loadAppointments();
    }
  });
});

// ---------- Submit form ----------

const form = document.getElementById("appointment-form");
const statusMsg = document.getElementById("submit-status");

// ---------- Reminder message dropdown ----------

const messageTemplate = document.getElementById("message_template");
const customMessageField = document.getElementById("custom-message-field");
const customMessageInput = document.getElementById("message_custom");

messageTemplate.addEventListener("change", () => {
  const isCustom = messageTemplate.value === "custom";
  customMessageField.hidden = !isCustom;
  if (!isCustom) customMessageInput.value = "";
});

function resolveMessage() {
  if (messageTemplate.value === "custom") {
    return customMessageInput.value.trim();
  }
  return messageTemplate.value; // "" for default, or a preset template string
}

// Auto-insert the ":" as the person types digits, e.g. "930" -> "9:30".
const timeInput = document.getElementById("appointment_time_only");
timeInput.addEventListener("input", () => {
  let digits = timeInput.value.replace(/[^0-9]/g, "").slice(0, 4);
  if (digits.length >= 3) {
    timeInput.value = `${digits.slice(0, digits.length - 2)}:${digits.slice(-2)}`;
  } else {
    timeInput.value = digits;
  }
});

// Converts "9:30" + "PM" -> "21:30" (24-hour, what the backend expects).
function to24Hour(timeStr, ampm) {
  const [hStr, mStr] = timeStr.split(":");
  let h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10);

  if (isNaN(h) || isNaN(m) || h < 1 || h > 12 || m < 0 || m > 59) return null;

  if (ampm === "AM") {
    if (h === 12) h = 0;
  } else {
    if (h !== 12) h += 12;
  }
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const submitBtn = form.querySelector("button[type=submit]");

  const dateVal = document.getElementById("appointment_date").value; // e.g. "2026-07-18"
  const timeVal12 = timeInput.value.trim(); // e.g. "9:30"
  const ampm = document.getElementById("appointment_ampm").value; // "AM" | "PM"

  if (!dateVal || !timeVal12) {
    showStatus("Please pick both a date and a time.", "error");
    return;
  }

  const time24 = to24Hour(timeVal12, ampm);
  if (!time24) {
    showStatus("Please enter a valid time as HH:MM.", "error");
    return;
  }

  submitBtn.disabled = true;

  const payload = {
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    appointment_time: `${dateVal}T${time24}`, // matches the ISO format the backend expects
    message: resolveMessage(),
    reminder_lead_minutes: document.getElementById("reminder_lead").value,
  };

  try {
    const res = await fetch("/api/appointments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    showStatus(data.message, data.success ? "success" : "error");

    if (data.success) {
      form.reset();
      customMessageField.hidden = true;
    }
  } catch (err) {
    showStatus("Could not reach the server. Please try again.", "error");
  } finally {
    submitBtn.disabled = false;
  }
});

function showStatus(text, kind) {
  statusMsg.textContent = text;
  statusMsg.className = "status-msg show " + kind;
}

// ---------- List appointments ----------

const listContainer = document.getElementById("list-container");
const refreshBtn = document.getElementById("refresh-btn");

refreshBtn.addEventListener("click", loadAppointments);

async function loadAppointments() {
  listContainer.innerHTML = '<p class="empty-state">Loading…</p>';

  try {
    const res = await fetch("/api/appointments");
    const data = await res.json();

    if (!data.success) {
      listContainer.innerHTML = `<p class="empty-state">Could not load list: ${escapeHtml(data.message)}</p>`;
      return;
    }

    if (data.appointments.length === 0) {
      listContainer.innerHTML = '<p class="empty-state">No appointments booked yet.</p>';
      return;
    }

    listContainer.innerHTML = data.appointments
      .map((appt, i) => renderTicket(appt, i + 1))
      .join("");
  } catch (err) {
    listContainer.innerHTML = '<p class="empty-state">Could not reach the server.</p>';
  }
}

function renderTicket(appt, index) {
  const time = formatTime(appt.appointment_time);
  const statusClass = appt.reminder_sent ? "sent" : "pending";
  const statusText = appt.reminder_sent ? "Reminder sent" : "Pending";

  return `
    <div class="ticket-row" data-id="${escapeHtml(appt.id)}">
      <div class="ticket-num">#${String(index).padStart(3, "0")}</div>
      <div class="ticket-info">
        <div class="ticket-name">${escapeHtml(appt.name)}</div>
        <div class="ticket-email">${escapeHtml(appt.email)}</div>
      </div>
      <div class="ticket-time">
        ${time}
        <span class="ticket-status ${statusClass}">${statusText}</span>
      </div>
      <button class="ticket-delete" type="button" data-id="${escapeHtml(appt.id)}" title="Delete this appointment" aria-label="Delete appointment for ${escapeHtml(appt.name)}">✕</button>
    </div>
  `;
}

function formatTime(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  if (isNaN(d)) return isoString;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------- Delete a single appointment ----------

listContainer.addEventListener("click", async (e) => {
  const btn = e.target.closest(".ticket-delete");
  if (!btn) return;

  const id = btn.dataset.id;
  const row = btn.closest(".ticket-row");

  if (!confirm("Delete this appointment? This cannot be undone.")) return;

  btn.disabled = true;

  try {
    const res = await fetch(`/api/appointments/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    const data = await res.json();

    if (data.success) {
      // Remove just this row instead of a full reload, so the rest of
      // the list doesn't flash/scroll.
      if (row) row.remove();
      if (!listContainer.querySelector(".ticket-row")) {
        listContainer.innerHTML = '<p class="empty-state">No appointments booked yet.</p>';
      }
    } else {
      alert(data.message || "Could not delete appointment.");
      btn.disabled = false;
    }
  } catch (err) {
    alert("Could not reach the server.");
    btn.disabled = false;
  }
});

// ---------- Clear all appointments ----------

const clearAllBtn = document.getElementById("clear-all-btn");

clearAllBtn.addEventListener("click", async () => {
  if (!confirm("Delete ALL appointments? This cannot be undone.")) return;

  clearAllBtn.disabled = true;

  try {
    const res = await fetch("/api/appointments", { method: "DELETE" });
    const data = await res.json();

    if (data.success) {
      loadAppointments();
    } else {
      alert(data.message || "Could not clear appointments.");
    }
  } catch (err) {
    alert("Could not reach the server.");
  } finally {
    clearAllBtn.disabled = false;
  }
});

// Load the list once on first page load in the background so the tab
// feels instant when clicked.
loadAppointments();
