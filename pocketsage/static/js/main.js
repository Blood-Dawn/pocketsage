// PocketSage frontend bootstrapping

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed"]);
const ALERT_FLASH_CATEGORIES = new Set(["danger", "warning", "error"]);

const FLASH_ICONS = Object.freeze({
    success: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.707a1 1 0 00-1.414-1.414L9 10.172 7.707 8.879a1 1 0 10-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>`,
    danger: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-9-3a1 1 0 112 0v4a1 1 0 11-2 0V7zm1 8a1.25 1.25 0 100-2.5A1.25 1.25 0 0010 15z" clip-rule="evenodd"></path></svg>`,
    error: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-9-3a1 1 0 112 0v4a1 1 0 11-2 0V7zm1 8a1.25 1.25 0 100-2.5A1.25 1.25 0 0010 15z" clip-rule="evenodd"></path></svg>`,
    warning: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l6.518 11.59c.75 1.333-.214 2.99-1.742 2.99H3.48c-1.528 0-2.492-1.657-1.742-2.99l6.52-11.59zM11 14a1 1 0 10-2 0 1 1 0 002 0zm-1-2a1 1 0 01-1-1V8a1 1 0 112 0v3a1 1 0 01-1 1z"></path></svg>`,
    info: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM9 9a1 1 0 112 0v5a1 1 0 11-2 0V9zm1-4a1 1 0 100 2 1 1 0 000-2z" clip-rule="evenodd"></path></svg>`,
});

const FLASH_DISMISS_ICON =
    '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>';

document.addEventListener("DOMContentLoaded", () => {
    initFlashDismissal();
    initAdminDashboard();
    initPortfolioUpload();
    initPortfolioSorting();
});

function initFlashDismissal() {
    const container = document.querySelector(".flash-messages");
    if (!container) {
        return;
    }

    container.addEventListener("click", (event) => {
        const dismissButton = event.target.closest("[data-flash-dismiss]");
        if (!dismissButton || !container.contains(dismissButton)) {
            return;
        }
        event.preventDefault();
        const flash = dismissButton.closest(".flash");
        if (flash) {
            flash.remove();
        }
    });
}

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

function initPortfolioSorting() {
    const table = document.querySelector(".holdings-table");
    if (!table) {
        return;
    }

    const tbody = table.querySelector("tbody");
    const headerRow = table.querySelector("thead tr");
    if (!tbody || !headerRow) {
        return;
    }

    const sortLinks = table.querySelectorAll(".sort-link");
    if (!sortLinks.length) {
        return;
    }

    const sortInput = document.querySelector(".portfolio-controls input[name='sort']");
    const directionInput = document.querySelector(".portfolio-controls input[name='direction']");

    const parseValue = (cell, type) => {
        if (!cell) {
            return "";
        }
        const rawValue = cell.dataset.sortValue ?? cell.textContent ?? "";
        if (type === "numeric") {
            const numeric = Number(rawValue);
            return Number.isNaN(numeric) ? 0 : numeric;
        }
        return String(rawValue).toLowerCase();
    };

    const updateHeaderState = (activeHeader, direction) => {
        headerRow.querySelectorAll("th").forEach((th) => {
            th.setAttribute(
                "aria-sort",
                th === activeHeader
                    ? direction === "asc"
                        ? "ascending"
                        : "descending"
                    : "none"
            );
        });
    };

    sortLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            const headerCell = link.closest("th");
            if (!headerCell) {
                window.location.href = link.href;
                return;
            }

            const columnIndex = Array.from(headerRow.children).indexOf(headerCell);
            if (columnIndex < 0) {
                window.location.href = link.href;
                return;
            }

            const sortType = link.dataset.sortType || "text";
            const nextDirection = link.dataset.nextDirection || "asc";
            const rows = Array.from(tbody.querySelectorAll("tr"));
            rows
                .sort((rowA, rowB) => {
                    const cellA = rowA.children.item(columnIndex);
                    const cellB = rowB.children.item(columnIndex);
                    const valueA = parseValue(cellA, sortType);
                    const valueB = parseValue(cellB, sortType);
                    if (valueA === valueB) {
                        return 0;
                    }
                    if (sortType === "numeric") {
                        return nextDirection === "asc" ? valueA - valueB : valueB - valueA;
                    }
                    return nextDirection === "asc"
                        ? String(valueA).localeCompare(String(valueB))
                        : String(valueB).localeCompare(String(valueA));
                })
                .forEach((row) => tbody.appendChild(row));

            sortLinks.forEach((candidate) => {
                if (candidate === link) {
                    candidate.dataset.activeDirection = nextDirection;
                    candidate.dataset.nextDirection = nextDirection === "asc" ? "desc" : "asc";
                    candidate.classList.add("is-active");
                } else {
                    candidate.dataset.activeDirection = "none";
                    candidate.dataset.nextDirection = "desc";
                    candidate.classList.remove("is-active");
                }
            });

            updateHeaderState(headerCell, nextDirection);

            if (sortInput && link.dataset.sort) {
                sortInput.value = link.dataset.sort;
            }
            if (directionInput) {
                directionInput.value = nextDirection;
            }

            const url = new URL(window.location.href);
            if (link.dataset.sort) {
                url.searchParams.set("sort", link.dataset.sort);
            }
            url.searchParams.set("direction", nextDirection);
            window.history.replaceState(null, "", url);
        });
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

function titleCase(value) {
    if (!value) {
        return "";
    }
    return value
        .toString()
        .split(/[_\s-]+/)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function formatCurrency(value) {
    const number = Number(value) || 0;
    return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
        minimumFractionDigits: 0,
    }).format(number);
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
    const normalizedCategory = (typeof category === "string" && category.trim())
        ? category.trim().toLowerCase()
        : "info";
    const element = document.createElement("div");
    element.className = `flash flash-${normalizedCategory}`;
    element.setAttribute("role", ALERT_FLASH_CATEGORIES.has(normalizedCategory) ? "alert" : "status");

    const icon = document.createElement("span");
    icon.className = "flash-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = getFlashIconMarkup(normalizedCategory);

    const content = document.createElement("div");
    content.className = "flash-message";
    content.textContent = message;

    const dismissButton = document.createElement("button");
    dismissButton.type = "button";
    dismissButton.className = "flash-dismiss";
    dismissButton.setAttribute("aria-label", "Dismiss notification");
    dismissButton.setAttribute("data-flash-dismiss", "");
    dismissButton.innerHTML = FLASH_DISMISS_ICON;
    dismissButton.addEventListener("click", () => {
        element.remove();
    });

    element.append(icon, content, dismissButton);
    container.appendChild(element);
    setTimeout(() => {
        element.remove();
    }, 5000);
}
