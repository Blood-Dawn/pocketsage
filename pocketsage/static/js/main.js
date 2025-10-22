// PocketSage frontend bootstrapping

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed"]);

document.addEventListener("DOMContentLoaded", () => {
    initAdminDashboard();
    initPortfolioUpload();
    initHabitVisualizations();
});

function initAdminDashboard() {
    const adminRoot = document.querySelector("[data-admin-dashboard]");
    if (!adminRoot) {
        return;
    }

    const jobEndpointTemplate = adminRoot.dataset.jobStatusEndpoint || "";
    const jobList = adminRoot.querySelector("[data-job-list]");
    const initialJobs = safeParseJSON(adminRoot.dataset.initialJobs) || [];
    const jobs = new Map(initialJobs.map((job) => [job.id, job]));

    const renderJobs = () => {
        if (!jobList) {
            return;
        }
        if (jobs.size === 0) {
            jobList.innerHTML = `<li class="job-item"><span class="empty">No background jobs yet.</span></li>`;
            return;
        }

        const items = Array.from(jobs.values())
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map((job) => jobItemTemplate(job))
            .join("");
        jobList.innerHTML = items;
    };

    const trackJob = (job) => {
        if (!job || !job.id) {
            return;
        }
        jobs.set(job.id, job);
        renderJobs();
    };

    const pollJob = async (jobId) => {
        if (!jobId || !jobEndpointTemplate) {
            return;
        }
        try {
            const response = await fetch(jobEndpointTemplate.replace("__JOB__", jobId), {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            trackJob(payload);
        } catch (error) {
            console.warn("Failed to poll job", jobId, error);
        }
    };

    const pollActiveJobs = () => {
        Array.from(jobs.values())
            .filter((job) => !FINAL_JOB_STATUSES.has(job.status))
            .forEach((job) => pollJob(job.id));
    };

    const handleJobSubmit = async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const submitButton = form.querySelector("button[type='submit']");
        if (submitButton) {
            submitButton.disabled = true;
        }

        try {
            const payload = safeParseJSON(form.dataset.payload) || {};
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                showFlash(
                    error.error === "confirmation_required"
                        ? "Please confirm before running this job."
                        : "Unable to schedule job.",
                    "warning"
                );
                return;
            }

            const job = await response.json();
            trackJob(job);
            showFlash("Job scheduled", "info");
            pollJob(job.id);
        } catch (error) {
            console.error("Job submission failed", error);
            form.submit();
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
            }
        }
    };

    adminRoot
        .querySelectorAll("form[data-job-submit]")
        .forEach((form) => form.addEventListener("submit", handleJobSubmit));

    renderJobs();
    pollActiveJobs();
    setInterval(pollActiveJobs, 5000);
}

function initPortfolioUpload() {
    const uploadForm = document.querySelector("[data-portfolio-upload]");
    if (!uploadForm) {
        return;
    }

    const fileInput = uploadForm.querySelector("input[type='file']");
    const fileLabel = uploadForm.querySelector("[data-file-label]");
    const progress = uploadForm.querySelector("[data-upload-progress]");
    const redirectUrl = uploadForm.dataset.redirect;

    const resetProgress = () => {
        if (!progress) {
            return;
        }
        progress.hidden = true;
        progress.textContent = "";
        progress.dataset.state = "idle";
    };

    const setProgress = (message, state = "info") => {
        if (!progress) {
            return;
        }
        progress.hidden = false;
        progress.dataset.state = state;
        progress.textContent = message;
    };

    resetProgress();

    if (fileInput) {
        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files.length > 0) {
                const [{ name }] = fileInput.files;
                if (fileLabel) {
                    fileLabel.textContent = name;
                }
                setProgress(`Ready to upload ${name}`, "ready");
            } else {
                if (fileLabel) {
                    fileLabel.textContent = "Choose a CSV file";
                }
                resetProgress();
            }
        });
    }

    uploadForm.addEventListener("submit", async (event) => {
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            event.preventDefault();
            showFlash("Please choose a CSV file first.", "warning");
            setProgress("Select a CSV file before uploading.", "warning");
            return;
        }

        event.preventDefault();
        const submitButton = uploadForm.querySelector("button[type='submit']");
        let skipUnlock = false;
        if (submitButton) {
            submitButton.disabled = true;
        }

        setProgress("Uploading…", "progress");

        try {
            const formData = new FormData(uploadForm);
            const response = await fetch(uploadForm.action, {
                method: "POST",
                body: formData,
                headers: { Accept: "application/json" },
            });

            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.error) {
                const message = payload.message || "Upload failed. Please try again.";
                showFlash(message, "warning");
                setProgress(message, "warning");
                return;
            }

            const message = payload.message || "Portfolio imported.";
            showFlash(message, "success");
            setProgress("Upload complete.", "success");
            const nextLocation = payload.redirect || redirectUrl;
            skipUnlock = Boolean(nextLocation);
            if (nextLocation) {
                setTimeout(() => {
                    window.location.href = nextLocation;
                }, 600);
            }
        } catch (error) {
            console.error("Portfolio upload failed", error);
            if (submitButton) {
                submitButton.disabled = false;
            }
            uploadForm.submit();
        } finally {
            if (submitButton && !skipUnlock) {
                submitButton.disabled = false;
            }
        }
    });
}

function initHabitVisualizations() {
    const cards = document.querySelectorAll("[data-habit-visualization]");
    if (!cards.length) {
        return;
    }

    cards.forEach((card) => {
        const history = safeParseJSON(card.dataset.history) || [];
        if (!history.length) {
            return;
        }

        const weekly = safeParseJSON(card.dataset.weekly) || [];
        const habitName = card.dataset.habitName || "habit";
        const chart = card.querySelector(".habit-chart");

        if (!chart) {
            return;
        }

        chart.innerHTML = "";

        const heatmap = buildHabitHeatmap(history, habitName);
        if (heatmap) {
            chart.appendChild(heatmap);
        }

        const weeklyBars = buildHabitWeeklyBars(weekly, habitName);
        if (weeklyBars) {
            chart.appendChild(weeklyBars);
        }

        const fallback = card.querySelector("[data-fallback]");
        if (fallback) {
            fallback.classList.add("habit-fallback--hidden");
        }
    });
}

function safeParseJSON(value) {
    if (!value) {
        return null;
    }
    try {
        return JSON.parse(value);
    } catch (error) {
        console.warn("Failed to parse JSON", error);
        return null;
    }
}

function buildHabitHeatmap(history, habitName) {
    if (!Array.isArray(history) || history.length === 0) {
        return null;
    }

    const container = document.createElement("div");
    container.className = "habit-heatmap";
    container.setAttribute(
        "aria-label",
        `${history.length}-day completion history for ${habitName}`,
    );
    container.setAttribute("role", "img");

    history.forEach((day, index) => {
        const cell = document.createElement("span");
        cell.className = "habit-heatmap__day";
        const recency = history.length - index - 1;
        let level = 0;
        if (day && day.completed) {
            if (recency <= 6) {
                level = 3;
            } else if (recency <= 13) {
                level = 2;
            } else {
                level = 1;
            }
        }
        cell.dataset.level = String(level);
        const label = day && day.label ? day.label : day.date;
        const weekday = day && day.weekday ? day.weekday : "";
        const status = day && day.completed ? "Completed" : "Missed";
        cell.title = `${weekday ? `${weekday} · ` : ""}${label} — ${status}`;
        cell.setAttribute("aria-label", cell.title);
        container.appendChild(cell);
    });

    return container;
}

function buildHabitWeeklyBars(weekly, habitName) {
    if (!Array.isArray(weekly) || weekly.length === 0) {
        return null;
    }

    const container = document.createElement("div");
    container.className = "habit-weekly-bars";
    container.setAttribute(
        "aria-label",
        `Weekly completion totals for ${habitName}`,
    );
    container.setAttribute("role", "group");

    weekly.forEach((week) => {
        const row = document.createElement("div");
        row.className = "habit-weekly-bars__row";

        const label = document.createElement("div");
        label.className = "habit-weekly-bars__label";
        label.textContent = week && week.label ? week.label : week.start_date;

        const track = document.createElement("div");
        track.className = "habit-weekly-bars__track";
        track.setAttribute("aria-hidden", "true");

        const fill = document.createElement("span");
        fill.className = "habit-weekly-bars__fill";
        const totalDays = week && typeof week.total === "number" ? week.total : 0;
        const completed = week && typeof week.completed === "number" ? week.completed : 0;
        const ratio = totalDays > 0 ? Math.min(completed / totalDays, 1) : 0;
        fill.style.setProperty("--habit-weekly-progress", (ratio * 100).toFixed(2));
        track.appendChild(fill);

        const value = document.createElement("div");
        value.className = "habit-weekly-bars__value";
        value.textContent = `${completed}/${totalDays} days`;
        value.setAttribute(
            "aria-label",
            `${label.textContent}: completed ${completed} of ${totalDays} days`,
        );

        row.appendChild(label);
        row.appendChild(track);
        row.appendChild(value);
        container.appendChild(row);
    });

    return container;
}

function jobItemTemplate(job) {
    const created = formatDate(job.created_at);
    const started = job.started_at ? formatDate(job.started_at) : "—";
    const finished = job.finished_at ? formatDate(job.finished_at) : "—";
    const error = job.error ? `<div class="job-error">${job.error}</div>` : "";

    return `
		<li class="job-item">
			<header>
				<span class="job-name">${job.name}</span>
				<span class="job-status" data-status="${job.status}">${job.status}</span>
			</header>
			<div class="job-meta">
				<span>Created: ${created}</span>
				<span>Started: ${started}</span>
				<span>Finished: ${finished}</span>
			</div>
			${error}
		</li>
	`;
}

function formatDate(value) {
    if (!value) {
        return "—";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

function showFlash(message, category) {
    const container = document.querySelector(".flash-messages");
    if (!container) {
        return;
    }
    const element = document.createElement("div");
    element.className = `flash flash-${category}`;
    element.textContent = message;
    container.appendChild(element);
    setTimeout(() => {
        element.remove();
    }, 5000);
}
