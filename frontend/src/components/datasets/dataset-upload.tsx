"use client";

import { ArrowRightIcon } from "@phosphor-icons/react/ArrowRight";
import { CheckCircleIcon } from "@phosphor-icons/react/CheckCircle";
import { CloudArrowUpIcon } from "@phosphor-icons/react/CloudArrowUp";
import { FileCsvIcon } from "@phosphor-icons/react/FileCsv";
import { ShieldCheckIcon } from "@phosphor-icons/react/ShieldCheck";
import { SpinnerGapIcon } from "@phosphor-icons/react/SpinnerGap";
import { UploadSimpleIcon } from "@phosphor-icons/react/UploadSimple";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import { XIcon } from "@phosphor-icons/react/X";
import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
} from "react";

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import {
  getDataset,
  registerDataset,
  uploadDatasetContent,
} from "@/lib/datasets/api";
import { sha256File } from "@/lib/datasets/checksum";
import { datasetExplorePath } from "@/lib/datasets/routes";
import { datasetUploadSessionKey } from "@/lib/datasets/session";

const DATASET_MAX_UPLOAD_BYTES = 1_073_741_824;
const VALIDATION_POLL_INTERVAL_MS = 250;

type DatasetUploadProps = {
  workspaceId: string;
  projectId: string;
  initialDatasetId?: string;
};

type UploadState =
  | { status: "idle" }
  | { status: "hashing" }
  | { status: "registering" }
  | { status: "uploading" }
  | { status: "uploaded"; datasetId: string }
  | { status: "interrupted"; datasetId: string }
  | {
      status: "upload_error";
      datasetId: string;
      message: string;
    }
  | { status: "error"; message: string };

type ValidationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "pending" }
  | { status: "interrupted" }
  | { status: "validating" }
  | {
      status: "ready";
      rowCount: number | null;
      columnCount: number | null;
    }
  | { status: "failed"; message: string }
  | { status: "error"; message: string };

function isUploadActive(state: UploadState): boolean {
  return (
    state.status === "hashing"
    || state.status === "registering"
    || state.status === "uploading"
  );
}

export function DatasetUpload(
  props: DatasetUploadProps,
) {
  return (
    <DatasetUploadScope
      key={`${props.workspaceId}:${props.projectId}`}
      {...props}
    />
  );
}

function DatasetUploadScope({
  workspaceId,
  projectId,
  initialDatasetId,
}: DatasetUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>({
    status: "idle",
  });
  const [validationState, setValidationState] = useState<ValidationState>({
    status: "idle",
  });
  const validationPollTimer = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const validationFailureRef = useRef<HTMLDivElement>(null);
  const validationSuccessRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    const datasetId =
      initialDatasetId
      ?? window.sessionStorage.getItem(
        datasetUploadSessionKey(
          workspaceId,
          projectId,
        ),
      );

    if (datasetId) {
      const token = window.localStorage.getItem(SESSION_TOKEN_KEY);

      queueMicrotask(() => {
        if (cancelled) {
          return;
        }

        if (token) {
          setUploadState({
            status: "uploaded",
            datasetId,
          });

          void refreshValidationState(
            token,
            datasetId,
          );
          return;
        }

        setValidationState({
          status: "error",
          message:
            "Your session is no longer available. Please sign in again.",
        });
      });
    }

    return () => {
      cancelled = true;

      if (validationPollTimer.current !== null) {
        clearTimeout(validationPollTimer.current);
      }
    };

    // Scope changes remount DatasetUploadScope via its key.
    // refreshValidationState intentionally uses the mounted scope.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    initialDatasetId,
    projectId,
    workspaceId,
  ]);

  function scheduleValidationRefresh(
    token: string,
    datasetId: string,
  ) {
    if (validationPollTimer.current !== null) {
      clearTimeout(validationPollTimer.current);
    }

    validationPollTimer.current = setTimeout(() => {
      void refreshValidationState(token, datasetId);
    }, VALIDATION_POLL_INTERVAL_MS);
  }

  async function refreshValidationState(
    token: string,
    datasetId: string,
  ) {
    setValidationState({ status: "loading" });

    try {
      const dataset = await getDataset(
        token,
        workspaceId,
        projectId,
        datasetId,
      );

      if (dataset.status === "pending_upload") {
        setUploadState({
          status: "interrupted",
          datasetId,
        });
        setValidationState({
          status: "interrupted",
        });
        return;
      }

      if (dataset.status === "uploaded") {
        setValidationState({ status: "pending" });
        scheduleValidationRefresh(token, datasetId);
        return;
      }

      if (dataset.status === "validating") {
        setValidationState({ status: "validating" });
        scheduleValidationRefresh(token, datasetId);
        return;
      }

      if (validationPollTimer.current !== null) {
        clearTimeout(validationPollTimer.current);
        validationPollTimer.current = null;
      }

      if (dataset.status === "ready") {
        setValidationState({
          status: "ready",
          rowCount: dataset.row_count,
          columnCount: dataset.column_count,
        });
        return;
      }

      setValidationState({
        status: "failed",
        message:
          dataset.failure_reason
          ?? "The dataset did not pass validation.",
      });
    } catch {
      if (validationPollTimer.current !== null) {
        clearTimeout(validationPollTimer.current);
        validationPollTimer.current = null;
      }

      setValidationState({
        status: "error",
        message:
          "We couldn't load the dataset validation status. Please try again.",
      });
    }
  }

  async function uploadRegisteredDataset(
    token: string,
    datasetId: string,
    file: File,
  ) {
    setUploadState({ status: "uploading" });

    try {
      const uploadedDataset = await uploadDatasetContent(
        token,
        workspaceId,
        projectId,
        datasetId,
        file,
      );

      setUploadState({
        status: "uploaded",
        datasetId: uploadedDataset.id,
      });

      await refreshValidationState(
        token,
        uploadedDataset.id,
      );
    } catch {
      setUploadState({
        status: "upload_error",
        datasetId,
        message: "We couldn't upload the dataset. Please try again.",
      });
    }
  }

  async function resumeInterruptedUpload() {
    if (
      !selectedFile
      || uploadState.status !== "interrupted"
    ) {
      return;
    }

    const token = window.localStorage.getItem(
      SESSION_TOKEN_KEY,
    );

    if (!token) {
      setUploadState({
        status: "error",
        message:
          "Your session is no longer available. Please sign in again.",
      });
      return;
    }

    await uploadRegisteredDataset(
      token,
      uploadState.datasetId,
      selectedFile,
    );
  }

  async function uploadSelectedFile() {
    if (!selectedFile || isUploadActive(uploadState)) {
      return;
    }

    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);

    if (!token) {
      setUploadState({
        status: "error",
        message: "Your session is no longer available. Please sign in again.",
      });
      return;
    }

    try {
      setUploadState({ status: "hashing" });

      const checksum = await sha256File(selectedFile);

      setUploadState({ status: "registering" });

      const dataset = await registerDataset(
        token,
        workspaceId,
        projectId,
        {
          source_filename: selectedFile.name,
          media_type: "text/csv",
          byte_size: selectedFile.size,
          checksum_sha256: checksum,
        },
      );

      window.sessionStorage.setItem(
        datasetUploadSessionKey(
          workspaceId,
          projectId,
        ),
        dataset.id,
      );

      await uploadRegisteredDataset(
        token,
        dataset.id,
        selectedFile,
      );
    } catch {
      setUploadState({
        status: "error",
        message: "We couldn't upload the dataset. Please try again.",
      });
    }
  }

  async function retryUpload() {
    if (
      !selectedFile
      || uploadState.status !== "upload_error"
    ) {
      return;
    }

    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);

    if (!token) {
      setUploadState({
        status: "error",
        message: "Your session is no longer available. Please sign in again.",
      });
      return;
    }

    await uploadRegisteredDataset(
      token,
      uploadState.datasetId,
      selectedFile,
    );
  }

  useEffect(() => {
    if (validationState.status === "failed") {
      validationFailureRef.current?.focus();
      return;
    }

    if (validationState.status === "ready") {
      validationSuccessRef.current?.focus();
    }
  }, [validationState.status]);

  function resetForCorrectedFile() {
    window.sessionStorage.removeItem(
      datasetUploadSessionKey(
        workspaceId,
        projectId,
      ),
    );

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    setSelectedFile(null);
    setSelectionError(null);
    setUploadState({ status: "idle" });
    setValidationState({ status: "idle" });
  }

  function selectFile(file: File | null) {
    if (!file) {
      setSelectedFile(null);
      setSelectionError(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setSelectedFile(null);
      setSelectionError("Choose a CSV file.");
      return;
    }

    if (file.size === 0) {
      setSelectedFile(null);
      setSelectionError("Choose a non-empty CSV file.");
      return;
    }

    if (file.size > DATASET_MAX_UPLOAD_BYTES) {
      setSelectedFile(null);
      setSelectionError(
        "File exceeds the 1 GB upload limit.",
      );
      return;
    }

    setSelectionError(null);
    setSelectedFile(file);
  }

  return (
    <section
      className="dataset-upload-shell"
      aria-labelledby="dataset-upload-heading"
      data-workspace-id={workspaceId}
      data-project-id={projectId}
    >
      <header className="dataset-upload-header">
        <div>
          <p className="dataset-upload-context">Dataset setup</p>
          <h1 id="dataset-upload-heading">Upload Dataset</h1>
          <p className="dataset-upload-intro">
            Add the source data for this measurement project. We will verify
            the file before it can be mapped or analyzed.
          </p>
        </div>

        <div
          className="dataset-upload-requirements"
          role="group"
          aria-label="Upload requirements"
        >
          <span>
            <FileCsvIcon size={17} weight="duotone" aria-hidden="true" />
            CSV only
          </span>
          <span>Up to 1 GB</span>
        </div>
      </header>

      <div className="dataset-upload-card">
        <div
          className="dataset-upload-dropzone"
          role="button"
          tabIndex={0}
          aria-label="Drop CSV file here"
          data-drag-active={dragActive}
          onKeyDown={(event) => {
            if (
              event.key === "Enter"
              || event.key === " "
            ) {
              event.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setDragActive(false);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setDragActive(true);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setDragActive(false);
            selectFile(event.dataTransfer.files?.[0] ?? null);
          }}
        >
          <span className="dataset-upload-icon" aria-hidden="true">
            <CloudArrowUpIcon size={32} weight="duotone" />
          </span>
          <h2>{dragActive ? "Release to add your CSV" : "Drop your CSV here"}</h2>
          <p>One file at a time. You can replace it before uploading.</p>
        </div>

        <div className="dataset-upload-picker-row">
          <span aria-hidden="true" />
          <small>or</small>
          <span aria-hidden="true" />
        </div>

        <button
          className="dataset-upload-picker"
          type="button"
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadSimpleIcon size={18} aria-hidden="true" />
          Browse files
        </button>

        <input
          ref={fileInputRef}
          className="dataset-upload-native-input"
          type="file"
          accept=".csv,text/csv"
          aria-label="Choose CSV file"
          onChange={(event) => {
            selectFile(event.target.files?.[0] ?? null);
          }}
        />

        <p className="dataset-upload-assurance">
          <ShieldCheckIcon size={16} weight="fill" aria-hidden="true" />
          The file stays scoped to this project and workspace.
        </p>
      </div>

      <div className="dataset-upload-legacy-requirements">
        <p>Supported format: CSV</p>
        <p>Maximum file size: 1 GB</p>
      </div>

      {selectionError && (
        <div
          className="dataset-upload-feedback dataset-upload-feedback-error"
          role="alert"
        >
          <WarningCircleIcon size={20} weight="fill" aria-hidden="true" />
          <div>
            <strong>File not selected</strong>
            <p>{selectionError}</p>
          </div>
        </div>
      )}

      {selectedFile && (
        <div
          className="dataset-upload-selection"
          role="region"
          aria-label="Selected CSV file"
        >
          <span className="dataset-upload-file-icon" aria-hidden="true">
            <FileCsvIcon size={24} weight="duotone" />
          </span>
          <div className="dataset-upload-file-copy">
            <strong>{selectedFile.name}</strong>
            <span>{selectedFile.size} bytes</span>
          </div>

          <div className="dataset-upload-file-actions">
            <button
              className="dataset-upload-remove"
              type="button"
              onClick={() => selectFile(null)}
              disabled={isUploadActive(uploadState)}
            >
              <XIcon size={16} aria-hidden="true" />
              Remove selected file
            </button>

            <button
              className="dataset-upload-primary"
              type="button"
              onClick={() => void uploadSelectedFile()}
              disabled={isUploadActive(uploadState)}
            >
              Upload Dataset
              <ArrowRightIcon size={17} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {isUploadActive(uploadState) && (
        <div className="dataset-upload-activity">
          <SpinnerGapIcon
            className="dataset-upload-spinner"
            size={20}
            aria-hidden="true"
          />
          <p role="status">
            {uploadState.status === "hashing"
              ? "Preparing dataset…"
              : uploadState.status === "registering"
                ? "Initializing upload…"
                : "Uploading dataset…"}
          </p>

          {uploadState.status === "uploading" && (
            <progress
              className="dataset-upload-progress"
              aria-label="Dataset upload in progress"
            />
          )}
        </div>
      )}

      {uploadState.status === "uploaded"
        && validationState.status !== "interrupted" && (
        <p className="dataset-upload-status" role="status">
          <CheckCircleIcon size={18} weight="fill" aria-hidden="true" />
          Upload complete
        </p>
      )}

      {validationState.status === "loading" && (
        <p className="dataset-upload-status" role="status">
          <SpinnerGapIcon className="dataset-upload-spinner" size={18} aria-hidden="true" />
          Checking validation status…
        </p>
      )}

      {validationState.status === "interrupted" && (
        <div className="dataset-upload-feedback dataset-upload-feedback-warning" role="status">
          <WarningCircleIcon size={20} weight="fill" aria-hidden="true" />
          <div>
          <strong>Upload interrupted</strong>
          <p>
            Reselect the CSV file to continue uploading.
          </p>

          {selectedFile && (
            <button
              type="button"
              onClick={() => {
                void resumeInterruptedUpload();
              }}
              disabled={isUploadActive(uploadState)}
            >
              Resume Upload
            </button>
          )}
          </div>
        </div>
      )}

      {validationState.status === "pending" && (
        <p className="dataset-upload-status" role="status">
          <SpinnerGapIcon className="dataset-upload-spinner" size={18} aria-hidden="true" />
          Validation pending…
        </p>
      )}

      {validationState.status === "validating" && (
        <p className="dataset-upload-status" role="status">
          <SpinnerGapIcon className="dataset-upload-spinner" size={18} aria-hidden="true" />
          Validating dataset…
        </p>
      )}

      {validationState.status === "ready"
        && uploadState.status === "uploaded" && (
        <div
          className="dataset-upload-result dataset-upload-result-success"
          ref={validationSuccessRef}
          role="region"
          aria-label="Dataset validation result"
          tabIndex={-1}
        >
          <CheckCircleIcon size={24} weight="fill" aria-hidden="true" />
          <div>
            <strong>Dataset ready</strong>

          {validationState.rowCount !== null && (
            <p>{validationState.rowCount} rows</p>
          )}

          {validationState.columnCount !== null && (
            <p>{validationState.columnCount} columns</p>
          )}
          </div>

          <Link
            href={datasetExplorePath(
              workspaceId,
              projectId,
              uploadState.datasetId,
            )}
          >
            Explore Dataset
            <ArrowRightIcon size={17} aria-hidden="true" />
          </Link>
        </div>
      )}

      {validationState.status === "failed" && (
        <div className="dataset-upload-result-stack">
          <div
            className="dataset-upload-feedback dataset-upload-feedback-error"
            ref={validationFailureRef}
            role="alert"
            tabIndex={-1}
          >
            <WarningCircleIcon size={20} weight="fill" aria-hidden="true" />
            <div>
              <strong>Dataset validation failed</strong>
              <p>{validationState.message}</p>
            </div>
          </div>

          <button
            className="dataset-upload-secondary"
            type="button"
            onClick={resetForCorrectedFile}
          >
            Upload corrected file
          </button>
        </div>
      )}

      {validationState.status === "error" && (
        <div className="dataset-upload-feedback dataset-upload-feedback-error" role="alert">
          <WarningCircleIcon size={20} weight="fill" aria-hidden="true" />
          <div>
            <strong>Validation status unavailable</strong>
            <p>{validationState.message}</p>
          </div>
        </div>
      )}

      {(uploadState.status === "error"
        || uploadState.status === "upload_error") && (
        <div className="dataset-upload-result-stack">
          <div className="dataset-upload-feedback dataset-upload-feedback-error" role="alert">
            <WarningCircleIcon size={20} weight="fill" aria-hidden="true" />
            <div>
              <strong>Upload not completed</strong>
              <p>{uploadState.message}</p>
            </div>
          </div>

          {uploadState.status === "upload_error" && (
            <button
              className="dataset-upload-secondary"
              type="button"
              onClick={() => void retryUpload()}
            >
              Retry Upload
            </button>
          )}
        </div>
      )}
    </section>
  );
}
