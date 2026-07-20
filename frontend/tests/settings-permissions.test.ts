import {
  describe,
  expect,
  it,
} from "vitest";

import {
  canManageMembers,
  canManageProjects,
  canManageWorkspace,
} from "@/lib/settings/permissions";

describe("settings permission helpers", () => {
  describe("canManageProjects", () => {
    it.each([
      "owner",
      "admin",
      "analyst",
    ])(
      "allows %s to manage projects",
      (role) => {
        expect(
          canManageProjects(role),
        ).toBe(true);
      },
    );

    it("keeps viewers read-only", () => {
      expect(
        canManageProjects("viewer"),
      ).toBe(false);
    });
  });

  describe("canManageWorkspace", () => {
    it.each([
      "owner",
      "admin",
    ])(
      "allows %s according to the backend permission policy",
      (role) => {
        expect(
          canManageWorkspace(role),
        ).toBe(true);
      },
    );

    it.each([
      "analyst",
      "viewer",
    ])(
      "denies %s workspace management",
      (role) => {
        expect(
          canManageWorkspace(role),
        ).toBe(false);
      },
    );
  });

  describe("canManageMembers", () => {
    it.each([
      "owner",
      "admin",
    ])(
      "allows %s according to the backend permission policy",
      (role) => {
        expect(
          canManageMembers(role),
        ).toBe(true);
      },
    );

    it.each([
      "analyst",
      "viewer",
    ])(
      "denies %s member management",
      (role) => {
        expect(
          canManageMembers(role),
        ).toBe(false);
      },
    );
  });

  it("fails closed for unknown roles", () => {
    expect(
      canManageProjects("super-admin"),
    ).toBe(false);

    expect(
      canManageWorkspace("super-admin"),
    ).toBe(false);

    expect(
      canManageMembers("super-admin"),
    ).toBe(false);
  });
});
