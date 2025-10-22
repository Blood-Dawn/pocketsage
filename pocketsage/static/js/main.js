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
