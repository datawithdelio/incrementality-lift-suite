import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const sha256File = vi.fn();
const getDataset = vi.fn();
const registerDataset = vi.fn();
const uploadDatasetContent = vi.fn();

vi.mock("../src/lib/datasets/checksum", () => ({
  sha256File: (...args: unknown[]) => sha256File(...args),
}));

vi.mock("../src/lib/datasets/api", () => ({
  getDataset: (...args: unknown[]) => getDataset(...args),
  registerDataset: (...args: unknown[]) => registerDataset(...args),
  uploadDatasetContent: (...args: unknown[]) => uploadDatasetContent(...args),
}));

import { DatasetUpload } from "../src/components/datasets/dataset-upload";


beforeEach(() => {
  localStorage.setItem(
    "incrementality_session_token",
    "session-token",
  );

  sha256File.mockResolvedValue("a".repeat(64));

  getDataset.mockResolvedValue({
    id: "dataset-1",
    status: "uploaded",
    row_count: null,
    column_count: null,
    failure_reason: null,
  });

  registerDataset.mockResolvedValue({
    id: "dataset-1",
    workspace_id: "workspace-1",
    project_id: "project-1",
    created_by_user_id: "user-1",
    source_filename: "campaign-results.csv",
    storage_key: "private-storage-key",
    media_type: "text/csv",
    byte_size: 30,
    checksum_sha256: "a".repeat(64),
    status: "pending_upload",
    created_at: "2026-07-18T12:00:00Z",
    uploaded_at: null,
    validation_started_at: null,
    validation_completed_at: null,
    row_count: null,
    column_count: null,
    failure_reason: null,
  });

  uploadDatasetContent.mockResolvedValue({
    id: "dataset-1",
    workspace_id: "workspace-1",
    project_id: "project-1",
    created_by_user_id: "user-1",
    source_filename: "campaign-results.csv",
    storage_key: "private-storage-key",
    media_type: "text/csv",
    byte_size: 30,
    checksum_sha256: "a".repeat(64),
    status: "uploaded",
    created_at: "2026-07-18T12:00:00Z",
    uploaded_at: "2026-07-18T12:01:00Z",
    validation_started_at: null,
    validation_completed_at: null,
    row_count: null,
    column_count: null,
    failure_reason: null,
  });
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
  vi.clearAllMocks();
});

describe("dataset upload experience", () => {
  it("lets a user select a CSV file and shows its real filename and size", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const input = screen.getByLabelText("Choose CSV file");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute("accept", ".csv,text/csv");

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(input, {
      target: { files: [file] },
    });

    expect(
      screen.getByText("campaign-results.csv"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(`${file.size} bytes`),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Remove selected file" }),
    ).toBeEnabled();
  });

  it("accepts a CSV file through the keyboard-accessible drop area", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const dropArea = screen.getByRole("button", {
      name: "Drop CSV file here",
    });

    expect(dropArea).toHaveAttribute("tabindex", "0");

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "dropped-results.csv",
      { type: "text/csv" },
    );

    fireEvent.drop(dropArea, {
      dataTransfer: {
        files: [file],
      },
    });

    expect(
      screen.getByText("dropped-results.csv"),
    ).toBeInTheDocument();
  });

  it("shows focused drag feedback without changing the upload behavior", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const dropArea = screen.getByRole("button", {
      name: "Drop CSV file here",
    });

    expect(dropArea).toHaveAttribute(
      "data-drag-active",
      "false",
    );

    fireEvent.dragEnter(dropArea);

    expect(dropArea).toHaveAttribute(
      "data-drag-active",
      "true",
    );

    fireEvent.dragLeave(dropArea);

    expect(dropArea).toHaveAttribute(
      "data-drag-active",
      "false",
    );
  });

  it("presents a selected CSV as a clear review step", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      { target: { files: [file] } },
    );

    expect(
      screen.getByRole("region", {
        name: "Selected CSV file",
      }),
    ).toHaveTextContent(
      `campaign-results.csv${file.size} bytes`,
    );
  });


  it("rejects an unsupported file type before upload", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const input = screen.getByLabelText("Choose CSV file");

    const file = new File(
      ["not,a,csv"],
      "campaign-results.json",
      { type: "application/json" },
    );

    fireEvent.change(input, {
      target: { files: [file] },
    });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose a CSV file.",
    );

    expect(
      screen.queryByText("campaign-results.json"),
    ).not.toBeInTheDocument();
  });



  it("rejects an empty CSV file before upload", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const input = screen.getByLabelText("Choose CSV file");

    const file = new File(
      [],
      "empty.csv",
      { type: "text/csv" },
    );

    fireEvent.change(input, {
      target: { files: [file] },
    });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose a non-empty CSV file.",
    );

    expect(
      screen.queryByText("empty.csv"),
    ).not.toBeInTheDocument();
  });



  it("registers and uploads the selected CSV through the real backend lifecycle", async () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    await waitFor(() => {
      expect(sha256File).toHaveBeenCalledWith(file);
    });

    expect(registerDataset).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      {
        source_filename: "campaign-results.csv",
        media_type: "text/csv",
        byte_size: file.size,
        checksum_sha256: "a".repeat(64),
      },
    );

    expect(uploadDatasetContent).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
      file,
    );

    expect(
      await screen.findByText("Upload complete"),
    ).toBeInTheDocument();
  });



  it("prevents duplicate upload submission while an upload is active", async () => {
    let resolveChecksum: ((value: string) => void) | undefined;

    sha256File.mockImplementationOnce(
      () =>
        new Promise<string>((resolve) => {
          resolveChecksum = resolve;
        }),
    );

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    const uploadButton = screen.getByRole(
      "button",
      { name: "Upload Dataset" },
    );

    fireEvent.click(uploadButton);
    fireEvent.click(uploadButton);

    expect(uploadButton).toBeDisabled();
    expect(sha256File).toHaveBeenCalledTimes(1);
    expect(registerDataset).not.toHaveBeenCalled();

    resolveChecksum?.("a".repeat(64));

    await waitFor(() => {
      expect(registerDataset).toHaveBeenCalledTimes(1);
    });

    expect(uploadDatasetContent).toHaveBeenCalledTimes(1);
  });



  it("retries a failed content upload without registering a duplicate dataset", async () => {
    uploadDatasetContent.mockRejectedValueOnce(
      new Error("network disconnected"),
    );

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "We couldn't upload the dataset. Please try again.",
    );

    expect(registerDataset).toHaveBeenCalledTimes(1);
    expect(uploadDatasetContent).toHaveBeenCalledTimes(1);

    fireEvent.click(
      screen.getByRole("button", { name: "Retry Upload" }),
    );

    await waitFor(() => {
      expect(uploadDatasetContent).toHaveBeenCalledTimes(2);
    });

    expect(registerDataset).toHaveBeenCalledTimes(1);

    expect(
      await screen.findByText("Upload complete"),
    ).toBeInTheDocument();
  });


  it("reloads backend state after upload and shows validation in progress", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "validating",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText("Validating dataset…"),
    ).toBeInTheDocument();

    expect(getDataset).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );
  });


  it("shows the validated dataset summary and explorer action when ready", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "ready",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: "2026-07-18T12:03:00Z",
      row_count: 1537,
      column_count: 13,
      failure_reason: null,
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText("Dataset ready"),
    ).toBeInTheDocument();

    expect(screen.getByText("1537 rows")).toBeInTheDocument();
    expect(screen.getByText("13 columns")).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Explore Dataset" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/explore",
    );
  });


  it("shows backend validation failure separately from upload failure", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "failed",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: "2026-07-18T12:03:00Z",
      row_count: null,
      column_count: null,
      failure_reason: "CSV contains inconsistent column counts.",
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText("Dataset validation failed"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("CSV contains inconsistent column counts."),
    ).toBeInTheDocument();

    expect(
      screen.queryByText(
        "We couldn't upload the dataset. Please try again.",
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Upload corrected file" }),
    ).toBeEnabled();
  });


  it("keeps polling backend validation state until the dataset is ready", async () => {
    getDataset
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "validating",
        row_count: null,
        column_count: null,
        failure_reason: null,
      })
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "ready",
        row_count: 1537,
        column_count: 13,
        failure_reason: null,
      });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText("Validating dataset…"),
    ).toBeInTheDocument();

    await waitFor(
      () => {
        expect(getDataset).toHaveBeenCalledTimes(2);
      },
      { timeout: 2000 },
    );

    expect(
      await screen.findByText("Dataset ready"),
    ).toBeInTheDocument();

    expect(screen.getByText("1537 rows")).toBeInTheDocument();
    expect(screen.getByText("13 columns")).toBeInTheDocument();
  });


  it("restores backend validation state after the upload page is refreshed", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "validating",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
        initialDatasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByText("Validating dataset…"),
    ).toBeInTheDocument();

    expect(getDataset).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );

    expect(registerDataset).not.toHaveBeenCalled();
    expect(uploadDatasetContent).not.toHaveBeenCalled();
  });


  it("restores the scoped registered dataset from session storage after refresh", async () => {
    const firstRender = render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    await waitFor(() => {
      expect(registerDataset).toHaveBeenCalledTimes(1);
    });

    firstRender.unmount();

    vi.clearAllMocks();

    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "validating",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Validating dataset…"),
    ).toBeInTheDocument();

    expect(getDataset).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );

    expect(registerDataset).not.toHaveBeenCalled();
    expect(uploadDatasetContent).not.toHaveBeenCalled();
  });


  it("rejects a CSV that exceeds the backend upload size limit", async () => {
    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "too-large.csv",
      { type: "text/csv" },
    );

    Object.defineProperty(file, "size", {
      value: 1_073_741_825,
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    expect(
      await screen.findByText(
        "File exceeds the 1 GB upload limit.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("button", { name: "Upload Dataset" }),
    ).not.toBeInTheDocument();

    expect(sha256File).not.toHaveBeenCalled();
    expect(registerDataset).not.toHaveBeenCalled();
    expect(uploadDatasetContent).not.toHaveBeenCalled();
  });


  it("opens the file picker when the drop zone is activated from the keyboard", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const fileInput = screen.getByLabelText(
      "Choose CSV file",
    );

    const clickSpy = vi.spyOn(
      fileInput,
      "click",
    );

    fireEvent.keyDown(
      screen.getByRole(
        "button",
        { name: "Drop CSV file here" },
      ),
      { key: "Enter" },
    );

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });


  it("shows honest indeterminate progress while dataset content is uploading", async () => {
    let resolveUpload: (() => void) | undefined;

    uploadDatasetContent.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveUpload = resolve;
        }),
    );

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    const progress = await screen.findByRole(
      "progressbar",
      { name: "Dataset upload in progress" },
    );

    expect(progress).not.toHaveAttribute("value");
    expect(
      screen.getByText("Uploading dataset…"),
    ).toBeInTheDocument();

    resolveUpload?.();
  });


  it("clears stale dataset state when switching to another project", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "ready",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: "2026-07-18T12:03:00Z",
      row_count: 1537,
      column_count: 13,
      failure_reason: null,
    });

    const { rerender } = render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
        initialDatasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByText("Dataset ready"),
    ).toBeInTheDocument();

    rerender(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-2"
      />,
    );

    await waitFor(() => {
      expect(
        screen.queryByText("Dataset ready"),
      ).not.toBeInTheDocument();
    });

    expect(
      screen.getByLabelText("Choose CSV file"),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("link", { name: "Explore Dataset" }),
    ).not.toBeInTheDocument();
  });


  it("registers a new dataset when uploading a corrected file after validation failure", async () => {
    registerDataset
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "pending_upload",
      })
      .mockResolvedValueOnce({
        id: "dataset-2",
        status: "pending_upload",
      });

    getDataset
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "failed",
        row_count: null,
        column_count: null,
        failure_reason: "Missing required date column.",
      })
      .mockResolvedValueOnce({
        id: "dataset-2",
        status: "ready",
        row_count: 100,
        column_count: 4,
        failure_reason: null,
      });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const firstFile = new File(
      ["revenue\n100\n"],
      "invalid.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [firstFile] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText("Dataset validation failed"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Upload corrected file",
      }),
    );

    const correctedFile = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "corrected.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [correctedFile] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    await waitFor(() => {
      expect(registerDataset).toHaveBeenCalledTimes(2);
    });

    expect(
      registerDataset.mock.calls[0]?.[3],
    ).toMatchObject({
      source_filename: "invalid.csv",
    });

    expect(
      registerDataset.mock.calls[1]?.[3],
    ).toMatchObject({
      source_filename: "corrected.csv",
    });

    expect(
      await screen.findByText("Dataset ready"),
    ).toBeInTheDocument();

    expect(
      sessionStorage.getItem(
        "incrementality_dataset_upload:workspace-1:project-1",
      ),
    ).toBe("dataset-2");
  });


  it("clears the native file input when starting a corrected upload", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      status: "failed",
      row_count: null,
      column_count: null,
      failure_reason: "Missing required date column.",
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const fileInput = screen.getByLabelText(
      "Choose CSV file",
    ) as HTMLInputElement;

    const file = new File(
      ["revenue\n100\n"],
      "dataset.csv",
      { type: "text/csv" },
    );

    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    Object.defineProperty(fileInput, "value", {
      configurable: true,
      writable: true,
      value: "C:\\fakepath\\dataset.csv",
    });

    expect(fileInput.value).toBe(
      "C:\\fakepath\\dataset.csv",
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText("Dataset validation failed"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Upload corrected file",
      }),
    );

    expect(fileInput.value).toBe("");
  });


  it("shows the supported file format and maximum upload size", () => {
    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      screen.getByText("Supported format: CSV"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Maximum file size: 1 GB"),
    ).toBeInTheDocument();
  });


  it("moves focus to the validation failure result", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      status: "failed",
      row_count: null,
      column_count: null,
      failure_reason: "Missing required date column.",
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    const file = new File(
      ["revenue\n100\n"],
      "invalid.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    const failureResult = await screen.findByRole("alert");

    await waitFor(() => {
      expect(failureResult).toHaveFocus();
    });
  });


  it("moves focus to the validated dataset result", async () => {
    getDataset.mockResolvedValueOnce({
      id: "dataset-1",
      status: "ready",
      row_count: 1537,
      column_count: 13,
      failure_reason: null,
    });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
        initialDatasetId="dataset-1"
      />,
    );

    const successResult = await screen.findByRole(
      "region",
      { name: "Dataset validation result" },
    );

    await waitFor(() => {
      expect(successResult).toHaveFocus();
    });
  });


  it("reselects a file to continue an interrupted pending upload without creating a new dataset", async () => {
    sessionStorage.setItem(
      "incrementality_dataset_upload:workspace-1:project-1",
      "dataset-1",
    );

    getDataset
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "pending_upload",
        row_count: null,
        column_count: null,
        failure_reason: null,
      })
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "ready",
        row_count: 100,
        column_count: 4,
        failure_reason: null,
      });

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Upload interrupted"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Reselect the CSV file to continue uploading.",
      ),
    ).toBeInTheDocument();

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Resume Upload",
      }),
    );

    await waitFor(() => {
      expect(uploadDatasetContent).toHaveBeenCalledWith(
        "session-token",
        "workspace-1",
        "project-1",
        "dataset-1",
        file,
      );
    });

    expect(registerDataset).not.toHaveBeenCalled();

    expect(
      await screen.findByText("Dataset ready"),
    ).toBeInTheDocument();
  });

  it("resumes an interrupted upload after a duplicate registration attempt fails", async () => {
    sessionStorage.setItem(
      "incrementality_dataset_upload:workspace-1:project-1",
      "dataset-1",
    );

    getDataset
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "pending_upload",
        row_count: null,
        column_count: null,
        failure_reason: null,
      })
      .mockResolvedValueOnce({
        id: "dataset-1",
        status: "ready",
        row_count: 100,
        column_count: 4,
        failure_reason: null,
      });
    registerDataset.mockRejectedValueOnce(
      new Error("Dataset already exists."),
    );

    render(
      <DatasetUpload
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Upload interrupted"),
    ).toBeInTheDocument();

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    fireEvent.change(
      screen.getByLabelText("Choose CSV file"),
      {
        target: { files: [file] },
      },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Upload Dataset" }),
    );

    expect(
      await screen.findByText(
        "We couldn't upload the dataset. Please try again.",
      ),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Resume Upload" }),
    );

    await waitFor(() => {
      expect(uploadDatasetContent).toHaveBeenCalledWith(
        "session-token",
        "workspace-1",
        "project-1",
        "dataset-1",
        file,
      );
    });
  });

});
