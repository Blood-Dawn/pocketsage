// PocketSage frontend bootstrapping

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed"]);

document.addEventListener("DOMContentLoaded", () => {
    initAdminDashboard();
    initPortfolioUpload();
    initLiabilitiesSchedule();
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

function initLiabilitiesSchedule() {
    const dashboard = document.querySelector("[data-liabilities-dashboard]");
    if (!dashboard) {
        return;
    }

    const list = dashboard.querySelector("[data-liability-list]");
    const cards = list ? Array.from(list.querySelectorAll("[data-liability]")) : [];
    const searchInput = dashboard.querySelector("[data-liability-search]");
    const strategySelect = dashboard.querySelector("[data-liability-strategy]");
    const sortSelect = dashboard.querySelector("[data-liability-sort]");
    const emptyState = dashboard.querySelector("[data-liability-empty]");
    const countTarget = dashboard.querySelector("[data-liability-count]");
    const upcomingRange = dashboard.querySelector("[data-upcoming-range]");
    const upcomingRows = Array.from(
        dashboard.querySelectorAll("[data-upcoming-row]")
    );
    const upcomingEmptyRow = dashboard.querySelector("[data-upcoming-empty]");

    let filterTerm = "";
    let filterStrategy = "all";

    const normalize = (value) => (value || "").toString().trim().toLowerCase();

    const parseDate = (value) => {
        if (!value) {
            return Number.MAX_SAFE_INTEGER;
        }
        const timestamp = Date.parse(value);
        if (Number.isNaN(timestamp)) {
            return Number.MAX_SAFE_INTEGER;
        }
        return timestamp;
    };

    const comparators = {
        next_due: (a, b) =>
            parseDate(a.dataset.liabilityNextDue) -
            parseDate(b.dataset.liabilityNextDue),
        balance: (a, b) =>
            parseFloat(b.dataset.liabilityBalance || "0") -
            parseFloat(a.dataset.liabilityBalance || "0"),
        name: (a, b) =>
            normalize(a.dataset.liabilityName).localeCompare(
                normalize(b.dataset.liabilityName)
            ),
    };

    const applyUpcomingFilters = () => {
        const rangeValue = parseInt(upcomingRange?.value ?? "", 10);
        let visibleRows = 0;

        upcomingRows.forEach((row) => {
            const rowName = normalize(row.dataset.liabilityName);
            const rowStrategy = normalize(row.dataset.liabilityStrategy);
            const matchesTerm = !filterTerm || rowName.includes(filterTerm);
            const matchesStrategy =
                filterStrategy === "all" ||
                rowStrategy === normalize(filterStrategy);
            const days = parseInt(row.dataset.upcomingDays ?? "", 10);
            const matchesRange =
                Number.isNaN(rangeValue) ||
                rangeValue < 0 ||
                Number.isNaN(days)
                    ? true
                    : days <= rangeValue;

            const shouldShow = matchesTerm && matchesStrategy && matchesRange;
            row.hidden = !shouldShow;
            if (shouldShow) {
                visibleRows += 1;
            }
        });

        if (upcomingEmptyRow) {
            upcomingEmptyRow.hidden = visibleRows !== 0;
        }
    };

    const applyLiabilityFilters = () => {
        if (list) {
            const sortKey = sortSelect?.value || "next_due";
            const comparator = comparators[sortKey] || comparators.next_due;
            const sortedCards = [...cards].sort(comparator);

            sortedCards.forEach((card) => list.appendChild(card));

            let visibleCards = 0;
            cards.forEach((card) => {
                const name = normalize(card.dataset.liabilityName);
                const strategy = normalize(card.dataset.liabilityStrategy);
                const matchesTerm = !filterTerm || name.includes(filterTerm);
                const matchesStrategy =
                    filterStrategy === "all" ||
                    strategy === normalize(filterStrategy);
                const shouldShow = matchesTerm && matchesStrategy;
                card.hidden = !shouldShow;
                if (shouldShow) {
                    visibleCards += 1;
                }
            });

            if (countTarget) {
                countTarget.textContent = visibleCards.toString();
            }
            if (emptyState) {
                emptyState.hidden = visibleCards !== 0;
            }
        }

        applyUpcomingFilters();
    };

    if (searchInput) {
        searchInput.addEventListener("input", (event) => {
            filterTerm = normalize(event.target.value);
            applyLiabilityFilters();
        });
    }

    if (strategySelect) {
        strategySelect.addEventListener("change", (event) => {
            filterStrategy = event.target.value || "all";
            applyLiabilityFilters();
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener("change", () => {
            applyLiabilityFilters();
        });
    }

    if (upcomingRange) {
        upcomingRange.addEventListener("change", () => {
            applyUpcomingFilters();
        });
    }

    applyLiabilityFilters();
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
