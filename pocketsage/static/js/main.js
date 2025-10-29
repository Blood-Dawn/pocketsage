// PocketSage frontend bootstrapping

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed"]);

document.addEventListener("DOMContentLoaded", () => {
    initAdminDashboard();
    initPortfolioUpload();
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
    const announcer = adminRoot.querySelector("[data-job-announcer]");
    let hasRenderedOnce = false;

    const renderJobs = () => {
        if (!jobList) {
            return;
        }
        if (jobs.size === 0) {
            jobList.innerHTML = `<li class="job-item job-item--empty"><span class="empty">No background jobs yet.</span></li>`;
            jobList.dataset.state = "idle";
            jobList.removeAttribute("aria-busy");
            hasRenderedOnce = true;
            return;
        }

        const items = Array.from(jobs.values())
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map((job) => jobItemTemplate(job))
            .join("");
        jobList.innerHTML = items;

        const hasPendingJobs = Array.from(jobs.values()).some(
            (job) => !FINAL_JOB_STATUSES.has(job.status)
        );
        if (hasPendingJobs) {
            jobList.dataset.state = "loading";
            jobList.setAttribute("aria-busy", "true");
        } else {
            jobList.dataset.state = "idle";
            jobList.removeAttribute("aria-busy");
        }

        hasRenderedOnce = true;
    };

    const trackJob = (job) => {
        if (!job || !job.id) {
            return;
        }
        const previous = jobs.get(job.id);
        jobs.set(job.id, job);
        renderJobs();

        if (
            announcer &&
            hasRenderedOnce &&
            (!previous || previous.status !== job.status)
        ) {
            announceJobStatus(announcer, job);
        }
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
    const status = job.status || "queued";
    const statusLabel = formatStatusLabel(status);
    const isPending = !FINAL_JOB_STATUSES.has(status);
    const createdMarkup = formatJobTime(job.created_at);
    const startedMarkup = formatJobTime(job.started_at);
    const finishedMarkup = formatJobTime(job.finished_at);
    const errorMarkup = job.error
        ? `<div class="job-error" role="status">${formatJobError(job.error)}</div>`
        : "";

    return `
        <li class="job-item" data-job-id="${escapeHTML(job.id)}" data-job-status="${escapeHTML(status)}">
            <header class="job-item__header">
                <span class="job-item__name">${escapeHTML(job.name || "Untitled job")}</span>
                <span
                    class="job-status-badge job-status-badge--${escapeHTML(status)}${isPending ? " is-loading" : ""}"
                    data-status="${escapeHTML(status)}"
                    aria-label="Job status: ${escapeHTML(statusLabel)}"
                >
                    ${isPending ? '<span class="job-status-badge__spinner" aria-hidden="true"></span>' : ""}
                    <span class="job-status-badge__label">${escapeHTML(statusLabel)}</span>
                </span>
            </header>
            <dl class="job-timestamps">
                <div>
                    <dt>Created</dt>
                    <dd>${createdMarkup}</dd>
                </div>
                <div>
                    <dt>Started</dt>
                    <dd>${startedMarkup}</dd>
                </div>
                <div>
                    <dt>Finished</dt>
                    <dd>${finishedMarkup}</dd>
                </div>
            </dl>
            ${errorMarkup}
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

function formatStatusLabel(status) {
    const statusLabels = {
        queued: "Queued",
        running: "Running",
        succeeded: "Succeeded",
        failed: "Failed",
    };
    return statusLabels[status] || status;
}

function formatJobTime(value) {
    if (!value) {
        return '<span class="empty">—</span>';
    }
    const formatted = formatDate(value);
    if (!formatted || formatted === "—") {
        return '<span class="empty">—</span>';
    }
    return `<time datetime="${escapeHTML(value)}">${escapeHTML(formatted)}</time>`;
}

function formatJobError(message) {
    return escapeHTML(String(message)).replace(/\n/g, "<br>");
}

function escapeHTML(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function announceJobStatus(announcer, job) {
    if (!announcer) {
        return;
    }
    const statusMessages = {
        queued: "queued",
        running: "in progress",
        succeeded: "complete",
        failed: "failed",
    };
    const status = job.status || "queued";
    const suffix = statusMessages[status] || status;
    const name = job.name ? job.name.trim() : job.id;
    const message = status === "succeeded"
        ? `Job ${name} completed successfully.`
        : status === "failed"
        ? `Job ${name} failed. Check the details below.`
        : `Job ${name} is ${suffix}.`;
    announcer.textContent = message;
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
