import { describe, expect, it } from "vitest";

import { sha256File } from "../src/lib/datasets/checksum";

describe("dataset checksum", () => {
  it("computes the SHA-256 checksum required by dataset registration", async () => {
    const file = new File(
      ["hello"],
      "dataset.csv",
      { type: "text/csv" },
    );

    const checksum = await sha256File(file);

    expect(checksum).toBe(
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    );
  });
});
