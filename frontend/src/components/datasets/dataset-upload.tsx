"use client";

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
      aria-labelledby="dataset-upload-heading"
      data-workspace-id={workspaceId}
      data-project-id={projectId}
    >
      <h1 id="dataset-upload-heading">Upload Dataset</h1>

      <div>
        <p>Supported format: CSV</p>
        <p>Maximum file size: 1 GB</p>
      </div>

      <div
        role="button"
        tabIndex={0}
        aria-label="Drop CSV file here"
        onKeyDown={(event) => {
          if (
            event.key === "Enter"
            || event.key === " "
          ) {
            event.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
        }}
        onDrop={(event) => {
          event.preventDefault();
          selectFile(event.dataTransfer.files?.[0] ?? null);
        }}
      >
        <p>Drag and drop your CSV file here</p>
      </div>

      <p>or</p>

      <label>
        <span>Choose CSV file</span>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          aria-label="Choose CSV file"
          onChange={(event) => {
            selectFile(event.target.files?.[0] ?? null);
          }}
        />
      </label>

      {selectionError && (
        <p role="alert">{selectionError}</p>
      )}

      {selectedFile && (
        <div>
          <p>{selectedFile.name}</p>
          <p>{selectedFile.size} bytes</p>

          <button
            type="button"
            onClick={() => selectFile(null)}
            disabled={isUploadActive(uploadState)}
          >
            Remove selected file
          </button>

          <button
            type="button"
            onClick={() => void uploadSelectedFile()}
            disabled={isUploadActive(uploadState)}
          >
            Upload Dataset
          </button>
        </div>
      )}

      {isUploadActive(uploadState) && (
        <div>
          <p role="status">
            {uploadState.status === "hashing"
              ? "Preparing dataset…"
              : uploadState.status === "registering"
                ? "Initializing upload…"
                : "Uploading dataset…"}
          </p>

          {uploadState.status === "uploading" && (
            <progress
              aria-label="Dataset upload in progress"
            />
          )}
        </div>
      )}

      {uploadState.status === "uploaded"
        && validationState.status !== "interrupted" && (
        <p role="status">Upload complete</p>
      )}

      {validationState.status === "loading" && (
        <p role="status">Checking validation status…</p>
      )}

      {validationState.status === "interrupted" && (
        <div role="status">
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
      )}

      {validationState.status === "pending" && (
        <p role="status">Validation pending…</p>
      )}

      {validationState.status === "validating" && (
        <p role="status">Validating dataset…</p>
      )}

      {validationState.status === "ready"
        && uploadState.status === "uploaded" && (
        <div
          ref={validationSuccessRef}
          role="region"
          aria-label="Dataset validation result"
          tabIndex={-1}
        >
          <strong>Dataset ready</strong>

          {validationState.rowCount !== null && (
            <p>{validationState.rowCount} rows</p>
          )}

          {validationState.columnCount !== null && (
            <p>{validationState.columnCount} columns</p>
          )}

          <Link
            href={datasetExplorePath(
              workspaceId,
              projectId,
              uploadState.datasetId,
            )}
          >
            Explore Dataset
          </Link>
        </div>
      )}

      {validationState.status === "failed" && (
        <div>
          <div
            ref={validationFailureRef}
            role="alert"
            tabIndex={-1}
          >
            <strong>Dataset validation failed</strong>
            <p>{validationState.message}</p>
          </div>

          <button
            type="button"
            onClick={resetForCorrectedFile}
          >
            Upload corrected file
          </button>
        </div>
      )}

      {validationState.status === "error" && (
        <p role="alert">{validationState.message}</p>
      )}

      {(uploadState.status === "error"
        || uploadState.status === "upload_error") && (
        <div>
          <p role="alert">{uploadState.message}</p>

          {uploadState.status === "upload_error" && (
            <button
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
