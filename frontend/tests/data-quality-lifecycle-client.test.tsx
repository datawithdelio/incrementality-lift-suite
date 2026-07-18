import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { useDataQuality } = vi.hoisted(() => ({
  useDataQuality: vi.fn(),
}));

vi.mock(
  "../src/lib/data-products/use-data-products",
  () => ({
    useDataQuality,
  }),
);

import { DataQualityClient } from "../src/components/data-products/data-quality-client";

afterEach(() => {
  cleanup();
  useDataQuality.mockReset();
});

describe("DataQualityClient dataset lifecycle", () => {
  it("shows validation-in-progress state", () => {
    useDataQuality.mockReturnValue({
      state: {
        kind: "loading",
      },
      dataset: {
        status: "validating",
        failure_reason: null,
      },
    });

    render(
      <DataQualityClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Validation in progress",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Data-quality results will be available when validation finishes.",
      ),
    ).toBeInTheDocument();
  });

  it("shows the real backend validation failure reason", () => {
    useDataQuality.mockReturnValue({
      state: {
        kind: "loading",
      },
      dataset: {
        status: "failed",
        failure_reason:
          "The uploaded CSV has inconsistent column counts.",
      },
    });

    render(
      <DataQualityClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Dataset validation failed",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "The uploaded CSV has inconsistent column counts.",
      ),
    ).toBeInTheDocument();
  });
});

describe("DataQualityClient pre-validation lifecycle", () => {
  it("shows an honest pending-upload state", () => {
    useDataQuality.mockReturnValue({
      state: {
        kind: "loading",
      },
      dataset: {
        status: "pending_upload",
        failure_reason: null,
      },
    });

    render(
      <DataQualityClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Dataset upload is not complete",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Complete the dataset upload before data-quality validation can begin.",
      ),
    ).toBeInTheDocument();
  });

  it("shows an honest validation-pending state", () => {
    useDataQuality.mockReturnValue({
      state: {
        kind: "loading",
      },
      dataset: {
        status: "uploaded",
        failure_reason: null,
      },
    });

    render(
      <DataQualityClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Validation is pending",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "The upload is complete and is waiting for backend validation to begin.",
      ),
    ).toBeInTheDocument();
  });
});
