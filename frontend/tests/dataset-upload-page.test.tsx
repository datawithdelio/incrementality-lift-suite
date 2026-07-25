import {
  cleanup,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import UploadDatasetPage from "../src/app/workspaces/[workspaceId]/projects/[projectId]/datasets/upload/page";

afterEach(() => {
  cleanup();
});

describe("dataset upload page", () => {
  it("renders the scoped dataset upload experience", async () => {
    const page = await UploadDatasetPage({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        projectId: "project-1",
      }),
    });

    render(page);

    expect(
      screen.getByRole("heading", { name: "Upload Dataset" }),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Choose CSV file"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Browse files" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("group", { name: "Upload requirements" }),
    ).toHaveTextContent("CSV onlyUp to 1 GB");
  });
});
