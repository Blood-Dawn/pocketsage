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
    initLedger();
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

function initLedger() {
    const ledgerRoot = document.querySelector("[data-ledger-root]");
    if (!ledgerRoot) {
        return;
    }

    const tableBody = ledgerRoot.querySelector("[data-ledger-rows]");
    const pagination = ledgerRoot.querySelector("[data-ledger-pagination]");
    const sentinel = ledgerRoot.querySelector("[data-ledger-sentinel]");

    if (!tableBody || !pagination) {
        return;
    }

    if (sentinel) {
        sentinel.hidden = false;
    }

    let nextUrl = null;
    const nextAnchor = pagination.querySelector("[data-pagination-next]");
    if (nextAnchor && nextAnchor.getAttribute("href")) {
        nextUrl = nextAnchor.getAttribute("href");
    }

    if (!sentinel || !nextUrl) {
        return;
    }

    const status = sentinel.querySelector("[data-ledger-status]");
    const loadMoreButton = sentinel.querySelector("[data-ledger-load-more]");

    const updateStatus = (message, state = "idle") => {
        if (!status) {
            return;
        }
        status.textContent = message;
        status.dataset.state = state;
    };

    const refreshPagination = (doc) => {
        const newPagination = doc.querySelector("[data-ledger-pagination]");
        if (newPagination) {
            pagination.innerHTML = newPagination.innerHTML;
        }
        const updatedNext = pagination.querySelector("[data-pagination-next]");
        if (updatedNext && updatedNext.getAttribute("href")) {
            nextUrl = updatedNext.getAttribute("href");
        } else {
            nextUrl = null;
        }
    };

    let observer = null;
    let loading = false;

    const teardown = () => {
        if (observer) {
            observer.disconnect();
            observer = null;
        }
        if (sentinel) {
            sentinel.dataset.inactive = "true";
        }
    };

    const fetchNextPage = async () => {
        if (loading || !nextUrl) {
            return;
        }
        loading = true;
        ledgerRoot.dataset.loading = "true";
        updateStatus("Loading more transactions…", "loading");
        if (loadMoreButton) {
            loadMoreButton.disabled = true;
        }

        try {
            const response = await fetch(nextUrl, { headers: { Accept: "text/html" } });
            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const newRows = doc.querySelectorAll("[data-ledger-rows] tr");
            if (newRows.length === 0) {
                nextUrl = null;
                updateStatus("No additional transactions found.", "done");
                teardown();
                return;
            }
            newRows.forEach((row) => tableBody.appendChild(row));

            const newSummary = doc.querySelector("[data-ledger-summary]");
            const currentSummary = ledgerRoot.querySelector("[data-ledger-summary]");
            if (newSummary && currentSummary) {
                currentSummary.innerHTML = newSummary.innerHTML;
            }

            refreshPagination(doc);

            if (nextUrl) {
                updateStatus("Scroll to load more transactions.");
            } else {
                updateStatus("You’re all caught up.", "done");
                teardown();
            }
        } catch (error) {
            console.warn("Ledger infinite scroll failed", error);
            updateStatus("Automatic loading paused. Use pagination links above.", "error");
            teardown();
        } finally {
            ledgerRoot.dataset.loading = "false";
            if (loadMoreButton) {
                loadMoreButton.disabled = false;
            }
            loading = false;
        }
    };

    if (loadMoreButton) {
        loadMoreButton.addEventListener("click", fetchNextPage);
    }

    observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    fetchNextPage();
                }
            });
        },
        { rootMargin: "0px 0px 200px 0px" }
    );

    observer.observe(sentinel);

    ledgerRoot.dataset.enhanced = "true";
    updateStatus("Scroll to load more transactions.");
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

function getFlashIconMarkup(category) {
    const normalized = typeof category === "string" ? category.toLowerCase() : "";
    return FLASH_ICONS[normalized] || FLASH_ICONS.info;
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
