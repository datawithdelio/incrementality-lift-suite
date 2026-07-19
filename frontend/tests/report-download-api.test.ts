import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  downloadReport,
} from "../src/lib/data-products/api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe(
  "report download API",
  () => {
    it(
      "requests the exact run-scoped download with bearer authorization",
      async () => {
        const blob = new Blob(
          ["report"],
          {
            type: "application/pdf",
          },
        );

        const fetchMock = vi.fn(
          async () =>
            new Response(
              blob,
              {
                status: 200,
                headers: {
                  "Content-Type":
                    "application/pdf",
                  "Content-Disposition":
                    'attachment; filename="analysis-report-v2.pdf"',
                },
              },
            ),
        );

        vi.stubGlobal(
          "fetch",
          fetchMock,
        );

        const result =
          await downloadReport(
            "workspace-1",
            "project-1",
            "run-1",
            "report-1",
            "session-token",
          );

        expect(
          fetchMock,
        ).toHaveBeenCalledWith(
          "/api/v1/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/reports/report-1/download",
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization:
                "Bearer session-token",
            }),
            cache: "no-store",
          }),
        );

        expect(
          result.blob.type,
        ).toBe(
          "application/pdf",
        );

        expect(
          result.filename,
        ).toBe(
          "analysis-report-v2.pdf",
        );
      },
    );
  },
);
