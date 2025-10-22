// PocketSage frontend bootstrapping

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed"]);

document.addEventListener("DOMContentLoaded", () => {
    initAdminDashboard();
    initPortfolioUpload();
    initLiabilityDashboard();
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

function initLiabilityDashboard() {
    const root = document.querySelector("[data-liability-dashboard]");
    if (!root) {
        return;
    }

    const jobEndpointTemplate = root.dataset.jobStatusEndpoint || "";
    const initialJobs = safeParseJSON(root.dataset.initialJobs) || [];
    const cards = new Map();
    const jobs = new Map();
    const flashTimers = new Map();

    root.querySelectorAll("[data-liability-card]").forEach((card) => {
        const liabilityId = Number(card.dataset.liabilityId);
        if (!Number.isFinite(liabilityId)) {
            return;
        }

        const form = card.querySelector("form[data-job-submit]");
        const button = form ? form.querySelector("button[type='submit']") : null;
        const status = card.querySelector("[data-status-region]");
        const flash = card.querySelector("[data-inline-flash]");
        const defaultStatus = status ? status.textContent.trim() : "";
        const defaultState = status ? status.dataset.state || "idle" : "idle";

        cards.set(liabilityId, {
            card,
            form,
            button,
            status,
            flash,
            defaultStatus,
            defaultState,
            name: card.dataset.liabilityName || "This liability",
        });

        if (form) {
            form.addEventListener("submit", (event) =>
                handleRecalcSubmit(event, liabilityId)
            );
        }
    });

    const clearStatus = (liabilityId) => {
        const entry = cards.get(liabilityId);
        if (!entry || !entry.status) {
            return;
        }
        if (entry.defaultStatus) {
            entry.status.hidden = false;
            entry.status.dataset.state = entry.defaultState;
            entry.status.textContent = entry.defaultStatus;
        } else {
            entry.status.hidden = true;
            entry.status.textContent = "";
        }
    };

    const setStatus = (liabilityId, message, state = "info") => {
        const entry = cards.get(liabilityId);
        if (!entry || !entry.status) {
            return;
        }
        if (!message) {
            clearStatus(liabilityId);
            return;
        }
        entry.status.hidden = false;
        entry.status.dataset.state = state;
        entry.status.textContent = message;
    };

    const clearInlineFlash = (liabilityId) => {
        const entry = cards.get(liabilityId);
        if (!entry || !entry.flash) {
            return;
        }
        entry.flash.hidden = true;
        entry.flash.textContent = "";
        entry.flash.className = "liability-inline-flash";
        const timer = flashTimers.get(liabilityId);
        if (timer) {
            clearTimeout(timer);
            flashTimers.delete(liabilityId);
        }
    };

    const showInlineFlash = (liabilityId, message, category = "info") => {
        const entry = cards.get(liabilityId);
        if (!entry || !entry.flash) {
            return;
        }
        entry.flash.hidden = false;
        entry.flash.textContent = message;
        entry.flash.className = `liability-inline-flash liability-inline-flash-${category}`;

        const timer = flashTimers.get(liabilityId);
        if (timer) {
            clearTimeout(timer);
        }
        const timeout = window.setTimeout(() => {
            clearInlineFlash(liabilityId);
        }, 6000);
        flashTimers.set(liabilityId, timeout);
    };

    const trackJob = (job) => {
        if (!job || !job.id) {
            return;
        }
        jobs.set(job.id, job);
        const metadata = job.metadata || {};
        const liabilityId = Number(metadata.liability_id);
        if (!Number.isFinite(liabilityId) || !cards.has(liabilityId)) {
            return;
        }

        const entry = cards.get(liabilityId);
        if (entry && entry.button) {
            entry.button.disabled = !FINAL_JOB_STATUSES.has(job.status);
        }

        if (entry && FINAL_JOB_STATUSES.has(job.status)) {
            const finished = job.finished_at
                ? formatDate(job.finished_at)
                : "just now";
            if (job.status === "succeeded") {
                setStatus(
                    liabilityId,
                    `Last recalculated ${finished}`,
                    "success"
                );
                showInlineFlash(
                    liabilityId,
                    `${entry.name} payoff schedule refreshed successfully.`,
                    "success"
                );
            } else {
                const message = job.error || "Recalculation failed.";
                setStatus(liabilityId, message, "warning");
                showInlineFlash(liabilityId, message, "warning");
            }
        } else {
            setStatus(liabilityId, "Recalculation running…", "pending");
        }
    };

    const pollJob = async (jobId) => {
        if (!jobId || !jobEndpointTemplate) {
            return;
        }
        try {
            const response = await fetch(
                jobEndpointTemplate.replace("__JOB__", jobId),
                {
                    headers: { Accept: "application/json" },
                }
            );
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            trackJob(payload);
        } catch (error) {
            console.warn("Failed to poll liability job", jobId, error);
        }
    };

    const pollActiveJobs = () => {
        Array.from(jobs.values())
            .filter((job) => !FINAL_JOB_STATUSES.has(job.status))
            .forEach((job) => pollJob(job.id));
    };

    const handleRecalcSubmit = async (event, liabilityId) => {
        event.preventDefault();
        const entry = cards.get(liabilityId);
        if (!entry || !entry.form) {
            return;
        }

        const { form, button } = entry;
        const payload = safeParseJSON(form.dataset.payload) || {};

        if (button) {
            button.disabled = true;
        }
        clearInlineFlash(liabilityId);
        setStatus(liabilityId, "Scheduling recalculation…", "pending");

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify(payload),
            });

            const result = await response.json().catch(() => null);
            if (!response.ok || !result || result.error) {
                const message =
                    (result && (result.message || result.error)) ||
                    "Unable to schedule recalculation.";
                showInlineFlash(liabilityId, message, "warning");
                setStatus(liabilityId, message, "warning");
                if (button) {
                    button.disabled = false;
                }
                return;
            }

            showInlineFlash(liabilityId, "Recalculation started…", "info");
            trackJob(result);
            pollJob(result.id);
        } catch (error) {
            console.error("Recalculation submission failed", error);
            if (button) {
                button.disabled = false;
            }
            form.submit();
        }
    };

    initialJobs.forEach((job) => {
        trackJob(job);
    });

    pollActiveJobs();
    setInterval(pollActiveJobs, 5000);
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
