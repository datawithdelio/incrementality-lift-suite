import {
  render,
  screen,
} from "@testing-library/react";
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

import MembersAccessPage from "@/app/workspaces/[workspaceId]/members/page";

vi.mock(
  "@/components/settings/members-access",
  () => ({
    MembersAccess: ({
      workspaceId,
    }: {
      workspaceId: string;
    }) => (
      <div>
        Members and access for {workspaceId}
      </div>
    ),
  }),
);

describe("Members & Access page", () => {
  it("preserves workspace scope from the route", async () => {
    const page = await MembersAccessPage({
      params: Promise.resolve({
        workspaceId: "workspace-1",
      }),
    });

    render(page);

    expect(
      screen.getByText(
        "Members and access for workspace-1",
      ),
    ).toBeInTheDocument();
  });
});
