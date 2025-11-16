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
    initTopNav();
    initAdminDashboard();
    initPortfolioUpload();
    applyAllocationFallback();
});

function applyAllocationFallback() {
    const supportsCustomProperties =
        typeof window.CSS !== "undefined" &&
        typeof window.CSS.supports === "function" &&
        window.CSS.supports("(--allocation: 0)");

    if (supportsCustomProperties) {
        return;
    }

    document
        .querySelectorAll(".allocation-bar-fill[data-allocation]")
        .forEach((bar) => {
            const value = Number.parseFloat(bar.dataset.allocation);
            if (!Number.isFinite(value)) {
                return;
            }
            const clamped = Math.max(0, Math.min(value, 100));
            bar.style.width = `${clamped}%`;
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
    const previewSection = uploadForm.querySelector("[data-upload-preview]");
    const mappingContainer = uploadForm.querySelector("[data-mapping-table]");
    const sampleContainer = uploadForm.querySelector("[data-sample-table]");
    const previewSummary = uploadForm.querySelector("[data-preview-summary]");
    const confirmButton = uploadForm.querySelector("[data-confirm-import]");
    const submitButton = uploadForm.querySelector("button[type='submit']");
    const mappingInput = uploadForm.querySelector("[data-mapping-input]");

    let currentMapping = {};
    let availableColumns = [];
    let previewSamples = [];
    let previewAvailable = false;
    let previewStale = false;

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

    const updatePreviewSummary = (message) => {
        if (!previewSummary) {
            return;
        }
        previewSummary.textContent = message;
    };

    const syncMappingInput = () => {
        if (mappingInput) {
            if (Object.keys(currentMapping).length > 0) {
                mappingInput.value = JSON.stringify(currentMapping);
            } else {
                mappingInput.value = "";
            }
        }
    };

    const resetPreview = () => {
        previewAvailable = false;
        previewStale = false;
        currentMapping = {};
        availableColumns = [];
        previewSamples = [];
        if (previewSection) {
            previewSection.hidden = true;
        }
        if (mappingContainer) {
            mappingContainer.innerHTML = "<p class=\"empty\">Run a preview to detect column mappings.</p>";
        }
        if (sampleContainer) {
            sampleContainer.innerHTML = "<p class=\"empty\">Sample rows will appear after generating a preview.</p>";
        }
        if (confirmButton) {
            confirmButton.hidden = true;
            confirmButton.disabled = true;
        }
        updatePreviewSummary("Review detected mappings before importing.");
        syncMappingInput();
        updateConfirmState();
    };

    const updateConfirmState = () => {
        if (!confirmButton) {
            return;
        }
        confirmButton.hidden = !previewAvailable;
        confirmButton.disabled = !previewAvailable || previewStale;
        if (previewAvailable && previewStale) {
            confirmButton.title = "Refresh the preview before importing.";
        } else {
            confirmButton.removeAttribute("title");
        }
    };

    const renderMappingControls = () => {
        if (!mappingContainer) {
            return;
        }

        const canonicalFields = Object.keys(currentMapping);
        if (canonicalFields.length === 0) {
            mappingContainer.innerHTML = "<p class=\"empty\">No recognizable columns were detected.</p>";
            return;
        }

        const table = document.createElement("table");
        table.className = "preview-table";

        const thead = document.createElement("thead");
        thead.innerHTML = "<tr><th>Field</th><th>CSV column</th></tr>";
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        canonicalFields
            .sort()
            .forEach((field) => {
                const row = document.createElement("tr");
                const labelCell = document.createElement("th");
                labelCell.scope = "row";
                labelCell.textContent = field.replace(/_/g, " ");

                const selectCell = document.createElement("td");
                const select = document.createElement("select");
                select.name = `mapping-${field}`;

                const emptyOption = document.createElement("option");
                emptyOption.value = "";
                emptyOption.textContent = "Ignore";
                select.appendChild(emptyOption);

                availableColumns.forEach((column) => {
                    const option = document.createElement("option");
                    option.value = column;
                    option.textContent = column;
                    select.appendChild(option);
                });

                select.value = currentMapping[field] || "";
                select.addEventListener("change", () => {
                    currentMapping[field] = select.value || null;
                    previewStale = true;
                    syncMappingInput();
                    updateConfirmState();
                    updatePreviewSummary("Mapping updated. Preview again to refresh sample data.");
                    setProgress("Mapping updated. Preview again to refresh sample data.", "info");
                    if (sampleContainer) {
                        sampleContainer.innerHTML =
                            "<p class=\"empty\">Preview is out of date. Generate a new preview to refresh sample rows.</p>";
                    }
                });

                selectCell.appendChild(select);
                row.appendChild(labelCell);
                row.appendChild(selectCell);
                tbody.appendChild(row);
            });

        table.appendChild(tbody);
        mappingContainer.innerHTML = "";
        mappingContainer.appendChild(table);
    };

    const renderSampleTable = () => {
        if (!sampleContainer) {
            return;
        }

        const activeFields = Object.entries(currentMapping)
            .filter(([, column]) => column)
            .map(([field]) => field)
            .sort();

        if (previewSamples.length === 0 || activeFields.length === 0) {
            sampleContainer.innerHTML = "<p class=\"empty\">No sample rows available yet.</p>";
            return;
        }

        const table = document.createElement("table");
        table.className = "preview-table";

        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        activeFields.forEach((field) => {
            const cell = document.createElement("th");
            cell.textContent = field.replace(/_/g, " ");
            headerRow.appendChild(cell);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        previewSamples.forEach((sample) => {
            const row = document.createElement("tr");
            activeFields.forEach((field) => {
                const cell = document.createElement("td");
                cell.textContent = sample[field] || "";
                row.appendChild(cell);
            });
            tbody.appendChild(row);
        });
        table.appendChild(tbody);

        sampleContainer.innerHTML = "";
        sampleContainer.appendChild(table);
    };

    const buildFormData = (includePreviewFlag) => {
        const formData = new FormData(uploadForm);
        if (Object.keys(currentMapping).length > 0) {
            formData.set("mapping", JSON.stringify(currentMapping));
        } else {
            formData.delete("mapping");
        }
        syncMappingInput();
        if (includePreviewFlag) {
            formData.set("preview", "1");
        } else {
            formData.delete("preview");
        }
        return formData;
    };

    const requestPreview = async () => {
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            showFlash("Please choose a CSV file first.", "warning");
            setProgress("Select a CSV file before uploading.", "warning");
            return;
        }

        if (submitButton) {
            submitButton.disabled = true;
        }
        setProgress("Analyzing CSV…", "progress");
        previewStale = false;
        updateConfirmState();

        try {
            const formData = buildFormData(true);
            const response = await fetch(uploadForm.action, {
                method: "POST",
                body: formData,
                headers: { Accept: "application/json" },
            });

            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.error) {
                const message = payload.message || "Unable to generate preview.";
                setProgress(message, "warning");
                showFlash(message, "warning");
                resetPreview();
                return;
            }

            previewAvailable = true;
            previewStale = false;
            currentMapping = payload.mapping || {};
            availableColumns = payload.source_columns || [];
            previewSamples = payload.samples || [];
            syncMappingInput();

            renderMappingControls();
            renderSampleTable();

            if (previewSection) {
                previewSection.hidden = false;
            }

            const totalRows = payload.total_rows || 0;
            const summary = totalRows
                ? `Preview generated for ${totalRows} row${totalRows === 1 ? "" : "s"}.`
                : "Preview generated.";
            updatePreviewSummary(summary);
            setProgress(payload.message || summary, "ready");
        } catch (error) {
            console.error("Preview request failed", error);
            setProgress("Preview failed. Please try again.", "warning");
            showFlash("Preview failed. Please try again.", "warning");
            resetPreview();
        } finally {
            updateConfirmState();
            if (submitButton) {
                submitButton.disabled = false;
            }
        }
    };

    const finalizeImport = async () => {
        if (previewStale) {
            setProgress("Preview is out of date. Generate a new preview before importing.", "warning");
            showFlash("Preview is out of date. Run the preview again first.", "warning");
            return;
        }
        if (!previewAvailable) {
            setProgress("Generate a preview before importing.", "warning");
            showFlash("Generate a preview before importing.", "warning");
            return;
        }

        let skipUnlock = false;
        if (confirmButton) {
            confirmButton.disabled = true;
        }
        setProgress("Importing holdings…", "progress");

        try {
            const formData = buildFormData(false);
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
                confirmButton && (confirmButton.disabled = false);
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
            if (confirmButton) {
                confirmButton.disabled = false;
            }
            uploadForm.submit();
        } finally {
            if (confirmButton && !skipUnlock) {
                confirmButton.disabled = false;
            }
        }
    };

    resetProgress();
    resetPreview();

    if (fileInput) {
        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files.length > 0) {
                const [{ name }] = fileInput.files;
                if (fileLabel) {
                    fileLabel.textContent = name;
                }
                setProgress(`Ready to upload ${name}`, "ready");
                resetPreview();
            } else {
                if (fileLabel) {
                    fileLabel.textContent = "Choose a CSV file";
                }
                resetProgress();
                resetPreview();
            }
        });
    }

    uploadForm.addEventListener("submit", (event) => {
        event.preventDefault();
        requestPreview();
    });

    if (confirmButton) {
        confirmButton.addEventListener("click", finalizeImport);
    }
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
